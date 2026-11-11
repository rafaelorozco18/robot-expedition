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
        n = X.listar().index(exp) + 1
        calidad = m[f"marte.{pert}"].get("calidad_media", "—") if f"marte.{pert}" in m else "—"
        filas.append(f"| {n} | [{exp['titulo']}](experimentos/{exp['id']}.md) | "
                     f"{'Aprobado' if ev['aprobado'] else 'No aprobado'} | {planetas} | {calidad} | "
                     f"{exp['aprobar']['tasa_exito'] * 100:.0f} % | {c['pasos'] / 1e6:.1f} M | {c['segundos'] / 60:.0f} min |")
    texto = ("# Resultados de la Serie Marte\n\n"
             "Éxito en Marte, medido en escenarios de prueba fijos, en la condición que exige cada experimento.\n"
             "La política actúa con su propio ruido, sembrado por episodio (ver `docs/serie-marte.md`).\n"
             "Los resultados de la serie anterior, con tres planetas, están en el tag `exp-028`.\n\n"
             "| # | Experimento | Resultado | Éxito | Calidad media (0 a 100) | Exigido | Pasos | Tiempo |\n"
             "|---|---|---|---|---|---|---|---|\n" + "\n".join(filas) + "\n")
    ruta = X.RAIZ / "docs" / "resultados.md"
    ruta.write_text(texto)
    return ruta
