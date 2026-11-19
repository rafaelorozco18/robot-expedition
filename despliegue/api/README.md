---
title: Robot Expedition API
emoji: 🤖
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Robot Expedition · API de simulación e inferencia

Corre episodios reales en MuJoCo con los modelos publicados de la Serie Marte (Exps 1 a 8).
La web de la entrega (Vercel) la usa para «Lanzar episodio» en vivo.

- `GET /api/experimentos`: catálogo.
- `GET /api/estado`: versión servida de cada modelo (SHA-256), latencia y errores.
- `GET /api/exp/<id>/mundo`, `/progreso`, `/evolucion`.
- `GET /api/exp/<id>/episodio?agente=experto&planeta=marte&perturbacion=ninguna&semilla=7`:
  agentes `experto`, `aprendiz`, `paso:<n>` (cualquier foto del entrenamiento), `foto:<exp>:<paso>`, `sin_entrenar`, `aleatorio`.

Código y versionado: repositorio `rafaelorozco18/robot-expedition` (privado; acceso para el docente por invitación).
