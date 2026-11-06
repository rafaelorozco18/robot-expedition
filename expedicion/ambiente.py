"""Ambiente MuJoCo del bípedo. La tarea concreta la define cada experimento.

Estado del mundo (simulador): posiciones y velocidades completas, contactos, gravedad.
Acción (agente): ángulo objetivo de cada articulación, relativo a la postura de pie.
Un servo de posición (robots/*.xml) lo convierte en torque, con límite por articulación.
Observación (agente): orientación y velocidades del torso, ángulos y velocidades de las
articulaciones, última acción, contacto de cada pie y gravedad. No ve su posición absoluta
ni el tipo de piso.
"""

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from .experimentos import RAIZ
from .tareas import TAREAS

GRAVEDADES = {"luna": 1.62, "marte": 3.71, "tierra": 9.81}
PLANETAS = list(GRAVEDADES)
PERTURBACIONES = ["ninguna", "empujon"]
POSTURA = {"cadera_pitch": -0.15, "rodilla": 0.3, "tobillo_pitch": -0.15}


class BipedoEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, exp, entrenando=False):
        self.exp = exp
        self.entrenando = entrenando
        self.tarea = TAREAS[exp["tarea"]](exp)
        self.model = mujoco.MjModel.from_xml_path(str(RAIZ / exp["robot"]))
        self.data = mujoco.MjData(self.model)
        self.frame_skip = exp["ambiente"]["frame_skip"]
        self.dt = self.model.opt.timestep * self.frame_skip
        self.max_pasos = int(exp["ambiente"]["duracion_s"] / self.dt)

        m = self.model
        self.nombres_motor = [m.actuator(i).name for i in range(m.nu)]
        self.adr_q = np.array([m.joint(n).qposadr[0] for n in self.nombres_motor])
        self.adr_v = np.array([m.joint(n).dofadr[0] for n in self.nombres_motor])
        self.control = exp["control"]
        self.torque_max = m.actuator_forcerange[:, 1].copy()
        self.id_torso = m.body("torso").id
        self.id_piso = m.geom("piso").id
        self.ids_pies = [m.geom("pie_i").id, m.geom("pie_d").id]

        self.postura_inicial = np.array(
            [next((v for k, v in POSTURA.items() if n.startswith(k)), 0.0) for n in self.nombres_motor])
        self._colocar(self.postura_inicial)
        self.altura_pie = self.altura_torso()
        self.qpos_inicial = self.data.qpos.copy()

        self.action_space = spaces.Box(-1.0, 1.0, shape=(m.nu,), dtype=np.float32)
        n_obs = 1 + 6 + 3 + 3 + m.nu * 3 + 2 + 1 + 4 + 2
        self.observation_space = spaces.Box(-10.0, 10.0, shape=(n_obs,), dtype=np.float32)

    # ------------------------------------------------------------- mediciones
    def angulos(self):
        return self.data.qpos[self.adr_q]

    def altura_torso(self):
        return float(self.data.xpos[self.id_torso, 2])

    def arriba_del_torso(self):
        return self.data.xmat[self.id_torso].reshape(3, 3)[2]  # z del mundo en ejes del torso

    def mundo_x_en_torso(self):
        return self.data.xmat[self.id_torso].reshape(3, 3)[0]  # x del mundo en ejes del torso

    def centro_masa(self):
        return self.data.subtree_com[self.id_torso]

    def posicion_pie(self, lado):
        return self.data.geom_xpos[self.ids_pies[lado]]

    def distancia(self):
        return float(self.data.qpos[0] - self.x_inicial)

    def recorrido(self):
        return float(np.hypot(self.data.qpos[0] - self.x_inicial, self.data.qpos[1] - self.y_inicial))

    def fase(self):
        periodo = self.exp.get("parametros", {}).get("periodo_s", 0.8) * np.sqrt(9.81 / self.g)
        return 2 * np.pi * self.pasos * self.dt / min(periodo, 1.6)

    def inclinacion_grados(self):
        return float(np.degrees(np.arccos(np.clip(self.arriba_del_torso()[2], -1, 1))))

    def contactos(self):
        """(pie izquierdo apoyado, pie derecho apoyado, cuerpo toca el piso)."""
        pares = self.data.contact.geom[:self.data.ncon]
        con_piso = pares[(pares == self.id_piso).any(axis=1)]
        otros = con_piso[con_piso != self.id_piso]
        izq = bool((otros == self.ids_pies[0]).any())
        der = bool((otros == self.ids_pies[1]).any())
        return izq, der, bool(((otros != self.ids_pies[0]) & (otros != self.ids_pies[1])).any())

    def torques_relativos(self):
        return self.data.actuator_force / self.torque_max

    def toca_piso_con_cuerpo(self):
        return self.contactos()[2]

    # --------------------------------------------------------------- simulación
    def _colocar(self, angulos):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.adr_q] = angulos
        mujoco.mj_forward(self.model, self.data)
        fondo = min((self.data.geom_xpos[g, 2] - 0.02) for g in self.ids_pies)
        self.data.qpos[2] -= fondo
        mujoco.mj_forward(self.model, self.data)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        self.planeta = options.get("planeta") or PLANETAS[self.np_random.integers(len(PLANETAS))]
        rango_g = self.exp.get("parametros", {}).get("gravedad_rango")
        self.g = float(self.np_random.uniform(*rango_g)) if rango_g and self.entrenando else GRAVEDADES[self.planeta]
        self.model.opt.gravity[2] = -self.g

        ruido = self.exp["ambiente"]["ruido_inicial"]
        self.data.ctrl[:] = self.postura_inicial
        self._colocar(self.postura_inicial + self.np_random.normal(0, ruido, self.model.nu))
        self.perturbacion = options.get("perturbacion")
        if self.perturbacion is None:
            prob = self.exp["ambiente"]["empujon_entrenando"] if self.entrenando else 0.0
            self.perturbacion = "empujon" if self.np_random.random() < prob else "ninguna"
        self.paso_empujon = None
        self.direccion_empujon = None
        if self.perturbacion == "empujon":
            self.paso_empujon = int(self.np_random.integers(self.max_pasos // 4, 3 * self.max_pasos // 4))
            ang = self.np_random.uniform(0, 2 * np.pi)
            self.direccion_empujon = np.array([np.cos(ang), np.sin(ang), 0.0])

        self.pasos = 0
        self.energia = 0.0
        self.x_inicial = float(self.data.qpos[0])
        self.y_inicial = float(self.data.qpos[1])
        self.accion_previa = np.zeros(self.model.nu)
        self.empujado = False
        self.tarea.iniciar(self)
        self.tarea.actualizar(self)
        return self._observar(), self._info()

    def step(self, action):
        accion = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        self.tarea.actualizar(self)
        self.empujado = self.pasos == self.paso_empujon
        if self.empujado:
            self.data.qvel[:3] += self.direccion_empujon * self.exp["ambiente"]["empujon_ms"]
        self.data.ctrl[:] = self.postura_inicial + accion * self.control["rango"]
        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)
        self.pasos += 1
        self.energia += float(np.sum(np.abs(self.data.actuator_force * self.data.actuator_velocity))) * self.dt

        desglose = self.tarea.recompensa(self, accion, self.accion_previa)
        recompensa = sum(desglose.values())
        self.accion_previa = accion
        self.motivo = self.tarea.fin(self)
        terminated = self.motivo is not None
        if terminated:
            recompensa -= self.exp["recompensa"]["caida"]
            desglose["caida"] = -self.exp["recompensa"]["caida"]
        truncated = not terminated and self.pasos >= self.max_pasos
        info = self._info(desglose)
        if terminated or truncated:
            info["exito"] = bool(self.tarea.exito(self, truncated))
        return self._observar(), float(recompensa), terminated, truncated, info

    def _observar(self):
        d = self.data
        izq, der, _ = self.contactos()
        reloj = [np.sin(self.fase()), np.cos(self.fase())] if self.tarea.usa_reloj else [0.0, 0.0]
        rot = d.xmat[self.id_torso].reshape(3, 3)
        return np.clip(np.concatenate([
            [self.altura_torso() - self.altura_pie],
            rot[2], rot[0],
            rot @ d.qvel[:3], d.qvel[3:6] * 0.25,
            self.angulos() - self.postura_inicial,
            d.qvel[self.adr_v] * 0.1,
            self.accion_previa,
            [float(izq), float(der)],
            [self.g / 9.81],
            self.comando, reloj,
        ]), -10, 10).astype(np.float32)

    def _info(self, desglose=None):
        return {"pasos": self.pasos, "desglose": desglose or {}, "planeta": self.planeta}
