#!/usr/bin/env bash
# Arma y despliega la aplicación en Vercel (producción), ligada al commit de GitHub.
# Uso: bash despliegue/desplegar_vercel.sh     (requiere `npx vercel login` una vez y el commit ya subido a GitHub)
# Vercel no compila desde el repositorio porque los modelos viven en DVC (fuera de git): la carpeta se arma aquí
# con despliegue/armar_vercel.py y el deployment lleva el SHA del commit en sus metadatos y en /sim/api/estado.
set -euo pipefail
cd "$(dirname "$0")/.."
SALIDA="${SALIDA:-$HOME/robot-expedition-vercel}"
SHA=$(git rev-parse HEAD)
RAMA=$(git rev-parse --abbrev-ref HEAD)
MENSAJE=$(git log -1 --format=%s)
.venv/bin/python despliegue/armar_vercel.py "$SALIDA"
cp despliegue/vercel/.vercelignore "$SALIDA/.vercelignore"
cd "$SALIDA"
[ -d .vercel ] || npx --yes vercel@latest link --yes --project robot-expedition >/dev/null
npx --yes vercel@latest deploy --prod --yes \
  --meta githubCommitSha="$SHA" --meta githubCommitRef="$RAMA" --meta githubCommitMessage="$MENSAJE" \
  --meta githubOrg=rafaelorozco18 --meta githubRepo=robot-expedition --meta commit="$SHA"
