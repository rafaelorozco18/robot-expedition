"""Exporta el registro de MLflow (mlflow.db) para la entrega: el docente lo consulta sin instalar MLflow.

Uso: python scripts/registro_mlflow.py [salida.json]   (por omisión docs/registro-mlflow.json)
Incluye cada experimento de MLflow de la serie, sus runs (parámetros, métricas finales, etiquetas, estado,
duración) y las versiones del Model Registry con sus alias (`campeon`). La base completa (mlflow.db y
mlruns/) se publica además como release del repositorio para recuperarla con la UI de MLflow.
"""
import json
import sys
from pathlib import Path

import mlflow

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from expedicion.entrenar import URI_MLFLOW  # noqa: E402

PREFIJOS = ("exp-101", "exp-102", "exp-103", "exp-104", "exp-105", "exp-106", "exp-107", "exp-108")


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "registro-mlflow.json"
    mlflow.set_tracking_uri(URI_MLFLOW)
    c = mlflow.MlflowClient()
    experimentos = []
    for e in sorted(c.search_experiments(), key=lambda e: e.name):
        if not e.name.startswith(PREFIJOS):
            continue
        runs = []
        for r in c.search_runs([e.experiment_id], max_results=500, order_by=["attributes.start_time ASC"]):
            d = r.data
            runs.append({
                "run_id": r.info.run_id, "nombre": r.info.run_name, "estado": r.info.status,
                "inicio": r.info.start_time, "fin": r.info.end_time,
                "params": d.params, "metricas": d.metrics,
                "tags": {k: v for k, v in d.tags.items() if not k.startswith("mlflow.") or k in ("mlflow.runName",)},
            })
        experimentos.append({"id": e.experiment_id, "nombre": e.name, "runs": runs})
    modelos = []
    for m in c.search_registered_models():
        if not m.name.startswith("robot-exp-1"):
            continue
        versiones = []
        for v in sorted(c.search_model_versions(f"name='{m.name}'"), key=lambda v: int(v.version)):
            versiones.append({"version": int(v.version), "run_id": v.run_id, "estado": v.status,
                              "alias": list(c.get_model_version(m.name, v.version).aliases), "tags": v.tags,
                              "creado": v.creation_timestamp})
        modelos.append({"nombre": m.name, "versiones": versiones})
    datos = {"tracking_uri": "sqlite:///mlflow.db (release mlflow-registro del repositorio)",
             "experimentos": experimentos, "modelos": modelos}
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1, default=str))
    n = sum(len(e["runs"]) for e in experimentos)
    print(f"{len(experimentos)} experimentos, {n} runs, {len(modelos)} modelos registrados → {salida}")


if __name__ == "__main__":
    main()
