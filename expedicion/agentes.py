"""Versiones del robot: aleatorio, codicioso (heurística) y Q-learning (aprendiz / experto)."""

from pathlib import Path

import numpy as np

from . import config as C

LADO = 23  # dx, dy ∈ [-11, 11]
N_ESTADOS = 3 * LADO * LADO * len(C.NOMBRES_CLIMA) * len(C.NOMBRES_GRAVEDAD)
VALORES_G = np.array([C.GRAVEDADES[n] for n in C.NOMBRES_GRAVEDAD])


def discretizar(obs):
    """Convierte la observación en un índice de tabla usando solo lo que el agente ve.

    (etapa, dx, dy) identifica la celda porque cada etapa tiene un objetivo fijo;
    clima y gravedad cambian la física, así que también entran al estado.
    """
    dx, dy = (int(v) + LADO // 2 for v in obs["objetivo"])
    g = int(np.abs(VALORES_G - float(obs["gravedad"][0])).argmin())
    return (((int(obs["etapa"]) * LADO + dx) * LADO + dy) * len(C.NOMBRES_CLIMA)
            + int(obs["clima"])) * len(C.NOMBRES_GRAVEDAD) + g


class Aleatorio:
    nombre = "aleatorio"
    descripcion = "Elige cualquiera de las 9 acciones al azar. Línea base mínima."

    def __init__(self, semilla=None):
        self.rng = np.random.default_rng(semilla)

    def actuar(self, obs):
        return int(self.rng.integers(len(C.ACCIONES)))


class Codicioso:
    nombre = "codicioso"
    descripcion = ("Heurística sin aprendizaje: va en línea recta al objetivo, "
                   "salta si un rayo detecta un obstáculo pegado. No conoce el terreno.")

    # índice de rayo para cada dirección
    RAYO = {"N": 0, "E": 2, "S": 4, "O": 6}

    def __init__(self, semilla=None):
        self.rng = np.random.default_rng(semilla)

    def actuar(self, obs):
        dx, dy = (int(v) for v in obs["objetivo"])
        if dx == 0 and dy == 0:
            return C.AGARRAR
        candidatas = []
        if dx:
            candidatas.append("E" if dx > 0 else "O")
        if dy:
            candidatas.append("S" if dy > 0 else "N")
        if abs(dy) > abs(dx):
            candidatas.reverse()
        for d in candidatas:
            if obs["rayos"][self.RAYO[d]] > 0.8:
                return ["N", "S", "E", "O"].index(d)
        if self.rng.random() < 0.5:  # obstáculo pegado: intenta saltarlo
            return 4 + ["N", "S", "E", "O"].index(candidatas[0])
        return int(self.rng.integers(4))


class AgenteQ:
    """Política voraz sobre una tabla Q aprendida."""

    def __init__(self, ruta, nombre="experto", descripcion=""):
        datos = np.load(ruta)
        self.q = datos["q"]
        self.episodios = int(datos["episodios"])
        self.nombre = nombre
        self.descripcion = descripcion

    def valores(self, obs):
        return self.q[discretizar(obs)]

    def actuar(self, obs):
        fila = self.valores(obs)
        return int(np.flatnonzero(fila == fila.max())[0])


DESCRIPCIONES = {
    "experto": "Q-learning entrenado completo: domina el mapa con cualquier clima y gravedad.",
    "aprendiz": "La misma tabla Q, guardada al inicio del entrenamiento: todavía explora a ciegas.",
    "codicioso": Codicioso.descripcion,
    "aleatorio": Aleatorio.descripcion,
}


def cargar_agente(nombre, carpeta_modelos="models", semilla=None):
    if nombre == "aleatorio":
        return Aleatorio(semilla)
    if nombre == "codicioso":
        return Codicioso(semilla)
    if nombre in ("experto", "aprendiz"):
        ruta = Path(carpeta_modelos) / f"q_{nombre}.npz"
        if not ruta.exists():
            raise FileNotFoundError(f"No existe {ruta}. Entrena primero: expedicion entrenar")
        return AgenteQ(ruta, nombre, DESCRIPCIONES[nombre])
    raise ValueError(f"Agente desconocido: {nombre}")


def agentes_disponibles(carpeta_modelos="models"):
    lista = []
    for nombre in ["experto", "aprendiz", "codicioso", "aleatorio"]:
        listo = nombre in ("codicioso", "aleatorio") or \
            (Path(carpeta_modelos) / f"q_{nombre}.npz").exists()
        lista.append({"id": nombre, "descripcion": DESCRIPCIONES[nombre], "disponible": listo})
    return lista
