"""Tabla de comparación de todas las corridas (semillas) de la serie, incluidos los intentos rechazados.

Uso: python scripts/comparacion.py   →   docs/comparacion-experimentos.md y docs/evaluaciones/<exp>.csv
Todo sale de metrics/<exp>/evaluacion.json (examen oficial por semilla) y models/<exp>/semilla-N/corrida.json.
"""
import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from expedicion import experimentos as X  # noqa: E402

SERIE = ["exp-101", "exp-102", "exp-103", "exp-104", "exp-105", "exp-106", "exp-107a", "exp-108", "exp-109", "exp-107"]
NUM = {"exp-101": "1", "exp-102": "2", "exp-103": "3", "exp-104": "4", "exp-105": "5", "exp-106": "6",
       "exp-107a": "7", "exp-108": "8", "exp-109": "9", "exp-107": "7 (terreno, descartado)"}


def pct(v):
    return "—" if v is None else f"{round(100 * v)} %"


def origen(exp, s):
    p = exp["entrenamiento"]
    cont = p.get("continuar_de", {}).get(s) if isinstance(p.get("continuar_de"), dict) else None
    if cont is not None:
        return f"continúa semilla {cont}"
    return f"campeón de {exp['parte_de']}" if exp["parte_de"] else "desde cero"


def main():
    filas_md = []
    resumen = []
    carpeta_csv = RAIZ / "docs" / "evaluaciones"
    carpeta_csv.mkdir(parents=True, exist_ok=True)
    for i in SERIE:
        exp = X.cargar(i)
        ev_ruta = X.carpeta_metricas(exp) / "evaluacion.json"
        if not ev_ruta.exists():
            continue
        ev = json.loads(ev_ruta.read_text())
        minimo = exp["aprobar"]["tasa_exito"]
        minimos = {p: X.cargar(p)["aprobar"]["tasa_exito"] for p in exp["aprobar"].get("sin_olvidar", [])}
        filas_csv = []
        for s, m in sorted(ev["semillas"].items(), key=lambda kv: int(kv[0])):
            ruta = X.carpeta_modelos(exp) / f"semilla-{s}" / "corrida.json"
            corrida = json.loads(ruta.read_text()) if ruta.exists() else {}
            pert = exp["aprobar"].get("perturbacion", "ninguna")
            grupo = m.get(f"marte.{pert}", m["global"])  # la aprobación se decide en esta condición
            tasa = grupo["tasa_exito"]
            empujon = m.get("marte.empujon", {}).get("tasa_exito") if pert != "empujon" else None
            previos = ev.get("examenes_previos", {}).get(s, {})
            olvida = [p for p, mn in minimos.items() if previos.get(p, 0) < mn]
            if int(s) == ev["campeon"] and ev["aprobado"]:
                decision = "**campeón · aprobado**"
            elif tasa >= minimo and not olvida:
                decision = "aprueba (no elegido)"
            elif tasa >= minimo:
                decision = f"rechazado: olvida {', '.join(olvida)}"
            else:
                decision = "rechazado: no llega al mínimo" + (f"; olvida {', '.join(olvida)}" if olvida else "")
            if int(s) == ev["campeon"] and not ev["aprobado"]:
                decision = "campeón (no aprueba): " + decision.split(": ", 1)[-1]
            previos_txt = " · ".join(f"{p[4:]} {pct(v)}" for p, v in previos.items()) or "—"
            filas_md.append(f"| {NUM[i]} | {s} | {origen(exp, int(s))} | {corrida.get('pasos', 0):,} | "
                            f"{round(corrida.get('segundos', 0) / 60)} min | {pct(tasa)} | {pct(empujon)} | {previos_txt} | {decision} | "
                            f"`{corrida.get('mlflow_run_id', '—')[:8]}` |")
            filas_csv.append({"experimento": i, "semilla": s, "origen": origen(exp, int(s)), "pasos": corrida.get("pasos"),
                              "segundos": corrida.get("segundos"), "git_commit": corrida.get("git_commit"),
                              "mlflow_run_id": corrida.get("mlflow_run_id"), "tasa_exito_examen": tasa, "episodios_examen": grupo["episodios"],
                              "tasa_con_empujon": empujon, "calidad_media": grupo.get("calidad_media"),
                              "segundos_medios": grupo.get("segundos_medios"),
                              **{f"previo_{p}": v for p, v in previos.items()}, "decision": decision.replace("*", "")})
        with open(carpeta_csv / f"{i}-semillas.csv", "w", newline="") as f:
            campos = sorted({k for fila in filas_csv for k in fila}, key=lambda k: list(filas_csv[0]).index(k) if k in filas_csv[0] else 99)
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(filas_csv)
        resumen.append((NUM[i], exp["titulo"], len(ev["semillas"]), ev["campeon"], ev["aprobado"]))
    texto = ["# Comparación de experimentos y corridas", "",
             "Generado por `scripts/comparacion.py` desde `metrics/<exp>/evaluacion.json` y `models/<exp>/semilla-N/corrida.json`.",
             "Una **corrida** es una semilla de un experimento (un run de MLflow). Examen oficial: 12 episodios fijos en la",
             "condición que decide la aprobación (sin perturbación), 12 más con un empujón (informativo) y 12 por cada examen",
             "anterior (`aprobar.sin_olvidar`). Se conservan todos los intentos,",
             "también los que no mejoraron. Resultados por episodio de cada campeón: `data/<exp>/trayectorias.jsonl`;",
             "tabla por semilla en CSV: `docs/evaluaciones/<exp>-semillas.csv`.", "",
             "## Resumen", "", "| Exp | Título | Corridas | Campeón | Estado |", "|---|---|---|---|---|"]
    texto += [f"| {n} | {t} | {k} | semilla {c} | {'aprobado' if a else 'no aprobado'} |" for n, t, k, c, a in resumen]
    texto += ["", "## Todas las corridas", "",
              "| Exp | Semilla | Origen | Pasos | Tiempo | Examen propio | Con empujón (informativo) | Exámenes anteriores | Decisión | Run MLflow |",
              "|---|---|---|---|---|---|---|---|---|---|", *filas_md, ""]
    (RAIZ / "docs" / "comparacion-experimentos.md").write_text("\n".join(texto))
    print(f"{len(filas_md)} corridas en docs/comparacion-experimentos.md")


if __name__ == "__main__":
    main()
