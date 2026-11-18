#!/usr/bin/env bash
# Baja los modelos y escenarios (DVC) publicados como releases «datos-dvc-*» del repositorio de GitHub
# y los deja listos en el proyecto. Requiere `gh auth login`. Uso: bash scripts/bajar_modelos.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=rafaelorozco18/robot-expedition
DIR="${DVC_EQUIPO:-$HOME/robot-expedition-dvc}"
DVC="${DVC:-.venv/bin/dvc}"
mkdir -p "$DIR/descargas" "$DIR/remoto"

for tag in $(gh release list -R "$REPO" --limit 200 --json tagName --jq '.[].tagName' | grep '^datos-dvc-' | sort); do
  if [ -f "$DIR/descargas/$tag.ok" ]; then continue; fi
  echo "== $tag"
  rm -rf "$DIR/descargas/$tag" && mkdir -p "$DIR/descargas/$tag"
  gh release download "$tag" -R "$REPO" -D "$DIR/descargas/$tag"
  (cd "$DIR/descargas/$tag" && sha256sum -c SHA256SUMS)
  cat "$DIR/descargas/$tag"/*.part* | tar -xf - -C "$DIR"
  rm -f "$DIR/descargas/$tag"/*.part*
  touch "$DIR/descargas/$tag.ok"
done

"$DVC" remote add --local -f -d equipo "$DIR/remoto"
"$DVC" pull
(cd "$DIR" && find remoto -type f | sort) > "$DIR/conocidos"
echo "Listo. Visor: expedicion publicar && expedicion servir"
