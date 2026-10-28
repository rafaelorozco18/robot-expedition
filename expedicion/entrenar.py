"""Entrenamiento con Q-learning tabular y registro del experimento en MLflow."""

import json
import subprocess
import time
from pathlib import Path

import numpy as np

from .agentes import N_ESTADOS, discretizar
from .ambiente import ExpedicionEnv
from . import config as C


def elegir_accion(q, s, epsilon, rng):
    """ε-greedy con desempate aleatorio."""
    if rng.random() < epsilon:
        return int(rng.integers(q.shape[1]))
    fila = q[s]
    return int(rng.choice(np.flatnonzero(fila == fila.max())))


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "sin-commit"


def entrenar(p_amb, p_ent, carpeta_modelos="models", carpeta_metricas="metrics",
             usar_mlflow=True, verbose=True):
    episodios = p_ent["episodios"]
    alpha, gamma = p_ent["alpha"], p_ent["gamma"]
    eps_ini, eps_fin = p_ent["epsilon_inicial"], p_ent["epsilon_final"]
    fin_decaimiento = int(episodios * p_ent["fraccion_exploracion"])
    guardar_aprendiz = int(episodios * p_ent["fraccion_aprendiz"])
    ventana = p_ent["ventana_metricas"]

    rng = np.random.default_rng(p_ent["semilla"])
    env = ExpedicionEnv(**p_amb)
    q = np.zeros((N_ESTADOS, len(C.ACCIONES)))

    modelos = Path(carpeta_modelos)
    metricas = Path(carpeta_metricas)
    modelos.mkdir(parents=True, exist_ok=True)
    metricas.mkdir(parents=True, exist_ok=True)

    run = None
    if usar_mlflow:
        import mlflow
        mlflow.set_tracking_uri(p_ent.get("mlflow_uri", "sqlite:///mlflow.db"))
        mlflow.set_experiment("robot-expedition")
        run = mlflow.start_run(run_name=f"qlearning-{git_commit()}")
        mlflow.log_params({f"amb.{k}": v for k, v in p_amb.items()})
        mlflow.log_params({f"ent.{k}": v for k, v in p_ent.items() if k != "mlflow_uri"})
        mlflow.set_tags({"git_commit": git_commit(), "ambiente": "RobotExpedition-v0.1",
                         "algoritmo": "q-learning tabular"})

    curva = []
    recompensas, exitos, pasos_ep = [], [], []
    t0 = time.time()
    semillas = rng.integers(0, 2**31 - 1, size=episodios)
    for ep in range(episodios):
        frac = min(1.0, ep / max(1, fin_decaimiento))
        epsilon = eps_ini + (eps_fin - eps_ini) * frac
        obs, info = env.reset(seed=int(semillas[ep]))
        s = discretizar(obs)
        total, terminado = 0.0, False
        while not terminado:
            a = elegir_accion(q, s, epsilon, rng)
            obs, r, term, trunc, info = env.step(a)
            s2 = discretizar(obs)
            futuro = 0.0 if term else gamma * q[s2].max()
            q[s, a] += alpha * (r + futuro - q[s, a])
            s, total = s2, total + r
            terminado = term or trunc
        recompensas.append(total)
        exitos.append(float(info["exito"]))
        pasos_ep.append(info["pasos"])

        if ep + 1 == guardar_aprendiz:
            np.savez_compressed(modelos / "q_aprendiz.npz", q=q, episodios=ep + 1)
        if (ep + 1) % ventana == 0:
            fila = {"episodio": ep + 1, "epsilon": round(epsilon, 4),
                    "recompensa_media": round(float(np.mean(recompensas[-ventana:])), 3),
                    "tasa_exito": round(float(np.mean(exitos[-ventana:])), 3),
                    "pasos_medios": round(float(np.mean(pasos_ep[-ventana:])), 1)}
            curva.append(fila)
            if run:
                mlflow.log_metrics({k: v for k, v in fila.items() if k != "episodio"}, step=ep + 1)
            if verbose:
                print(f"ep {ep + 1:6d} · ε {epsilon:.2f} · recompensa {fila['recompensa_media']:7.2f}"
                      f" · éxito {fila['tasa_exito']:.0%} · pasos {fila['pasos_medios']:.0f}")

    np.savez_compressed(modelos / "q_experto.npz", q=q, episodios=episodios)
    resumen = {
        "episodios": episodios,
        "segundos": round(time.time() - t0, 1),
        "recompensa_final": curva[-1]["recompensa_media"],
        "tasa_exito_final": curva[-1]["tasa_exito"],
        "estados_visitados": int((np.abs(q).sum(axis=1) > 0).sum()),
    }
    with open(metricas / "curva.csv", "w") as f:
        f.write(",".join(curva[0]) + "\n")
        for fila in curva:
            f.write(",".join(str(v) for v in fila.values()) + "\n")
    with open(metricas / "entrenamiento.json", "w") as f:
        json.dump(resumen, f, indent=2)

    tarjeta = {"nombre": "robot-expedition-qlearning", "version": p_ent["version_modelo"],
               "ambiente": "RobotExpedition-v0.1", "git_commit": git_commit(),
               "mlflow_run_id": run.info.run_id if run else None, **resumen}
    with open(modelos / "modelo.json", "w") as f:
        json.dump(tarjeta, f, indent=2)

    if run:
        mlflow.log_metrics({"segundos": resumen["segundos"],
                            "estados_visitados": resumen["estados_visitados"]})
        mlflow.log_artifacts(str(modelos), artifact_path="modelos")
        mlflow.log_artifact(str(metricas / "curva.csv"))
        registrar_modelo(modelos / "q_experto.npz")
        mlflow.end_run()
    return resumen


def registrar_modelo(ruta_q):
    """Registra la tabla Q como modelo pyfunc en el Model Registry de MLflow."""
    import mlflow
    import mlflow.pyfunc

    class PoliticaQ(mlflow.pyfunc.PythonModel):
        def load_context(self, context):
            self.q = np.load(context.artifacts["q_tabla"])["q"]

        def predict(self, context, model_input, params=None):
            # Entrada: columna "estado" con índices de discretizar(obs).
            estados = np.asarray(model_input["estado"], dtype=int)
            return self.q[estados].argmax(axis=1)

    import pandas as pd
    ejemplo = pd.DataFrame({"estado": [0, 1]})
    mlflow.pyfunc.log_model(
        name="politica",
        python_model=PoliticaQ(),
        artifacts={"q_tabla": str(ruta_q)},
        input_example=ejemplo,
        registered_model_name="robot-expedition-qlearning",
    )
