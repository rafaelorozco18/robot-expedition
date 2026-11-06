# Robot Expedition: contexto del proyecto

Proyecto final de MLOps (MLOps Autonomous Lab). Se trabaja en español.
**Lee este archivo primero y actualiza "Estado actual" al terminar cada sesión.**

## Qué estamos haciendo

Entrenar un robot con articulaciones, subiendo la dificultad **de a una cosa por experimento**
(pedido del profesor). Se esperan cientos de experimentos con el tiempo. Una plataforma web
muestra la evolución, con un selector para ir de experimento en experimento.

## Decisiones tomadas

- **3D completo desde el inicio** (lo pidió el usuario). Cuerpo: torso y dos piernas, sin brazos por ahora.
- **Simulador:** MuJoCo con Gymnasium. **Algoritmo:** PPO (Stable-Baselines3) en CPU.
- **Control:** la red pide ángulos objetivo y un PD por articulación calcula el torque, con
  ganancias bajas. Con torque directo PPO no aprendió a sostenerse en 500 mil pasos. Sin red y
  con kp = 0.3 el robot aguanta 10 s en la Luna, ~3 s en Marte y <2 s en la Tierra.
- **Exp 1 usa Luna, Marte y Tierra a la vez**, sorteados por episodio.
- **El robot ve la gravedad, pero no el piso:** el terreno lo descubre por cómo responden sus pies.
- **Física ≠ decoración:** el simulador corre en Python y el visor Three.js solo reproduce cuadros.
- **Experimento ≠ corrida.** Experimento: una pregunta nueva. Corrida: un intento dentro de ella (semilla o parámetros).
- Cada experimento es un archivo en `experimentos/`; agregar uno no debe exigir copiar código.
- Cada modelo nuevo repite las pruebas de los experimentos anteriores (regresión).

## Hoja de ruta

El plan vigente son los 50 experimentos de `docs/plan-50-experimentos.md` (definido el 2026-11-06).
Reemplaza la lista corta anterior: Caminar pasó a ser el Exp 10 y Barro el 23. Los archivos
`experimentos/exp-002` a `exp-005` todavía tienen la numeración vieja y deben regenerarse.

## Versionado (exigido por el profesor)

| Qué | Cómo |
|---|---|
| Código | git, un tag por experimento: `exp-001`, `exp-002`… |
| Dataset | DVC: escenarios de prueba congelados y trayectorias grabadas |
| Pipeline | Un solo `dvc.yaml` que recorre los experimentos |
| Experimento | MLflow: un experimento por pregunta, una corrida por semilla |
| Modelo | Registro de MLflow, con el modelo del que partió cada uno |
| Robot | El archivo del cuerpo (MJCF) con versión propia |

Cada experimento lleva además `docs/experimentos/exp-00N.md` con los 8 puntos de la guía del
profesor: mapa, estado frente a observación, variables, dinámica, recompensa y fin de episodio,
métricas y perturbación, cinco transiciones reales, y trampas y decisiones pendientes.

## Forma de trabajar

- **La máquina se comparte.** El usuario suele tener otra conversación en la plataforma BOFBET.
  Antes de entrenar, revisa `uptime` y `free -g`. Entrena con `nice` y sin ocupar todos los núcleos.
- Máquina: 10 núcleos, 7 GB de RAM, sin GPU, Python 3.14 en `.venv`.
- Commits en rama de trabajo, con mensajes en español. No hay remoto de git, DVC ni MLflow.
- Antes de decir que el visor funciona, revísalo con capturas.

## Trabajo anterior

La navegación en rejilla con Q-learning quedó archivada en el tag `legado-navegacion`
(también en la rama `experimento-01`). Volverá como experimento tardío, cuando el robot ya sepa caminar.
Sus datos y modelos se recuperan con `git checkout legado-navegacion && dvc checkout`.
Sus artefactos de MLflow están en `archivo/mlruns-navegacion/` (ignorado por git). El índice
`mlflow.db` de esa etapa se borró por error el 2026-11-04: se perdió el historial de corridas
y el registro de modelos; las métricas y parámetros siguen en git.
**No borres archivos ignorados por git sin revisarlos: no tienen copia.**

## Estado actual (2026-11-06)

- El usuario autorizó trabajar solo de 10:00 a 15:00 (cierre hasta 15:30): hacer todos los experimentos posibles.
- `expedicion campana exp-NNN ...` entrena, evalúa, reintenta con otra semilla, registra, documenta, hace commit y tag.
- Rama `exp-001-de-pie`. El avance real está en `metrics/campana.log` y `git tag`.
- Claves aprendidas: escalar la recompensa (0.05) fue lo que permitió aprender; el i5-1235U rinde más
  con 4 procesos que con 8; limitar BLAS a 1 hilo es obligatorio; parar solo con prueba sin exploración.
