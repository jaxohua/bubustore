import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import requests
import random
import re
import io
import threading
import tempfile
import os
import subprocess

PRODUCTOS_URL = 'https://jaxohua.github.io/bubustore/data/productos.json'
ESTADO_URL    = 'https://jaxohua.github.io/bubustore/data/estado_productos.json'

# ─── Versión de la aplicación ─────────────────────────────────────────────────
APP_VERSION = '1.1.0'

# Referencia global para evitar que el GC borre la imagen del canvas
_tk_preview_img  = None
_composite_img   = None   # PIL Image final para copiar

# ─── Fonts del sistema (con fallback) ────────────────────────────────────────
FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNSText.ttf",
    "/System/Library/Fonts/Arial.ttf",
]

def _get_font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ─── Fetch data ───────────────────────────────────────────────────────────────
def fetch_data():
    try:
        r1 = requests.get(PRODUCTOS_URL, timeout=10)
        r1.raise_for_status()
        r2 = requests.get(ESTADO_URL, timeout=10)
        r2.raise_for_status()
        return r1.json(), r2.json()
    except Exception as e:
        messagebox.showerror("Error de red", f"No se pudo obtener el catálogo:\n{e}")
        return None, None

# ─── Generar texto del post ───────────────────────────────────────────────────
def generate_post_text(product, estado):
    ganchos = [
        "✨ ¡No te pierdas esta oportunidad!",
        "🔥 ¡Atención a este producto destacado!",
        "⭐ ¡Mejora tu día con este increíble artículo!",
        "✨ Hoy te recomendamos:"
    ]
    gancho   = random.choice(ganchos)
    titulo   = product.get('titulo', 'Producto sin nombre').strip()

    price = estado.get('precio')
    if not price:
        price = estado.get('amazon_precio', 'Consultar por mensaje')
    else:
        price = f"${price}" if not str(price).startswith('$') else price

    desc     = product.get('descripcion', '')
    sections = desc.split('|')
    beneficios = []
    for sec in sections[:3]:
        sec = sec.strip()
        if not sec:
            continue
        m = re.split(r'[.!?]', sec)
        if m and m[0].strip():
            beneficios.append(f"✅ {m[0].strip()}")
    if not beneficios:
        beneficios = ["✅ Excelente calidad.", "✅ Diseño práctico y funcional."]

    url      = "https://jaxohua.github.io/bubustore/"
    words    = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{5,}\b', titulo)
    hashtags = ["#BubuStore"]
    for w in random.sample(words, min(len(words), 3)):
        hashtags.append(f"#{w.capitalize()}")

    return f"""{gancho}
{titulo}

💰 Precio: {price}

{chr(10).join(beneficios[:3])}

🔗 {url}

📩 Envíanos mensaje para coordinar tu compra.

{' '.join(hashtags)}"""

# ─── Crear imagen compuesta (foto + texto) ────────────────────────────────────
def create_post_card(product_pil_img, post_text, card_width=640):
    """Devuelve un PIL.Image con la foto arriba y el texto abajo, estilo post card."""
    PAD        = 28
    BG         = (255, 255, 255)
    HEADER_BG  = (24, 119, 242)   # azul Facebook
    TEXT_COLOR = (30, 30, 30)
    MUTED      = (100, 100, 100)

    font_title  = _get_font(22)
    font_body   = _get_font(17)
    font_small  = _get_font(14)

    inner_w = card_width - PAD * 2

    # ── Preparar imagen del producto ──────────────────────────────────────────
    if product_pil_img:
        aspect     = product_pil_img.height / product_pil_img.width
        photo_w    = card_width
        photo_h    = int(photo_w * aspect)
        photo_h    = min(photo_h, 420)          # cap de altura
        prod_img   = product_pil_img.resize((photo_w, photo_h), Image.LANCZOS)
    else:
        photo_h  = 0
        prod_img = None

    # ── Calcular altura del texto ─────────────────────────────────────────────
    lines      = post_text.strip().split('\n')
    LINE_H     = 26
    text_block = len(lines) * LINE_H + PAD * 2

    # ── Canvas total ──────────────────────────────────────────────────────────
    total_h = photo_h + text_block + PAD
    card    = Image.new('RGB', (card_width, total_h), BG)
    draw    = ImageDraw.Draw(card)

    # ── Pegar foto ────────────────────────────────────────────────────────────
    y = 0
    if prod_img:
        card.paste(prod_img, (0, 0))
        y = photo_h

    # ── Franja separadora azul ────────────────────────────────────────────────
    draw.rectangle([(0, y), (card_width, y + 5)], fill=HEADER_BG)
    y += 5 + PAD

    # ── Texto ─────────────────────────────────────────────────────────────────
    for i, line in enumerate(lines):
        if i == 0 and line.strip():                 # gancho — primera línea
            font = font_title
            color = HEADER_BG
        elif line.startswith('💰') or line.startswith('🔗') or line.startswith('📩'):
            font  = font_body
            color = TEXT_COLOR
        elif line.startswith('#'):
            font  = font_small
            color = MUTED
        else:
            font  = font_body
            color = TEXT_COLOR

        draw.text((PAD, y), line, fill=color, font=font)
        y += LINE_H

    # ── Borde redondeado sutil (sin libs externas) ────────────────────────────
    # Solo añadimos un borde fino
    draw.rectangle([(0, 0), (card_width - 1, total_h - 1)],
                   outline=(200, 200, 200), width=1)

    return card

