"""Arma la carpeta que se despliega en Vercel: visor estático + función Python de evaluación en vivo.

Uso: .venv/bin/python despliegue/armar_vercel.py [salida]   (por omisión ~/robot-expedition-vercel)
Después: cd <salida> && npx vercel deploy --prod

- El visor se exporta con API_REMOTA=/sim: «Lanzar episodio» corre MuJoCo en la función api/sim.py.
- La función no lleva PyTorch (no cabe en Vercel): cada modelo servido va como .npz (actor exportado,
  verificado por tests/test_politica_numpy.py) y su servido.json guarda el SHA-256 del .zip original.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
from exportar_politicas import exportar as a_npz  # noqa: E402
from expedicion import experimentos as X  # noqa: E402
from expedicion import publicar as P  # noqa: E402
from expedicion import servidor as S  # noqa: E402
from expedicion.evaluar import paso_de  # noqa: E402

SERIE = ["exp-101", "exp-102", "exp-103", "exp-104", "exp-105", "exp-106", "exp-107a", "exp-108"]
METRICAS = ("exp.json", "evaluacion.json", "regresion.json", "progreso.json", "evolucion.json", "curva.json")


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def copiar_npz(origen, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".zip")
    shutil.copy(origen, tmp)
    a_npz(tmp)
    tmp.unlink()


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "robot-expedition-vercel"
    enlace = salida / ".vercel"
    guardado = None
    if enlace.exists():  # el enlace al proyecto de Vercel se conserva entre armados
        guardado = Path.home() / ".cache" / "robot-expedition-vercel-enlace"
        shutil.rmtree(guardado, ignore_errors=True)
        shutil.copytree(enlace, guardado)
    shutil.rmtree(salida, ignore_errors=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RAIZ, text=True).strip()

    # 1. Visor estático con evaluación en vivo en /sim
    from expedicion.exportar import exportar
    os.environ["API_REMOTA"] = "/sim"
    exportado, episodios = exportar(salida)
    (salida / "robot-expedition.html").unlink(missing_ok=True)
    if guardado:
        shutil.copytree(guardado, enlace)

    # 2. Función y configuración de Vercel
    for f in ("vercel.json", "requirements.txt", ".python-version"):
        shutil.copy(RAIZ / "despliegue" / "vercel" / f, salida / f)
    shutil.copytree(RAIZ / "despliegue" / "vercel" / "api", salida / "api")
    shutil.copytree(RAIZ / "expedicion", salida / "expedicion", ignore=shutil.ignore_patterns("__pycache__"))
    (salida / "experimentos").mkdir()
    for y in (RAIZ / "experimentos").glob("*.yaml"):
        shutil.copy(y, salida / "experimentos" / y.name)
    shutil.copytree(RAIZ / "robots", salida / "robots")
    (salida / "COMMIT").write_text(commit + "\n")
    # Registro de MLflow exportado y manifiestos, para la página registro.html
    shutil.copy(RAIZ / "docs" / "registro-mlflow.json", salida / "datos" / "registro-mlflow.json")
    shutil.copytree(RAIZ / "manifests", salida / "manifests")

    # 3. Modelos servidos (actor en numpy) con su identidad original
    servidos = 0
    for i in SERIE:
        exp = P.cargar(i)
        origen = P.carpeta(i).resolve()
        destino = salida / "publicado" / i
        destino.mkdir(parents=True)
        for m in METRICAS:
            if (origen / m).exists():
                shutil.copy(origen / m, destino / m)
        copiar_npz(origen / "experto.zip", destino / "experto.npz")
        agentes = {"aprendiz": S.progreso(exp)["aprendiz"]}
        ev = S.evolucion(exp)
        for plan in ev["planetas"].values():
            for h in plan["hitos"]:
                agentes[h["agente"]] = h["agente"]
        n = 1
        for nombre, valor in agentes.items():
            if nombre == "aprendiz" or str(valor).startswith("paso:"):
                paso = valor if nombre == "aprendiz" else int(str(valor)[5:])
                fotos = {paso_de(r): r for r in (origen / "fotos").glob("paso-*.zip")}
                if paso in fotos:
                    copiar_npz(fotos[paso], destino / "fotos" / fotos[paso].name.replace(".zip", ".npz"))
                    n += 1
            elif str(valor).startswith("foto:"):
                _, o, paso = str(valor).split(":")
                ruta = origen / "linaje" / f"{o}-{paso}.zip"
                if ruta.exists():
                    copiar_npz(ruta, destino / "linaje" / f"{o}-{paso}.npz")
                    n += 1
        ev_json = json.loads((origen / "evaluacion.json").read_text())
        (destino / "servido.json").write_text(json.dumps({
            "version": origen.name, "campeon": ev_json.get("campeon"),
            "model_sha256": sha(origen / "experto.zip"), "npz_sha256": sha(destino / "experto.npz"),
            "modelos_servidos": n}, indent=1))
        servidos += n
    tam = sum(f.stat().st_size for f in salida.rglob("*") if f.is_file()) / 1e6
    print(f"{salida}: {episodios} episodios grabados, {servidos} modelos servidos, {tam:.0f} MB, commit {commit[:8]}")


if __name__ == "__main__":
    main()
