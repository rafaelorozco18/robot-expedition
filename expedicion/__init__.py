"""Robot Expedition: un bípedo que aprende por experimentos de dificultad creciente."""

import os

# Cada proceso ya es un núcleo: los hilos de BLAS compiten entre sí y multiplican el tiempo por 10.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

import gymnasium as gym

__version__ = "0.2.0"

gym.register(id="RobotExpedition-v1", entry_point="expedicion.ambiente:BipedoEnv")
