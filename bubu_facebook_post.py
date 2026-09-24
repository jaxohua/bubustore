import tkinter as tk
from tkinter import messagebox
import requests
import random
import re

PRODUCTOS_URL = 'https://jaxohua.github.io/bubustore/data/productos.json'
ESTADO_URL = 'https://jaxohua.github.io/bubustore/data/estado_productos.json'

def fetch_data():
    try:
        productos_res = requests.get(PRODUCTOS_URL)
        productos_res.raise_for_status()
        productos = productos_res.json()

        estado_res = requests.get(ESTADO_URL)
        estado_res.raise_for_status()
        estado = estado_res.json()

        return productos, estado
    except Exception as e:
        messagebox.showerror("Error de red", f"No se pudo obtener el catálogo:\n{e}")
        return None, None

def generate_post(product, estado):
    # Título
    ganchos = [
        "✨ ¡No te pierdas esta oportunidad!",
        "🔥 ¡Atención a este producto destacado!",
        "⭐ ¡Mejora tu día con este increíble artículo!",
        "✨ Hoy te recomendamos:"
    ]
    gancho = random.choice(ganchos)
    
    titulo = product.get('titulo', 'Producto sin nombre').strip()
    
    # Precio
    price = estado.get('precio')
    if not price:
        price = estado.get('amazon_precio', 'Consultar por mensaje')
    else:
        price = f"${price}" if not str(price).startswith('$') else price
        
    # Beneficios
    desc = product.get('descripcion', '')
    sections = desc.split('|')
    beneficios = []
    
    for sec in sections[:3]:
        sec = sec.strip()
        if not sec:
            continue
        # Take the first sentence or up to 80 chars
        match = re.split(r'[.!?]', sec)
        if match and match[0].strip():
            beneficio = match[0].strip()
            # If it's too short, maybe take more, but this is simple enough
            beneficios.append(f"✅ {beneficio}")
            
    if not beneficios:
        beneficios = ["✅ Excelente calidad.", "✅ Diseño práctico y funcional."]
    
    beneficios_text = "\n".join(beneficios[:3])
    
    # URL
    url = "https://jaxohua.github.io/bubustore/"
    
    # Imagen
    product_id = product.get('id', '')
    imagen_url = f"https://jaxohua.github.io/bubustore/images/{product_id}_01.jpg" if product_id else ""
    
    # Hashtags
    words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{5,}\b', titulo)
    hashtags = ["#BubuStore"]
    for w in random.sample(words, min(len(words), 3)):
        hashtags.append(f"#{w.capitalize()}")
    hashtags_text = " ".join(hashtags)
    
    post = f"""{gancho}
{titulo}

📸 Imagen: {imagen_url}

💰 Precio: {price}

{beneficios_text}

🔗 Consíguelo en nuestro catálogo (busca el producto aquí):
{url}

📩 Envíanos mensaje para coordinar tu compra.

{hashtags_text}
"""
    return post

def generar_publicacion(text_widget):
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, "Cargando datos...\n")
    text_widget.update()
    
    productos, estado_dict = fetch_data()
    if not productos or not estado_dict:
        text_widget.delete("1.0", tk.END)
        return
        
    # Filtrar disponibles
    disponibles = []
    for p in productos:
        p_id = p.get('id')
        est = estado_dict.get(p_id, {})
        if not est.get('vendido'):
            disponibles.append((p, est))
            
    if not disponibles:
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, "No hay productos disponibles actualmente.")
        return
        
    prod, est = random.choice(disponibles)
    post_text = generate_post(prod, est)
    
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, post_text)

def copiar_al_portapapeles(root, text_widget):
    contenido = text_widget.get("1.0", tk.END).strip()
    if contenido:
        root.clipboard_clear()
        root.clipboard_append(contenido)
        messagebox.showinfo("Copiado", "Publicación copiada al portapapeles.")
    else:
        messagebox.showwarning("Vacío", "No hay texto para copiar.")

def main():
    root = tk.Tk()
    root.title("Generador de Posts - BubuStore")
    root.geometry("600x500")
    
    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(expand=True, fill=tk.BOTH)
    
    lbl = tk.Label(frame, text="Publicación para Facebook:", font=("Arial", 12, "bold"))
    lbl.pack(anchor=tk.W, pady=(0, 5))
    
    text_area = tk.Text(frame, wrap=tk.WORD, font=("Arial", 11))
    text_area.pack(expand=True, fill=tk.BOTH, pady=(0, 10))
    
    btn_frame = tk.Frame(frame)
    btn_frame.pack(fill=tk.X)
    
    btn_generar = tk.Button(btn_frame, text="🔄 Generar Publicación", command=lambda: generar_publicacion(text_area), font=("Arial", 11), bg="#4CAF50", fg="black")
    btn_generar.pack(side=tk.LEFT, padx=(0, 10))
    
    btn_copiar = tk.Button(btn_frame, text="📋 Copiar al Portapapeles", command=lambda: copiar_al_portapapeles(root, text_area), font=("Arial", 11), bg="#2196F3", fg="black")
    btn_copiar.pack(side=tk.LEFT)
    
    root.mainloop()

if __name__ == '__main__':
    main()
