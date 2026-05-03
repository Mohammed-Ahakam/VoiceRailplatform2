import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.environ.get("MONGODB_URI")
print(f"URI loaded: {bool(uri)}")

if not uri:
    print("Error: MONGODB_URI not found in .env")
    exit(1)

try:
    print("Attempting to connect to MongoDB...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client.get_database("ham_db")
    clients_col = db.get_collection("clients")
    
    count = clients_col.count_documents({})
    print(f"Success! Connected to database. Found {count} clients.")
    
    clients = list(clients_col.find())
    for c in clients:
        print(c.get("companyName"), c.get("plan"))
        
except Exception as e:
    print(f"Connection Failed: {e}")
