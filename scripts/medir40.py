"""Mide modelos en 40 episodios nuevos (semillas 3000+) por tarea. Uso: medir40.py ruta [ruta ...]"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from expedicion import experimentos as X
from expedicion.evaluar import Politica, correr_episodio
TAREAS = ["exp-105", "exp-101", "exp-103", "exp-104"]
def uno(a):
    ruta, t = a
    exp = {**X.cargar(t), "control": X.cargar("exp-105")["control"]}
    pol = Politica(Path(ruta))
    return ruta, t, sum(correr_episodio(exp, pol, {"planeta": "marte", "perturbacion": "ninguna", "semilla": 3000 + k})[0]["exito"] for k in range(40))
if __name__ == "__main__":
    with ProcessPoolExecutor(4) as pool:
        for ruta, t, n in pool.map(uno, [(r, t) for r in sys.argv[1:] for t in TAREAS]):
            print(Path(ruta).parent.name if "experto" in ruta else ruta, t, f"{n}/40", flush=True)
