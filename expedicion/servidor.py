"""Servidor local: sirve el visor Three.js (web/) y una API que corre episodios reales."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config as C
from .agentes import agentes_disponibles, cargar_agente
from .evaluar import correr_episodio

WEB = Path(__file__).resolve().parent.parent / "web"


def mundo(p_amb, carpeta_modelos):
    modelo = Path(carpeta_modelos) / "modelo.json"
    return {
        "titulo": "Robot Expedition",
        "mision": "Visitar dos balizas en orden y volver a la base antes de agotar la batería.",
        "mapa": C.MAPA_V01,
        "terrenos": {k: v["nombre"] for k, v in C.TERRENOS.items()},
        "incidentes": {inc: [[x, y, c] for (x, y), c in cambios.items()]
                       for inc, cambios in C.INCIDENTES.items()},
        "climas": C.CLIMAS, "gravedades": C.GRAVEDADES, "acciones": C.NOMBRES_ACCION,
        "rayos": C.NOMBRES_RAYO, "parametros": p_amb, "recompensas": C.RECOMPENSAS,
        "agentes": agentes_disponibles(carpeta_modelos),
        "modelo": json.loads(modelo.read_text()) if modelo.exists() else None,
    }


def crear_manejador(p_amb, carpeta_modelos):
    class Manejador(BaseHTTPRequestHandler):
        def _json(self, datos, codigo=200):
            cuerpo = json.dumps(datos).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/api/mundo":
                return self._json(mundo(p_amb, carpeta_modelos))
            if url.path == "/api/episodio":
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                try:
                    escenario = {"clima": q.get("clima", "despejado"),
                                 "gravedad": q.get("gravedad", "tierra"),
                                 "incidente": q.get("incidente", "ninguno"),
                                 "semilla": int(q.get("semilla", 0))}
                    if escenario["clima"] not in C.CLIMAS or \
                            escenario["gravedad"] not in C.GRAVEDADES or \
                            escenario["incidente"] not in C.INCIDENTES:
                        raise ValueError("condición desconocida")
                    agente = cargar_agente(q.get("agente", "experto"), carpeta_modelos,
                                           semilla=escenario["semilla"])
                    resumen, cuadros = correr_episodio(agente, escenario, p_amb)
                    return self._json({"resumen": resumen, "cuadros": cuadros})
                except (ValueError, FileNotFoundError) as e:
                    return self._json({"error": str(e)}, 400)

            ruta = (WEB / url.path.lstrip("/")).resolve()
            if url.path == "/":
                ruta = WEB / "index.html"
            if not ruta.is_file() or WEB not in ruta.parents:
                self.send_error(404)
                return
            cuerpo = ruta.read_bytes()
            self.send_response(200)
            tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
            if ruta.suffix == ".js":
                tipo = "text/javascript"
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *args):
            pass

    return Manejador


def servir(p_amb, carpeta_modelos="models", puerto=8765, host="127.0.0.1"):
    servidor = ThreadingHTTPServer((host, puerto), crear_manejador(p_amb, carpeta_modelos))
    print(f"Robot Expedition en http://localhost:{puerto}  (Ctrl+C para salir)", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
