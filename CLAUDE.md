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
- **Solo Marte (pedido del usuario, 2026-11-11):** la Serie Marte entrena y se evalúa solo en Marte, y el visor
  oculta el selector de planeta. La serie anterior usó Luna, Marte y Tierra.
- **«Ver su aprendizaje»:** `expedicion/evolucion.py` prueba las fotos de todo el linaje en un escenario fijo y
  guarda las etapas en `metrics/exp-NNN/evolucion.json`. Un experimento nuevo lo genera solo en su campaña.
- **El visor solo lee `publicado/exp-NNN`** (enlace a una copia autosuficiente, fuera de git). Reentrenar nunca lo rompe:
  la versión anterior sigue visible hasta que `campana` publique la nueva. Tras clonar: `expedicion publicar`.
- **Experimento ≠ corrida.** Experimento: una pregunta nueva. Corrida: un intento dentro de ella (semilla o parámetros).
- Cada experimento es un archivo en `experimentos/`; agregar uno no debe exigir copiar código.
- Cada modelo nuevo repite las pruebas de los experimentos anteriores (regresión).

## Hoja de ruta

**Vigente desde 2026-11-13: la Serie Marte en orden** (`docs/serie-marte.md`, `experimentos/exp-101` a `exp-109`):
de pie, caminar, caminar bien, terreno difícil, esquina, curva, dominio, de pie con viento y caminar con viento.
Solo Marte, robot v2 (12 articulaciones). El usuario pidió 5 etapas por experimento en «Ver cómo aprendió»:
fracaso absoluto, fracaso pero mejor, punto de inflexión, cumplido y perfeccionado.
**Un experimento a la vez (pedido del usuario, 2026-11-13):** entrenar uno, revisar por qué falla, ajustar una cosa
y reintentar; pasar al siguiente solo con un robot mejor. Nunca lanzar la cadena entera en lote.
Mientras el usuario usa la máquina: 4 procesos, `nice -n 19 ionice -c3`.

El plan de 50 experimentos y sus resultados quedaron archivados en `experimentos/plan-50/` y en los
tags `exp-001` a `exp-028`.

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

## Estado actual (2026-11-14, 06:15)

- Serie en orden (ver `docs/serie-marte.md`). Aprobados: 1, 2, 3 y 4. **El Exp 5 ya no cuenta como aprobado:**
  con la regla de no olvidar (desde el 2026-11-14 el campeón se elige con `sin_olvidar`) su mejor semilla, la 10,
  hace esquina 92 %, Caminar bien 100 % y Terreno 92 %, pero De pie 58 % (pide 80 %).
- Con el filtro de servos actual (0,6) el propio campeón del Exp 1 hace 67 % en De pie: **pendiente que el usuario
  decida** si el mínimo de sin_olvidar para De pie debe ser lo que logra el campeón original con el mismo control.
- Los Exps 6 a 9 esperan al 5. Exp 6 y 7 ya tienen repaso (con De pie) y sin_olvidar configurados.
- La consolidación (`continuar_de` una semilla buena con repaso al 50 %) fue lo que mejor funcionó; subir
  `pasos_minimos` a los pasos totales al continuar. Bajar la tasa de aprendizaje a 1e-4 (semilla 13) derrumbó la esquina.
- Enlace para compartir: https://claude.ai/artifact/Ruy6W73UXNamsQyjnRkz5x (privado; se comparte desde su menú).
  Se actualiza con `expedicion exportar` y publicando `exportado/robot-expedition.html` con sus archivos.
- Para medir de verdad un candidato: 40 episodios nuevos (`correr_episodio` con semillas 3000+): el examen de 12
  episodios varía ±8 puntos por episodio.

### Lecciones que no hay que volver a aprender

- No hacer `git add -A` mientras DVC entrena: si git toma las salidas, DVC se niega a guardarlas.
  Por eso `/models/exp-1*/semilla-*` está en `.gitignore`.
- Evaluar con el ruido de la política, sembrado por episodio (`Politica.para_episodio`): en la Serie Marte la
  media sola no se sostiene. Nunca usar el generador global de torch: el servidor atiende episodios en paralelo.
- `dvc repro` puede reponer resultados viejos desde su caché aunque se borren: para recalcular, correr el
  comando de la etapa directamente y después `dvc commit -f`.
- En Marte el servo solo ya sostiene al robot: el Exp 101 arranca desequilibrado para que haya algo que aprender.

- DVC borra las salidas al reentrenar: nada que se muestre al usuario debe leer `models/` o `metrics/` en vivo.

- Escalar la recompensa (0.05) permitió aprender: sin eso la función de valor satura el optimizador.
- El i5-1235U rinde más con 4 procesos que con 8. BLAS debe ir a 1 hilo (`expedicion/__init__.py`).
- Evaluar siempre sin exploración: con ruido alto (`log_std_init` -1.5) el modelo depende del ruido; -2.2 ayuda en equilibrio.
- La Luna es la condición más difícil en equilibrio y barro: casi todos los fallos son solo ahí.
- Sentadilla: lejos de la meta la recompensa debe seguir dando pistas, o el robot se queda a media altura.
- `pkill -f` y `pgrep -f` coinciden con el propio comando si el texto aparece en él: esperar con `kill -0 PID`.
- No matar una campaña antes de que escriba "aprobado" o "no aprobó": se pierde el cierre del experimento.
- El directorio temporal y el navegador de Playwright pueden desaparecer entre sesiones.
- Repaso: el índice que recibe `crear(i)` es global; la fracción se aplica al índice local del proceso
  (antes solo repasaba el primer proceso: 6 % de los robots).
- Al continuar una semilla que ya sabe la tarea, el corte temprano (`pasos_minimos`) corta enseguida:
  subir `pasos_minimos` a los pasos totales.
- El campeón lo elige `evaluar` contando `aprobar.sin_olvidar`: una semilla que olvida no aprueba.
- El Exp 2 no entra a sin_olvidar: su ritmo (0,8 s y 0,5–0,6 m/s) lo reemplazó la marcha del Exp 3;
  el robot camina los 22 s con calidad 76 pero no llega a 10 m.
