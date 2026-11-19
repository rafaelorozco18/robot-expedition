# Robot Expedition

Proyecto final de MLOps (Universidad Externado de Colombia · Visualización 2). Un robot bípedo de 12 articulaciones
aprende, en Marte y de a una dificultad por experimento, a sostenerse, caminar, caminar bien, cruzar terreno difícil,
girar, caminar en curva, encadenar órdenes y, al final, **llegar a balizas**. Física en MuJoCo, agente PPO, todo
versionado con git, DVC y MLflow, orquestado con Prefect y publicado en Vercel.

| | |
|---|---|
| **Aplicación (Vercel)** | https://robot-expedition-tawny.vercel.app |
| **Registro de experimentos y modelos** | https://robot-expedition-tawny.vercel.app/registro.html |
| **API de evaluación (estado y versión servida)** | https://robot-expedition-tawny.vercel.app/sim/api/estado |
| **Entrega** | [entrega/ENTREGA.md](entrega/ENTREGA.md): qué se entrega y dónde está cada cosa |

## Misión

El escenario asignado es **Robot Expedition**: un robot debe llegar a balizas. Elegimos un robot con patas, en 3D
completo y con gravedad de Marte: es más difícil que uno con ruedas, pero el que puede ir donde no llega una rueda.
La serie tiene 9 experimentos (`experimentos/exp-101` a `exp-109`; el 7 es `exp-107a`); cada uno parte del campeón del anterior
y, desde el Exp 5, **solo aprueba si no olvida los exámenes anteriores**.

| Exp | Pregunta | Nivel | Estado |
|---|---|---|---|
| 1 | ¿Se mantiene de pie en Marte, arrancando desequilibrado? | N1 | aprobado |
| 2 | ¿Camina 10 m sin caer? | N1 | aprobado |
| 3 | ¿Camina como una persona (zancada, ritmo, sin vibrar)? | N1 | aprobado |
| 4 | ¿Mantiene la marcha sobre arena, grava, barro y listones? | N2 | aprobado |
| 5 | ¿Camina recto, gira 90° sobre su eje y sigue? | N2 | aprobado |
| 6 | ¿Camina en círculo (avanza y gira a la vez)? | N2 | aprobado |
| 7 | ¿Encadena rectas, giros y curvas en orden al azar? (`exp-107a`) | N2 | aprobado |
| 8 | ¿Llega, una tras otra, a tres balizas puestas al azar? | N3 | aprobado |
| 9 | ¿Llega a tres balizas en un campo de rocas que no puede cruzar, pisando arena y grava? | N3 | en curso: 33 % (4 de 12) en el examen (mínimo 60 %) |

Ficha del ambiente y niveles: [docs/ficha-ambiente.md](docs/ficha-ambiente.md) · comparación de todas las corridas:
[docs/comparacion-experimentos.md](docs/comparacion-experimentos.md) · incidente y rollback:
[docs/incidente-y-rollback.md](docs/incidente-y-rollback.md) · informe: [docs/informe.md](docs/informe.md) ·
bitácora completa: [docs/serie-marte.md](docs/serie-marte.md) · ficha de cada experimento: [docs/experimentos/](docs/experimentos/).

## Arquitectura

```
                 entrenamiento (PC del equipo, CPU)                         despliegue (Vercel)
 experimentos/*.yaml ─► expedicion (Gymnasium + MuJoCo) ─► PPO / destilación ─► models/  (DVC)
        │                       │                                │
        │                 dvc.yaml / dvc.lock              MLflow (mlflow.db): runs, métricas,
        │                 (una etapa por semilla)          Model Registry con alias «campeon»
        ▼                       ▼                                ▼
 pipelines/flujo.py (Prefect): validar → pruebas → entrenar → evaluar → registrar → seleccionar → publicar → verificar
                                                                 │
                                       publicado/<exp> (copia autosuficiente, versionada en .versiones/)
                                                                 │
                    despliegue/armar_vercel.py ─► sitio estático (visor Three.js + replays + registro)
                                                 + función Python api/sim.py (MuJoCo + política en numpy)
```

- **Python es la autoridad**: la física la calcula MuJoCo. El visor Three.js solo dibuja los cuadros que devuelve la
  simulación (replays grabados o episodios corridos en vivo por la función de Vercel).
- **Exp 9, dos niveles de control**: un navegador (PPO, 15 sensores de distancia + baliza → 7 direcciones) decide por
  dónde rodear las rocas y el caminante del Exp 8 ejecuta. El navegador entrena en un simulador cinemático calibrado
  con el caminante real (`expedicion/navegador.py`) y se evalúa en MuJoCo (`scripts/comparar_navegadores.py`).
