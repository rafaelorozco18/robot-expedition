"""Entrenamiento con PPO y registro de cada corrida en MLflow."""

import json
import subprocess
import time
from collections import deque
from pathlib import Path

import numpy as np

from .ambiente import BipedoEnv
from .experimentos import RAIZ, carpeta_metricas, carpeta_modelos

URI_MLFLOW = f"sqlite:///{RAIZ / 'mlflow.db'}"


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "sin-commit"


def _crear_entorno(exp, semilla):
    def crear():
        from stable_baselines3.common.monitor import Monitor
        env = Monitor(BipedoEnv(exp, entrenando=True))
        env.reset(seed=semilla)
        return env
    return crear


def entrenar(exp, semilla, pasos=None, usar_mlflow=True, hilos=2):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    torch.set_num_threads(hilos)
    p = exp["entrenamiento"]
    total = pasos or p["pasos"]
    salida = carpeta_modelos(exp) / f"semilla-{semilla}"
    fotos = salida / "fotos"
    fotos.mkdir(parents=True, exist_ok=True)
    for vieja in fotos.glob("*.zip"):
        vieja.unlink()
    metricas = carpeta_metricas(exp)
    metricas.mkdir(parents=True, exist_ok=True)

    run = None
    if usar_mlflow:
        import mlflow
        mlflow.set_tracking_uri(URI_MLFLOW)
        mlflow.set_experiment(f"{exp['id']}-{exp['titulo'].lower().replace(' ', '-')}")
        run = mlflow.start_run(run_name=f"semilla-{semilla}")
        mlflow.log_params({f"ent.{k}": v for k, v in p.items() if k != "semillas"})
        mlflow.log_params({f"amb.{k}": v for k, v in exp["ambiente"].items()})
        mlflow.log_params({f"rec.{k}": v for k, v in exp["recompensa"].items()})
        mlflow.log_param("semilla", semilla)
        mlflow.set_tags({"git_commit": git_commit(), "robot": exp["robot"], "parte_de": str(exp["parte_de"])})

    curva = []
    cada_foto = total // p["fotos"]

    class Registro(BaseCallback):
        """Guarda fotos del modelo y la curva con la exploración activa."""

        def __init__(self):
            super().__init__()
            self.duracion = deque(maxlen=100)
            self.recompensa = deque(maxlen=100)
            self.proxima = 0

        def _foto(self):
            self.model.save(fotos / f"paso-{self.num_timesteps:09d}.zip")
            self.proxima += cada_foto

        def _on_training_start(self):
            self._foto()

        def _on_step(self):
            for info in self.locals["infos"]:
                if "episode" in info:
                    self.duracion.append(bool(info.get("TimeLimit.truncated", False) or info.get("truncado")))
                    self.recompensa.append(info["episode"]["r"])
            if self.num_timesteps >= self.proxima:
                self._foto()
                if self.duracion:
                    fila = {"paso": self.num_timesteps,
                            "tasa_exito": round(float(np.mean(self.duracion)), 3),
                            "recompensa_media": round(float(np.mean(self.recompensa)), 1)}
                    curva.append(fila)
                    print(fila, flush=True)
                    if run:
                        mlflow.log_metrics({k: v for k, v in fila.items() if k != "paso"},
                                           step=fila["paso"])
            return True

    env = SubprocVecEnv([_crear_entorno(exp, semilla * 1000 + i) for i in range(p["entornos"])])
    modelo = PPO("MlpPolicy", env, device="cpu", seed=semilla, verbose=0,
                 n_steps=p["n_steps"], batch_size=p["batch_size"], n_epochs=p["n_epochs"],
                 learning_rate=p["learning_rate"], gamma=p["gamma"], gae_lambda=p["gae_lambda"],
                 clip_range=p["clip_range"],
                 policy_kwargs={"net_arch": p["red"], "log_std_init": p["log_std_init"]})
    t0 = time.time()
    modelo.learn(total, callback=Registro())
    segundos = time.time() - t0
    env.close()

    modelo.save(fotos / f"paso-{modelo.num_timesteps:09d}.zip")
    modelo.save(salida / "experto.zip")
    resumen = {"semilla": semilla, "pasos": int(modelo.num_timesteps), "segundos": round(segundos, 1),
               "pasos_por_segundo": round(modelo.num_timesteps / segundos),
               "git_commit": git_commit(), "mlflow_run_id": run.info.run_id if run else None}
    (salida / "corrida.json").write_text(json.dumps(resumen, indent=2))
    (salida / "curva.json").write_text(json.dumps(curva))
    if run:
        mlflow.log_metrics({"segundos": resumen["segundos"],
                            "pasos_por_segundo": resumen["pasos_por_segundo"]})
        mlflow.log_artifact(str(salida / "experto.zip"), artifact_path="modelo")
        mlflow.end_run()
    return resumen
