import json
import time
import random
import os
import urllib.request
from urllib.error import HTTPError, URLError
import re

# Archivos
PRODUCTOS_FILE = "data/productos.json"
ESTADO_FILE = "data/estado_productos.json"

# Cabeceras para simular un navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept-Language': 'es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive'
}

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_price(html):
    """
    Busca patrones comunes de precio en el HTML de Amazon.
    """
    # Patrón 1: <span class="a-offscreen">$1,234.56</span>
    match = re.search(r'<span class="a-offscreen">([^<]+)</span>', html)
    if match:
        return match.group(1).strip()
    
    # Patrón 2: <span class="a-price-whole">1,234<span class="a-price-decimal">.</span></span>
    match_whole = re.search(r'<span class="a-price-whole">([^<]+)<', html)
    match_fraction = re.search(r'<span class="a-price-fraction">([^<]+)<', html)
    if match_whole and match_fraction:
        return f"${match_whole.group(1).strip()}{match_fraction.group(1).strip()}"
    elif match_whole:
        return f"${match_whole.group(1).strip()}"
        
    return None

def main():
    print("Iniciando scraper de Amazon...")
    
    productos_data = load_json(PRODUCTOS_FILE)
    estado_data = load_json(ESTADO_FILE)
    
    # Parsear lista de productos
    products_list = []
    if isinstance(productos_data, list):
        products_list = productos_data
    elif isinstance(productos_data, dict) and "productos" in productos_data:
        products_list = productos_data["productos"]
    else:
        for k, v in productos_data.items():
            if isinstance(v, list):
                products_list = v
                break

    print(f"Se encontraron {len(products_list)} productos. Procesando...")
    
    for idx, prod in enumerate(products_list):
        prod_id = prod.get("id")
        url = prod.get("url")
        
        if not prod_id or not url:
            continue
            
        # Si ya tenemos el precio, podemos saltarlo (opcional, pero ayuda a evitar baneos)
        # if prod_id in estado_data and estado_data[prod_id].get("amazon_precio"):
        #     print(f"[{prod_id}] Ya tiene precio, saltando...")
        #     continue

        print(f"[{prod_id}] Consultando URL: {url}...")
        
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                precio = extract_price(html)
                
                if precio:
                    print(f"  -> Precio encontrado: {precio}")
                    if prod_id not in estado_data:
                        estado_data[prod_id] = {}
                    estado_data[prod_id]["amazon_precio"] = precio
                    # Guardar progresivamente
                    save_json(ESTADO_FILE, estado_data)
                else:
                    print(f"  -> No se pudo encontrar el precio en el HTML.")
        except HTTPError as e:
            print(f"  -> Error HTTP: {e.code}. Amazon podría estar bloqueando la petición.")
        except URLError as e:
            print(f"  -> Error de red: {e.reason}")
        except Exception as e:
            print(f"  -> Error inesperado: {str(e)}")
            
        # Esperar entre 2 y 5 segundos para no saturar
        sleep_time = random.uniform(2.0, 5.0)
        print(f"Esperando {sleep_time:.1f} segundos...\n")
        time.sleep(sleep_time)

    print("Proceso finalizado.")

if __name__ == "__main__":
    main()
