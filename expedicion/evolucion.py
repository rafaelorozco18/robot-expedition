"""Cómo aprendió el robot: etapas relevantes de cada experimento, por planeta.

Un modelo heredado ya sabe casi todo cuando empieza su experimento, así que se recorre todo su
linaje: las fotos de cada antecesor y las propias se prueban en el mismo escenario fijo de este
experimento. Se conservan la primera, la última y las que cruzan los cuartos de la mejora total,
y cada una se recorta al tramo que muestra el contraste: la caída, el cruce o la reacción al empujón.
"""

import json

from .evaluar import (Politica, SinEntrenar, campeon, correr_episodio, fotos_de, paso_de)
from .experimentos import cargar, carpeta_datos, carpeta_metricas, carpeta_modelos

PLANETAS_VISOR = ["tierra", "marte"]
FOTOS_POR_ANTECESOR = 6


def linaje(exp):
    """Antecesores desde la raíz, sin incluir al experimento."""
    if "linaje" in exp:  # cuando un antecesor se reentrenó después y ya no es el modelo original
        return [cargar(i) for i in exp["linaje"]]
    if not exp["parte_de"]:
        return []
    padre = cargar(exp["parte_de"])
    return linaje(padre) + [padre]


def _muestrear(fotos, n):
    if len(fotos) <= n:
        return fotos
    return [fotos[round(i * (len(fotos) - 1) / (n - 1))] for i in range(n)]


def _avance(exp, r):
    """Puntaje de 0 a 1 para ordenar etapas. 1 es cumplir la tarea."""
    if r["exito"]:
        return 1.0
    meta = exp.get("parametros", {}).get("distancia_m")
    if meta and exp["tarea"] == "marcha":
        return min(0.95, max(r["distancia"], 0.0) / meta)
    return min(0.95, r["segundos"] / exp["ambiente"]["duracion_s"])


def _clip(exp, resumen, cuadros):
    """Ventana (inicio, fin) en segundos con el tramo que importa."""
    fin = cuadros[-1]["t"]
    empujon = next((c["t"] for c in cuadros if c["empujon"]), None)
    if empujon is not None:
        inicio = max(0.0, empujon - 1.5)
        return [round(inicio, 2), round(min(fin, inicio + 7.0), 2)]
    if not resumen["exito"] and resumen["motivo"] != "no cumplió la meta":
        return [round(max(0.0, fin - 6.0), 2), fin]
    if resumen["tramos"] and resumen["exito"]:
        x0 = resumen["tramos"][0][0]
        inicio = next((c["t"] for c in cuadros if c["cuerpos"][0][0] >= x0 - 0.8), 0.0)
        return [round(inicio, 2), round(min(fin, inicio + 9.0), 2)]
    return [0.0, round(min(fin, 7.0), 2)]


def _texto(exp, r):
    if r["exito"]:
        return f"{r['titulo_exito']}" + (f" · {r['detalle']}" if r["detalle"] else "")
    if exp["tarea"] == "marcha":
        avance = max(r["distancia"], 0.0)
        if r["motivo"] == "no cumplió la meta":
            return "Se queda en su sitio" if avance < 0.3 else f"Avanza {avance:.1f} m y no llega a la meta"
        return f"Avanza {avance:.1f} m y cae a los {r['segundos']:.1f} s"
    if r["motivo"] == "no cumplió la meta":
        return f"Aguanta, pero no cumple la orden · {r['detalle']}" if r["detalle"] else "Aguanta, pero no cumple la orden"
    return f"A los {r['segundos']:.1f} s: {r['motivo']}"


def _elegir(filas):
    """Primera, última y las que cruzan 1/4, 1/2 y 3/4 de la mejora total."""
    base, techo = filas[0]["avance"], max(f["avance"] for f in filas)
    elegidas = {0, len(filas) - 1}
    if techo - base >= 0.05:
        for fraccion in (0.25, 0.5, 0.75, 1.0):
            umbral = base + fraccion * (techo - base)
            elegidas.add(next(i for i, f in enumerate(filas) if f["avance"] >= umbral))
    return [filas[i] for i in sorted(elegidas)]


def _tasas(exp):
    datos = json.loads((carpeta_metricas(exp) / "progreso.json").read_text())
    return {f["paso"]: f for f in datos["fotos"]}


def calcular(exp):
    semilla = campeon(exp)
    escenarios = json.loads((carpeta_datos(exp) / "escenarios.json").read_text())
    pert = exp["aprobar"]["perturbacion"]
    agentes = [("sin_entrenar", None, exp["id"], SinEntrenar)]
    for previo in linaje(exp):
        for ruta in _muestrear(fotos_de(previo, campeon(previo)), FOTOS_POR_ANTECESOR):
            agentes.append((f"foto:{previo['id']}:{paso_de(ruta)}", paso_de(ruta), previo["id"], ruta))
    for ruta in fotos_de(exp, semilla):
        agentes.append((f"paso:{paso_de(ruta)}", paso_de(ruta), exp["id"], ruta))
    experto = Politica(carpeta_modelos(exp) / f"semilla-{semilla}" / "experto.zip")
    tasas = _tasas(exp)
    salida = {"perturbacion": pert, "planetas": {}}
    for planeta in PLANETAS_VISOR:
        candidatos = [e for e in escenarios if e["planeta"] == planeta and e["perturbacion"] == pert]
        # Escenario donde el experto muestra lo aprendido, si existe alguno.
        esc = next((e for e in candidatos if correr_episodio(exp, experto, e)[0]["exito"]), candidatos[0])
        filas = []
        for nombre, paso, origen, fuente in agentes:
            agente = fuente() if fuente is SinEntrenar else Politica(fuente)
            r, cuadros = correr_episodio(exp, agente, esc, grabar=True)
            tasa = tasas.get(paso, {}).get(f"exito_{planeta}") if origen == exp["id"] and paso is not None else None
            filas.append({"agente": nombre, "paso": paso, "origen": origen, "exito": r["exito"], "segundos": r["segundos"],
                          "distancia": r["distancia"], "avance": round(_avance(exp, r), 3),
                          "texto": _texto(exp, r), "clip": _clip(exp, r, cuadros), "tasa": tasa})
        hitos = _elegir(filas)
        salida["planetas"][planeta] = {"semilla": esc["semilla"], "hitos": hitos,
                                       "mejora": round(hitos[-1]["avance"] - hitos[0]["avance"], 3)}
    # A igual contraste se prefiere la Tierra: sin red se cae, y en Marte solo se queda quieto.
    tierra, marte = (salida["planetas"][p]["mejora"] for p in PLANETAS_VISOR)
    salida["recomendado"] = "tierra" if tierra >= marte - 0.15 else "marte"
    (carpeta_metricas(exp) / "evolucion.json").write_text(json.dumps(salida, indent=1, ensure_ascii=False))
    return salida
