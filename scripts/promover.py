"""Promueve una corrida concreta como versión servida de un experimento (versión nueva en publicado/.versiones).

Uso: python scripts/promover.py exp-108 2
Promover no borra nada: la versión anterior sigue en publicado/.versiones y se recupera con
`~/.venvs/prefect/bin/python pipelines/flujo.py exp-108 --rollback`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from expedicion import experimentos as X  # noqa: E402
from expedicion.publicar import publicar  # noqa: E402

if __name__ == "__main__":
    exp, semilla = sys.argv[1], int(sys.argv[2])
    print(publicar(X.cargar(exp), semilla=semilla))
