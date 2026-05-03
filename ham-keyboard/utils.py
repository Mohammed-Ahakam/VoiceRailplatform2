import os
import csv

def format_catalog_from_file(file_path):
    if not os.path.exists(file_path):
        return "- Aucun produit disponible pour le moment."
    
    catalog_lines = []
    file_ext = os.path.splitext(file_path)[1].lower()
    try:
        if file_ext == '.json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                products = data if isinstance(data, list) else data.get('products', [])
                for row in products:
                    name = row.get('Product') or row.get('Name') or 'Produit inconnu'
                    price = row.get('Price') or 'Prix sur demande'
                    specs = row.get('Description') or row.get('Specs') or 'Pas de specs'
                    stock = row.get('Stock') or '1'
                    line = f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}"
                    catalog_lines.append(line)
        else:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Product') or row.get('Name') or 'Produit inconnu'
                    price = row.get('Price') or 'Prix sur demande'
                    specs = row.get('Description') or row.get('Specs') or 'Pas de specs'
                    stock = row.get('Stock') or '1'
                    line = f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}"
                    catalog_lines.append(line)
        
        return "\n".join(catalog_lines)
    except Exception as e:
        print(f"Error reading file: {e}")
        return "- Erreur lors de la lecture du catalogue."

def get_latest_uploaded_catalog(base_dir):
    uploads_dir = os.path.join(base_dir, "ham-landing", "uploads")
    if not os.path.exists(uploads_dir):
        return None
    
    companies = [os.path.join(uploads_dir, d) for d in os.listdir(uploads_dir) if os.path.isdir(os.path.join(uploads_dir, d))]
    if not companies:
        return None
    
    latest_company = max(companies, key=os.path.getmtime)
    
    # Look for catalog.csv or catalog.json
    for ext in ['.csv', '.json']:
        file_path = os.path.join(latest_company, f"catalog{ext}")
        if os.path.exists(file_path):
            return file_path
            
    return None
