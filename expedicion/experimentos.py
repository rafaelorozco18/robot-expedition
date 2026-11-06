"""Catálogo de experimentos: cada uno es un archivo en experimentos/."""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "experimentos"


def listar():
    return [yaml.safe_load(r.read_text()) for r in sorted(CARPETA.glob("exp-*.yaml"))]


def cargar(identificador):
    for exp in listar():
        if exp["id"] == identificador:
            return exp
    raise ValueError(f"Experimento desconocido: {identificador}")


def carpeta_modelos(exp):
    return RAIZ / "models" / exp["id"]


def carpeta_metricas(exp):
    return RAIZ / "metrics" / exp["id"]


def carpeta_datos(exp):
    return RAIZ / "data" / exp["id"]
