import os
import csv

def format_catalog_from_string(data_string):
    print(f"DEBUG: Formatting catalog from string data (length: {len(data_string)})")
    if not data_string:
        return "- Aucun produit disponible pour le moment."
    
    catalog_lines = []
    
    try:
        # Try JSON first
        if data_string.strip().startswith(('[', '{')):
            import json
            data = json.loads(data_string)
            products = data if isinstance(data, list) else data.get('products', [])
            for row in products:
                name = row.get('Product') or row.get('Name') or row.get('Produit') or 'Produit inconnu'
                price = row.get('Price') or row.get('Prix') or 'Prix sur demande'
                specs = row.get('Description') or row.get('Specs') or row.get('Caractéristiques') or 'Pas de specs'
                stock = row.get('Stock') or '1'
                line = f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}"
                catalog_lines.append(line)
        else:
            # Fallback to CSV
            import io
            # Clean the string and handle potential encoding issues
            clean_data = data_string.strip().replace('\ufeff', '')
            f = io.StringIO(clean_data)
            
            # Use a basic reader first to check for headers
            raw_reader = csv.reader(f)
            rows = list(raw_reader)
            if not rows:
                return "- Catalogue vide."

            # Heuristic: Check if first row contains common header keywords
            first_row = [str(cell).lower() for cell in rows[0]]
            header_keywords = ['product', 'name', 'produit', 'price', 'prix', 'description', 'specs']
            has_header = any(key in cell for cell in first_row for key in header_keywords)

            if has_header:
                # Use DictReader and make it case-insensitive
                f.seek(0)
                dict_reader = csv.DictReader(f)
                for row in dict_reader:
                    # Create a lowercase mapping of the row
                    low_row = {k.lower(): v for k, v in row.items() if k}
                    name = low_row.get('product') or low_row.get('name') or low_row.get('produit') or 'Produit inconnu'
                    price = low_row.get('price') or low_row.get('prix') or 'Prix sur demande'
                    specs = low_row.get('description') or low_row.get('specs') or low_row.get('caractéristiques') or 'Pas de specs'
                    stock = low_row.get('stock') or '1'
                    catalog_lines.append(f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}")
            else:
                # No headers: Use positions (0: Name, 1: Price, 2: Specs)
                for row in rows:
                    if len(row) >= 2:
                        name = row[0]
                        price = row[1]
                        specs = row[2] if len(row) > 2 else "Produit de qualité"
                        catalog_lines.append(f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: 1")
        
        result = "\n".join(catalog_lines)
        print(f"DEBUG: Formatted {len(catalog_lines)} products successfully.")
        return result
    except Exception as e:
        print(f"DEBUG: Error parsing catalog string: {e}")
        # Final fallback: just return the raw lines formatted as bullets
        return "- " + data_string.replace('\n', '\n- ')

def format_catalog_from_file(file_path):
    print(f"DEBUG: Formatting catalog from {file_path}")
    if not os.path.exists(file_path):
        print(f"DEBUG: File path does not exist: {file_path}")
        return "- Aucun produit disponible pour le moment."
    
    catalog_lines = []
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == '.json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list of dicts and dict with products key
                products = data if isinstance(data, list) else data.get('products', [])
                for row in products:
                    name = row.get('Product') or row.get('Name') or row.get('Produit') or 'Produit inconnu'
                    price = row.get('Price') or row.get('Prix') or 'Prix sur demande'
                    specs = row.get('Description') or row.get('Specs') or row.get('Caractéristiques') or 'Pas de specs'
                    stock = row.get('Stock') or '1'
                    line = f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}"
                    catalog_lines.append(line)
        else:
            # Fallback to CSV
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Product') or row.get('Name') or row.get('Produit') or 'Produit inconnu'
                    price = row.get('Price') or row.get('Prix') or 'Prix sur demande'
                    specs = row.get('Description') or row.get('Specs') or row.get('Caractéristiques') or 'Pas de specs'
                    stock = row.get('Stock') or '1'
                    line = f"- Produit: {name}, Prix: {price}, Specs: {specs}, Stock: {stock}"
                    catalog_lines.append(line)
        
        result = "\n".join(catalog_lines)
        print(f"DEBUG: Formatted {len(catalog_lines)} products.")
        return result
    except Exception as e:
        print(f"DEBUG: Error reading file: {e}")
        return "- Erreur lors de la lecture du catalogue."

ANTI_GRAVITY_PROMPT_TEMPLATE = """[CRITICAL: LANGUAGE RULE]
YOU MUST SPEAK EXCLUSIVELY IN MOROCCAN DARIJA. 
- NEVER use French sentences.
- NEVER use Modern Standard Arabic (Fusha).
- Use English ONLY for technical specs (RAM, SSD) and Prices.
- Examples of your style: "Mreba bik", "Ach hab l-khater", "Had l-produit rah mzyan", "Llah i-barek fik".
- [STRICT] Use professional and polite Darija. NEVER use slang, vulgar words, or street language (avoid words like "m9awed", etc.).

[MISSION]
Tu es l'agent vocal professionnel de la boutique {COMPANY_NAME}. Ta mission est de conseiller les clients et de vendre uniquement les produits listés dans le catalogue fourni.

[SOURCE DE VÉRITÉ UNIQUE : CATALOGUE CSV]
Voici les seuls produits que tu as le droit de vendre :
{CATALOG_PLACEHOLDER}

[RÈGLES DE COMPORTEMENT]
1. AUCUNE HALLUCINATION : Ne parle jamais d'un produit qui n'est pas dans la liste ci-dessus.
2. RÉPONSE AUX PRODUITS ABSENTS : Si le client demande un produit absent, réponds poliment en Darija : "Smeh lia bzaf, had l-produit ma-3ndnach f l-magasin f had l-weqt. Chouf m3aya had l-choix akhor li 3ndna..."
3. VÉRIFICATION DU STOCK : Si Stock = 0, dis que c'est en rupture de stock.
4. CONCISION : Max 2 phrases.
5. POLITESSE : Reste toujours poli et serviable.

[LOGIQUE DE VENTE]
- Demande l'usage : "Lach ghadi t-sta3mel had l-produit?".
- Closing : Dès que le client confirme son intention d'achat (ex: "Wakha bghito", "Chrih lia", "Dir lia commande", "Sifto lia", "Bghit n-chri"), utilise l'outil `checkout` immédiatement. Dis : "Wakha, ghadi n-ftha lik l-fenêtre bach t-3mer l-info dyalk".
"""
