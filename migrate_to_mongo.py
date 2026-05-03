import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    print("Error: MONGODB_URI not found in .env")
    exit(1)

client = MongoClient(MONGODB_URI)
db = client.get_database("ham_db")
stores_col = db.get_collection("stores")
clients_col = db.get_collection("clients")

def migrate_stores():
    stores_path = "saas-platform/stores.json"
    if os.path.exists(stores_path):
        with open(stores_path, "r") as f:
            stores = json.load(f)
        
        if not stores:
            print("No stores to migrate.")
            return

        # stores.json is a dict keyed by apiKey
        # We want to store each as a document
        documents = []
        for api_key, data in stores.items():
            # Use apiKey as _id or just a field
            data["_id"] = api_key # apiKey is unique
            documents.append(data)
        
        if documents:
            try:
                # Upsert to avoid duplicates
                for doc in documents:
                    stores_col.replace_one({"_id": doc["_id"]}, doc, upsert=True)
                print(f"Successfully migrated {len(documents)} stores.")
            except Exception as e:
                print(f"Error migrating stores: {e}")
    else:
        print("stores.json not found.")

def migrate_clients():
    clients_path = "ham-landing/clients/clients.json"
    if os.path.exists(clients_path):
        with open(clients_path, "r") as f:
            clients = json.load(f)
        
        if not clients:
            print("No clients to migrate.")
            return

        # clients.json is a list
        try:
            for client_data in clients:
                # Use apiKey as unique identifier for clients too
                if "apiKey" in client_data:
                    client_data["_id"] = client_data["apiKey"]
                    clients_col.replace_one({"_id": client_data["_id"]}, client_data, upsert=True)
            print(f"Successfully migrated {len(clients)} clients.")
        except Exception as e:
            print(f"Error migrating clients: {e}")
    else:
        print("clients.json not found.")

if __name__ == "__main__":
    print("Starting migration to MongoDB...")
    migrate_stores()
    migrate_clients()
    print("Migration complete.")
