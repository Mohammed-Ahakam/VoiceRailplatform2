import os
import shutil
import json
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

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
    
    # Save the CSV file
    file_path = os.path.join(company_dir, "catalog.csv")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(catalog.file, buffer)
        
    # Update SaaS stores.json
    saas_dir = "d:/Gemini Voice2/Gemini Voice2/saas-platform"
    stores_file = os.path.join(saas_dir, "stores.json")
    
    print(f"Updating stores file: {stores_file}")
    
    stores = {}
    if os.path.exists(stores_file):
        try:
            with open(stores_file, "r") as f:
                stores = json.load(f)
            print(f"Current stores in DB: {list(stores.keys())}")
        except Exception as e:
            print(f"Error reading stores.json: {e}")
            
    stores[generated_api_key] = {
        "apiKey": generated_api_key,
        "companyName": companyName,
    # Define tools based on plan
    tools = [{"name": "navigate_to_product", "description": "Voir le produit", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}}]
    
    if plan == "Pro Agentic":
        tools.append({"name": "add_to_cart", "description": "Ajouter au panier", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}})
        tools.append({"name": "checkout", "description": "Finaliser la commande et demander les infos client", "parameters": {"type":"OBJECT", "properties":{"product":{"type":"STRING"}}}})

    stores[generated_api_key] = {
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
        with open(stores_file, "w") as f:
            json.dump(stores, f, indent=4)
        print(f"Successfully updated stores.json with key: {generated_api_key}")
    except Exception as e:
        print(f"Error writing to stores.json: {e}")

    # Record the new client in a master file
    clients_dir = "d:/Gemini Voice2/Gemini Voice2/ham-landing/clients"
    os.makedirs(clients_dir, exist_ok=True)
    clients_file = os.path.join(clients_dir, "clients.json")
    
    all_clients = []
    if os.path.exists(clients_file):
        try:
            with open(clients_file, "r") as f:
                all_clients = json.load(f)
        except: pass
    
    all_clients.append({
        "apiKey": generated_api_key,
        "companyName": companyName,
        "industry": industry,
        "whatsapp": whatsapp,
        "plan": plan,
        "duration": duration,
        "status": "active",
        "timestamp": str(uuid.uuid4()) # Using UUID as a dummy timestamp/ID
    })
    
    with open(clients_file, "w") as f:
        json.dump(all_clients, f, indent=4)

    return {
        "status": "success", 
        "apiKey": generated_api_key,
        "companyName": companyName
    }

@app.get("/api/admin/clients")
async def list_clients():
    clients_file = "d:/Gemini Voice2/Gemini Voice2/ham-landing/clients/clients.json"
    if os.path.exists(clients_file):
        with open(clients_file, "r") as f:
            return json.load(f)
    return []

@app.post("/api/admin/toggle-client")
async def toggle_client(data: dict):
    api_key = data.get("apiKey")
    status = data.get("status") # 'active' or 'inactive'
    
    # 1. Update clients.json
    clients_file = "d:/Gemini Voice2/Gemini Voice2/ham-landing/clients/clients.json"
    if os.path.exists(clients_file):
        with open(clients_file, "r") as f:
            all_clients = json.load(f)
        for c in all_clients:
            if c.get("apiKey") == api_key:
                c["status"] = status
        with open(clients_file, "w") as f:
            json.dump(all_clients, f, indent=4)

    # 2. Update stores.json (The SaaS Engine)
    saas_dir = "d:/Gemini Voice2/Gemini Voice2/saas-platform"
    stores_file = os.path.join(saas_dir, "stores.json")
    if os.path.exists(stores_file):
        with open(stores_file, "r") as f:
            stores = json.load(f)
        if api_key in stores:
            stores[api_key]["status"] = status
            with open(stores_file, "w") as f:
                json.dump(stores, f, indent=4)
            return {"status": "success", "newStatus": status}
            
    return {"status": "error", "message": "Client not found in SaaS engine"}

if __name__ == "__main__":
    import uvicorn
    # Use port 8004 for the landing page backend
    uvicorn.run(app, host="0.0.0.0", port=8004)
