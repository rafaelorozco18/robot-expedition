"""Genera dvc.yaml a partir de los experimentos activos: un solo pipeline para todos."""

import yaml

from . import experimentos as X


def generar():
    etapas = {}
    for exp in X.listar():
        if exp["estado"] == "pendiente":
            continue
        i = exp["id"]
        config = [f"experimentos/{i}.yaml", "experimentos/base.yaml", exp["robot"]]
        padre = [f"metrics/{exp['parte_de']}/evaluacion.json"] if exp["parte_de"] else []
        etapas[f"escenarios-{i}"] = {
            "cmd": f"python -m expedicion escenarios {i}", "deps": config[:2],
            "outs": [f"data/{i}/escenarios.json"]}
        if exp.get("navegador"):  # Exp 9: el navegador se entrena antes que el caminante, que lo usa
            nav = exp["navegador"]
            etapas[f"navegador-{i}"] = {
                "cmd": f"nice -n 10 python -m expedicion navegador {i}",
                "deps": [f"experimentos/{i}.yaml", nav["calibracion"], "expedicion/mundo.py", "expedicion/navegador.py"],
                "outs": [f"models/{i}/navegador"]}
            padre = padre + [f"models/{i}/navegador"]
        modelos = []
        for s in exp["entrenamiento"]["semillas"]:
            carpeta = f"models/{i}/semilla-{s}"
            modelos.append(carpeta)
            etapas[f"entrenar-{i}-s{s}"] = {
                "cmd": f"nice -n 10 python -m expedicion entrenar {i} --semilla {s}",
                "deps": config + padre, "outs": [carpeta]}
        etapas[f"evaluar-{i}"] = {
            "cmd": f"nice -n 10 python -m expedicion evaluar {i}",
            "deps": [f"data/{i}/escenarios.json", *modelos],
            "outs": [f"data/{i}/trayectorias.jsonl"],
            "metrics": [{f"metrics/{i}/evaluacion.json": {"cache": False}}]}
        etapas[f"progreso-{i}"] = {
            "cmd": f"nice -n 10 python -m expedicion progreso {i}",
            "deps": [f"metrics/{i}/evaluacion.json"],
            "metrics": [{f"metrics/{i}/progreso.json": {"cache": False}}]}
        etapas[f"regresion-{i}"] = {
            "cmd": f"nice -n 10 python -m expedicion regresion {i}",
            "deps": [f"metrics/{i}/evaluacion.json"],
            "metrics": [{f"metrics/{i}/regresion.json": {"cache": False}}]}
        etapas[f"evolucion-{i}"] = {
            "cmd": f"nice -n 10 python -m expedicion evolucion {i}",
            "deps": [f"metrics/{i}/progreso.json"],
            "metrics": [{f"metrics/{i}/evolucion.json": {"cache": False}}]}
    encabezado = "# Generado por `expedicion pipeline`. El código queda fijado por el tag de cada experimento.\n"
    (X.RAIZ / "dvc.yaml").write_text(encabezado + yaml.safe_dump({"stages": etapas}, sort_keys=False, allow_unicode=True))
    return list(etapas)
