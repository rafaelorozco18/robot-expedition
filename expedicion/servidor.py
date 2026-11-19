"""Servidor local: sirve el visor Three.js y una API que corre episodios reales en MuJoCo."""

import hashlib
import json
import mimetypes
import os
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import mujoco

from . import experimentos as X
from . import publicar as P
from .ambiente import GRAVEDADES, PERTURBACIONES, BipedoEnv
from .evolucion import PLANETAS_VISOR
from .evaluar import Aleatorio, Politica, SinEntrenar, correr_episodio, paso_de

WEB = X.RAIZ / "web"
DESCRIPCIONES = {
    "experto": "La red al final del entrenamiento, la mejor de sus semillas.",
    "aprendiz": "La misma red guardada a mitad de camino: todavía no domina.",
    "sin_entrenar": "Sin red: las articulaciones solo intentan conservar la postura inicial.",
    "aleatorio": "Ángulos objetivo al azar en las 10 articulaciones.",
}


def pub(exp):
    """Carpeta publicada: el visor nunca lee lo que se está entrenando."""
    return P.carpeta(exp["id"])


def _archivo_json(ruta):
    return json.loads(ruta.read_text()) if ruta.exists() else None


def aprobado_visor(exp, ev):
    """El visor solo muestra Tierra y Marte: el criterio se exige en esos planetas.
    Además no puede olvidar: los exámenes de aprobar.sin_olvidar (regla vigente) se revisan con la
    regresión publicada del campeón."""
    m = ev["semillas"][str(ev["campeon"])]
    pert = exp["aprobar"]["perturbacion"]
    propio = all(m[f"{p}.{pert}"]["tasa_exito"] >= exp["aprobar"]["tasa_exito"] for p in PLANETAS_VISOR)
    previos = _archivo_json(pub(exp) / "regresion.json") or {}
    vigente = X.cargar(exp["id"])["aprobar"].get("sin_olvidar", [])
    olvida = any(i in previos and previos[i] < X.cargar(i)["aprobar"]["tasa_exito"] for i in vigente)
    return propio and not olvida


def catalogo():
    lista = []
    for exp in X.listar():
        if exp["estado"] == "descartado":
            continue  # intento conservado en git, DVC y MLflow, fuera de la serie que muestra el visor
        visible = P.cargar(exp["id"]) or exp
        ev = _archivo_json(pub(exp) / "evaluacion.json")
        fila = {k: visible.get(k) for k in ("id", "titulo", "pregunta", "agrega", "criterio")}
        lista.append(fila | {"estado": "activo" if ev else "pendiente",
                             "entrenando": exp["estado"] == "activo" and not ev,
                             "aprobado": aprobado_visor(visible, ev) if ev else None,
                             "entrenado": ev is not None})
    return lista


def robot(exp):
    m = mujoco.MjModel.from_xml_path(str(X.RAIZ / exp["robot"]))
    tipos = {int(mujoco.mjtGeom.mjGEOM_SPHERE): "esfera", int(mujoco.mjtGeom.mjGEOM_CAPSULE): "capsula",
             int(mujoco.mjtGeom.mjGEOM_BOX): "caja"}
    geoms = []
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == 0:
            continue  # piso
        geoms.append({"cuerpo": int(m.geom_bodyid[g]) - 1, "nombre": m.geom(g).name, "tipo": tipos[int(m.geom_type[g])],
                      "tam": [float(v) for v in m.geom_size[g]],
                      "pos": [float(v) for v in m.geom_pos[g]],
                      "quat": [float(v) for v in m.geom_quat[g]],
                      "rgba": [float(v) for v in m.geom_rgba[g]]})
    return {"modelo": exp["robot"], "geoms": geoms, "cuerpos": [m.body(b).name for b in range(1, m.nbody)], "masa": float(m.body_mass.sum()),
            "motores": [m.actuator(i).name for i in range(m.nu)],
            "torque_max": [float(v) for v in m.actuator_forcerange[:, 1]]}


