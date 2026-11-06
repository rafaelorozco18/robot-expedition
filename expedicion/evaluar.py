"""Versiones del robot, escenarios fijos, episodios y métricas."""

import itertools
import json
from pathlib import Path

import numpy as np

from .ambiente import BipedoEnv
from .experimentos import carpeta_datos, carpeta_metricas, carpeta_modelos


class SinEntrenar:
    """Sin red: las articulaciones solo intentan conservar la postura inicial."""
    def actuar(self, obs, env):
        return np.zeros(env.action_space.shape)


class Aleatorio:
    def __init__(self, semilla):
        self.rng = np.random.default_rng(semilla)

    def actuar(self, obs, env):
        return self.rng.uniform(-1, 1, env.action_space.shape)


class Politica:
    """Red entrenada con PPO, sin exploración."""
    def __init__(self, ruta):
        from stable_baselines3 import PPO
        self.modelo = PPO.load(ruta, device="cpu")

    def actuar(self, obs, env):
        return self.modelo.predict(obs, deterministic=True)[0]


def fotos_de(exp, semilla):
    carpeta = carpeta_modelos(exp) / f"semilla-{semilla}" / "fotos"
    return sorted(carpeta.glob("paso-*.zip"))


def paso_de(ruta):
    return int(Path(ruta).stem.split("-")[1])


def campeon(exp):
    ruta = carpeta_metricas(exp) / "evaluacion.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text())["campeon"]


def generar_escenarios(exp):
    e = exp["evaluacion"]
    rng = np.random.default_rng(e["semilla"])
    escenarios = []
    for planeta, pert in itertools.product(e["planetas"], e["perturbaciones"]):
        for _ in range(e["episodios_por_condicion"]):
            escenarios.append({"id": len(escenarios), "planeta": planeta, "perturbacion": pert,
                               "semilla": int(rng.integers(0, 2**31 - 1))})
    return escenarios


def correr_episodio(exp, agente, escenario, grabar=False, cada=2):
    env = BipedoEnv(exp)
    obs, _ = env.reset(seed=escenario["semilla"], options={
        "planeta": escenario["planeta"], "perturbacion": escenario["perturbacion"]})
    bodies = range(1, env.model.nbody)
    total, inclinacion_max = 0.0, 0.0
    cuadros = []

    def cuadro(accion, r, desglose):
        izq, der, _ = env.contactos()
        return {
            "t": round(env.pasos * env.dt, 3),
            "cuerpos": [[round(float(v), 4) for v in (*env.data.xpos[b], *env.data.xquat[b])] for b in bodies],
            "torques": [round(float(v), 3) for v in env.torques_relativos()],
            "angulos": [round(float(v), 3) for v in env.angulos()],
            "altura": round(env.altura_torso(), 3),
            "altura_rel": round(env.altura_torso() / env.altura_pie, 3),
            "inclinacion": round(env.inclinacion_grados(), 1),
            "velocidad": round(float(np.linalg.norm(env.data.qvel[:3])), 3),
            "pies": [izq, der],
            "recompensa": round(r, 3), "total": round(total, 2),
            "desglose": {k: round(float(v), 3) for k, v in desglose.items()},
            "empujon": bool(env.empujado),
            "orden": env.tarea.orden(env),
            "distancia": round(env.distancia(), 2),
            "piso": env.piso_bajo_torso(),
        }

    if grabar:
        cuadros.append(cuadro(np.zeros(env.model.nu), 0.0, {}))
        env.empujado = False
    terminado = truncado = False
    hubo_empujon = False
    while not (terminado or truncado):
        accion = agente.actuar(obs, env)
        obs, r, terminado, truncado, info = env.step(accion)
        total += r
        inclinacion_max = max(inclinacion_max, env.inclinacion_grados())
        hubo_empujon = hubo_empujon or env.empujado
        if grabar and (env.pasos % cada == 0 or terminado or truncado or env.empujado):
            cuadros.append(cuadro(accion, r, info["desglose"]))

    segundos = env.pasos * env.dt
    resumen = {**escenario, "exito": bool(env.tarea.exito(env, truncado)), "segundos": round(segundos, 2),
               "motivo": env.motivo or ("cumplió la meta" if env.tarea.exito(env, truncado) else "no cumplió la meta"), "titulo_exito": env.tarea.titulo_exito,
               "detalle": env.tarea.resumen(env), "recompensa": round(total, 1),
               "energia_j": round(env.energia, 1), "inclinacion_max": round(inclinacion_max, 1),
               "distancia": round(env.distancia(), 2),
               "tramos": [[t["x0"], t["x1"], t["tipo"]] for t in env.tramos],
               "altura_final": round(env.altura_torso() / env.altura_pie, 3)}
    return resumen, cuadros


