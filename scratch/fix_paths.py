import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('d:/Gemini Voice2/Gemini Voice2/Gemini Voice2/.env')
client = MongoClient(os.environ.get('MONGODB_URI'))
db = client.get_database('ham_db')
stores = db.get_collection('stores')

print("Fixing paths in MongoDB...")
for s in stores.find():
    api_key = s.get('_id')
    csv_path = s.get('csv_path')
    if csv_path and 'Gemini Voice2' in csv_path:
        # Check if it's missing a level
        # Target: D:\Gemini Voice2\Gemini Voice2\Gemini Voice2\...
        # Current: d:\Gemini Voice2\Gemini Voice2\...
        
        parts = csv_path.split('\\')
        if len(parts) > 2 and parts[1] == 'Gemini Voice2' and parts[2] != 'Gemini Voice2':
            new_path = csv_path.replace('d:\\Gemini Voice2\\Gemini Voice2\\', 'd:\\Gemini Voice2\\Gemini Voice2\\Gemini Voice2\\')
            print(f"Updating {api_key}: {csv_path} -> {new_path}")
            stores.update_one({'_id': api_key}, {'$set': {'csv_path': new_path}})
        elif len(parts) > 1 and parts[1] == 'Gemini Voice2' and parts[2] == 'Gemini Voice2' and parts[3] != 'Gemini Voice2':
             new_path = csv_path.replace('d:\\Gemini Voice2\\Gemini Voice2\\', 'd:\\Gemini Voice2\\Gemini Voice2\\Gemini Voice2\\')
             print(f"Updating {api_key}: {csv_path} -> {new_path}")
             stores.update_one({'_id': api_key}, {'$set': {'csv_path': new_path}})

print("Done.")
