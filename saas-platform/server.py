import asyncio
import base64
import json
import os

import time
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pymongo import MongoClient

# Load .env from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()

# Enable CORS for SaaS (allow any origin to use the widget)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the widget library and assets
app.mount("/cdn", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public")), name="cdn")

# Serve the dashboard files
app.mount("/dashboard", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "dashboard")), name="dashboard")

# MongoDB Setup
MONGODB_URI = os.environ.get("MONGODB_URI")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client.get_database("ham_db")
stores_col = db.get_collection("stores")
clients_col = db.get_collection("clients")

def get_store_config(api_key):
    return stores_col.find_one({"_id": api_key})

def save_store_config(api_key, config):
    config["_id"] = api_key
    stores_col.replace_one({"_id": api_key}, config, upsert=True)

@app.post("/api/save-config")
async def save_config(config: dict):
    api_key = config.get("apiKey")
    save_store_config(api_key, config)
    return {"status": "success", "apiKey": api_key}

@app.get("/api/get-config/{api_key}")
async def get_config(api_key: str):
    config = get_store_config(api_key)
    return config or {}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    start_time = time.time()
    api_key = "unknown"

    # The first message from the client must be the setup configuration
    try:
        setup_data = await ws.receive_text()
        print(f"Setup data received: {setup_data}")
        config_payload = json.loads(setup_data)
        
        if config_payload.get("type") != "setup":
            await ws.close(code=1003, reason="First message must be 'setup'")
            return
        
        api_key = config_payload.get("apiKey")
        print(f"DEBUG: Received apiKey from widget: '{api_key}'")
        
        # Look up store settings in MongoDB
        store_settings = get_store_config(api_key)
        
        if store_settings:
            print(f"DEBUG: Match found in MongoDB for {api_key}")
            # Check if service is active
            if store_settings.get("status") == "inactive":
                print(f"DEBUG: REJECTED - Service inactive for {api_key}")
                await ws.send_json({"type": "error", "message": "Service suspended. Please contact support."})
                await ws.close(code=1008)
                return
        else:
            print(f"DEBUG: NO MATCH in stores.json for {api_key}. Using settings from payload.")
            store_settings = config_payload.get("settings", {})

        from utils import format_catalog_from_file, ANTI_GRAVITY_PROMPT_TEMPLATE
        
        system_instruction = store_settings.get("system_instruction", "You are a helpful assistant.")
        csv_path = store_settings.get("csv_path")
        
        print(f"DEBUG: Looking for catalog at {csv_path} for apiKey {api_key}")
        
        if csv_path and os.path.exists(csv_path):
            catalog_text = format_catalog_from_file(csv_path)
            company_name = store_settings.get("companyName", "notre boutique")
            system_instruction = ANTI_GRAVITY_PROMPT_TEMPLATE.replace("{CATALOG_PLACEHOLDER}", catalog_text).replace("{COMPANY_NAME}", company_name)
            print(f"DEBUG: SUCCESS - Injected CSV catalog and company name '{company_name}' for store: {api_key}")
        else:
            print(f"DEBUG: WARNING - CSV NOT FOUND or NOT PROVIDED for {api_key}. Using fallback instruction.")

        tools_schema = store_settings.get("tools", [])
        
        print(f"DEBUG: Final System Instruction Length: {len(system_instruction)}")
        # print(f"DEBUG: First 100 chars: {system_instruction[:100]}...")
        
    except Exception as e:
        print(f"Setup error: {e}")
        await ws.close(code=1003, reason="Invalid setup payload")
        return

    api_key_env = os.environ.get("GOOGLE_API_KEY")
    print(f"API Key loaded: {api_key_env[:10]}...")
    client = genai.Client(api_key=api_key_env)

    # Build the tools list from the schema provided by the client
    gemini_tools = []
    if tools_schema:
        gemini_tools.append(types.Tool(function_declarations=tools_schema))

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_instruction,
        tools=gemini_tools,
        speech_config=types.SpeechConfig(
            language_code="ar-MA",  # Default to Moroccan Arabic, can be made dynamic
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=config,
        ) as session:
            await ws.send_json({
            "type": "status", 
            "message": "Connected to Gemini SaaS Engine",
            "companyName": store_settings.get("companyName"),
            "whatsapp": store_settings.get("whatsapp", "212600000000")
        })

            async def browser_to_gemini():
                try:
                    while True:
                        data = await ws.receive_text()
                        msg = json.loads(data)

                        if msg["type"] == "audio":
                            audio_bytes = base64.b64decode(msg["data"])
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=audio_bytes,
                                    mime_type="audio/pcm;rate=16000",
                                ),
                            )
                except WebSocketDisconnect:
                    pass

            async def gemini_to_browser():
                try:
                    while True:
                        async for message in session.receive():
                            # Handle tool calls
                            if message.tool_call:
                                function_responses = []
                                for call in message.tool_call.function_calls:
                                    # Forward the tool call to the frontend widget
                                    await ws.send_json({
                                        "type": "action",
                                        "name": call.name,
                                        "args": call.args
                                    })
                                    
                                    # Return a generic success to Gemini
                                    # In a real SaaS, you might want to wait for the frontend to confirm
                                    function_responses.append(
                                        types.FunctionResponse(
                                            name=call.name,
                                            id=call.id,
                                            response={"result": "success"}
                                        )
                                    )
                                
                                # Send response back to Gemini so it can continue talking
                                await session.send(input=types.LiveClientContent(
                                    tool_response=types.LiveClientToolResponse(
                                        function_responses=function_responses
                                    )
                                ))

                            # Handle audio response
                            if message.server_content and message.server_content.model_turn:
                                for part in message.server_content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                                        await ws.send_json({
                                            "type": "audio",
                                            "data": audio_b64,
                                        })

                            # Handle transcriptions
                            if message.server_content:
                                if message.server_content.input_transcription:
                                    text = message.server_content.input_transcription.text
                                    if text:
                                        await ws.send_json({"type": "input_transcript", "text": text})
                                if message.server_content.output_transcription:
                                    text = message.server_content.output_transcription.text
                                    if text:
                                        await ws.send_json({"type": "output_transcript", "text": text})

                                if message.server_content.turn_complete:
                                    await ws.send_json({"type": "turn_complete"})
                                if message.server_content.interrupted:
                                    await ws.send_json({"type": "interrupted"})

                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"Error in gemini_to_browser: {e}")
                    await ws.send_json({"type": "error", "message": str(e)})

            await asyncio.gather(
                browser_to_gemini(),
                gemini_to_browser(),
            )
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for {api_key}")
    except Exception as e:
        print(f"Session error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Calculate and record usage
        end_time = time.time()
        duration_minutes = (end_time - start_time) / 60.0
        
        if api_key != "unknown":
            print(f"DEBUG: Recording usage for {api_key}: {duration_minutes:.2f} minutes")
            try:
                # Update both collections to keep them in sync
                stores_col.update_one({"_id": api_key}, {"$inc": {"usageMinutes": duration_minutes}})
                clients_col.update_one({"_id": api_key}, {"$inc": {"usageMinutes": duration_minutes}})
            except Exception as mongo_err:
                print(f"ERROR: Failed to update usage in MongoDB: {mongo_err}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
