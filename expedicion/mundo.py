"""Mundo de exploración del Exp 9: rocas que no se pueden cruzar, parches de piso y balizas en secuencia.

Numpy puro: lo usan igual el ambiente MuJoCo (tarea «exploracion») y el simulador cinemático rápido donde se entrena
el navegador. Así los dos ven exactamente los mismos mundos, sensores y reglas.
"""
import numpy as np

RADIO_ROBOT = 0.55          # m: alcance del robot en planta (medido: un paso lateral llega a 0,67 m del centro)
# El navegador elige hacia dónde ir (rumbo relativo al robot); el controlador del Exp 8, que el caminante ya domina,
# lo ejecuta: gira sobre su eje si el error es grande, si no camina corrigiendo en curva.
DIRECCIONES = np.radians([-90, -60, -30, 0, 30, 60, 90])
NOMBRES_DIRECCION = ["90° a la derecha", "60° a la derecha", "30° a la derecha", "de frente",
                     "30° a la izquierda", "60° a la izquierda", "90° a la izquierda"]


def controlador(e, modo_previo):
    """Mismo controlador que la tarea «balizas» (Exp 8). e: error entre el rumbo deseado y el pedido (rad)."""
    if abs(e) > 0.6 or (modo_previo == "giro" and abs(e) > 0.1):
        return "giro", 0.0, float(np.sign(e) * 0.8)
    if abs(e) < 0.05:
        return "recto", 0.5, 0.0
    return "curva", 0.45, float(np.clip(1.5 * e, -0.25, 0.25))


RADIOS_ROCA = (0.35, 0.44, 0.53, 0.61, 0.7)   # radios posibles (m): en MuJoCo cada roca es un cuerpo mocap de tamaño fijo
N_RAYOS = 15
ANGULOS_RAYOS = np.radians(np.linspace(-105, 105, N_RAYOS))
ALCANCE = 3.0               # m: alcance de los sensores de distancia
N_OBS = N_RAYOS + 3 + len(DIRECCIONES)


