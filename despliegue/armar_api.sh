#!/usr/bin/env bash
# Arma y sube la API al Space de Hugging Face. Uso: bash despliegue/armar_api.sh [usuario/space]
# Copia el código, los yaml, el robot, el visor y las versiones publicadas de la serie (copias reales,
# sin enlaces: version.txt guarda el nombre de la versión servida).
set -euo pipefail
cd "$(dirname "$0")/.."
SPACE="${1:-Rafoniloni/robot-expedition-api}"
HF="${HF:-$HOME/.venvs/hf/bin/hf}"
SALIDA="${SALIDA:-$HOME/robot-expedition-space}"
SERIE="exp-101 exp-102 exp-103 exp-104 exp-105 exp-106 exp-107a exp-108"
rm -rf "$SALIDA" && mkdir -p "$SALIDA/publicado"
cp -r expedicion experimentos robots web "$SALIDA/"
find "$SALIDA" -name __pycache__ -type d -prune -exec rm -rf {} +
cp despliegue/api/Dockerfile despliegue/api/README.md "$SALIDA/"
for e in $SERIE; do
  real=$(readlink -f "publicado/$e")
  cp -rL "$real" "$SALIDA/publicado/$e"
  basename "$real" > "$SALIDA/publicado/$e/version.txt"
done
echo "$(git rev-parse HEAD)" > "$SALIDA/COMMIT"
sed -i "s/^ENV PIP_NO_CACHE_DIR=1/ENV COMMIT_ENTREGA=$(git rev-parse HEAD) PIP_NO_CACHE_DIR=1/" "$SALIDA/Dockerfile"
du -sh "$SALIDA"
"$HF" repo create "$SPACE" --repo-type space --space-sdk docker --exist-ok >/dev/null
"$HF" upload "$SPACE" "$SALIDA" . --repo-type space --commit-message "API $(git rev-parse --short HEAD)"
echo "Space: https://huggingface.co/spaces/$SPACE"
