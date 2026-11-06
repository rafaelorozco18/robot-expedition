"""Corre experimentos en cadena: entrena, evalúa, reintenta, registra, documenta y versiona."""

import datetime
import json
import subprocess

import yaml

from . import experimentos as X
from .documentar import documentar
from .informe import informe
from .pipeline import generar
from .registro import registrar


def _sh(*cmd):
    subprocess.run(cmd, cwd=X.RAIZ, check=True)


def _editar(id_exp, **cambios):
    ruta = X.CARPETA / f"{id_exp}.yaml"
    d = yaml.safe_load(ruta.read_text())
    for k, v in cambios.items():
        if isinstance(v, dict):
            d.setdefault(k, {}).update(v)
        else:
            d[k] = v
    ruta.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))


def _repro(etapas):
    generar()
    for e in etapas:
        _sh("dvc", "repro", "--single-item", e)


def _anotar(texto):
    linea = f"{datetime.datetime.now():%H:%M} {texto}"
    print(linea, flush=True)
    (X.RAIZ / "metrics").mkdir(exist_ok=True)
    with open(X.RAIZ / "metrics" / "campana.log", "a") as f:
        f.write(linea + "\n")


def correr(i):
    """Devuelve True si el experimento quedó aprobado."""
    _editar(i, estado="activo")
    exp = X.cargar(i)
    _repro([f"escenarios-{i}"])
    while True:
        semillas = X.cargar(i)["entrenamiento"]["semillas"]
        s = semillas[-1]
        _repro([f"entrenar-{i}-s{s}", f"evaluar-{i}"])
        ev = json.loads((X.carpeta_metricas(exp) / "evaluacion.json").read_text())
        _anotar(f"{i} semilla {s}: aprobado={ev['aprobado']}")
        if ev["aprobado"] or len(semillas) > exp["entrenamiento"].get("reintentos", 1):
            break
        _editar(i, entrenamiento={"semillas": [*semillas, s + 1]})
    exp = X.cargar(i)
    _repro([f"progreso-{i}", f"regresion-{i}"])
    _anotar(f"{i}: {registrar(exp)}")
    documentar(exp)
    informe()
    _sh("git", "add", "-A")
    mensaje = (f"{i} {exp['titulo']}: {'aprobado' if ev['aprobado'] else 'no aprobado'}\n\n"
               f"{exp['pregunta']}\nCampeón: semilla {ev['campeon']}.\n\n"
               "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    _sh("git", "commit", "-q", "-m", mensaje)
    _sh("git", "tag", "-f", i)
    return ev["aprobado"]


def campana(ids, hasta=None, seguir=False):
    for i in ids:
        if hasta and datetime.datetime.now().strftime("%H:%M") >= hasta:
            _anotar(f"Hora límite {hasta}: no se inicia {i}")
            return
        if correr(i):
            _anotar(f"{i} aprobado")
        elif seguir:
            _anotar(f"{i} no aprobó: la campaña sigue")
        else:
            _anotar(f"{i} no aprobó: campaña detenida")
            return
