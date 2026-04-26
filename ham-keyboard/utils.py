import os
import csv

def format_catalog_from_csv(csv_path):
    if not os.path.exists(csv_path):
        return "- Aucun produit disponible pour le moment."
    
    catalog_lines = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
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
        print(f"Error reading CSV: {e}")
        return "- Erreur lors de la lecture du catalogue."

def get_latest_uploaded_csv(base_dir):
    uploads_dir = os.path.join(base_dir, "ham-landing", "uploads")
    if not os.path.exists(uploads_dir):
        return None
    
    # Find the most recently created company directory
    companies = [os.path.join(uploads_dir, d) for d in os.listdir(uploads_dir) if os.path.isdir(os.path.join(uploads_dir, d))]
    if not companies:
        return None
    
    latest_company = max(companies, key=os.path.getmtime)
    csv_path = os.path.join(latest_company, "catalog.csv")
    
    if os.path.exists(csv_path):
        return csv_path
    return None
