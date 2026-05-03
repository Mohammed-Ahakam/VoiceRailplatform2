import os
import shutil
import json
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# MongoDB Setup
MONGODB_URI = os.environ.get("MONGODB_URI")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client.get_database("ham_db")
stores_col = db.get_collection("stores")
clients_col = db.get_collection("clients")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save uploaded catalogs
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve static files (HTML, CSS)
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__)), name="static")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/styles.css")
async def serve_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "styles.css"))

@app.get("/admin")
async def serve_admin():
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin", "index.html"))

@app.post("/api/submit-onboarding")
async def submit_onboarding(
    plan: str = Form(...),
    companyName: str = Form(...),
    industry: str = Form(...),
    whatsapp: str = Form(None),
    duration: str = Form(...),
    catalog: UploadFile = File(...)
):
    print(f"New Onboarding Request: {companyName} ({plan})")
    
    # Generate a unique API Key for the client
    generated_api_key = f"ham_{uuid.uuid4().hex[:8]}"
    
    # Create a company-specific folder
    company_folder_name = companyName.replace(" ", "_")
    company_dir = os.path.join(UPLOAD_DIR, company_folder_name)
    os.makedirs(company_dir, exist_ok=True)
    
    # Save the catalog file (preserve extension)
    file_extension = os.path.splitext(catalog.filename)[1]
    file_path = os.path.join(company_dir, f"catalog{file_extension}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(catalog.file, buffer)
        
    # Define tools based on plan
    tools = [{"name": "navigate_to_product", "description": "Voir le produit", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}}]
    
    if plan == "Pro Agentic":
        tools.append({"name": "add_to_cart", "description": "Ajouter au panier", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}})
        tools.append({"name": "checkout", "description": "Finaliser la commande et demander les infos client", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}})

    # Update SaaS MongoDB
    stores_payload = {
        "_id": generated_api_key,
        "apiKey": generated_api_key,
        "companyName": companyName,
        "whatsapp": whatsapp or "",
        "plan": plan,
        "duration": duration,
        "status": "active",
        "csv_path": file_path,
        "tools": tools
    }
    
    try:
        stores_col.replace_one({"_id": generated_api_key}, stores_payload, upsert=True)
        print(f"Successfully updated MongoDB stores with key: {generated_api_key}")
    except Exception as e:
        print(f"Error writing to MongoDB: {e}")

    # Record the new client in MongoDB
    import time
    client_payload = {
        "_id": generated_api_key,
        "apiKey": generated_api_key,
        "companyName": companyName,
        "industry": industry,
        "whatsapp": whatsapp,
        "plan": plan,
        "duration": duration,
        "status": "active",
        "startDate": time.time()  # Current timestamp in seconds
    }
    
    try:
        clients_col.replace_one({"_id": generated_api_key}, client_payload, upsert=True)
        print(f"Successfully recorded client in MongoDB: {generated_api_key}")
    except Exception as e:
        print(f"Error saving client to MongoDB: {e}")
    
    # (clients_file logic removed as we use MongoDB now)

    return {
        "status": "success", 
        "apiKey": generated_api_key,
        "companyName": companyName
    }

@app.get("/api/admin/clients")
async def list_clients():
    import time
    try:
        clients = list(clients_col.find())
        # Calculate remaining days for each client
        for client in clients:
            start_date = client.get("startDate")
            # duration is "1", "6", or "12" (months)
            try:
                duration_months = int(client.get("duration", 1))
            except:
                duration_months = 1
                
            if start_date:
                # 30 days per month
                total_seconds = duration_months * 30 * 24 * 3600
                elapsed_seconds = time.time() - start_date
                remaining_seconds = total_seconds - elapsed_seconds
                remaining_days = int(remaining_seconds / (24 * 3600))
                client["remainingDays"] = max(0, remaining_days)
            else:
                client["remainingDays"] = "N/A"
                
        return clients
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return []

@app.post("/api/admin/toggle-client")
async def toggle_client(data: dict):
    api_key = data.get("apiKey")
    status = data.get("status") # 'active' or 'inactive'
    
    try:
        # 1. Update clients collection
        clients_col.update_one({"_id": api_key}, {"$set": {"status": status}})
        
        # 2. Update stores collection
        stores_col.update_one({"_id": api_key}, {"$set": {"status": status}})
        
        return {"status": "success", "newStatus": status}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/admin/delete-client")
async def delete_client(data: dict):
    api_key = data.get("apiKey")
    try:
        # 1. Delete from clients collection
        clients_col.delete_one({"_id": api_key})
        # 2. Delete from stores collection
        stores_col.delete_one({"_id": api_key})
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use port 8004 for the landing page backend
    uvicorn.run(app, host="0.0.0.0", port=8004)
