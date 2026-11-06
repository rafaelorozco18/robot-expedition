"""Entorno vectorizado por bloques: cada proceso simula varios robots y responde con un solo arreglo.

SubprocVecEnv hace una ida y vuelta por robot y serializa todos sus `info`. Con 16 robots, los
simuladores pasaban más del 80 % del tiempo esperando al proceso principal.
"""

import multiprocessing as mp

import numpy as np
from stable_baselines3.common.vec_env import VecEnv


def _trabajador(conexion, crear, n, escala):
    entornos = [crear(i) for i in range(n)]
    suma = [0.0] * n
    largo = [0] * n
    obs = np.stack([e.reset()[0] for e in entornos])
    while True:
        orden, datos = conexion.recv()
        if orden == "paso":
            recompensas = np.zeros(n, dtype=np.float32)
            hechos = np.zeros(n, dtype=bool)
            infos = []
            for i, e in enumerate(entornos):
                o, r, term, trunc, info = e.step(datos[i])
                r *= escala
                suma[i] += r
                largo[i] += 1
                recompensas[i] = r
                if term or trunc:
                    hechos[i] = True
                    infos.append((i, {"episode": {"r": suma[i], "l": largo[i], "t": 0.0},
                                      "exito": info["exito"], "TimeLimit.truncated": trunc and not term,
                                      "terminal_observation": o}))
                    suma[i], largo[i] = 0.0, 0
                    o = e.reset()[0]
                obs[i] = o
            conexion.send((obs, recompensas, hechos, infos))
        elif orden == "reiniciar":
            conexion.send(obs)
        else:
            conexion.close()
            return


class BloquesVecEnv(VecEnv):
    def __init__(self, crear, procesos, por_proceso, escala):
        contexto = mp.get_context("fork")
        self.por_proceso = por_proceso
        self.conexiones, self.procesos = [], []
        muestra = crear(0)
        for p in range(procesos):
            local, remoto = contexto.Pipe()
            fabrica = lambda i, base=p: crear(base * por_proceso + i)
            proceso = contexto.Process(target=_trabajador, args=(remoto, fabrica, por_proceso, escala), daemon=True)
            proceso.start()
            remoto.close()
            self.conexiones.append(local)
            self.procesos.append(proceso)
        super().__init__(procesos * por_proceso, muestra.observation_space, muestra.action_space)
        muestra.close()

    def reset(self):
        for c in self.conexiones:
            c.send(("reiniciar", None))
        return np.concatenate([c.recv() for c in self.conexiones])

    def step_async(self, actions):
        for j, c in enumerate(self.conexiones):
            c.send(("paso", actions[j * self.por_proceso:(j + 1) * self.por_proceso]))

    def step_wait(self):
        infos = [{} for _ in range(self.num_envs)]
        partes = [c.recv() for c in self.conexiones]
        for j, parte in enumerate(partes):
            for i, info in parte[3]:
                infos[j * self.por_proceso + i] = info
        return (np.concatenate([p[0] for p in partes]), np.concatenate([p[1] for p in partes]),
                np.concatenate([p[2] for p in partes]), infos)

    def close(self):
        for c in self.conexiones:
            c.send(("cerrar", None))
        for p in self.procesos:
            p.join(timeout=5)

    def get_attr(self, attr_name, indices=None):
        return [None] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        pass

    def env_method(self, method_name, *args, indices=None, **kwargs):
        return [None] * self.num_envs

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs
