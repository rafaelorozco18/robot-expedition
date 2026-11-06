"""Registra al campeón de un experimento en el Model Registry de MLflow."""

import json

from .entrenar import URI_MLFLOW
from .evaluar import campeon
from .experimentos import carpeta_metricas, carpeta_modelos


def registrar(exp):
    import mlflow
    import mlflow.pyfunc
    import pandas as pd

    class Politica(mlflow.pyfunc.PythonModel):
        def load_context(self, context):
            from stable_baselines3 import PPO
            self.modelo = PPO.load(context.artifacts["modelo"], device="cpu")

        def predict(self, context, model_input, params=None):
            return self.modelo.predict(model_input.to_numpy(dtype="float32"), deterministic=True)[0]

    semilla = campeon(exp)
    carpeta = carpeta_modelos(exp) / f"semilla-{semilla}"
    corrida = json.loads((carpeta / "corrida.json").read_text())
    evaluacion = json.loads((carpeta_metricas(exp) / "evaluacion.json").read_text())
    nombre = f"robot-{exp['id']}"

    mlflow.set_tracking_uri(URI_MLFLOW)
    with mlflow.start_run(run_id=corrida["mlflow_run_id"]):
        m = evaluacion["semillas"][str(semilla)]
        for grupo, valores in m.items():
            mlflow.log_metric(f"prueba.{grupo}.tasa_exito", valores["tasa_exito"])
        mlflow.set_tag("campeon", "si")
        info = mlflow.pyfunc.log_model(
            name="politica", python_model=Politica(),
            artifacts={"modelo": str(carpeta / "experto.zip")},
            registered_model_name=nombre)
    cliente = mlflow.MlflowClient()
    version = info.registered_model_version
    cliente.set_registered_model_alias(nombre, "campeon", version)
    cliente.set_model_version_tag(nombre, version, "aprobado", str(evaluacion["aprobado"]))
    cliente.set_model_version_tag(nombre, version, "parte_de", str(exp["parte_de"]))
    cliente.set_model_version_tag(nombre, version, "robot", exp["robot"])
    return f"{nombre} v{version}"
