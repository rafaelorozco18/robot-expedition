"""Servidor local: sirve el visor Three.js y una API que corre episodios reales en MuJoCo."""

import json
import mimetypes
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import mujoco

from . import experimentos as X
from .ambiente import GRAVEDADES, PERTURBACIONES, BipedoEnv
from .evaluar import Aleatorio, Politica, SinEntrenar, campeon, correr_episodio, fotos_de, paso_de

WEB = X.RAIZ / "web"
DESCRIPCIONES = {
    "experto": "La red al final del entrenamiento, la mejor de sus semillas.",
    "aprendiz": "La misma red guardada a mitad de camino: todavía no domina.",
    "sin_entrenar": "Sin red: las articulaciones solo intentan conservar la postura inicial.",
    "aleatorio": "Ángulos objetivo al azar en las 10 articulaciones.",
}


def _archivo_json(ruta):
    return json.loads(ruta.read_text()) if ruta.exists() else None


def catalogo():
    lista = []
    for exp in X.listar():
        evaluacion = _archivo_json(X.carpeta_metricas(exp) / "evaluacion.json") \
            if exp["estado"] != "pendiente" else None
        lista.append({k: exp.get(k) for k in ("id", "titulo", "pregunta", "agrega", "estado", "criterio")}
                     | {"aprobado": evaluacion["aprobado"] if evaluacion else None,
                        "entrenado": evaluacion is not None})
    return lista


def robot(exp):
    m = mujoco.MjModel.from_xml_path(str(X.RAIZ / exp["robot"]))
    tipos = {int(mujoco.mjtGeom.mjGEOM_SPHERE): "esfera", int(mujoco.mjtGeom.mjGEOM_CAPSULE): "capsula",
             int(mujoco.mjtGeom.mjGEOM_BOX): "caja"}
    geoms = []
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == 0:
            continue  # piso
        geoms.append({"cuerpo": int(m.geom_bodyid[g]) - 1, "tipo": tipos[int(m.geom_type[g])],
                      "tam": [float(v) for v in m.geom_size[g]],
                      "pos": [float(v) for v in m.geom_pos[g]],
                      "quat": [float(v) for v in m.geom_quat[g]],
                      "rgba": [float(v) for v in m.geom_rgba[g]]})
    return {"modelo": exp["robot"], "geoms": geoms, "masa": float(m.body_mass.sum()),
            "motores": [m.actuator(i).name for i in range(m.nu)],
            "torque_max": [float(v) for v in m.actuator_forcerange[:, 1]]}


def mundo(exp):
    return {"id": exp["id"], "titulo": exp["titulo"], "pregunta": exp["pregunta"], "robot": robot(exp),
            "gravedades": GRAVEDADES, "perturbaciones": PERTURBACIONES,
            "ambiente": exp["ambiente"], "recompensa": exp["recompensa"],
            "agentes": agentes(exp), "aprobar": exp["aprobar"],
            "evaluacion": _archivo_json(X.carpeta_metricas(exp) / "evaluacion.json"),
            "regresion": _archivo_json(X.carpeta_metricas(exp) / "regresion.json"),
            "titulos": {e["id"]: e["titulo"] for e in X.listar()}}


def agentes(exp):
    listo = campeon(exp) is not None
    return [{"id": n, "descripcion": d, "disponible": listo or n in ("sin_entrenar", "aleatorio")}
            for n, d in DESCRIPCIONES.items()]


def progreso(exp):
    datos = _archivo_json(X.carpeta_metricas(exp) / "progreso.json")
    if not datos:
        return None
    fotos = datos["fotos"]
    corrida = X.carpeta_modelos(exp) / f"semilla-{datos['semilla']}"
    objetivo = exp["entrenamiento"]["aprendiz"] * fotos[-1]["paso"]
    return {"curva": _archivo_json(corrida / "curva.json") or [], "fotos": fotos,
            "semilla": datos["semilla"], "episodios_por_foto": datos["episodios_por_foto"],
            "planetas": exp["evaluacion"]["planetas"],
            "aprendiz": min((f["paso"] for f in fotos), key=lambda p: abs(p - objetivo)),
            "experto": fotos[-1]["paso"]}


@lru_cache(maxsize=32)
def _politica(ruta):
    return Politica(ruta)


def crear_agente(exp, nombre, semilla):
    if nombre == "sin_entrenar":
        return SinEntrenar()
    if nombre == "aleatorio":
        return Aleatorio(semilla)
    c = campeon(exp)
    if c is None:
        raise FileNotFoundError("Este experimento todavía no tiene modelos entrenados.")
    fotos = {paso_de(r): r for r in fotos_de(exp, c)}
    if nombre == "experto":
        return _politica(str(X.carpeta_modelos(exp) / f"semilla-{c}" / "experto.zip"))
    if nombre == "aprendiz":
        return _politica(str(fotos[progreso(exp)["aprendiz"]]))
    if nombre.startswith("paso:"):
        paso = int(nombre[5:])
        if paso not in fotos:
            raise FileNotFoundError(f"No existe la foto del paso {paso}.")
        return _politica(str(fotos[paso]))
    raise ValueError(f"Agente desconocido: {nombre}")


class Manejador(BaseHTTPRequestHandler):
    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _api(self, url):
        partes = url.path.strip("/").split("/")
        if partes == ["api", "experimentos"]:
            return self._json(catalogo())
        if len(partes) != 4 or partes[:2] != ["api", "exp"]:
            return self._json({"error": "ruta desconocida"}, 404)
        exp = X.cargar(partes[2])
        if exp["estado"] == "pendiente":
            return self._json({"error": "Experimento pendiente."}, 400)
        if partes[3] == "mundo":
            return self._json(mundo(exp))
        if partes[3] == "progreso":
            return self._json(progreso(exp))
        if partes[3] == "episodio":
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            esc = {"planeta": q.get("planeta", "marte"), "perturbacion": q.get("perturbacion", "ninguna"),
                   "semilla": int(q.get("semilla", 0))}
            if esc["planeta"] not in GRAVEDADES or esc["perturbacion"] not in PERTURBACIONES:
                raise ValueError("condición desconocida")
            agente = crear_agente(exp, q.get("agente", "experto"), esc["semilla"])
            resumen, cuadros = correr_episodio(exp, agente, esc, grabar=True)
            return self._json({"resumen": resumen, "cuadros": cuadros})
        return self._json({"error": "ruta desconocida"}, 404)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            try:
                return self._api(url)
            except (ValueError, FileNotFoundError) as e:
                return self._json({"error": str(e)}, 400)
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


def servir(puerto=8765, host="127.0.0.1"):
    print(f"Robot Expedition en http://localhost:{puerto}  (Ctrl+C para salir)", flush=True)
    try:
        ThreadingHTTPServer((host, puerto), Manejador).serve_forever()
    except KeyboardInterrupt:
        pass
