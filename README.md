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

El código vive en GitHub (`rafaelorozco18/robot-expedition`, privado). Los modelos y escenarios, en el remoto
de DVC de DagsHub, y MLflow puede usar el servidor de DagsHub (ver abajo).

## Para el equipo: cómo empezar

1. Clonar e instalar:

   ```bash
   git clone https://github.com/rafaelorozco18/robot-expedition.git
   cd robot-expedition
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt && pip install -e .
   ```

2. Credenciales de DagsHub (cada uno con su token: DagsHub → *User Settings → Tokens*). Se guardan en
   `.dvc/config.local`, que git no sube:

   ```bash
   dvc remote modify origin --local auth basic
   dvc remote modify origin --local user TU_USUARIO_DAGSHUB
   dvc remote modify origin --local password TU_TOKEN
   ```

3. Bajar modelos y escenarios y preparar el visor:

   ```bash
   dvc pull
   expedicion publicar
   expedicion servir          # http://localhost:8765
   ```

4. MLflow compartido (opcional; sin esto cada uno registra en su `mlflow.db` local):

   ```bash
   export MLFLOW_TRACKING_URI=https://dagshub.com/rafaelorozco18/robot-expedition.mlflow
   export MLFLOW_TRACKING_USERNAME=TU_USUARIO_DAGSHUB
   export MLFLOW_TRACKING_PASSWORD=TU_TOKEN
   ```

### Reglas para entrenar

- **Los experimentos van en cadena.** Cada uno parte del campeón del anterior (`parte_de`): el Exp 8 no se puede
  entrenar hasta que el Exp 7 esté aprobado y su campeón esté en DVC (`dvc pull`).
- Antes de tocar un experimento, lee su `pendiente` en `experimentos/exp-NNN.yaml` y la bitácora
  `docs/serie-marte.md`: ahí está lo que ya se probó y falló.
- Trabaja en una rama propia (`git switch -c exp-107-nombre`) y cambia **una cosa por intento**.
- Entrenar ocupa la CPU por horas. Con el equipo en uso: `nice -n 19 ionice -c3` y `procesos: 4` en el yaml.
- Para correr un experimento completo: `expedicion campana exp-NNN` (entrena, evalúa, documenta, hace commit y tag).
- Al terminar, subir **las dos cosas**: `dvc push` (modelos) y `git push origin TU_RAMA --tags` (código y lock).
  Si solo se sube git, los demás tienen un `dvc.lock` que apunta a modelos que no existen en el remoto.
- Aprobar exige no olvidar: el campeón debe seguir pasando los exámenes anteriores (`aprobar.sin_olvidar`).
  No bajes los criterios de aprobación sin acordarlo con el grupo.

La navegación en rejilla con Q-learning, primera versión del proyecto, está archivada en el tag
`legado-navegacion`.

## Pruebas

```bash
pytest -q
```
