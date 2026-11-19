"""Exp 9: compara navegadores en MuJoCo completo con el mismo caminante (campeón del Exp 8) y los mismos episodios.

Uso: python scripts/comparar_navegadores.py N BASE nombre=ruta [nombre=ruta ...]
     (ruta: un .zip de navegador, o «regla:directo» / «regla:aleatorio» como referencias)
Ejemplo: python scripts/comparar_navegadores.py 24 5000 regla=regla:directo robusto-s1=models/exp-109/navegadores/robusto-s1/experto.zip
Escribe docs/evaluaciones/exp-109-navegadores-<BASE>.json con el resultado de cada episodio.
"""
import collections
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from expedicion import experimentos as X  # noqa: E402
from expedicion.evaluar import Politica, correr_episodio  # noqa: E402

CAMINANTE = RAIZ / "models" / "exp-108" / "semilla-1" / "experto.zip"


def uno(arg):
    nombre, ruta, semilla = arg
    exp = X.cargar("exp-109")
    exp = {**exp, "navegador": {**exp["navegador"], "modelo": ruta}}
    r, _ = correr_episodio(exp, Politica(CAMINANTE), {"planeta": "marte", "perturbacion": "ninguna", "semilla": semilla})
    return nombre, {"semilla": semilla, "exito": r["exito"], "motivo": r["motivo"], "detalle": r["detalle"],
                    "segundos": r["segundos"]}


def main():
    n, base = int(sys.argv[1]), int(sys.argv[2])
    pares = [a.split("=", 1) for a in sys.argv[3:]]
    # Exporta antes los .npz (una sola vez) para que los procesos no compitan al escribirlos.
    sys.path.insert(0, str(RAIZ / "scripts"))
    from exportar_politicas import exportar
    for _, ruta in pares:
        if ruta.endswith(".zip"):
            exportar(RAIZ / ruta)
    trabajos = [(nombre, ruta, base + k) for nombre, ruta in pares for k in range(n)]
    res = collections.defaultdict(list)
    with ProcessPoolExecutor(4) as pool:
        for nombre, fila in pool.map(uno, trabajos):
            res[nombre].append(fila)
    tabla = {}
    for nombre, _ in pares:
        filas = res[nombre]
        motivos = collections.Counter(f["motivo"] for f in filas)
        tabla[nombre] = {"exitos": sum(f["exito"] for f in filas), "episodios": len(filas), "motivos": dict(motivos)}
        print(f"{nombre:16s} {tabla[nombre]['exitos']:2d}/{len(filas)}  {dict(motivos)}", flush=True)
    salida = RAIZ / "docs" / "evaluaciones" / f"exp-109-navegadores-{base}.json"
    salida.write_text(json.dumps({"caminante": str(CAMINANTE.relative_to(RAIZ)), "episodios": n, "semilla_base": base,
                                  "resumen": tabla, "por_episodio": res}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
