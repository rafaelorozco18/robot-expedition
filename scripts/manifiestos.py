"""Manifiestos de modelos recuperables (sección 11 del enunciado): uno por modelo en manifests/.

Uso: python scripts/manifiestos.py
Escribe manifests/<exp>-semilla-<s>.json para el campeón de cada experimento de la serie, los modelos históricos
que se citan en la entrega y manifests/catalogo.json con su papel (recomendado, histórico o rechazado).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from expedicion import experimentos as X  # noqa: E402
from expedicion.ambiente import BipedoEnv  # noqa: E402
from expedicion.evaluar import campeon  # noqa: E402
from expedicion.entrenar import URI_MLFLOW  # noqa: E402

SERIE = ["exp-101", "exp-102", "exp-103", "exp-104", "exp-105", "exp-106", "exp-107a", "exp-108"]
NIVEL = {"exp-101": "N1", "exp-102": "N1", "exp-103": "N1", "exp-104": "N2", "exp-105": "N2", "exp-106": "N2",
         "exp-107a": "N2", "exp-108": "N3", "exp-107": "N3"}
# Modelos históricos que la entrega cita además de los campeones: (exp, semilla, papel, motivo)
EXTRA = [
    ("exp-107", 6, "rechazado", "Cumple el recorrido sobre terreno (71 %) pero olvida la curva (25 %): no aprueba."),
    ("exp-107", 10, "rechazado", "Intervención del incidente: no olvida, pero el recorrido sobre terreno queda en 50 %."),
    ("exp-107a", 2, "historico", "Misma receta que el campeón; falló solo el examen de Terreno (58 %)."),
    ("exp-108", 2, "rechazado", "Candidato de ajuste fino con PPO: 24 de 40 balizas en episodios nuevos (línea base: 37)."),
    ("exp-108", 3, "rechazado", "Candidato de ajuste fino con PPO: 25 de 40 balizas en episodios nuevos (línea base: 37)."),
    ("exp-108", 4, "rechazado", "Candidato de ajuste fino con PPO: 34 de 40 balizas en episodios nuevos (línea base: 37)."),
]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def sha_completo(corto):
    try:
        return subprocess.check_output(["git", "rev-parse", corto], cwd=RAIZ, text=True).strip()
    except subprocess.CalledProcessError:
        return corto


def contrato(exp):
    env = BipedoEnv(exp)
    motores = list(env.nombres_motor)
    nu = len(motores)
    obs = [("altura_torso_rel", 1, "m, altura del torso menos la de pie"),
           ("vertical_en_torso", 3, "eje z del mundo en ejes del torso (adimensional)"),
           ("rumbo_pedido_en_torso", 3, "dirección pedida (cos, sin, 0) en ejes del torso"),
           ("vel_lineal_torso", 3, "m/s, en ejes del mundo rotados al torso"),
           ("vel_angular_torso", 3, "rad/s × 0,25"),
           ("angulos_rel_postura", nu, "rad, ángulo de cada articulación menos la postura inicial"),
           ("vel_articulares", nu, "rad/s × 0,1"),
           ("accion_previa", nu, "la acción del paso anterior, [-1, 1]"),
           ("contacto_pies", 2, "1 si el pie izquierdo / derecho toca el piso"),
           ("gravedad_rel", 1, "g / 9,81 (Marte: 0,378)"),
           ("comando", 4, "velocidad x, velocidad y (m/s), altura relativa pedida, giro pedido (rad/s)"),
           ("reloj", 2, "sin y cos de la fase de la marcha (0 en tareas sin reloj)")]
    total = sum(n for _, n, _ in obs)
    assert total == env.observation_space.shape[0], (total, env.observation_space.shape)
    return {
        "observacion": {"dimension": total, "tipo": "float32", "recorte": [-10, 10],
                        "orden": [{"nombre": n, "dimension": d, "unidades": u} for n, d, u in obs]},
        "accion": {"dimension": nu, "tipo": "float32", "rango": [-1, 1], "articulaciones": motores,
                   "significado": f"ángulo objetivo = postura inicial + acción × {exp['control']['rango']} rad; "
                                  f"filtro de primer orden {exp['control'].get('filtro', 0)}; un servo PD por "
                                  "articulación convierte el ángulo en torque"},
        "normalizacion": "ninguna: sin VecNormalize; la observación se recorta a ±10 dentro del ambiente y la acción a ±1",
        "paso_fisico": {"dt_mujoco_s": float(env.model.opt.timestep), "frame_skip": env.frame_skip,
                        "dt_decision_s": round(float(env.dt), 4), "frecuencia_hz": round(1 / float(env.dt), 1)},
    }


def version_registro(nombre, run_id):
    try:
        import mlflow
        mlflow.set_tracking_uri(URI_MLFLOW)
        c = mlflow.MlflowClient()
        for v in c.search_model_versions(f"name='{nombre}'"):
            if v.run_id == run_id:
                alias = c.get_model_version(nombre, v.version).aliases
                return {"nombre": nombre, "version": int(v.version), "alias": list(alias),
                        "uri": f"models:/{nombre}/{v.version}"}
    except Exception as e:  # noqa: BLE001
        return {"nombre": nombre, "error": str(e)}
    return None


def dvc_md5(ruta_rel):
    lock = yaml.safe_load((RAIZ / "dvc.lock").read_text())
    for etapa in lock["stages"].values():
        for o in etapa.get("outs", []):
            if o["path"] == ruta_rel:
                return o.get("md5")
    return None


def manifiesto(id_exp, semilla, papel, motivo=None):
    exp = X.cargar(id_exp)
    carpeta = X.carpeta_modelos(exp) / f"semilla-{semilla}"
    corrida = json.loads((carpeta / "corrida.json").read_text())
    modelo = carpeta / "experto.zip"
    publicado = RAIZ / "publicado" / id_exp / "exp.json"
    config = json.dumps(exp, sort_keys=True, ensure_ascii=False).encode()
    padre = None
    p = exp["entrenamiento"]
    continuar = p.get("continuar_de", {}).get(semilla) if isinstance(p.get("continuar_de"), dict) else None
    if continuar is not None:
        origen = json.loads((X.carpeta_modelos(exp) / f"semilla-{continuar}" / "corrida.json").read_text())
        padre = {"tipo": "continuacion", "exp": id_exp, "semilla": continuar, "run_id": origen["mlflow_run_id"]}
    elif exp["parte_de"]:
        previo = X.cargar(exp["parte_de"])
        s = campeon(previo)
        origen = json.loads((X.carpeta_modelos(previo) / f"semilla-{s}" / "corrida.json").read_text())
        padre = {"tipo": "parte_de", "exp": previo["id"], "semilla": s, "run_id": origen["mlflow_run_id"]}
    escenarios = X.carpeta_datos(exp) / "escenarios.json"
    ruta_rel = str(carpeta.relative_to(RAIZ))
    return {
        "run_id": corrida["mlflow_run_id"],
        "level_id": NIVEL[id_exp],
        "experimento": id_exp, "titulo": exp["titulo"], "pregunta": exp["pregunta"],
        "papel": papel, **({"motivo": motivo} if motivo else {}),
        "environment_version": f"{exp['robot']} (sha256 {sha256(RAIZ / exp['robot'])[:16]}) + tarea «{exp['tarea']}»",
        "git_commit": sha_completo(corrida["git_commit"]),
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "config_publicada": str(publicado.relative_to(RAIZ)) if publicado.exists() else None,
        "model_uri": f"dvc://{ruta_rel}/experto.zip",
        "model_sha256": sha256(modelo),
        "dvc": {"salida": ruta_rel, "md5": dvc_md5(ruta_rel), "recuperar": f"dvc pull {ruta_rel}"},
        "mlflow_registro": version_registro(f"robot-{id_exp}", corrida["mlflow_run_id"]),
        "normalization_uri": None,
        "runtime_ref": "requirements.txt (Python 3.14, MuJoCo, Gymnasium, Stable-Baselines3, PyTorch CPU)",
        "evaluation_suite_id": f"{id_exp}/escenarios.json sha256 {sha256(escenarios)[:16]}" if escenarios.exists() else None,
        "seed": semilla,
        "presupuesto": {"pasos": corrida["pasos"], "segundos": corrida["segundos"]},
        "parent_run_id": padre["run_id"] if padre else None,
        "origen": padre or {"tipo": "desde_cero"},
        "algoritmo": "PPO (Stable-Baselines3), red 256×256; destilación DAgger cuando el yaml declara `destilar`",
        "contrato": contrato(exp),
    }


def main():
    salida = RAIZ / "manifests"
    salida.mkdir(exist_ok=True)
    filas = []
    for i in SERIE:
        exp = X.cargar(i)
        s = campeon(exp)
        papel = "recomendado" if i == SERIE[-1] else "historico"
        m = manifiesto(i, s, papel)
        filas.append(m)
    for i, s, papel, motivo in EXTRA:
        filas.append(manifiesto(i, s, papel, motivo))
    for m in filas:
        (salida / f"{m['experimento']}-semilla-{m['seed']}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    catalogo = [{k: m[k] for k in ("experimento", "titulo", "level_id", "seed", "papel", "run_id", "git_commit",
                                   "model_sha256", "model_uri", "parent_run_id")} for m in filas]
    (salida / "catalogo.json").write_text(json.dumps(catalogo, indent=1, ensure_ascii=False))
    print(f"{len(filas)} manifiestos en {salida}")


if __name__ == "__main__":
    main()
