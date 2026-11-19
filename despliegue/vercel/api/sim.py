"""Función de Vercel: la API de simulación e inferencia (MuJoCo en Python, política en numpy).

Reutiliza el servidor del proyecto (expedicion/servidor.py). vercel.json reescribe /sim/<ruta> a esta función
con ?ruta=<ruta>; también acepta /sim/<ruta> directo.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MUJOCO_GL", "disable")

from expedicion.servidor import Manejador  # noqa: E402


class handler(Manejador):  # noqa: N801 — nombre que exige el runtime de Python de Vercel
    def _ruta_original(self):
        url = urlparse(self.path)
        if url.path.startswith("/sim/"):
            return self.path[len("/sim"):]
        q = dict(parse_qsl(url.query))
        ruta = q.pop("ruta", "")
        return "/" + ruta.lstrip("/") + (f"?{urlencode(q)}" if q else "")

    def do_GET(self):
        self.path = self._ruta_original()
        if not self.path.startswith("/api/"):
            return self._json({"error": "Use /sim/api/estado o /sim/api/exp/<id>/episodio"}, 404)
        return super().do_GET()
