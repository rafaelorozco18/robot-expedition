"""Pipeline de Robot Expedition orquestado con Prefect (secuencia mínima de la sección 14 del enunciado).

Prefect corre en su propio entorno (~/.venvs/prefect) y llama a la CLI del proyecto (.venv) en cada etapa,
así sus dependencias no tocan las del entrenamiento. DVC sigue siendo quien decide qué recalcular:
si una etapa ya está en dvc.lock con las mismas dependencias, no se repite.

  ~/.venvs/prefect/bin/python pipelines/flujo.py exp-108             # entrena (si falta), evalúa, registra, publica
  ~/.venvs/prefect/bin/python pipelines/flujo.py exp-108 --rollback  # vuelve a la versión publicada anterior

Cada ejecución queda en el registro de Prefect (`prefect flow-run ls`) y en pipelines/ejecuciones/.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

from prefect import flow, get_run_logger, task

RAIZ = Path(__file__).resolve().parents[1]
PY = str(RAIZ / ".venv" / "bin" / "python")
DVC = str(RAIZ / ".venv" / "bin" / "dvc")
REGISTRO = RAIZ / "pipelines" / "ejecuciones"


def _sh(*cmd, check=True):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    salida = (r.stdout + r.stderr).strip()
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} falló ({r.returncode}):\n{salida[-2000:]}")
    return salida


def _py(codigo):
    return json.loads(_sh(PY, "-c", codigo).strip().splitlines()[-1])


@task(name="1 · validar perfil y ambiente")
def validar(exp):
    datos = _py(f"""
import json
from expedicion import experimentos as X
from expedicion.ambiente import BipedoEnv
e = X.cargar({exp!r}); env = BipedoEnv(e); o, _ = env.reset(seed=0)
o2, r, term, trunc, info = env.step(env.action_space.sample())
assert o.shape == env.observation_space.shape and o2.shape == o.shape
print(json.dumps({{"tarea": e["tarea"], "robot": e["robot"], "obs": list(o.shape), "acciones": int(env.action_space.shape[0]),
                  "parte_de": e["parte_de"], "semillas": e["entrenamiento"]["semillas"]}}))""")
    get_run_logger().info(f"Perfil válido: {datos}")
    return datos


@task(name="2 · pruebas de reglas y contrato")
def pruebas():
    salida = _sh(PY, "-m", "pytest", "-q", "tests")
    get_run_logger().info(salida.splitlines()[-1])
    return salida.splitlines()[-1]


@task(name="3 · entrenar o reutilizar checkpoint")
def entrenar(exp, semilla):
    _sh(PY, "-m", "expedicion", "pipeline")
    _sh(DVC, "repro", "--single-item", f"escenarios-{exp}")
    salida = _sh(DVC, "repro", "--single-item", f"entrenar-{exp}-s{semilla}")
    reutilizado = "didn't change" in salida or "up to date" in salida
    get_run_logger().info("checkpoint reutilizado (DVC al día)" if reutilizado else "semilla entrenada")
    return {"semilla": semilla, "reutilizado": reutilizado}


@task(name="4 · evaluar con la suite fija")
def evaluar(exp):
    _sh(DVC, "repro", "--single-item", f"evaluar-{exp}")
    _sh(DVC, "repro", "--single-item", f"regresion-{exp}")
    ev = json.loads((RAIZ / "metrics" / exp / "evaluacion.json").read_text())
    reg = json.loads((RAIZ / "metrics" / exp / "regresion.json").read_text())
    c = str(ev["campeon"])
    pert = _py(f"from expedicion import experimentos as X; import json; "
               f"print(json.dumps(X.cargar({exp!r})['aprobar'].get('perturbacion', 'ninguna')))")
    grupo = ev["semillas"][c].get(f"marte.{pert}", ev["semillas"][c]["global"])  # condición que decide la aprobación
    return {"campeon": ev["campeon"], "condicion": pert, "tasa": grupo["tasa_exito"],
            "tasa_global": ev["semillas"][c]["global"]["tasa_exito"],
            "sin_olvidar": ev["examenes_previos"].get(c, {}), "regresion": reg, "aprobado": ev["aprobado"]}


@task(name="5 · registrar en MLflow")
def registrar(exp):
    salida = _sh(PY, "-c", f"from expedicion import experimentos as X; from expedicion.registro import registrar; "
                           f"print('REGISTRO', registrar(X.cargar({exp!r})))")
    linea = next(l for l in reversed(salida.splitlines()) if l.startswith("REGISTRO"))[9:]
    get_run_logger().info(linea)
    return linea


@task(name="6 · seleccionar o rechazar (criterios fijados)")
def seleccionar(exp, ev):
    criterio = _py(f"from expedicion import experimentos as X; import json; e = X.cargar({exp!r}); "
                   f"print(json.dumps({{'minimo': e['aprobar']['tasa_exito'], 'sin_olvidar': e['aprobar'].get('sin_olvidar', [])}}))")
    minimos = _py("from expedicion import experimentos as X; import json; "
                  f"print(json.dumps({{i: X.cargar(i)['aprobar']['tasa_exito'] for i in {criterio['sin_olvidar']!r}}}))")
    olvida = [i for i, m in minimos.items() if ev["sin_olvidar"].get(i, 0) < m]
    decision = "seleccionar" if ev["tasa"] >= criterio["minimo"] and not olvida else "rechazar"
    get_run_logger().info(f"{decision}: éxito {ev['tasa']:.0%} (mínimo {criterio['minimo']:.0%}); olvida: {olvida or 'nada'}")
    return {"decision": decision, "olvida": olvida, **criterio}


@task(name="7 · publicar catálogo y manifiestos")
def publicar(exp):
    _sh(DVC, "repro", "--single-item", f"progreso-{exp}")
    _sh(DVC, "repro", "--single-item", f"evolucion-{exp}")
    salida = _sh(PY, "-m", "expedicion", "publicar", exp)
    _sh(PY, "scripts/manifiestos.py")
    return salida.splitlines()[-1] if salida else ""


@task(name="8 · verificar la versión servida")
def verificar(exp, episodios=10):
    """Identidad (carpeta, semilla, SHA-256) y salud (éxito en episodios nuevos, semillas 7000+) de lo servido."""
    datos = _py(f"""
