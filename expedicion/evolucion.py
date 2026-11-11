"""Cómo aprendió el robot: cinco etapas por experimento.

Se prueban, en un mismo escenario fijo de Marte, el robot sin entrenar, algunas fotos de sus
antecesores y todas las fotos de este entrenamiento (densas al inicio). De ellas se eligen:

1. Fracaso absoluto: el peor intento.
2. Fracaso, pero mejor: un intento fallido a mitad de camino entre el peor y el mejor fallido.
3. Punto de inflexión: el mejor intento que todavía falla.
4. Cumplido: el primero que cumple el objetivo.
5. Perfeccionado: el que lo cumple con la mejor calidad de movimiento.

Cada etapa se recorta al tramo que muestra el contraste.
"""

import json

from .evaluar import Politica, SinEntrenar, campeon, correr_episodio, fotos_de, paso_de
from .experimentos import cargar, carpeta_datos, carpeta_metricas, carpeta_modelos

PLANETAS_VISOR = ["marte"]
FOTOS_POR_ANTECESOR = 4
ETAPAS = ["Fracaso absoluto", "Fracaso, pero mejor", "Punto de inflexión", "Cumplido", "Perfeccionado"]


def linaje(exp):
    """Antecesores desde la raíz, sin incluir al experimento."""
    if "linaje" in exp:
        return [cargar(i) for i in exp["linaje"]]
    if not exp["parte_de"]:
        return []
    padre = cargar(exp["parte_de"])
    return linaje(padre) + [padre]


def _muestrear(fotos, n):
    if len(fotos) <= n:
        return fotos
    return [fotos[round(i * (len(fotos) - 1) / (n - 1))] for i in range(n)]


def _puntaje(exp, r):
    """Éxitos por encima de 1, ordenados por calidad; fallos entre 0 y 0,95 según su avance."""
    if r["exito"]:
        return 1.0 + r["calidad"] / 1000
    minimo = exp.get("parametros", {}).get("calidad_min")
    factor = min(1.0, r["calidad"] / minimo) if minimo else 1.0
    return 0.95 * r["avance"] * (0.5 + 0.5 * factor)


def _clip(exp, r, cuadros):
    """Ventana [inicio, fin, velocidad] con el tramo que importa."""
    fin = cuadros[-1]["t"]
    cae = not r["exito"] and r["motivo"] not in ("no cumplió la meta", "cumplió la meta")
    if cae:
        return [round(max(0.0, fin - 6.0), 2), fin, 1]
    if exp["tarea"] in ("esquina", "curva", "recorrido"):
        return [0.0, fin, 2.5]
    if exp["tarea"] == "marcha":
        return [0.0, round(min(fin, 14.0), 2), 1.5]
    return [0.0, round(min(fin, 8.0), 2), 1]


def _texto(exp, r):
    calidad = f" · calidad {r['calidad']:.0f}/100" if r.get("calidad") is not None else ""
    if r["exito"]:
        return f"{r['titulo_exito']}{calidad}" + (f" · {r['detalle']}" if r["detalle"] else "")
    if r["motivo"] != "no cumplió la meta":
        extra = f" · {r['detalle']}" if r["detalle"] and exp["tarea"] != "de_pie" else ""
        return f"A los {r['segundos']:.1f} s: {r['motivo']}{extra}"
    meta = exp.get("parametros", {}).get("distancia_m")
    if exp["tarea"] == "marcha" and meta:
        if r["distancia"] < 0.3:
            return f"Se queda en su sitio{calidad}"
        if r["distancia"] < meta:
            return f"Avanza {r['distancia']:.1f} m pero no llega a la meta{calidad}"
        return f"Llega, pero sin la calidad pedida: {r['calidad']:.0f}/100 de {exp['parametros'].get('calidad_min', '—')}"
    return f"No cumple el objetivo{calidad}" + (f" · {r['detalle']}" if r["detalle"] else "")


def _elegir(filas):
    """Devuelve las cinco etapas (o menos si el experimento no llegó a cumplirse)."""
    exitos = [i for i, f in enumerate(filas) if f["exito"]]
    if exitos:
        cumplido = exitos[0]
        posteriores = [i for i in exitos if i != cumplido]
        perfecto = max(posteriores, key=lambda i: (filas[i]["puntaje"], i)) if posteriores else None
        fallos = [i for i, f in enumerate(filas[:cumplido]) if not f["exito"]]
    else:
        cumplido = perfecto = None
        fallos = [i for i, f in enumerate(filas)]
    if not fallos:
        fallos = [0]
    peor = min(fallos, key=lambda i: (filas[i]["puntaje"], i))
    tras_peor = [i for i in fallos if i > peor] or fallos
    inflexion = max(tras_peor, key=lambda i: (filas[i]["puntaje"], i))
    medio = (filas[peor]["puntaje"] + filas[inflexion]["puntaje"]) / 2
    entre = [i for i in fallos if peor < i < inflexion] or [i for i in fallos if i not in (peor, inflexion)]
    intermedio = min(entre, key=lambda i: abs(filas[i]["puntaje"] - medio)) if entre else None
    elegidos = [peor, intermedio, inflexion, cumplido, perfecto]
    etapas = []
    for nombre, i in zip(ETAPAS, elegidos):
        if i is not None and all(i != e["indice"] for e in etapas):
            etapas.append({**filas[i], "indice": i, "etapa": nombre})
    if cumplido is None:
        etapas[-1]["etapa"] = "Mejor intento (aún no cumple)"
    return etapas


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
        # Escenario donde el experto muestra lo aprendido con su mejor calidad.
        pruebas = [(correr_episodio(exp, experto, e)[0], e) for e in candidatos[:6]]
        logrados = [p for p in pruebas if p[0]["exito"]]
        esc = max(logrados, key=lambda p: p[0]["calidad"])[1] if logrados else candidatos[0]
        filas = []
        for nombre, paso, origen, fuente in agentes:
            agente = fuente() if fuente is SinEntrenar else Politica(fuente)
            r, cuadros = correr_episodio(exp, agente, esc, grabar=True)
            tasa = tasas.get(paso, {}).get(f"exito_{planeta}") if origen == exp["id"] and paso is not None else None
            filas.append({"agente": nombre, "paso": paso, "origen": origen, "exito": r["exito"],
                          "segundos": r["segundos"], "distancia": r["distancia"], "calidad": r["calidad"],
                          "avance": r["avance"], "puntaje": round(_puntaje(exp, r), 4),
                          "texto": _texto(exp, r), "clip": _clip(exp, r, cuadros), "tasa": tasa})
        hitos = _elegir(filas)
        salida["planetas"][planeta] = {"semilla": esc["semilla"], "hitos": hitos,
                                       "mejora": round(hitos[-1]["puntaje"] - hitos[0]["puntaje"], 3)}
    salida["recomendado"] = PLANETAS_VISOR[0]
    (carpeta_metricas(exp) / "evolucion.json").write_text(json.dumps(salida, indent=1, ensure_ascii=False))
    return salida