def mundo(exp):
    return {"id": exp["id"], "titulo": exp["titulo"], "pregunta": exp["pregunta"], "robot": robot(exp),
            "gravedades": {p: GRAVEDADES[p] for p in PLANETAS_VISOR}, "perturbaciones": PERTURBACIONES,
            "ambiente": exp["ambiente"], "recompensa": exp["recompensa"],
            "meta_m": exp.get("parametros", {}).get("distancia_m") if exp["tarea"] == "marcha" else None,
            "parametros": exp.get("parametros", {}),
            "viento": bool(exp.get("adversidad", {}).get("viento_n")),
            "tarea": exp["tarea"],
            "clima_visual": exp.get("clima_visual", "despejado"),
            "pendiente_grados": exp.get("pendiente_grados", 0),
            "agentes": agentes(exp), "aprobar": exp["aprobar"],
            "evaluacion": _archivo_json(pub(exp) / "evaluacion.json"),
            "regresion": _archivo_json(pub(exp) / "regresion.json"),
            "titulos": {e["id"]: e["titulo"] for e in X.listar()}}


def agentes(exp):
    return [{"id": n, "descripcion": d, "disponible": True}
            for n, d in DESCRIPCIONES.items()]


def progreso(exp):
    datos = _archivo_json(pub(exp) / "progreso.json")
    if not datos:
        return None
    fotos = datos["fotos"]
    for f in fotos:
        f["tasa_exito"] = round(sum(f[f"exito_{p}"] for p in PLANETAS_VISOR) / len(PLANETAS_VISOR), 3)
    objetivo = exp["entrenamiento"]["aprendiz"] * fotos[-1]["paso"]
    return {"curva": _archivo_json(pub(exp) / "curva.json") or [], "fotos": fotos,
            "semilla": datos["semilla"],
            "episodios_por_foto": exp["evaluacion"]["episodios_por_foto"] * len(PLANETAS_VISOR),
            "planetas": PLANETAS_VISOR,
            "aprendiz": min((f["paso"] for f in fotos if f["paso"]), key=lambda p: abs(p - objetivo)),
            "experto": fotos[-1]["paso"]}


def _pasos(n):
    if not n:
        return "al empezar"
    return f"{n / 1e6:.1f} millones de pasos".replace(".", ",") if n >= 1e6 else f"{round(n / 1000)} mil pasos"


def evolucion(exp):
    datos = _archivo_json(pub(exp) / "evolucion.json")
    if not datos:
        return None
    ev = _archivo_json(pub(exp) / "evaluacion.json")
    aprobado = aprobado_visor(exp, ev)
    for plan in datos["planetas"].values():
        for h in plan["hitos"]:
            if h["paso"] is None:
                origen = "sin entrenar"
            elif h["origen"] != exp["id"]:
                previo = P.cargar(h["origen"]) or X.cargar(h["origen"])
                origen = f"heredado de «{previo['titulo']}» · {_pasos(h['paso'])}"
            else:
                origen = f"este entrenamiento · {_pasos(h['paso'])}"
            h["etiqueta"] = h.get("etapa", "Etapa")
            h["origen_texto"] = origen
    return {**datos, "aprobado": aprobado}


@lru_cache(maxsize=32)
def _politica(ruta):
    npz = Path(ruta).with_suffix(".npz")
    if npz.exists():  # servidor sin PyTorch (Vercel): el actor exportado a numpy
        from .evaluar import PoliticaNumpy
        return PoliticaNumpy(npz)
    return Politica(ruta)


def crear_agente(exp, nombre, semilla):
    if nombre == "sin_entrenar":
        return SinEntrenar()
    if nombre == "aleatorio":
        return Aleatorio(semilla)
    carpeta = pub(exp)
    fotos = {paso_de(r): r.with_suffix(".zip") for r in (carpeta / "fotos").glob("paso-*.*")}  # .zip o .npz
    if nombre == "experto":
        ruta = carpeta / "experto.zip"
    elif nombre == "aprendiz":
        ruta = fotos[progreso(exp)["aprendiz"]]
    elif nombre.startswith("foto:"):
        _, origen, paso = nombre.split(":")
        ruta = carpeta / "linaje" / f"{origen}-{paso}.zip"
    elif nombre.startswith("paso:"):
        ruta = fotos.get(int(nombre[5:]))
    else:
        raise ValueError(f"Agente desconocido: {nombre}")
    if ruta is None or not (ruta.exists() or ruta.with_suffix(".npz").exists()):
        raise FileNotFoundError(f"El modelo {nombre} no está en este servidor.")
    return _politica(str(ruta.resolve()))


def _version(exp):
    """Cambia con cada publicación: invalida los episodios guardados."""
    return str(pub(exp).resolve())


@lru_cache(maxsize=256)
def episodio(id_exp, agente, planeta, perturbacion, semilla, version):
    exp = P.cargar(id_exp)
    esc = {"planeta": planeta, "perturbacion": perturbacion, "semilla": semilla}
    resumen, cuadros = correr_episodio(exp, crear_agente(exp, agente, semilla), esc, grabar=True)
    return json.dumps({"resumen": resumen, "cuadros": cuadros}).encode()


