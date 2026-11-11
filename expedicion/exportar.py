"""Exporta el visor como sitio estático: los episodios que muestra quedan precalculados.

Sirve para compartir un enlace sin dejar el servidor de Python encendido. Incluye, por
experimento publicado: catálogo, mundo, curva de progreso, etapas de aprendizaje y los episodios
de las cinco etapas y de las cuatro versiones del robot en el escenario de las etapas.
"""

import json
import shutil

from . import experimentos as X
from . import publicar as P
from . import servidor as S


def _guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))


def exportar(destino=None):
    destino = destino or (X.RAIZ / "exportado")
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(S.WEB, destino)
    indice = (destino / "index.html").read_text()
    (destino / "index.html").write_text(indice.replace(
        "<head>", "<head>\n  <script>window.VISOR_ESTATICO = true;</script>", 1))
    # Variante para publicar como artifact de claude.ai: sin doctype/html/head/body propios.
    import re
    cuerpo = re.sub(r"<!doctype html>|</?html[^>]*>|</?head>|</?body>", "", (destino / "index.html").read_text(), flags=re.I)
    (destino / "robot-expedition.html").write_text(cuerpo.strip() + "\n")
    api = destino / "api"
    _guardar(api / "catalogo.json", {"experimentos": S.catalogo()})
    episodios = 0
    for exp_actual in X.listar():
        exp = P.cargar(exp_actual["id"])
        if exp is None:
            continue
        i = exp["id"]
        paquete = {"mundo": S.mundo(exp), "progreso": S.progreso(exp)}
        evolucion = S.evolucion(exp)
        paquete["evolucion"] = evolucion
        pert = evolucion["perturbacion"]
        for planeta, plan in evolucion["planetas"].items():
            agentes = {h["agente"] for h in plan["hitos"]} | {"experto", "aprendiz", "sin_entrenar", "aleatorio"}
            for agente in sorted(agentes):
                datos = S.episodio(i, agente, planeta, pert, plan["semilla"], S._version(exp))
                paquete[f"ep-{agente.replace(':', '_')}-{plan['semilla']}-{pert}"] = json.loads(datos)
                episodios += 1
        _guardar(api / f"{i}.json", paquete)
    return destino, episodios