def _metricas(filas):
    return {
        "episodios": len(filas),
        "tasa_exito": round(float(np.mean([f["exito"] for f in filas])), 3),
        "segundos_medios": round(float(np.mean([f["segundos"] for f in filas])), 2),
        "energia_media_j": round(float(np.mean([f["energia_j"] for f in filas])), 1),
        "inclinacion_max_media": round(float(np.mean([f["inclinacion_max"] for f in filas])), 1),
    }


def resumir(exp, filas):
    res = {"global": _metricas(filas)}
    for planeta in exp["evaluacion"]["planetas"]:
        for pert in exp["evaluacion"]["perturbaciones"]:
            sub = [f for f in filas if f["planeta"] == planeta and f["perturbacion"] == pert]
            if sub:
                res[f"{planeta}.{pert}"] = _metricas(sub)
    return res


def aprueba(exp, res):
    """El criterio se exige en cada planeta, con la perturbación que indique el experimento."""
    pert = exp["aprobar"]["perturbacion"]
    return all(res[f"{pl}.{pert}"]["tasa_exito"] >= exp["aprobar"]["tasa_exito"]
               for pl in exp["evaluacion"]["planetas"])


def evaluar(exp):
    escenarios = json.loads((carpeta_datos(exp) / "escenarios.json").read_text())
    semillas = exp["entrenamiento"]["semillas"]
    resultados, por_semilla = {}, {}
    trayectorias = carpeta_datos(exp) / "trayectorias.jsonl"
    with open(trayectorias, "w") as f:
        for nombre, agente in [("sin_entrenar", SinEntrenar()), ("aleatorio", Aleatorio(0))]:
            filas = [correr_episodio(exp, agente, esc)[0] for esc in escenarios]
            resultados[nombre] = resumir(exp, filas)
            for fila in filas:
                f.write(json.dumps({"agente": nombre, **fila}) + "\n")
        for semilla in semillas:
            ruta = carpeta_modelos(exp) / f"semilla-{semilla}" / "experto.zip"
            if not ruta.exists():
                continue
            filas = [correr_episodio(exp, Politica(ruta), esc)[0] for esc in escenarios]
            por_semilla[str(semilla)] = resumir(exp, filas)
            for fila in filas:
                f.write(json.dumps({"agente": f"semilla-{semilla}", **fila}) + "\n")

    # Campeón: mejor tasa global; en empate, menor energía.
    mejor = max(por_semilla, key=lambda s: (por_semilla[s]["global"]["tasa_exito"],
                                            -por_semilla[s]["global"]["energia_media_j"]))
    resultado = {"experimento": exp["id"], "campeon": int(mejor), "agentes": resultados,
                 "semillas": por_semilla, "aprobado": aprueba(exp, por_semilla[mejor])}
    carpeta_metricas(exp).mkdir(parents=True, exist_ok=True)
    (carpeta_metricas(exp) / "evaluacion.json").write_text(json.dumps(resultado, indent=2))
    return resultado


def evaluar_progreso(exp):
    """Evalúa cada foto del campeón, sin exploración, en un subconjunto fijo de escenarios."""
    semilla = campeon(exp)
    escenarios = json.loads((carpeta_datos(exp) / "escenarios.json").read_text())
    vistos, sub = {}, []
    for esc in escenarios:
        clave = (esc["planeta"], esc["perturbacion"])
        vistos[clave] = vistos.get(clave, 0) + 1
        if esc["perturbacion"] == exp["aprobar"]["perturbacion"] and vistos[clave] <= exp["evaluacion"]["episodios_por_foto"]:
            sub.append(esc)
    filas = []
    for ruta in fotos_de(exp, semilla):
        agente = Politica(ruta)
        res = [correr_episodio(exp, agente, esc)[0] for esc in sub]
        filas.append({"paso": paso_de(ruta), **_metricas(res), **{
            f"exito_{pl}": round(float(np.mean([r["exito"] for r in res if r["planeta"] == pl])), 3)
            for pl in exp["evaluacion"]["planetas"]}})
        print(filas[-1], flush=True)
    (carpeta_metricas(exp) / "progreso.json").write_text(json.dumps(
        {"semilla": semilla, "episodios_por_foto": len(sub), "fotos": filas}, indent=1))
    return filas


def regresion(exp):
    """Prueba al campeón en las pruebas de los experimentos anteriores."""
    from . import experimentos as X
    semilla = campeon(exp)
    agente = Politica(carpeta_modelos(exp) / f"semilla-{semilla}" / "experto.zip")
    resultado = {}
    for previo in X.listar():
        if previo["id"] > exp["id"] or previo["estado"] == "pendiente":
            continue
        escenarios = json.loads((carpeta_datos(previo) / "escenarios.json").read_text())
        pert = previo["aprobar"]["perturbacion"]
        sub = [e for e in escenarios if e["perturbacion"] == pert][:12]
        filas = [correr_episodio(previo, agente, e)[0] for e in sub]
        resultado[previo["id"]] = round(float(np.mean([f["exito"] for f in filas])), 3)
    (carpeta_metricas(exp) / "regresion.json").write_text(json.dumps(resultado, indent=1))
    return resultado
