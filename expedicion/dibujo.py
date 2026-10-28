"""Dibujo del mapa v0.1 en SVG (para docs/)."""

from . import config as C

COLOR = {".": "#d9b98a", "a": "#f0d98c", "b": "#7a5230", "h": "#bfe3f5", "R": "#8a8f96",
         "#": "#3b4452", "G": "#1b0f0a", "B": "#3aa655", "1": "#2ec4d6", "2": "#2ec4d6"}


def mapa_svg(mapa=None, celda=40):
    mapa = mapa or C.MAPA_V01
    alto, ancho = len(mapa), len(mapa[0])
    m = 40  # margen para ejes
    w, h = ancho * celda + m + 220, alto * celda + m + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#f5f3ee"/>',
           f'<text x="{m}" y="18" font-size="15" font-weight="bold" fill="#13293d">'
           f'Robot Expedition · mapa v0.1 (12 m × 12 m, celda = 1 m)</text>']
    for y, fila in enumerate(mapa):
        for x, c in enumerate(fila):
            px, py = m + x * celda, m + y * celda
            out.append(f'<rect x="{px}" y="{py}" width="{celda}" height="{celda}" '
                       f'fill="{COLOR[c]}" stroke="#00000022"/>')
            etiqueta = {"B": "BASE", "1": "1", "2": "2", "R": "▲", "G": "▼", "h": "≈"}.get(c)
            if etiqueta:
                color = "#fff" if c in "B12G" else "#33333399"
                out.append(f'<text x="{px + celda / 2}" y="{py + celda / 2 + 4}" text-anchor="middle" '
                           f'fill="{color}" font-weight="bold">{etiqueta}</text>')
    for (x, y), _ in C.INCIDENTES["corredor_bloqueado"].items():
        px, py = m + x * celda, m + y * celda
        out.append(f'<rect x="{px + 3}" y="{py + 3}" width="{celda - 6}" height="{celda - 6}" '
                   f'fill="none" stroke="#d9592a" stroke-width="3" stroke-dasharray="5 3"/>')
    for i in range(ancho):
        out.append(f'<text x="{m + i * celda + celda / 2}" y="{m - 6}" text-anchor="middle" '
                   f'fill="#555">{i}</text>')
    for j in range(alto):
        out.append(f'<text x="{m - 8}" y="{m + j * celda + celda / 2 + 4}" text-anchor="end" '
                   f'fill="#555">{j}</text>')
    lx = m + ancho * celda + 20
    out.append(f'<text x="{lx}" y="{m + 4}" font-weight="bold" fill="#13293d">Leyenda</text>')
    for k, (c, nombre) in enumerate([(c, t["nombre"]) for c, t in C.TERRENOS.items()]):
        yy = m + 20 + k * 24
        out.append(f'<rect x="{lx}" y="{yy}" width="16" height="16" fill="{COLOR[c]}" stroke="#0003"/>')
        out.append(f'<text x="{lx + 24}" y="{yy + 12}" fill="#222">{nombre}</text>')
    yy = m + 20 + len(C.TERRENOS) * 24
    out.append(f'<rect x="{lx}" y="{yy}" width="16" height="16" fill="none" stroke="#d9592a" '
               f'stroke-width="2" stroke-dasharray="4 2"/>')
    out.append(f'<text x="{lx + 24}" y="{yy + 12}" fill="#222">incidente: derrumbe</text>')
    out.append(f'<text x="{lx}" y="{yy + 44}" fill="#555">N ↑  ·  x → Este, y → Sur</text>')
    out.append(f'<text x="{m}" y="{h - 8}" fill="#555">Ruta segura más corta: '
               f'base → 1 (10 m) → 2 (16 m) → base (22 m) = 48 m</text>')
    out.append("</svg>")
    return "\n".join(out)
