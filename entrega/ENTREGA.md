# Entrega final · Robot Expedition

Mapa de la entrega: cada punto que pide el enunciado y dónde se revisa. Todo lo de la columna «Dónde» está en el
repositorio `rafaelorozco18/robot-expedition` o en la aplicación publicada.

## Identidad de la versión entregada

| | |
|---|---|
| Aplicación (Vercel) | https://robot-expedition-tawny.vercel.app |
| Release / tag | `entrega-final-v2` (con el Exp 9). La versión anterior, solo con los Exps 1 a 8, es `entrega-final` |
| Commit entregado | el del tag `entrega-final-v2` (`git rev-parse entrega-final-v2`); el SHA completo está en la descripción de la release y en `/sim/api/estado` |
| Deployment de Vercel | lleva el mismo commit en sus metadatos y en https://robot-expedition-tawny.vercel.app/sim/api/estado (`commit`) |
| Modelo recomendado | `exp-108` semilla 1 · run `a6328691a8d14623a3b879d2b365f7c4` · `robot-exp-108` alias `campeon` · [manifiesto](../manifests/exp-108-semilla-1.json) |
| Modelo histórico (ejemplo) | `exp-103` semilla 1 · run `5288517fb4ff4dd58116e3ae442017c7` · ambiente `robots/bipedo-v2.xml` + tarea «marcha» · [manifiesto](../manifests/exp-103-semilla-1.json) |
| Presentación | https://robot-expedition-tawny.vercel.app/presentacion.html |

## Experimento 9 (extra, en curso)

El Exp 9 «Exploración entre rocas» agrega rocas que no se pueden cruzar y parches de arena, grava y barro, con un
navegador aprendido (segunda familia de modelos) sobre el caminante del Exp 8. Llega en el 25 % de los mundos (mínimo
60 %): **no aprueba**, y se entrega como intento documentado con sus hipótesis, variantes, referencias y hallazgos
(`docs/serie-marte.md`, `docs/informe.md`, `manifests/exp-109-*.json`, MLflow `exp-109-navegador`). Se puede ver y
evaluar en vivo en la aplicación (Exp 9). La versión sin el Exp 9 queda en el tag `entrega-final` (alias `entrega-final-8-experimentos`); la aplicación publicada corresponde a `entrega-final-v2`.

## Paquete final (sección 17 del enunciado)

| Pide | Dónde |
|---|---|
| URL Vercel y repositorio con release/tag | Arriba. Release `entrega-final-v2` en GitHub |
| README con instalación, ejecución, variables, arquitectura y reproducción | [README.md](../README.md), [.env.example](../.env.example) |
| Ficha del ambiente y tres niveles | [docs/ficha-ambiente.md](../docs/ficha-ambiente.md); ficha por experimento en [docs/experimentos/](../docs/experimentos/) |
| Cuatro configuraciones con hipótesis y sus runs/estados en MLflow | [docs/comparacion-experimentos.md](../docs/comparacion-experimentos.md) (49 corridas) y la página [registro](https://robot-expedition-tawny.vercel.app/registro.html); hipótesis en la etiqueta `hipotesis` de cada run y en el `pendiente` de cada `experimentos/exp-NNN.yaml` |
| Modelos finales recuperables, normalización, manifiestos y referencias | [manifests/](../manifests/) (SHA-256, contrato de 58 observaciones y 12 acciones, normalización «ninguna», DVC y MLflow); recuperación con `bash scripts/bajar_modelos.sh` |
| Evaluaciones por caso, comparación de finalistas y presupuesto | `data/<exp>/trayectorias.jsonl` (cada episodio del examen), [docs/evaluaciones/](../docs/evaluaciones/) (por semilla, con pasos y segundos), comparación del Exp 8 en [docs/informe.md](../docs/informe.md) |
| Pipeline | [pipelines/flujo.py](../pipelines/flujo.py) (Prefect, 8 etapas) y sus ejecuciones en [pipelines/ejecuciones/](../pipelines/ejecuciones/); `dvc.yaml` / `dvc.lock` |
| Degradación, intervención y prueba de rollback | [docs/incidente-y-rollback.md](../docs/incidente-y-rollback.md) |
| Informe breve y presentación | [docs/informe.md](../docs/informe.md), [presentación](https://robot-expedition-tawny.vercel.app/presentacion.html) |

## Cómo revisarlo (lo que pide la sección «Cómo se revisará»)

1. **Elegir una ejecución histórica y comprobar su identidad.** En la [página de registro](https://robot-expedition-tawny.vercel.app/registro.html)
   cada modelo muestra run, commit y SHA-256; el manifiesto completo está en `manifests/`. `/sim/api/estado` da el SHA-256
   del modelo que se está sirviendo para cada experimento.
2. **Cargar el modelo y evaluarlo.** En la aplicación, abrir cualquier experimento (por ejemplo el Exp 3) y pulsar
   «Lanzar episodio» con una semilla: el episodio se corre en ese momento en MuJoCo (función Python de Vercel) y se
   marca «Evaluación en vivo». «Versión del robot» permite evaluar también el aprendiz, la regla sin red y el agente
   aleatorio.
3. **Comparar candidatos compatibles.** Todos los modelos son de la misma familia (mismo robot, 58 observaciones,
   12 acciones). Comparación por semilla en `docs/comparacion-experimentos.md`; «Carrera de versiones» en la aplicación.
4. **Explicar fallos.** Cada episodio muestra su motivo de fin (cayó, se inclinó, no llegó) y el desglose de la recompensa.
5. **Reconstruir una evaluación desde la release.** `git checkout entrega-final-v2 && bash scripts/bajar_modelos.sh &&
   dvc repro evaluar-exp-108` (o `python scripts/medir40.py models/exp-108/semilla-1/experto.zip`).
6. **Restaurar una versión anterior.** `~/.venvs/prefect/bin/python pipelines/flujo.py exp-108 --rollback`; la prueba
   ejecutada está en `docs/incidente-y-rollback.md`. A nivel de código: `git checkout exp-107a` (tag de cada experimento).

## Reproducción verificada

El 2026-11-19 se clonó el tag `entrega-final` (Exps 1 a 8) en una carpeta limpia y se corrió `bash scripts/bajar_modelos.sh`: se
descargaron 1690 archivos de DVC, el modelo recomendado tiene el SHA-256 de su manifiesto
(`2083930f7bb0c766082d1f83f0b760bdfc9540f773a1220bf3b0681ed1f1f460`), `dvc status` está al día y
`scripts/medir40.py` vuelve a dar 37 de 40 balizas, igual que la medición original.

## Lo que requiere al equipo antes de enviar

- Completar en `entrega/CORREO.md` el grupo (A o B) y los nombres completos.
- Dar acceso al repositorio privado al docente (invitarlo con su usuario de GitHub, o pedírselo en el correo).
- Completar las contribuciones de cada integrante en `docs/informe.md`.
