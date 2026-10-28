"""Definición del mundo de Robot Expedition v0.1: mapa, terrenos, clima y gravedad.

Todo lo que es "física" vive aquí y en ambiente.py. El visor 3D solo dibuja
lo que el simulador le manda: física ≠ decoración.

Convenciones:
    - El mapa es una rejilla de celdas de 1 m × 1 m. x crece hacia el Este,
      y crece hacia el Sur (fila 0 = borde Norte).
    - Un paso de simulación dura 1 s.
"""

# --- Mapa v0.1 (12 m × 12 m) -------------------------------------------------
#   .  suelo firme        a  arena (gasta más batería)
#   b  barro (atasca)     h  hielo (desliza)
#   R  roca baja: no se puede caminar encima, pero sí saltar por encima
#   #  muro alto: no se puede cruzar de ninguna forma
#   G  grieta: caer dentro termina la misión (se puede saltar por encima)
#   B  base (inicio y regreso)   1, 2  balizas, en ese orden
MAPA_V01 = [
    "....aaaa..h2",  # y=0
    ".##.aaaa#.h#",  # y=1
    ".#..aa..#.h#",  # y=2
    ".#.RR...GGh.",  # y=3
    "...R..bbGG..",  # y=4
    "###R..bb..aa",  # y=5
    "....G.....aa",  # y=6
    ".hh.G.###...",  # y=7
    ".hh...#1#.bb",  # y=8
    ".RRR..#.#.bb",  # y=9
    "......b.....",  # y=10
    "B....bbb..##",  # y=11
]

# Terrenos: nombre, si se puede pisar caminando, si se puede sobrevolar en salto,
# y costo de batería (%) por entrar a la celda.
TERRENOS = {
    ".": {"nombre": "suelo", "pisable": True, "saltable": True, "costo": 0.6},
    "a": {"nombre": "arena", "pisable": True, "saltable": True, "costo": 1.2},
    "b": {"nombre": "barro", "pisable": True, "saltable": True, "costo": 1.8},
    "h": {"nombre": "hielo", "pisable": True, "saltable": True, "costo": 0.6},
    "R": {"nombre": "roca", "pisable": False, "saltable": True, "costo": 0.0},
    "#": {"nombre": "muro", "pisable": False, "saltable": False, "costo": 0.0},
    "G": {"nombre": "grieta", "pisable": True, "saltable": True, "costo": 0.0},
    "B": {"nombre": "base", "pisable": True, "saltable": True, "costo": 0.6},
    "1": {"nombre": "baliza 1", "pisable": True, "saltable": True, "costo": 0.6},
    "2": {"nombre": "baliza 2", "pisable": True, "saltable": True, "costo": 0.6},
}
# Orden fijo para codificar el terreno en la observación (Discrete).
CODIGOS_TERRENO = list(TERRENOS)

# --- Clima ---------------------------------------------------------------------
# deslizar: probabilidad base de patinar al entrar a hielo.
# atasco:   probabilidad de no avanzar al intentar salir del barro.
# consumo:  multiplicador del gasto de batería (frío, viento).
# ruido:    multiplicador del ruido de los sensores de distancia.
CLIMAS = {
    "despejado": {"deslizar": 0.20, "atasco": 0.25, "consumo": 1.00, "ruido": 1.0},
    "lluvia": {"deslizar": 0.35, "atasco": 0.40, "consumo": 1.15, "ruido": 1.5},
    "tormenta": {"deslizar": 0.50, "atasco": 0.50, "consumo": 1.35, "ruido": 2.5},
}
NOMBRES_CLIMA = list(CLIMAS)

# --- Gravedad (m/s²) -----------------------------------------------------------
GRAVEDADES = {"luna": 1.62, "marte": 3.71, "tierra": 9.81}
NOMBRES_GRAVEDAD = list(GRAVEDADES)
G_TIERRA = 9.81

# --- Acciones ------------------------------------------------------------------
# Direcciones (dx, dy). y crece hacia el Sur.
DIRECCIONES = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0)}
ACCIONES = [
    ("mover", "N"), ("mover", "S"), ("mover", "E"), ("mover", "O"),
    ("saltar", "N"), ("saltar", "S"), ("saltar", "E"), ("saltar", "O"),
    ("agarrar", None),
]
NOMBRES_ACCION = [f"{tipo} {d}" if d else tipo for tipo, d in ACCIONES]
AGARRAR = 8

# --- Sensores ------------------------------------------------------------------
# 8 rayos en rosa de los vientos: N, NE, E, SE, S, SO, O, NO.
RAYOS = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
NOMBRES_RAYO = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]

# --- Incidentes (perturbaciones para evaluar robustez) -------------------------
# Cada incidente cambia celdas del mapa: {(x, y): nuevo_codigo}.
INCIDENTES = {
    "ninguno": {},
    # Un derrumbe tapa el único corredor de acceso a la baliza 1.
    # Sigue siendo resoluble saltando por encima de la roca.
    "corredor_bloqueado": {(7, 10): "R"},
}

# --- Parámetros por defecto (se pueden sobreescribir desde params.yaml) --------
PARAMETROS_AMBIENTE = {
    "bateria_inicial": 100.0,   # %
    "max_pasos": 200,           # pasos de 1 s → límite de tiempo del episodio
    "alcance_sensor": 5.0,      # m
    "ruido_sensor": 0.1,        # m, desviación estándar con cielo despejado
    "gamma_moldeado": 1.0,      # 1.0 → un ciclo cerrado suma exactamente 0 de progreso
}

RECOMPENSAS = {
    "paso": -0.05,            # cada segundo cuesta
    "consumo": -0.02,         # por cada % de batería gastado
    "progreso": 0.5,          # por metro de ruta restante que se acorta (moldeado por potencial)
    "baliza": 10.0,           # agarrar la baliza correcta, una sola vez
    "agarrar_invalido": -1.0, # agarrar fuera de lugar o repetido
    "choque": -1.0,           # chocar con muro, roca o límite del mapa
    "caida": -25.0,           # caer en una grieta → fracaso
    "sin_bateria": -15.0,     # agotar la batería → fracaso
    "mision": 30.0,           # volver a la base con ambas balizas
    "bateria_restante": 0.1,  # bono por cada % de batería al terminar la misión
}

COSTOS = {
    "agarrar": 0.3,  # % batería
    "choque": 0.5,   # % batería extra por golpe
}


def costo_salto(gravedad):
    """Batería (%) que cuesta un salto: más gravedad, más energía."""
    return 1.0 + 2.0 * gravedad / G_TIERRA


def prob_sobrevuelo(gravedad):
    """Con poca gravedad el salto puede pasarse una celda de largo."""
    return 0.3 * max(0.0, 1.0 - gravedad / G_TIERRA)


def factor_traccion(gravedad):
    """Con poca gravedad hay menos agarre: el hielo desliza más."""
    return 1.0 + 0.5 * max(0.0, (G_TIERRA - gravedad) / G_TIERRA)