def hay_camino(rocas, puntos, lado, paso=0.1, holgura=RADIO_ROBOT + 0.05):
    """¿Se puede ir de cada punto al siguiente sin tocar una roca (inflada por el radio del robot)?
    Rejilla de 10 cm: todos los puntos deben caer en la misma componente libre."""
    try:
        from scipy import ndimage
    except ImportError:
        ndimage = None
    n = int(2 * lado / paso) + 1
    xs = np.linspace(-lado, lado, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    ocupado = np.zeros((n, n), bool)
    for x, y, r in rocas:
        ocupado |= (X - x) ** 2 + (Y - y) ** 2 <= (r + holgura) ** 2
    celdas = [(int(round((p[0] + lado) / paso)), int(round((p[1] + lado) / paso))) for p in puntos]
    if ndimage is None:  # sin scipy (función de Vercel): búsqueda en anchura desde el primer punto
        if any(ocupado[c] for c in celdas):
            return False
        visto = np.zeros_like(ocupado)
        pila = [celdas[0]]
        visto[celdas[0]] = True
        while pila:
            i, j = pila.pop()
            for v in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= v[0] < n and 0 <= v[1] < n and not ocupado[v] and not visto[v]:
                    visto[v] = True
                    pila.append(v)
        return all(visto[c] for c in celdas)
    etiquetas, _ = ndimage.label(~ocupado)
    comp = {int(etiquetas[c]) for c in celdas}
    return 0 not in comp and len(comp) == 1


def _radio(rng, t):
    lo, hi = t["radio_roca_m"]
    validos = [r for r in RADIOS_ROCA if lo - 1e-9 <= r <= hi + 1e-9]
    return float(validos[int(rng.integers(len(validos)))])


def _balizas_separadas(rng, t, lado):
    """Balizas repartidas por el campo: lejos de la salida y lejos entre sí. El orden de visita es el del vecino más
    cercano desde la salida, así la ruta tiene sentido y nunca termina donde empezó."""
    margen = 0.8
    for _ in range(20000):  # cada intento es barato; con 500 a veces no alcanzaba (falló una vez en 2 M de mundos)
        cand = [rng.uniform(-lado + margen, lado - margen, 2) for _ in range(t["balizas"])]
        if any(np.linalg.norm(c) < t["despeje_salida_m"] for c in cand):
            continue
        if any(np.linalg.norm(a - b) < t["separacion_balizas_m"] for i, a in enumerate(cand) for b in cand[i + 1:]):
            continue
        orden, actual, resto = [], np.zeros(2), list(cand)
        while resto:
            k = int(np.argmin([np.linalg.norm(c - actual) for c in resto]))
            actual = resto.pop(k)
            orden.append(actual)
        return orden
    raise RuntimeError("no se pudieron separar las balizas")


def generar(rng, t):
    """Un mundo al azar con solución. t: parámetros de la tarea (yaml del experimento)."""
    lado = t["lado_m"]
    for _ in range(200):
        balizas = _balizas_separadas(rng, t, lado)
        puntos = [np.zeros(2), *balizas]
        rocas = []
        # Rocas que tapan la línea recta entre metas: obligan a elegir rodear por un lado o por el otro.
        for a, b in zip(puntos[:-1], puntos[1:]):
            for _ in range(t["rocas_en_ruta"]):
                f = rng.uniform(0.35, 0.65)
                c = a + f * (b - a) + rng.normal(0, 0.25, 2)
                rocas.append((c[0], c[1], _radio(rng, t)))
        # Rocas dispersas por el campo.
        while len(rocas) < t["rocas"]:
            c = rng.uniform(-lado, lado, 2)
            rocas.append((c[0], c[1], _radio(rng, t)))
        # Ninguna roca encima de la salida ni de una baliza.
        rocas = [(x, y, r) for x, y, r in rocas
                 if all(np.hypot(x - p[0], y - p[1]) > r + t["despeje_meta_m"] for p in puntos)]
        if hay_camino(rocas, puntos, lado):
            # Parches de piso sobre la ruta, en el tramo de llegada a cada baliza (casi recto, lejos de las rocas que
            # obligan a girar): el robot los tiene que pisar para llegar. Girar sobre pisos sueltos es el límite
            # conocido del caminante (Exp 7 de terreno).
            parches = []
            for a, b in zip(puntos[:-1], puntos[1:]):
                tipo = t["tipos_piso"][int(rng.integers(len(t["tipos_piso"])))]
                c = a + rng.uniform(*t.get("parche_en_tramo", [0.3, 0.7])) * (b - a)
                ancho = rng.uniform(*t["lado_parche_m"])
                parches.append((c[0] - ancho / 2, c[0] + ancho / 2, tipo, c[1] - ancho / 2, c[1] + ancho / 2))
            return {"balizas": [p for p in balizas], "rocas": rocas, "parches": parches, "lado": lado}
    raise RuntimeError("no se encontró un mundo con solución")


def rayos(pos, rumbo, rocas, lado):
    """Distancia (0 a 1, en fracción del alcance) a la roca o al borde del campo en cada dirección."""
    ang = rumbo + ANGULOS_RAYOS
    d = np.stack([np.cos(ang), np.sin(ang)], 1)                     # (R, 2)
    mejor = np.full(N_RAYOS, ALCANCE)
    if rocas:
        R = np.asarray(rocas, float)                                 # (K, 3)
        oc = pos[None, :] - R[:, :2]                                 # (K, 2)
        b = d @ oc.T                                                 # (R, K)
        c = (oc ** 2).sum(1) - R[:, 2] ** 2                          # (K,)
        disc = b ** 2 - c[None, :]
        t = -b - np.sqrt(np.where(disc >= 0, disc, 0.0))
        t = np.where((disc >= 0) & (t >= 0), t, np.inf)
        mejor = np.minimum(mejor, t.min(1))
    with np.errstate(divide="ignore", invalid="ignore"):
        for eje in (0, 1):  # bordes del campo
            borde = np.where(d[:, eje] > 0, lado, -lado)
            t = (borde - pos[eje]) / d[:, eje]
            mejor = np.minimum(mejor, np.where(np.isfinite(t) & (t >= 0), t, np.inf))
    return mejor / ALCANCE


def observacion(pos, rumbo, meta, rocas, lado, previa):
    """Lo que ve el navegador: 15 sensores, la meta en ejes del robot y la dirección elegida antes (one-hot)."""
    v = meta - pos
    dist = np.linalg.norm(v)
    ang = np.arctan2(v[1], v[0]) - rumbo
    uno = np.zeros(len(DIRECCIONES))
    uno[previa] = 1.0
    return np.concatenate([rayos(pos, rumbo, rocas, lado), [np.sin(ang), np.cos(ang), min(dist / 8.0, 1.0)], uno]).astype(np.float32)


def choca(pos, rocas, holgura=RADIO_ROBOT):
    if not rocas:
        return False
    R = np.asarray(rocas, float)
    return bool((np.hypot(pos[0] - R[:, 0], pos[1] - R[:, 1]) < R[:, 2] + holgura).any())
