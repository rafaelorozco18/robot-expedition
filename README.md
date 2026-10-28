# Robot Expedition

Proyecto final · MLOps Autonomous Lab. Entrenar un agente que se mueva por territorio hostil:
controla su cuerpo (moverse, saltar, agarrar, gestionar batería) y enfrenta adversidades
(arena, barro, hielo, grietas, rocas, clima y gravedad variables).

**Misión v0.1:** visitar la baliza 1, luego la baliza 2, y volver a la base antes de agotar la batería.
Diseño completo del ambiente: [docs/ambiente-v0.1.md](docs/ambiente-v0.1.md).

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # gymnasium, numpy, dvc, mlflow, pytest + este paquete
```

## CLI

```bash
expedicion info                                   # espacios de observación y acción
expedicion entrenar                               # Q-learning (lee params.yaml) + MLflow
expedicion evaluar                                # métricas por agente → metrics/evaluacion.json
expedicion ver --agente experto --clima tormenta --gravedad luna    # episodio animado en la terminal
expedicion transiciones --clima lluvia --gravedad marte --semilla 3 # tabla de transiciones
expedicion mapa                                   # docs/mapa-v0.1.svg
expedicion servir                                 # visor 3D en http://localhost:8765
```

Opciones de `ver` / `transiciones`: `--agente {experto,aprendiz,codicioso,aleatorio}`,
`--clima {despejado,lluvia,tormenta}`, `--gravedad {luna,marte,tierra}`,
`--incidente {ninguno,corredor_bloqueado}`, `--semilla N`.

Uso como ambiente Gymnasium:

```python
import gymnasium as gym, expedicion
env = gym.make("RobotExpedition-v0", clima="tormenta", gravedad="marte")
obs, info = env.reset(seed=0)
obs, recompensa, terminated, truncated, info = env.step(env.action_space.sample())
```

## Visor 3D (Three.js)

`expedicion servir` levanta un servidor local. Cada episodio lo corre el simulador de Python
(`/api/episodio`) y el navegador solo lo dibuja: física ≠ decoración. El panel derecho muestra
la versión del robot (experto, aprendiz, codicioso, aleatorio), las condiciones (clima, gravedad,
incidente, semilla), las acciones con sus valores Q, la batería, la etapa y los sensores, y las
adversidades del momento. Three.js r160 está incluido en `web/vendor/`, así que no requiere internet.

## Versionado

| Qué | Herramienta | Dónde |
|---|---|---|
| **Código** | git | rama `experimento-01`, tag `exp-01` |
| **Pipeline** | DVC | `dvc.yaml` (etapas `escenarios → entrenar → evaluar`) + `dvc.lock` (hashes de cada entrada y salida) |
| **Dataset** | DVC | `data/escenarios.json` (180 escenarios de evaluación) y `data/trayectorias.jsonl` (720 episodios grabados), en el caché `.dvc/cache` |
| **Experimento** | MLflow + `params.yaml` | experimento `robot-expedition` en `mlflow.db`: parámetros, curvas, métricas de evaluación y artefactos por run; `dvc exp show` / `dvc metrics show` comparan entre commits |
| **Modelo** | DVC + MLflow Model Registry | `models/q_experto.npz`, `models/q_aprendiz.npz`, tarjeta `models/modelo.json`; registrado como `robot-expedition-qlearning` (pyfunc; la v2 corresponde al commit `c1f5815`) |

```bash
dvc repro                    # reconstruye solo las etapas cuyo código, datos o parámetros cambiaron
dvc metrics show             # métricas de la versión actual
dvc params diff              # qué parámetros cambiaron respecto al último commit
mlflow ui --backend-store-uri sqlite:///mlflow.db    # http://localhost:5000
```

**Nuevo experimento:** cambia `params.yaml`, ejecuta `dvc repro` y haz commit de `dvc.lock`,
`metrics/` y `models/modelo.json`. Los binarios viven en el caché de DVC.

**Pendiente para compartir con el equipo:** configurar un remoto de DVC (`dvc remote add -d ...` y luego `dvc push`)
y un servidor de MLflow compartido. Hoy ambos son locales: `mlflow.db` está en `.gitignore`.

## Pruebas

```bash
pytest -q    # API de Gymnasium, choques, saltos, grietas, orden de balizas, anti-trampas, truncamiento
```