# ─── Copiar imagen al portapapeles macOS ──────────────────────────────────────
def copy_image_to_clipboard(pil_img):
    """Copia un PIL.Image al portapapeles de macOS como PNG."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        tmp_path = f.name
    try:
        pil_img.save(tmp_path, 'PNG')
        subprocess.run(
            ['osascript', '-e',
             f'set the clipboard to (read (POSIX file "{tmp_path}") as «class PNGf»)'],
            check=True, capture_output=True
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

# ─── Mostrar preview en el canvas ────────────────────────────────────────────
def show_preview(canvas, pil_card):
    """Redimensiona la card para que quepa en el canvas y la muestra."""
    global _tk_preview_img
    cw = canvas.winfo_width()  or 600
    ch = canvas.winfo_height() or 500

    # Escalar manteniendo proporción
    scale  = min(cw / pil_card.width, ch / pil_card.height, 1.0)
    new_w  = int(pil_card.width  * scale)
    new_h  = int(pil_card.height * scale)
    thumb  = pil_card.resize((new_w, new_h), Image.LANCZOS)

    _tk_preview_img = ImageTk.PhotoImage(thumb)
    canvas.delete("all")
    canvas.create_image(cw // 2, ch // 2, image=_tk_preview_img, anchor=tk.CENTER)

# ─── Acción principal: Generar ────────────────────────────────────────────────
def generar_publicacion(canvas, status_var, btn_gen, btn_copy):
    global _composite_img

    btn_gen.configure(state=tk.DISABLED, text="Cargando…")
    btn_copy.configure(state=tk.DISABLED)
    status_var.set("⏳ Obteniendo catálogo…")
    canvas.delete("all")
    canvas.create_text(canvas.winfo_width() // 2 or 300,
                       canvas.winfo_height() // 2 or 250,
                       text="⏳ Generando publicación…",
                       fill="#888", font=("Arial", 14))

    def _task():
        productos, estado_dict = fetch_data()
        if not productos or not estado_dict:
            canvas.after(0, lambda: btn_gen.configure(state=tk.NORMAL, text="🔄 Generar"))
            return

        disponibles = [(p, estado_dict.get(p.get('id'), {}))
                       for p in productos
                       if not estado_dict.get(p.get('id'), {}).get('vendido')]

        if not disponibles:
            canvas.after(0, lambda: status_var.set("⚠️ No hay productos disponibles"))
            canvas.after(0, lambda: btn_gen.configure(state=tk.NORMAL, text="🔄 Generar"))
            return

        prod, est   = random.choice(disponibles)
        post_text   = generate_post_text(prod, est)
        product_id  = prod.get('id', '')
        imagen_url  = (f"https://jaxohua.github.io/bubustore/images/{product_id}_01.jpg"
                       if product_id else "")

        # Descargar foto del producto
        product_pil = None
        if imagen_url:
            try:
                resp = requests.get(imagen_url, timeout=10)
                resp.raise_for_status()
                product_pil = Image.open(io.BytesIO(resp.content)).convert('RGB')
            except Exception:
                product_pil = None

        # Crear post card
        card = create_post_card(product_pil, post_text)

        def _update_ui():
            global _composite_img
            _composite_img = card
            show_preview(canvas, card)
            btn_gen.configure(state=tk.NORMAL, text="🔄 Generar")
            btn_copy.configure(state=tk.NORMAL)
            status_var.set("✅ Publicación lista — haz clic en 'Copiar' para compartir")

        canvas.after(0, _update_ui)

    threading.Thread(target=_task, daemon=True).start()

# ─── Copiar publicación ───────────────────────────────────────────────────────
def copiar_publicacion(status_var):
    global _composite_img
    if _composite_img is None:
        messagebox.showwarning("Vacío", "Primero genera una publicación.")
        return

    status_var.set("⏳ Copiando al portapapeles…")

    def _copy():
        try:
            copy_image_to_clipboard(_composite_img)
            status_var.set("✅ ¡Imagen copiada! Pégala directamente en WhatsApp o Facebook.")
        except Exception as e:
            status_var.set(f"❌ Error al copiar: {e}")

    threading.Thread(target=_copy, daemon=True).start()

# ─── UI ───────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.title(f"Generador de Posts · BubuStore  v{APP_VERSION}")
    root.geometry("700x640")
    root.configure(bg="#0f0f1a")
    root.resizable(True, True)

    status_var = tk.StringVar(value="Presiona 'Generar' para crear tu publicación")

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = tk.Label(root, text="🛍️  BubuStore · Generador de Publicaciones",
                   font=("Arial", 13, "bold"), fg="#e0e0ff", bg="#0f0f1a")
    hdr.pack(pady=(12, 2))

    ver_lbl = tk.Label(root, text=f"v{APP_VERSION}",
                       font=("Arial", 9), fg="#44446a", bg="#0f0f1a")
    ver_lbl.pack(pady=(0, 2))

    sub = tk.Label(root,
                   text="Genera una imagen con foto y texto lista para pegar en WhatsApp o Facebook",
                   font=("Arial", 10), fg="#555577", bg="#0f0f1a")
    sub.pack(pady=(0, 8))

    # ── Canvas: preview del post card ────────────────────────────────────────
    canvas_frame = tk.Frame(root, bg="#1a1a2e",
                            highlightbackground="#2a2a4a", highlightthickness=1)
    canvas_frame.pack(expand=True, fill=tk.BOTH, padx=14, pady=(0, 8))

    canvas = tk.Canvas(canvas_frame, bg="#1a1a2e", bd=0, highlightthickness=0)
    canvas.pack(expand=True, fill=tk.BOTH, padx=2, pady=2)

    canvas.create_text(330, 220,
                       text="📸  La publicación aparecerá aquí\n(imagen + texto juntos)",
                       fill="#3a3a5a", font=("Arial", 13), justify=tk.CENTER)

    # ── Botones ───────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg="#0f0f1a")
    btn_frame.pack(fill=tk.X, padx=14, pady=(0, 6))

    btn_copy = tk.Button(btn_frame, text="📋 Copiar publicación",
                         font=("Arial", 11, "bold"), state=tk.DISABLED,
                         bg="#1a5e20", fg="white",
                         activebackground="#2e7d32", activeforeground="white",
                         relief=tk.FLAT, padx=16, pady=9, cursor="hand2",
                         command=lambda: copiar_publicacion(status_var))

    btn_gen = tk.Button(btn_frame, text="🔄 Generar",
                        font=("Arial", 11, "bold"),
                        bg="#3a3aff", fg="white",
                        activebackground="#2020cc", activeforeground="white",
                        relief=tk.FLAT, padx=16, pady=9, cursor="hand2",
                        command=lambda: generar_publicacion(canvas, status_var, btn_gen, btn_copy))

    btn_gen.pack(side=tk.LEFT, padx=(0, 10))
    btn_copy.pack(side=tk.LEFT)

    # ── Instrucción de uso ────────────────────────────────────────────────────
    tip = tk.Label(root,
                   text="💡  Tip: después de copiar, ve a WhatsApp o Facebook y presiona Pegar (⌘V)",
                   font=("Arial", 10), fg="#3a3a5a", bg="#0f0f1a")
    tip.pack(pady=(0, 4))

    # ── Barra de estado ───────────────────────────────────────────────────────
    tk.Label(root, textvariable=status_var,
             font=("Arial", 10), fg="#555577", bg="#0a0a14",
             anchor=tk.W, padx=14, pady=5).pack(fill=tk.X, side=tk.BOTTOM)

    root.mainloop()

if __name__ == '__main__':
    main()