- **Evaluación en vivo sin PyTorch**: la función de Vercel carga el actor exportado a numpy (`.npz`). La equivalencia
  con Stable-Baselines3 está probada en `tests/test_politica_numpy.py` (media de la acción igual a 1e-5 y mismo
  resultado por episodio).

## Instalación

Probado con Python 3.14 en Linux (WSL2), CPU, sin GPU.

```bash
git clone https://github.com/rafaelorozco18/robot-expedition.git
cd robot-expedition
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt && pip install -e .
bash scripts/bajar_modelos.sh      # modelos y escenarios de DVC (releases datos-dvc-*; pide `gh auth login`)
```

MLflow completo (`mlflow.db` y `mlruns/`): release `mlflow-registro` del repositorio. Se abre con
`mlflow ui --backend-store-uri sqlite:///mlflow.db`.

## Ejecución

```bash
expedicion lista                               # experimentos y su estado
expedicion info exp-108                        # espacios de observación y acción
expedicion servir                              # visor y API local en http://localhost:8765
expedicion campana exp-108                     # entrena la última semilla, evalúa, registra, documenta, commit y tag
~/.venvs/prefect/bin/python pipelines/flujo.py exp-108             # pipeline completo con Prefect
~/.venvs/prefect/bin/python pipelines/flujo.py exp-108 --rollback  # vuelve a la versión publicada anterior
python scripts/medir40.py models/exp-108/semilla-1/experto.zip     # 40 episodios nuevos por tarea (TAREAS, BASE)
pytest -q                                      # reglas, contrato del ambiente y equivalencia numpy
```

Prefect se instala aparte para no tocar las dependencias del entrenamiento:
`python3 -m venv ~/.venvs/prefect && ~/.venvs/prefect/bin/pip install prefect`.

## Variables

| Variable | Dónde | Para qué |
|---|---|---|
| `MLFLOW_TRACKING_URI` | entrenamiento | Servidor de MLflow compartido; sin ella, `sqlite:///mlflow.db` |
| `API_REMOTA` | `expedicion exportar` | Dirección de la API para evaluar en vivo desde la web estática (`/sim` en Vercel) |
| `PORT`, `HOST` | `expedicion servir` | Puerto y host del servidor (8765 y 127.0.0.1 por omisión) |
| `CORS_ORIGEN` | servidor | Origen permitido (por omisión `*`; la API solo lee) |
| `TAREAS`, `CONTROL`, `BASE` | `scripts/medir40.py` | Tareas a medir, control y semilla inicial (5000 para elegir, 3000 para confirmar) |

No hay secretos en el repositorio. Ver [.env.example](.env.example).

## Reproducir un resultado

1. `git checkout exp-108` (o el tag del experimento) y `bash scripts/bajar_modelos.sh` (equivale a `dvc pull`).
2. `dvc repro evaluar-exp-108` reconstruye el examen; `dvc status` muestra qué cambió.
3. Cada modelo tiene un manifiesto en [manifests/](manifests/) con run, commit, SHA-256 del modelo y de la
   configuración, contrato de observación y acción, suite de evaluación, semilla y modelo de origen.
4. `python scripts/manifiestos.py` y `python scripts/comparacion.py` regeneran manifiestos y la tabla de comparación.

## Versionado

| Qué | Herramienta | Dónde |
|---|---|---|
| Código | git | Un commit y un tag por experimento (`exp-101` … `exp-109`); release final `entrega-final-v3` (`entrega-final`: solo Exps 1 a 8) |
| Pipeline | DVC + Prefect | `dvc.yaml`/`dvc.lock` (una etapa por semilla); `pipelines/flujo.py` |
| Escenarios y trayectorias | DVC | `data/exp-NNN/escenarios.json` (suite fija) y `trayectorias.jsonl` (resultado por episodio) |
| Experimento | MLflow | Un experimento por pregunta, un run por semilla, con hipótesis, parámetros y commit |
| Modelo | DVC + MLflow Model Registry | `models/exp-NNN/semilla-N/`, alias `campeon` en `robot-exp-NNN`; manifiestos en `manifests/` |
| Robot | git | `robots/bipedo-v2.xml` |
| Despliegue | Vercel | Cada deployment lleva el commit (`/sim/api/estado` → `commit`) |

## Equipo

Trabajo en GitHub (`rafaelorozco18/robot-expedition`, privado). Para entrenar: rama propia, `nice -n 19` y
`procesos: 4`, y al terminar `git push` y `bash scripts/subir_modelos.sh`. Reglas completas en
[docs/serie-marte.md](docs/serie-marte.md) y [CLAUDE.md](CLAUDE.md).

La primera versión del proyecto (navegación en rejilla con Q-learning) está archivada en el tag `legado-navegacion`;
la serie anterior de tres planetas, en los tags `exp-001` a `exp-028`.
