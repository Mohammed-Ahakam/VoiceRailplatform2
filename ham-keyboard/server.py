import asyncio
import base64
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google import genai
from google.genai import types

from utils import format_catalog_from_csv, get_latest_uploaded_csv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()

# --- System Prompt Template ---
PROMPT_TEMPLATE = """ROLE & PERSONNALITÉ
Tu es l'assistant commercial virtuel de Anti-Gravity. Ton but est d'aider les clients, de répondre à leurs questions sur les produits et de les pousser à l'achat. Tu es chaleureux, efficace et tu as un excellent sens du contact (style "commerçant marocain" moderne).

STRUCTURE DES DONNÉES (LECTURE DU CSV)
Le texte ci-dessous est extrait d'un fichier CSV. Chaque ligne représente un produit. Pour chaque produit, respecte la logique suivante :
- Name / Produit : Le nom officiel à utiliser.
- Price / Prix : Le montant à annoncer en Anglais (ex: "One hundred dollars").
- Description / Specs : Les caractéristiques techniques à traduire ou expliquer en Darija (sauf les termes techniques en Anglais).
- Stock : Si la valeur est "0", dis que le produit est temporairement en rupture de stock.

CATALOGUE DYNAMIQUE (DONNÉES CLIENT)
{CATALOG_PLACEHOLDER}

RÈGLES LINGUISTIQUES (STRICTES)
- Langue principale : Réponds EXCLUSIVEMENT en Darija marocaine.
- Interdictions : N'utilise JAMAIS l'Arabe Classique (Fusha) ni le Français pour tes phrases.
- Usage de l'Anglais : Utilise l'Anglais UNIQUEMENT pour les noms de produits, les spécifications techniques (ex: Carbon fiber, Torque, LED, Water-resistant) et les prix.
- Ton : Utilise des expressions comme "Mreba bik", "Ach hab l-khater", ou "Llah ybarek fik".

DIRECTIVES DE VENTE
- Concision : Tes réponses doivent être courtes (maximum 2 à 3 phrases).
- Analyse : Si le client pose une question vague, va chercher dans le catalogue le produit qui correspond le mieux aux mots-clés du client.
- Appel à l'action (Closing) : Dès qu'un client est intéressé, propose de finaliser : "Bghiti n-ajouter lik had l-produit l-panier ?".
- Livraison : Rappelle que la livraison est gratuite partout au Maroc.

GESTION DES LIMITES
- Si un produit n'est pas dans la liste, dis poliment en Darija que tu ne l'as pas pour le moment.
- Si la question est hors-sujet, redirige gentiment vers la vente de produits Anti-Gravity.
"""

# --- Tool Schemas ---
TOOLS = [
    {
        "name": "add_to_cart",
        "description": "Ajouter un produit au panier d'achat.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {"type": "STRING", "description": "Le nom du produit à ajouter."}
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "navigate_to_product",
        "description": "Afficher un produit spécifique à l'écran.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {"type": "STRING", "description": "Le nom du produit à afficher."}
            },
            "required": ["product_name"]
        }
    }
]

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "public", "index.html"))

app.mount("/css", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public", "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public", "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public", "assets")), name="assets")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Load dynamic catalog
    root_dir = os.path.join(os.path.dirname(__file__), "..")
    csv_path = get_latest_uploaded_csv(root_dir)
    if not csv_path:
        # Fallback to test catalog if nothing uploaded
        csv_path = os.path.join(root_dir, "test_catalog.csv")
    
    catalog_text = format_catalog_from_csv(csv_path)
    system_prompt = PROMPT_TEMPLATE.replace("{CATALOG_PLACEHOLDER}", catalog_text)
    
    print(f"Starting session with catalog from: {csv_path}")

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    gemini_tools = [types.Tool(function_declarations=TOOLS)]

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        tools=gemini_tools,
        speech_config=types.SpeechConfig(
            language_code="ar-MA",
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=config,
        ) as session:
            await ws.send_json({"type": "status", "message": "Connected to Anti-Gravity Agent"})

            async def browser_to_gemini():
                try:
                    while True:
                        data = await ws.receive_text()
                        msg = json.loads(data)
                        if msg["type"] == "audio":
                            audio_bytes = base64.b64decode(msg["data"])
                            await session.send_realtime_input(
                                audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
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
                                    print(f"Tool Call: {call.name}({call.args})")
                                    await ws.send_json({"type": "action", "name": call.name, "args": call.args})
                                    function_responses.append(
                                        types.FunctionResponse(name=call.name, id=call.id, response={"result": "success"})
                                    )
                                await session.send(input=types.LiveClientContent(
                                    tool_response=types.ToolResponse(function_responses=function_responses)
                                ))

                            # Handle audio response
                            if message.server_content and message.server_content.model_turn:
                                for part in message.server_content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                                        await ws.send_json({"type": "audio", "data": audio_b64})

                            # Handle transcriptions
                            if message.server_content:
                                if message.server_content.input_transcription:
                                    text = message.server_content.input_transcription.text
                                    if text: await ws.send_json({"type": "input_transcript", "text": text})
                                if message.server_content.output_transcription:
                                    text = message.server_content.output_transcription.text
                                    if text: await ws.send_json({"type": "output_transcript", "text": text})
                                if message.server_content.turn_complete:
                                    await ws.send_json({"type": "turn_complete"})
                                if message.server_content.interrupted:
                                    await ws.send_json({"type": "interrupted"})
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"Error: {e}")
                    await ws.send_json({"type": "error", "message": str(e)})

            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except Exception as e:
        print(f"Session error: {e}")
        try: await ws.send_json({"type": "error", "message": str(e)})
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
