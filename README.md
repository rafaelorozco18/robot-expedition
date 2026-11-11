# Robot Expedition

Proyecto final de MLOps Autonomous Lab. Un robot bípedo de 12 articulaciones aprende a moverse en Marte,
subiendo la dificultad de a una cosa por experimento: sostenerse, caminar, resistir el viento, caminar con
buena técnica, girar en una esquina, caminar en curva y dominar todo eso en terreno difícil.

- Serie vigente: [docs/serie-marte.md](docs/serie-marte.md) (experimentos `exp-101` a `exp-109`)
- Ficha de cada experimento: [docs/experimentos/](docs/experimentos/)
- Resultados: [docs/resultados.md](docs/resultados.md)
- Contexto de trabajo: [CLAUDE.md](CLAUDE.md)
- Serie anterior (plan de 50, tres planetas): [docs/plan-50-experimentos.md](docs/plan-50-experimentos.md)

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Visor 3D

```bash
expedicion servir        # http://localhost:8765
expedicion exportar      # versión estática en exportado/, para compartir sin servidor
```

El selector superior recorre los experimentos de la serie. El botón **Ver cómo aprendió** reproduce cinco
etapas de cada uno: fracaso absoluto, fracaso pero mejor, punto de inflexión, cumplido y perfeccionado, todas
en el mismo escenario de Marte. En los experimentos con viento se ven las estelas de polvo y una manga de viento
que siguen la fuerza que aplica el simulador.

Además se ven las versiones del robot, la curva de aprendizaje, el torque de cada articulación y si el
modelo olvidó pruebas anteriores. MuJoCo corre cada episodio en Python y el navegador solo lo dibuja.
Three.js está incluido en `web/vendor/`, así que no requiere internet.

## CLI

```bash
expedicion lista                           # experimentos y su estado
expedicion info exp-001                    # espacios de observación y acción
expedicion entrenar exp-001 --semilla 0    # una corrida con PPO
expedicion evaluar exp-001                 # compara semillas y elige al campeón
expedicion progreso exp-001                # prueba cada foto del entrenamiento
expedicion regresion exp-001               # repite las pruebas anteriores
expedicion evolucion exp-001               # calcula las etapas de aprendizaje del visor
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