MONITOR = {"inicio": time.strftime("%Y-%m-%dT%H:%M:%S"), "episodios": 0, "errores": 0, "latencias_ms": []}


@lru_cache(maxsize=64)
def _sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def estado():
    """Monitoreo mínimo: versión servida de cada experimento, latencia y errores de inferencia."""
    servidas = {}
    for exp in X.listar():
        c = pub(exp)
        if exp["estado"] == "descartado":
            continue
        if (c / "experto.zip").exists():
            ev = _archivo_json(c / "evaluacion.json") or {}
            servidas[exp["id"]] = {"version": c.resolve().name, "campeon": ev.get("campeon"),
                                   "model_sha256": _sha(str((c / "experto.zip").resolve()))}
        elif (c / "servido.json").exists():  # despliegue sin .zip (Vercel): copia con su identidad original
            servidas[exp["id"]] = json.loads((c / "servido.json").read_text())
    lat = MONITOR["latencias_ms"][-200:]
    commit = os.environ.get("COMMIT_ENTREGA") or ((X.RAIZ / "COMMIT").read_text().strip() if (X.RAIZ / "COMMIT").exists() else None)
    return {"servidor": "MuJoCo en Python con la política PPO publicada", "inicio": MONITOR["inicio"],
            "episodios_servidos": MONITOR["episodios"], "errores": MONITOR["errores"],
            "latencia_ms": {"media": round(sum(lat) / len(lat), 1) if lat else None, "max": max(lat) if lat else None},
            "versiones_servidas": servidas, "commit": commit}


class Manejador(BaseHTTPRequestHandler):
    def _json(self, datos, codigo=200):
        self._bytes(json.dumps(datos).encode(), codigo)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", os.environ.get("CORS_ORIGEN", "*"))
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _bytes(self, cuerpo, codigo=200):
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self._cors()
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _api(self, url):
        partes = url.path.strip("/").split("/")
        if partes == ["api", "experimentos"]:
            return self._json(catalogo())
        if partes == ["api", "estado"]:
            return self._json(estado())
        if len(partes) != 4 or partes[:2] != ["api", "exp"]:
            return self._json({"error": "ruta desconocida"}, 404)
        exp = P.cargar(partes[2])
        if exp is None:
            return self._json({"error": "Experimento pendiente."}, 400)
        if partes[3] == "mundo":
            return self._json(mundo(exp))
        if partes[3] == "progreso":
            return self._json(progreso(exp))
        if partes[3] == "evolucion":
            return self._json(evolucion(exp))
        if partes[3] == "episodio":
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            esc = {"planeta": q.get("planeta", "tierra"), "perturbacion": q.get("perturbacion", "ninguna"),
                   "semilla": int(q.get("semilla", 0))}
            if esc["planeta"] not in PLANETAS_VISOR or esc["perturbacion"] not in PERTURBACIONES:
                raise ValueError("condición desconocida")
            t0 = time.perf_counter()
            cuerpo = episodio(exp["id"], q.get("agente", "experto"), esc["planeta"],
                              esc["perturbacion"], esc["semilla"], _version(exp))
            MONITOR["episodios"] += 1
            MONITOR["latencias_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
            return self._bytes(cuerpo)
        return self._json({"error": "ruta desconocida"}, 404)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            try:
                return self._api(url)
            except (ValueError, FileNotFoundError) as e:
                MONITOR["errores"] += 1
                return self._json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001 — un fallo del servicio se informa como error, no como replay
                MONITOR["errores"] += 1
                return self._json({"error": f"Error del servidor: {e}"}, 500)
        ruta = WEB / "index.html" if url.path == "/" else (WEB / url.path.lstrip("/")).resolve()
        if not ruta.is_file() or WEB not in ruta.parents:
            return self.send_error(404)
        cuerpo = ruta.read_bytes()
        self.send_response(200)
        tipo = "text/javascript" if ruta.suffix == ".js" else \
            mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


def servir(puerto=None, host=None):
    puerto = int(puerto or os.environ.get("PORT", 8765))
    host = host or os.environ.get("HOST", "127.0.0.1")
    print(f"Robot Expedition en http://localhost:{puerto}  (Ctrl+C para salir)", flush=True)
    try:
        ThreadingHTTPServer((host, puerto), Manejador).serve_forever()
    except KeyboardInterrupt:
        pass
