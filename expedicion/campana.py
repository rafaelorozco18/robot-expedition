"""Corre experimentos en cadena: entrena, evalúa, reintenta, registra, documenta y versiona."""

import datetime
import json
import subprocess

import yaml

from . import experimentos as X
from .documentar import documentar
from .informe import informe
from .pipeline import generar
from .publicar import publicar
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
        _sh("dvc", "repro", "--single-item", "--no-run-cache", e)


def _anotar(texto):
    linea = f"{datetime.datetime.now():%H:%M} {texto}"
    print(linea, flush=True)
    (X.RAIZ / "metrics").mkdir(exist_ok=True)
    with open(X.RAIZ / "metrics" / "campana.log", "a") as f:
        f.write(linea + "\n")


def _limite(hasta):
    """Próxima vez que el reloj marque HH:MM (hoy o mañana): la campaña puede cruzar la medianoche."""
    if not hasta:
        return None
    ahora = datetime.datetime.now()
    h, m = map(int, hasta.split(":"))
    limite = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    return limite if limite > ahora else limite + datetime.timedelta(days=1)


def correr(i, hasta=None, limite=None):
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
        if limite and datetime.datetime.now() >= limite:
            _anotar(f"Hora límite {hasta}: {i} no se reintenta")
            break
        _editar(i, entrenamiento={"semillas": [*semillas, s + 1]})
    exp = X.cargar(i)
    _repro([f"progreso-{i}", f"regresion-{i}", f"evolucion-{i}"])
    _anotar(f"{i}: {registrar(exp)}")
    documentar(exp)
    informe()
    publicar(exp)
    _sh("git", "add", "-A")
    mensaje = (f"{i} {exp['titulo']}: {'aprobado' if ev['aprobado'] else 'no aprobado'}\n\n"
               f"{exp['pregunta']}\nCampeón: semilla {ev['campeon']}.\n\n"
               "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    _sh("git", "commit", "-q", "-m", mensaje)
    _sh("git", "tag", "-f", i)
    return ev["aprobado"]


def campana(ids, hasta=None, seguir=False):
    limite = _limite(hasta)
    for i in ids:
        if limite and datetime.datetime.now() >= limite:
            _anotar(f"Hora límite {hasta}: no se inicia {i}")
            return
        if correr(i, hasta, limite):
            _anotar(f"{i} aprobado")
        elif seguir:
            _anotar(f"{i} no aprobó: la campaña sigue")
        else:
            _anotar(f"{i} no aprobó: campaña detenida")
            return
