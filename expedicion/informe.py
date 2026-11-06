"""Resumen de todos los experimentos corridos: docs/resultados.md."""

import json

from . import experimentos as X


def informe():
    filas = []
    for exp in X.listar():
        ruta = X.carpeta_metricas(exp) / "evaluacion.json"
        if not ruta.exists():
            continue
        ev = json.loads(ruta.read_text())
        m = ev["semillas"][str(ev["campeon"])]
        c = json.loads((X.carpeta_modelos(exp) / f"semilla-{ev['campeon']}" / "corrida.json").read_text())
        pert = exp["aprobar"]["perturbacion"]
        planetas = " · ".join(f"{m[f'{p}.{pert}']['tasa_exito'] * 100:.0f} %" for p in exp["evaluacion"]["planetas"])
        filas.append(f"| {int(exp['id'][4:])} | [{exp['titulo']}](experimentos/{exp['id']}.md) | "
                     f"{'Aprobado' if ev['aprobado'] else 'No aprobado'} | {planetas} | "
                     f"{exp['aprobar']['tasa_exito'] * 100:.0f} % | {c['pasos'] / 1e6:.1f} M | {c['segundos'] / 60:.0f} min |")
    texto = ("# Resultados de los experimentos\n\n"
             "Éxito sin exploración, medido en escenarios de prueba fijos, en la condición que exige cada experimento.\n\n"
             "| # | Experimento | Resultado | Luna · Marte · Tierra | Exigido | Pasos | Tiempo |\n"
             "|---|---|---|---|---|---|---|\n" + "\n".join(filas) + "\n")
    ruta = X.RAIZ / "docs" / "resultados.md"
    ruta.write_text(texto)
    return ruta