import hashlib, json, multiprocessing
from concurrent.futures import ProcessPoolExecutor
from expedicion import publicar as P
from expedicion.evaluar import Politica, correr_episodio
c = P.carpeta({exp!r}).resolve()
exp = P.cargar({exp!r})
def uno(k):
    return correr_episodio(exp, Politica(c / "experto.zip"), {{"planeta": "marte", "perturbacion": "ninguna", "semilla": 7000 + k}})[0]["exito"]
with ProcessPoolExecutor(4, mp_context=multiprocessing.get_context("fork")) as pool:
    exitos = list(pool.map(uno, range({episodios})))
print(json.dumps({{"servida": c.name, "semilla_servida": json.loads((c / "corrida.json").read_text())["semilla"],
                  "model_sha256": hashlib.sha256((c / "experto.zip").read_bytes()).hexdigest(),
                  "exito": sum(exitos), "episodios": len(exitos)}}))""")
    get_run_logger().info(f"Versión servida {datos['servida']} (semilla {datos['semilla_servida']}) · sha256 "
                          f"{datos['model_sha256'][:12]} · {datos['exito']}/{datos['episodios']} episodios nuevos con éxito")
    return datos


@flow(name="robot-expedition")
def pipeline(exp: str):
    perfil = validar(exp)
    resultado = {"exp": exp, "inicio": datetime.datetime.now().isoformat(timespec="seconds"), "perfil": perfil}
    resultado["pruebas"] = pruebas()
    resultado["entrenamiento"] = [entrenar(exp, s) for s in perfil["semillas"]]
    ev = evaluar(exp)
    resultado["evaluacion"] = ev
    resultado["registro"] = registrar(exp)
    resultado["seleccion"] = seleccionar(exp, ev)
    resultado["publicacion"] = publicar(exp)
    resultado["verificacion"] = verificar(exp)
    _guardar(resultado)
    return resultado


@flow(name="robot-expedition-rollback")
def rollback(exp: str):
    """Vuelve a la versión publicada anterior (publicado/.versiones) y comprueba que funciona."""
    versiones = sorted((RAIZ / "publicado" / ".versiones").glob(f"{exp}-*"), key=lambda p: int(p.name.rsplit("-", 1)[1]))
    actual = (RAIZ / "publicado" / exp).resolve()
    previas = [v for v in versiones if v != actual and int(v.name.rsplit("-", 1)[1]) < int(actual.name.rsplit("-", 1)[1])]
    if not previas:
        raise RuntimeError(f"{exp} no tiene una versión publicada anterior")
    destino = previas[-1]
    enlace = RAIZ / "publicado" / exp
    temporal = enlace.with_name(f".{exp}.tmp")
    temporal.unlink(missing_ok=True)
    temporal.symlink_to(destino.relative_to(enlace.parent))
    temporal.replace(enlace)
    get_run_logger().info(f"Rollback: {actual.name} → {destino.name}")
    resultado = {"exp": exp, "rollback_desde": actual.name, "rollback_a": destino.name, "verificacion": verificar(exp)}
    _guardar(resultado, "rollback")
    return resultado


@flow(name="robot-expedition-monitoreo")
def monitorear(exp: str, episodios: int = 20):
    """Revisa la versión servida (identidad y éxito en episodios nuevos) y lo deja registrado."""
    resultado = {"exp": exp, "verificacion": verificar(exp, episodios)}
    _guardar(resultado, "monitoreo")
    return resultado


def _guardar(resultado, tipo="pipeline"):
    REGISTRO.mkdir(parents=True, exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (REGISTRO / f"{marca}-{tipo}-{resultado['exp']}.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("exp")
    a.add_argument("--rollback", action="store_true")
    a.add_argument("--monitorear", action="store_true")
    args = a.parse_args()
    flujo = rollback if args.rollback else monitorear if args.monitorear else pipeline
    print(json.dumps(flujo(args.exp), indent=1, ensure_ascii=False, default=str))
