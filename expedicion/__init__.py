"""Robot Expedition: un bípedo que aprende por experimentos de dificultad creciente."""

import gymnasium as gym

__version__ = "0.2.0"

gym.register(id="RobotExpedition-v1", entry_point="expedicion.ambiente:BipedoEnv")
