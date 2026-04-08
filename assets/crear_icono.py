#!/usr/bin/env python3
"""
Genera el ícono de la aplicación Vinoteca.
Produce:
  assets/icon.ico  – Windows (multi-resolución: 16/32/48/64/128/256 px)
  assets/icon.png  – macOS / referencia (256×256)

Ejecutar: python3 assets/crear_icono.py
"""

import os
from PIL import Image, ImageDraw

# ── Paleta de la app ──────────────────────────────────────────────────────────
WINE       = (114, 47,  55)   # #722F37
WINE_DARK  = ( 60, 15,  22)   # #3C0F16
GOLD       = (201, 168, 76)   # #C9A84C
BG         = ( 26, 26,  26)   # #1A1A1A
TRANSP     = (0, 0, 0, 0)


def _draw_copa(draw: ImageDraw.ImageDraw, sz: int) -> None:
    """
    Dibuja una copa de vino centrada en un canvas sz × sz.
    Todos los valores están escalados respecto a 256 px.
    """
    cx = sz / 2
    s  = sz / 256          # factor de escala

    # ── Fondo redondeado ─────────────────────────────────────────────────────
    r = max(4, int(36 * s))
    draw.rounded_rectangle([0, 0, sz - 1, sz - 1], radius=r, fill=BG)

    # ── Bowl (cuerpo de la copa) ──────────────────────────────────────────────
    #    Trapecio: ancho arriba, angosto abajo
    bt_y = int(36 * s)              # y superior del bowl
    bb_y = int(148 * s)             # y inferior del bowl (unión con el tallo)
    bt_w = int(80 * s)              # semi-ancho en la boca
    bb_w = max(3, int(14 * s))      # semi-ancho en la base del bowl

    draw.polygon([
        (cx - bt_w, bt_y),
        (cx + bt_w, bt_y),
        (cx + bb_w, bb_y),
        (cx - bb_w, bb_y),
    ], fill=WINE)

    # Borde superior redondeado (elipse en el labio)
    rim_h = max(2, int(14 * s))
    draw.ellipse(
        [cx - bt_w, bt_y - rim_h, cx + bt_w, bt_y + rim_h],
        fill=WINE,
    )

    # ── Vino dentro (líquido más oscuro) ──────────────────────────────────────
    wine_y = int(94 * s)                       # nivel de la superficie del vino
    t      = (wine_y - bt_y) / max(1, bb_y - bt_y)
    wine_w = bt_w - (bt_w - bb_w) * t          # ancho interpolado del bowl en wine_y

    draw.polygon([
        (cx - wine_w, wine_y),
        (cx + wine_w, wine_y),
        (cx + bb_w,   bb_y),
        (cx - bb_w,   bb_y),
    ], fill=WINE_DARK)

    # Superficie del vino (elipse)
    wrim_h = max(1, int(9 * s))
    draw.ellipse(
        [cx - wine_w, wine_y - wrim_h, cx + wine_w, wine_y + wrim_h],
        fill=WINE_DARK,
    )

    # Reflejo sutil en el costado izquierdo del bowl (solo tamaños grandes)
    if sz >= 48:
        hl_x1 = cx - bt_w + int(9  * s)
        hl_x2 = cx - bt_w + int(26 * s)
        hl_y1 = bt_y       + int(16 * s)
        hl_y2 = bt_y       + int(50 * s)
        draw.ellipse([hl_x1, hl_y1, hl_x2, hl_y2], fill=(165, 70, 80))

    # ── Tallo ─────────────────────────────────────────────────────────────────
    sw     = max(2, int(7 * s))
    st_bot = int(196 * s)
    draw.rectangle([cx - sw, bb_y, cx + sw, st_bot], fill=GOLD)

    # ── Base ──────────────────────────────────────────────────────────────────
    bw = int(68 * s)
    bh = max(3, int(13 * s))
    draw.ellipse(
        [cx - bw, st_bot - bh // 2, cx + bw, st_bot + bh],
        fill=GOLD,
    )


def crear_icono(output_dir: str = "assets") -> str:
    """
    Genera icon.ico + icon.png en `output_dir`.
    Devuelve la ruta del archivo .ico creado.
    """
    os.makedirs(output_dir, exist_ok=True)

    sizes  = [16, 32, 48, 64, 128, 256]
    images = []

    for sz in sizes:
        img  = Image.new("RGBA", (sz, sz), TRANSP)
        draw = ImageDraw.Draw(img)
        _draw_copa(draw, sz)
        images.append(img)

    # ── .ico  (Windows, multi-resolución) ────────────────────────────────────
    ico_path = os.path.join(output_dir, "icon.ico")
    # Pillow acepta sizes=[] para empacar múltiples resoluciones en un .ico
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"  ✓  icon.ico  →  {ico_path}")

    # ── .png  256×256 (macOS / referencia) ───────────────────────────────────
    png_path = os.path.join(output_dir, "icon.png")
    images[-1].save(png_path)
    print(f"  ✓  icon.png  →  {png_path}")

    return ico_path


if __name__ == "__main__":
    crear_icono()
