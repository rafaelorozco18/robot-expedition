"""Escenarios de evaluación, ejecución de episodios y métricas por agente."""

import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import config as C
from .agentes import AgenteQ, cargar_agente
from .ambiente import ETAPAS, ExpedicionEnv


def generar_escenarios(p_eval):
    """Dataset de evaluación: combinaciones fijas de clima × gravedad × incidente × semilla."""
    rng = np.random.default_rng(p_eval["semilla"])
    escenarios = []
    for clima, grav, inc in itertools.product(C.NOMBRES_CLIMA, C.NOMBRES_GRAVEDAD,
                                              list(C.INCIDENTES)):
        for _ in range(p_eval["episodios_por_condicion"]):
            escenarios.append({"id": len(escenarios), "clima": clima, "gravedad": grav,
                               "incidente": inc, "semilla": int(rng.integers(0, 2**31 - 1))})
    return escenarios


def _lista(v):
    return [round(float(x), 3) for x in np.asarray(v).ravel()]


def correr_episodio(agente, escenario, p_amb, registrar_cuadros=True):
    """Corre un episodio completo y devuelve resumen + cuadros paso a paso."""
    env = ExpedicionEnv(**p_amb)
    obs, info = env.reset(seed=escenario["semilla"], options={
        "clima": escenario["clima"], "gravedad": escenario["gravedad"],
        "incidente": escenario["incidente"]})

    def cuadro(accion, recompensa, total, obs, info, term=False, trunc=False, q=None):
        return {"paso": info["pasos"], "accion": accion,
                "accion_nombre": C.NOMBRES_ACCION[accion] if accion is not None else None,
                "posicion": list(info["posicion"]), "etapa": info["etapa"],
                "objetivo": ETAPAS[min(info["etapa"], 2)],
                "bateria": round(info["bateria"], 2), "recompensa": round(recompensa, 3),
                "recompensa_total": round(total, 3), "eventos": info["eventos"],
                "ruta_restante": info["ruta_restante"], "condiciones": info["condiciones"],
                "obs": {"rayos": _lista(obs["rayos"]), "objetivo": [int(v) for v in obs["objetivo"]],
                        "velocidad": float(obs["velocidad"][0]),
                        "terreno": C.TERRENOS[C.CODIGOS_TERRENO[obs["terreno"]]]["nombre"]},
                "q": q, "terminado": term, "truncado": trunc}

    es_q = isinstance(agente, AgenteQ)
    total = 0.0
    cuadros = [cuadro(None, 0.0, 0.0, obs, info)] if registrar_cuadros else []
    choques = 0
    terminado = truncado = False
    while not (terminado or truncado):
        q = _lista(agente.valores(obs)) if es_q and registrar_cuadros else None
        accion = agente.actuar(obs)
        obs, r, terminado, truncado, info = env.step(accion)
        total += r
        choques += any(e.startswith("choque") or e == "salto bloqueado" for e in info["eventos"])
        if registrar_cuadros:
            cuadros[-1]["q"] = q
            cuadros.append(cuadro(accion, r, total, obs, info, terminado, truncado))

    resumen = {"agente": agente.nombre, **escenario, "exito": info["exito"],
               "motivo": env.motivo, "balizas": min(info["etapa"], 2), "pasos": info["pasos"],
               "bateria_final": round(info["bateria"], 2), "recompensa": round(total, 3),
               "choques": choques, "cayo": env.motivo == "cayó en una grieta"}
    return resumen, cuadros


def _metricas(filas):
    exitos = [f for f in filas if f["exito"]]
    return {
        "episodios": len(filas),
        "tasa_mision": round(np.mean([f["exito"] for f in filas]), 3),
        "balizas_medias": round(np.mean([f["balizas"] for f in filas]), 3),
        "bateria_final_exito": round(np.mean([f["bateria_final"] for f in exitos]), 2) if exitos else 0.0,
        "pasos_exito": round(np.mean([f["pasos"] for f in exitos]), 1) if exitos else 0.0,
        "choques_medios": round(np.mean([f["choques"] for f in filas]), 2),
        "tasa_caida": round(np.mean([f["cayo"] for f in filas]), 3),
        "recompensa_media": round(np.mean([f["recompensa"] for f in filas]), 2),
    }


def evaluar(escenarios, p_amb, p_eval, carpeta_modelos="models",
            salida_trayectorias="data/trayectorias.jsonl", salida_metricas="metrics/evaluacion.json"):
    Path(salida_trayectorias).parent.mkdir(parents=True, exist_ok=True)
    Path(salida_metricas).parent.mkdir(parents=True, exist_ok=True)
    por_agente = defaultdict(list)
    with open(salida_trayectorias, "w") as f:
        for nombre in p_eval["agentes"]:
            for esc in escenarios:
                agente = cargar_agente(nombre, carpeta_modelos, semilla=esc["semilla"])
                resumen, cuadros = correr_episodio(agente, esc, p_amb)
                por_agente[nombre].append(resumen)
                transiciones = [{"a": c["accion"], "pos": c["posicion"], "r": c["recompensa"],
                                 "bat": c["bateria"], "ev": c["eventos"]} for c in cuadros[1:]]
                f.write(json.dumps({**resumen, "transiciones": transiciones}) + "\n")

    resultado = {}
    for nombre, filas in por_agente.items():
        resultado[nombre] = {"global": _metricas(filas)}
        for inc in C.INCIDENTES:
            resultado[nombre][inc] = _metricas([x for x in filas if x["incidente"] == inc])
        for clima in C.NOMBRES_CLIMA:
            resultado[nombre][f"clima_{clima}"] = _metricas([x for x in filas if x["clima"] == clima])
    with open(salida_metricas, "w") as f:
        json.dump(resultado, f, indent=2)
    return resultado


def evaluar_progreso(escenarios, p_amb, p_eval, carpeta_modelos="models",
                     salida="metrics/progreso.json"):
    """Evalúa cada checkpoint sin exploración (política voraz) en un subconjunto fijo."""
    from .agentes import checkpoints_disponibles
    vistos, subconjunto = defaultdict(int), []
    for esc in escenarios:
        clave = (esc["clima"], esc["gravedad"], esc["incidente"])
        if vistos[clave] < p_eval["semillas_progreso"]:
            vistos[clave] += 1
            subconjunto.append(esc)
    filas = []
    for ep in checkpoints_disponibles(carpeta_modelos):
        agente = cargar_agente(f"ep:{ep}", carpeta_modelos)
        resultados = [correr_episodio(agente, esc, p_amb, registrar_cuadros=False)[0]
                      for esc in subconjunto]
        fila = {"episodio": ep}
        for inc in C.INCIDENTES:
            m = _metricas([r for r in resultados if r["incidente"] == inc])
            fila.update({f"{inc}.{k}": v for k, v in m.items() if k != "episodios"})
        filas.append(fila)
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w") as f:
        json.dump({"episodios_por_checkpoint": len(subconjunto), "checkpoints": filas}, f, indent=1)
    return filas

