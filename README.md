# Robot Expedition

Proyecto final de MLOps Autonomous Lab. Un robot con articulaciones aprende a controlar su cuerpo
en mundos hostiles, subiendo la dificultad de a una cosa por experimento: primero sostenerse de pie,
después caminar, cruzar terrenos difíciles y, al final, completar una misión.

- Plan: [docs/plan-50-experimentos.md](docs/plan-50-experimentos.md)
- Ficha de cada experimento: [docs/experimentos/](docs/experimentos/)
- Contexto de trabajo: [CLAUDE.md](CLAUDE.md)

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Visor 3D

```bash
expedicion servir        # http://localhost:8765
```

El selector superior recorre los 50 experimentos. En cada uno se pueden ver las versiones del robot
(sin entrenar, aleatorio, aprendiz y experto), la curva de aprendizaje con cualquier foto intermedia,
las condiciones (planeta y perturbación), el torque de cada articulación y si el modelo olvidó pruebas
anteriores. MuJoCo corre cada episodio en Python y el navegador solo lo dibuja. Three.js está incluido
en `web/vendor/`, así que no requiere internet.

## CLI

```bash
expedicion lista                           # experimentos y su estado
expedicion info exp-001                    # espacios de observación y acción
expedicion entrenar exp-001 --semilla 0    # una corrida con PPO
expedicion evaluar exp-001                 # compara semillas y elige al campeón
expedicion progreso exp-001                # prueba cada foto del entrenamiento
expedicion regresion exp-001               # repite las pruebas anteriores
expedicion ver exp-001 --planeta luna      # imprime un episodio en la terminal
expedicion campana exp-002 exp-003         # corre, registra, documenta y versiona en cadena
```

## Cómo agregar un experimento

1. Edita `experimentos/exp-NNN.yaml`. Solo escribe lo que cambia frente a `experimentos/base.yaml`.
2. Si hace falta una tarea nueva, agrégala en `expedicion/tareas.py`.
3. Ejecuta `expedicion campana exp-NNN`.

## Versionado

| Qué | Herramienta | Dónde |
|---|---|---|
| **Código** | git | Un commit y un tag por experimento: `exp-001`, `exp-002`… |
| **Pipeline** | DVC | `dvc.yaml`, generado por `expedicion pipeline`, y `dvc.lock` con los hashes |
| **Dataset** | DVC | `data/exp-NNN/`: escenarios de prueba congelados y trayectorias grabadas |
| **Experimento** | MLflow | Un experimento por pregunta y una corrida por semilla, en `mlflow.db` |
| **Modelo** | DVC y MLflow Model Registry | `models/exp-NNN/`, con el alias `campeon` en `robot-exp-NNN` |
| **Robot** | git | `robots/bipedo-vN.xml`, con versión propia |

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db    # http://localhost:5000
dvc metrics show
```

DVC y MLflow son locales: para compartirlos con el equipo falta configurar un remoto (`dvc remote add`)
y un servidor de MLflow.

La navegación en rejilla con Q-learning, primera versión del proyecto, está archivada en el tag
`legado-navegacion`.

## Pruebas

```bash
pytest -q
```
