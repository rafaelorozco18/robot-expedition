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
    """Red entrenada con PPO. Actúa con su propio ruido (es una política estocástica), sembrado
    por episodio para que cada episodio se pueda repetir idéntico. En la Serie Marte la media sola,
    sin ruido, no se sostiene: el ruido forma parte de lo que aprendió."""
    def __init__(self, ruta):
        from stable_baselines3 import PPO
        self.modelo = PPO.load(ruta, device="cpu")

    def para_episodio(self, semilla):
        """Actor con su propio generador: episodios simultáneos (servidor) no se mezclan."""
        return _ActorEstocastico(self.modelo.policy, np.random.default_rng(semilla))

    def actuar(self, obs, env):
        return self.modelo.predict(obs, deterministic=False)[0]


class PoliticaNumpy:
    """La misma política sin PyTorch: el actor (58 → 256 → 256 → 12, tanh) exportado a .npz.

    Sirve para el servidor de evaluación en Vercel, donde PyTorch no cabe. `scripts/exportar_politicas.py` la crea
    desde el .zip de Stable-Baselines3 y comprueba que la media de la acción coincide (tests/test_politica_numpy.py).
    El ruido se siembra por episodio igual que en `Politica`, así que un episodio da la misma trayectoria salvo
    diferencias de redondeo de float32."""
    def __init__(self, ruta):
        d = np.load(ruta)
        self.capas = [(d["w0"], d["b0"]), (d["w1"], d["b1"])]
        self.salida = (d["w2"], d["b2"])
        self.desvio = np.exp(d["log_std"]).astype(np.float32)

    def media(self, obs):
        x = np.asarray(obs, dtype=np.float32)
        for w, b in self.capas:
            x = np.tanh(w @ x + b)
        return self.salida[0] @ x + self.salida[1]

    def para_episodio(self, semilla):
        return _ActorNumpy(self, np.random.default_rng(semilla))

    def actuar(self, obs, env):
        return np.clip(self.media(obs), -1.0, 1.0)


class _ActorNumpy:
    def __init__(self, politica, rng):
        self.politica, self.rng = politica, rng

    def actuar(self, obs, env):
        media = self.politica.media(obs)
        return np.clip(media + self.politica.desvio * self.rng.standard_normal(media.shape), -1.0, 1.0)


class _ActorEstocastico:
    def __init__(self, politica, rng):
        self.politica, self.rng = politica, rng

    def actuar(self, obs, env):
        import torch
        with torch.no_grad():
            dist = self.politica.get_distribution(self.politica.obs_to_tensor(obs)[0]).distribution
            media, desvio = dist.mean.numpy()[0], dist.stddev.numpy()[0]
        return np.clip(media + desvio * self.rng.standard_normal(media.shape), -1.0, 1.0)


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
    if hasattr(agente, "para_episodio"):
        agente = agente.para_episodio(escenario["semilla"])
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
            "altura_orden": round(float(env.comando[2] * env.altura_pie), 3),
            "pie_orden": round(float(env.comando[3]), 2),
            "distancia": round(env.distancia(), 2),
            "piso": env.piso_bajo_torso(),
            "viento": [round(float(v), 1) for v in env.viento_actual[:2]],
            "rumbo_orden": round(float(env.rumbo_objetivo), 3),
            **({"alcanzadas": int(env.tarea.alcanzadas)} if hasattr(env.tarea, "balizas") else {}),
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
               "altura_final": round(env.altura_torso() / env.altura_pie, 3),
               "avance": round(float(env.tarea.avance(env)), 3),
               "listones": env.listones,
               "balizas": [[round(float(v), 3) for v in b] for b in getattr(env.tarea, "balizas", [])],
               "radio_baliza": env.tarea.t.get("radio_m") if hasattr(env.tarea, "balizas") else None,
               **env.estadisticas()}
    return resumen, cuadros


def _metricas(filas):
    return {
        "episodios": len(filas),
        "tasa_exito": round(float(np.mean([f["exito"] for f in filas])), 3),
        "segundos_medios": round(float(np.mean([f["segundos"] for f in filas])), 2),
        "energia_media_j": round(float(np.mean([f["energia_j"] for f in filas])), 1),
        "inclinacion_max_media": round(float(np.mean([f["inclinacion_max"] for f in filas])), 1),
        "calidad_media": round(float(np.mean([f["calidad"] for f in filas])), 1),
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

    # No olvidar: cada semilla repite los exámenes de aprobar.sin_olvidar.
    previos = {s: examen_previo(exp, carpeta_modelos(exp) / f"semilla-{s}" / "experto.zip",
                                exp["aprobar"].get("sin_olvidar", [])) for s in por_semilla}
    cumple = {s: aprueba(exp, por_semilla[s]) and not olvidados(previos[s]) for s in por_semilla}
    # Campeón: primero la que cumple todo; luego tasa propia más la media de los exámenes
    # anteriores; en empate, menor energía.
    mejor = max(por_semilla, key=lambda s: (
        cumple[s], por_semilla[s]["global"]["tasa_exito"] + float(np.mean(list(previos[s].values()) or [0.0])),
        -por_semilla[s]["global"]["energia_media_j"]))
    resultado = {"experimento": exp["id"], "campeon": int(mejor), "agentes": resultados,
                 "semillas": por_semilla, "examenes_previos": previos,
                 "aprobado": cumple[mejor]}
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


def examen_previo(exp, ruta, ids):
    """Tasa de éxito del modelo en ruta en los exámenes (12 episodios) de los experimentos ids."""
    from . import experimentos as X
    agente = Politica(ruta)
    resultado = {}
    for i in ids:
        previo = X.cargar(i)
        escenarios = json.loads((carpeta_datos(previo) / "escenarios.json").read_text())
        previo = {**previo, "control": exp["control"]}  # el filtro de los servos es del robot que se prueba
        pert = previo["aprobar"]["perturbacion"]
        sub = [e for e in escenarios if e["perturbacion"] == pert][:12]
        filas = [correr_episodio(previo, agente, e)[0] for e in sub]
        resultado[i] = round(float(np.mean([f["exito"] for f in filas])), 3)
    return resultado


def olvidados(tasas):
    """Exámenes anteriores que ya no se aprueban."""
    from . import experimentos as X
    return [i for i, t in tasas.items() if t < X.cargar(i)["aprobar"]["tasa_exito"]]


def regresion(exp):
    """Prueba al campeón en las pruebas de los experimentos anteriores."""
    from . import experimentos as X
    lista = X.listar()  # en el orden de la serie (campo `orden`), no alfabético: exp-107a va antes que exp-107
    hasta = [p["id"] for p in lista].index(exp["id"])
    ids = [p["id"] for p in lista[:hasta + 1] if p["estado"] not in ("pendiente", "descartado")]
    resultado = examen_previo(exp, carpeta_modelos(exp) / f"semilla-{campeon(exp)}" / "experto.zip", ids)
    (carpeta_metricas(exp) / "regresion.json").write_text(json.dumps(resultado, indent=1))
    return resultado
