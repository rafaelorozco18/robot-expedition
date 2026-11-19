"""Catálogo de experimentos: base.yaml más lo que cambia cada exp-NNN.yaml."""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "experimentos"


def _mezclar(base, cambios):
    salida = dict(base)
    for k, v in cambios.items():
        salida[k] = _mezclar(salida[k], v) if isinstance(v, dict) and isinstance(salida.get(k), dict) else v
    return salida


def _leer(ruta):
    return yaml.safe_load(ruta.read_text())


def listar():
    base = _leer(CARPETA / "base.yaml")
    exps = [_mezclar(base, _leer(r)) for r in sorted(CARPETA.glob("exp-*.yaml"))]
    # `orden` (opcional) intercala un experimento entre otros: exp-107a va después del 106 y antes del 107.
    return sorted(exps, key=lambda e: float(e.get("orden", e["id"].split("-")[1].rstrip("abcdefghijklmnopqrstuvwxyz"))))


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
