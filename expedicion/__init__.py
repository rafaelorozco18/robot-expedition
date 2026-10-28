"""Robot Expedition: visitar dos balizas en orden y volver a la base antes de agotar la batería."""

import gymnasium as gym

__version__ = "0.1.0"

gym.register(id="RobotExpedition-v0", entry_point="expedicion.ambiente:ExpedicionEnv")
