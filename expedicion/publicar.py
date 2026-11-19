"""Publica una versión completa e independiente de cada experimento para el visor.

El entrenamiento borra y reescribe models/ y metrics/, y un experimento depende de las fotos de sus
antecesores. El visor solo lee publicado/exp-NNN, un enlace que apunta a una copia autosuficiente:
configuración con la que se entrenó, métricas, modelos y las fotos del linaje que usan sus etapas.
Publicar cambia el enlace de un solo golpe, así que siempre se ve una versión entera.
"""

import json
import os
import shutil
import time

from . import experimentos as X
from .evaluar import campeon, fotos_de, paso_de

RAIZ = X.RAIZ / "publicado"
VERSIONES = RAIZ / ".versiones"
METRICAS = ("evaluacion", "progreso", "regresion", "evolucion")


def carpeta(id_exp):
    return RAIZ / id_exp


def publicado(id_exp):
    return (carpeta(id_exp) / "exp.json").exists()


def cargar(id_exp):
    """Configuración publicada, o None si el experimento nunca se ha publicado."""
    ruta = carpeta(id_exp) / "exp.json"
    return json.loads(ruta.read_text()) if ruta.exists() else None


def publicar(exp, config=None, semilla=None):
    """Publica una versión nueva. Por omisión, el campeón; `semilla` promueve otra corrida (queda como versión
    nueva explícita: nunca se sobrescribe una versión anterior, y se puede volver a ella con el rollback)."""
    i = exp["id"]
    semilla = campeon(exp) if semilla is None else semilla
    origen = X.carpeta_modelos(exp) / f"semilla-{semilla}"
    destino = VERSIONES / f"{i}-{time.time_ns()}"
    (destino / "linaje").mkdir(parents=True)
    (destino / "exp.json").write_text(json.dumps(config or exp, ensure_ascii=False, indent=1))
    for nombre in METRICAS:
        shutil.copy(X.carpeta_metricas(exp) / f"{nombre}.json", destino)
    shutil.copy(origen / "experto.zip", destino)
    for nombre in ("curva.json", "corrida.json"):
        shutil.copy(origen / nombre, destino)
    shutil.copytree(origen / "fotos", destino / "fotos")
    evolucion = json.loads((destino / "evolucion.json").read_text())
    for plan in evolucion["planetas"].values():
        for h in plan["hitos"]:
            if h["agente"].startswith("foto:"):
                _, previo, paso = h["agente"].split(":")
                exp_previo = X.cargar(previo)
                fotos = {paso_de(r): r for r in fotos_de(exp_previo, campeon(exp_previo))}
                shutil.copy(fotos[int(paso)], destino / "linaje" / f"{previo}-{paso}.zip")

    enlace, temporal = carpeta(i), RAIZ / f".{i}.nuevo"
    anterior = enlace.resolve() if enlace.exists() else None
    temporal.unlink(missing_ok=True)
    temporal.symlink_to(destino.relative_to(RAIZ))
    os.replace(temporal, enlace)
    # Se conserva la versión anterior por si hay una petición en curso; las más viejas se borran.
    for vieja in VERSIONES.glob(f"{i}-*"):
        if vieja not in (destino, anterior):
            shutil.rmtree(vieja)
    return enlace
