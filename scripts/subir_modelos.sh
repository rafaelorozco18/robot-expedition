#!/usr/bin/env bash
# Sube al equipo los modelos nuevos de DVC: solo los archivos que no venían en las releases anteriores,
# como una release «datos-dvc-<rama>-<fecha>». Correrlo después del commit y del `git push`.
# Uso: bash scripts/subir_modelos.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=rafaelorozco18/robot-expedition
DIR="${DVC_EQUIPO:-$HOME/robot-expedition-dvc}"
DVC="${DVC:-.venv/bin/dvc}"
[ -f "$DIR/conocidos" ] || { echo "Primero: bash scripts/bajar_modelos.sh"; exit 1; }

"$DVC" push -r equipo
rama=$(git rev-parse --abbrev-ref HEAD)
tag="datos-dvc-$(date +%Y%m%d-%H%M)-${rama//\//-}"
tmp="$DIR/subida-$tag"; mkdir -p "$tmp"
(cd "$DIR" && find remoto -type f | sort) > "$tmp/todos"
comm -13 "$DIR/conocidos" "$tmp/todos" > "$tmp/lista"
if [ ! -s "$tmp/lista" ]; then echo "No hay modelos nuevos que subir."; rm -rf "$tmp"; exit 0; fi
echo "$(wc -l < "$tmp/lista") archivos nuevos"
tar -cf - -C "$DIR" -T "$tmp/lista" | split -b 1900M -d - "$tmp/dvc-remoto.tar.part"
(cd "$tmp" && sha256sum dvc-remoto.tar.part* > SHA256SUMS)
gh release create "$tag" -R "$REPO" --target "$(git rev-parse HEAD)" --title "Datos DVC · $rama" \
  --notes "Modelos nuevos de la rama \`$rama\` (commit $(git rev-parse --short HEAD))." \
  "$tmp"/dvc-remoto.tar.part* "$tmp/SHA256SUMS"
touch "$DIR/descargas/$tag.ok"
cp "$tmp/todos" "$DIR/conocidos"
rm -rf "$tmp"
echo "Subido: $tag"
