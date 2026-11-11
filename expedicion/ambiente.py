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

PLANETAS = ["luna", "marte", "tierra"]
# Titán y Venus solo se usan como gravedades nunca vistas en el examen del Exp 16.
GRAVEDADES = {"luna": 1.62, "marte": 3.71, "tierra": 9.81, "titan": 1.35, "venus": 8.87}
PERTURBACIONES = ["ninguna", "empujon"]
# Propiedades de cada piso. Fricción: rango sorteado por episodio. Arrastre: N por m/s sobre el pie
# hundido. Sacudida: fuerza horizontal al azar (N). MuJoCo no modela suelos blandos: son aproximaciones.
PISOS = {
    "suelo": {"friccion": [0.9, 0.9], "arrastre": [0, 0], "succion": 0, "sacudida": 0},
    "arena": {"friccion": [0.6, 0.8], "arrastre": [30, 60], "succion": 0, "sacudida": 0},
    "barro": {"friccion": [0.4, 0.6], "arrastre": [60, 120], "succion": 40, "sacudida": 0},
    "barro_profundo": {"friccion": [0.35, 0.5], "arrastre": [100, 200], "succion": 90, "sacudida": 0},
    "grava": {"friccion": [0.5, 0.7], "arrastre": [10, 20], "succion": 0, "sacudida": 25},
    "hielo": {"friccion": [0.08, 0.2], "arrastre": [0, 0], "succion": 0, "sacudida": 0},
}
POSTURA = {"cadera_pitch": -0.15, "rodilla": 0.3, "tobillo_pitch": -0.15}


class BipedoEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, exp, entrenando=False):
        self.exp = exp
        self.entrenando = entrenando
        self.tarea = TAREAS[exp["tarea"]](exp)
        xml = (RAIZ / exp["robot"]).read_text()
        self.conf_listones = exp.get("listones")
        if self.conf_listones:
            slots = "".join(f'<geom name="liston_{k}" type="box" size="0.03 1.6 {self.conf_listones["alto_m"] / 2}" '
                            f'pos="{200 + k} 0 0" rgba="0.55 0.35 0.2 1" friction="0.9 0.05 0.01"/>'
                            for k in range(self.conf_listones["cantidad"]))
            xml = xml.replace("</worldbody>", slots + "</worldbody>", 1)
        self.model = mujoco.MjModel.from_xml_string(xml)
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
        self.ids_listones = [m.geom(f"liston_{k}").id for k in range(self.conf_listones["cantidad"])] if self.conf_listones else []
        self.ids_suelo = np.array([self.id_piso, *self.ids_listones])
        self.ids_pies = [m.geom("pie_i").id, m.geom("pie_d").id]

        self.adversidad = exp.get("adversidad", {})
        self.pendiente = np.radians(exp.get("pendiente_grados", 0.0))
        self.gain_base = m.actuator_gainprm[:, 0].copy()
        self.bias_base = m.actuator_biasprm[:, :3].copy()
        self.fuerza_base = m.actuator_forcerange.copy()
        self.ids_cuerpo_pies = [m.body("pie_i").id, m.body("pie_d").id]
        self.conf_pisos = exp.get("pisos")
        if self.conf_pisos:
            m.geom_friction[self.id_piso, 0] = 0.01  # manda la fricción de cada pie, según el piso bajo él

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

    def rumbo(self):
        r = self.data.xmat[self.id_torso]
        return float(np.arctan2(r[3], r[0]))

    def error_rumbo(self):
        e = self.rumbo() - self.rumbo_objetivo
        return float(np.arctan2(np.sin(e), np.cos(e)))

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
        con_piso = pares[np.isin(pares, self.ids_suelo).any(axis=1)]
        otros = con_piso[~np.isin(con_piso, self.ids_suelo)]
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
        sorteables = self.exp.get("planetas_entrenamiento", PLANETAS)
        self.planeta = options.get("planeta") or sorteables[self.np_random.integers(len(sorteables))]
        rango_g = self.exp.get("parametros", {}).get("gravedad_rango")
        self.g = float(self.np_random.uniform(*rango_g)) if rango_g and self.entrenando else GRAVEDADES[self.planeta]
        # Una rampa equivale a inclinar la gravedad respecto del piso.
        self.model.opt.gravity[0] = -self.g * np.sin(self.pendiente)
        self.model.opt.gravity[2] = -self.g * np.cos(self.pendiente)

        ruido = self.exp["ambiente"]["ruido_inicial"]
        self.data.ctrl[:] = self.postura_inicial
        self._colocar(self.postura_inicial + self.np_random.normal(0, ruido, self.model.nu))
        v0 = self.exp["ambiente"].get("velocidad_inicial", 0.0)
        if v0:  # arranca desequilibrado: debe recuperar el equilibrio desde el primer instante
            ang = self.np_random.uniform(0, 2 * np.pi)
            self.data.qvel[:2] = v0 * np.array([np.cos(ang), np.sin(ang)])
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
        self.accion_aplicada = np.zeros(self.model.nu)
        self.empujado = False
        self._iniciar_estadisticas()
        self.tramos = self._sortear_tramos() if self.conf_pisos else []
        self.listones = self._colocar_listones() if self.conf_listones else []
        self.pie_previo = [self.posicion_pie(0).copy(), self.posicion_pie(1).copy()]
        self.rumbo_objetivo = 0.0
        self.destino = None
        self._iniciar_adversidad()
        self.tarea.iniciar(self)
        self.tarea.actualizar(self)
        return self._observar(), self._info()

    def step(self, action):
        accion = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        self.tarea.actualizar(self)
        self.empujado = self.pasos == self.paso_empujon
        if self.empujado:
            self.data.qvel[:3] += self.direccion_empujon * self.exp["ambiente"]["empujon_ms"]
        if self.retardo:
            self.cola_acciones.append(accion)
            accion_real = self.cola_acciones.pop(0) if len(self.cola_acciones) > self.retardo else np.zeros(self.model.nu)
        else:
            accion_real = accion
        # Filtro de primer orden: los servos no saltan de golpe a cada orden (marcha más suave).
        f = self.control.get("filtro", 0.0)
        self.accion_aplicada = (1 - f) * accion_real + f * self.accion_aplicada
        accion_real = self.accion_aplicada
        self.data.ctrl[:] = self.postura_inicial + accion_real * self.control["rango"]
        if self.adversidad:
            self._aplicar_viento()
        if self.tramos:
            self._aplicar_piso()
        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)
        self.pasos += 1
        self.energia += float(np.sum(np.abs(self.data.actuator_force * self.data.actuator_velocity))) * self.dt

        self._acumular_estadisticas(accion)
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

    def _iniciar_adversidad(self):
        a, m = self.adversidad, self.model
        self.data.xfrc_applied[:] = 0.0
        self.cola_acciones = []
        self.retardo = 0
        if "retardo_ms" in a:
            self.retardo = int(self.np_random.integers(a["retardo_ms"][0], a["retardo_ms"][1] + 1) / (self.dt * 1000))
        self.viento = np.zeros(3)
        if "viento_n" in a:
            fuerza = self.np_random.uniform(*a["viento_n"])
            if a.get("viento_libre"):
                ang = self.np_random.uniform(0, 2 * np.pi)
                self.viento[:2] = fuerza * np.array([np.cos(ang), np.sin(ang)])
            else:
                self.viento[1] = fuerza * self.np_random.choice([-1.0, 1.0])
        self.viento_actual = self.viento.copy()
        self.rafaga_hasta = -1
        self.rafaga = np.zeros(3)
        m.actuator_gainprm[:, 0] = self.gain_base
        m.actuator_biasprm[:, :3] = self.bias_base
        m.actuator_forcerange[:] = self.fuerza_base
        self.motor_debil = None
        if "motor_debil" in a:
            j = int(self.np_random.integers(m.nu))
            self.motor_debil = self.nombres_motor[j]
            f = a["motor_debil"]
            m.actuator_gainprm[j, 0] *= f
            m.actuator_biasprm[j, :3] *= f
            m.actuator_forcerange[j] *= f

    def _aplicar_viento(self):
        a = self.adversidad
        fuerza = self.viento.copy()
        if "rafaga_n" in a:
            if self.pasos > self.rafaga_hasta and self.np_random.random() < a.get("prob_rafaga", 0.01):
                self.rafaga_hasta = self.pasos + int(0.5 / self.dt)
                f = self.np_random.uniform(*a["rafaga_n"])
                base = self.viento[:2] / (np.linalg.norm(self.viento[:2]) + 1e-9) if np.any(self.viento) else np.array([0.0, 1.0])
                # la ráfaga sopla en la dirección del viento, a veces cruzada
                ang = self.np_random.normal(0, 0.5)
                c, sn = np.cos(ang), np.sin(ang)
                self.rafaga = np.array([f * (c * base[0] - sn * base[1]), f * (sn * base[0] + c * base[1]), 0.0])
            if self.pasos <= self.rafaga_hasta:
                fuerza = fuerza + self.rafaga
        self.viento_actual = fuerza
        self.data.xfrc_applied[self.id_torso, :3] = fuerza

    # --------------------------------------------------- calidad del movimiento
    def _iniciar_estadisticas(self):
        self.vel_pies = [0.0, 0.0]
        self.pos_pies = [self.posicion_pie(k)[:2].copy() for k in (0, 1)]
        self.est = {"pasos": [], "despejes": [], "cambios": [], "inclinaciones": [], "vel_torso": [],
                    "aire": [0, 0], "despegue": [None, None], "altura_vuelo": [0.0, 0.0],
                    "aplicada_previa": np.zeros(self.model.nu)}

    def _acumular_estadisticas(self, accion):
        """Un paso cuenta solo si el pie estuvo 0,1 s en el aire y subió 1,5 cm: el temblor no es caminar."""
        e = self.est
        izq, der, _ = self.contactos()
        for lado, apoyado in enumerate((izq, der)):
            pos = self.posicion_pie(lado)
            self.vel_pies[lado] = float(np.linalg.norm(pos[:2] - self.pos_pies[lado])) / self.dt
            self.pos_pies[lado] = pos[:2].copy()
            if not apoyado:
                if e["aire"][lado] == 0:
                    e["despegue"][lado] = pos[:2].copy()
                e["aire"][lado] += 1
                e["altura_vuelo"][lado] = max(e["altura_vuelo"][lado], float(pos[2]) - 0.04)
            else:
                if e["aire"][lado] * self.dt >= 0.1 and e["altura_vuelo"][lado] >= 0.015:
                    e["ultimo_vuelo"] = e["aire"][lado] * self.dt
                    e["pasos"].append(float(np.linalg.norm(pos[:2] - e["despegue"][lado])))
                    e["despejes"].append(e["altura_vuelo"][lado])
                e["aire"][lado], e["altura_vuelo"][lado] = 0, 0.0
        e["cambios"].append(float(np.mean(np.abs(self.accion_aplicada - e["aplicada_previa"]))))
        e["aplicada_previa"] = self.accion_aplicada.copy()
        e["inclinaciones"].append(self.inclinacion_grados())
        e["vel_torso"].append(float(np.linalg.norm(self.data.qvel[:2])))

    def estadisticas(self):
        """Indicadores de cómo se mueve, de 0 a 100. Ver docs/serie-marte.md."""
        e = self.est
        segundos = max(self.pasos * self.dt, 1e-6)
        largo = float(np.median(e["pasos"])) if e["pasos"] else 0.0
        despeje = float(np.median(e["despejes"])) if e["despejes"] else 0.0
        cambio = float(np.mean(e["cambios"])) if e["cambios"] else 0.0
        inclinacion = float(np.mean(e["inclinaciones"])) if e["inclinaciones"] else 0.0
        suavidad = float(np.exp(-cambio / 0.04))
        erguido = float(np.clip(1 - inclinacion / 20, 0, 1))
        if self.tarea.usa_reloj:
            zancada = float(np.exp(-(((largo - 0.5) / 0.2) ** 2)))   # recorrido del pie en cada paso
            elevacion = float(np.clip(despeje / 0.05, 0, 1))
            cadencia = len(e["pasos"]) / segundos
            ritmo = float(np.exp(-(((cadencia - 1.8) / 0.7) ** 2)))  # pasos por segundo
            partes = [suavidad, erguido, zancada, elevacion, ritmo]
        else:
            quietud = float(np.exp(-float(np.mean(e["vel_torso"])) / 0.05)) if e["vel_torso"] else 0.0
            cadencia = 0.0
            partes = [suavidad, erguido, quietud]
        return {"calidad": round(100 * float(np.mean(partes)), 1), "largo_paso_m": round(largo, 3),
                "despeje_m": round(despeje, 3), "pasos_por_s": round(cadencia, 2),
                "inclinacion_media": round(inclinacion, 1), "suavidad": round(100 * suavidad, 1)}

    def _sortear_tramos(self):
        conf = self.conf_pisos
        orden = list(conf["tramos"])
        if conf.get("mezclar"):
            self.np_random.shuffle(orden)
        tramos, x = [], float(conf.get("inicio_m", 2.0))
        for t in orden:
            p = PISOS[t["tipo"]]
            largo = float(self.np_random.uniform(*t["largo"])) if isinstance(t["largo"], list) else float(t["largo"])
            tramos.append({"x0": x, "x1": x + largo, "tipo": t["tipo"],
                           "friccion": float(self.np_random.uniform(*p["friccion"])),
                           "arrastre": float(self.np_random.uniform(*p["arrastre"])),
                           "succion": p["succion"], "sacudida": p["sacudida"]})
            x += largo
        return tramos

    def _colocar_listones(self):
        c = self.conf_listones
        posiciones, x = [], float(c["inicio_m"])
        for k, g in enumerate(self.ids_listones):
            x += float(self.np_random.uniform(*c["separacion_m"]))
            self.model.geom_pos[g] = [x, 0.0, c["alto_m"] / 2]
            posiciones.append([round(x, 3), c["alto_m"]])
        mujoco.mj_forward(self.model, self.data)
        return posiciones

    def _aplicar_piso(self):
        base = PISOS["suelo"]
        for lado in (0, 1):
            pos = self.posicion_pie(lado)
            piso = next((t for t in self.tramos if t["x0"] <= pos[0] < t["x1"]), None)
            self.model.geom_friction[self.ids_pies[lado], 0] = piso["friccion"] if piso else base["friccion"][0]
            fuerza = np.zeros(3)
            if piso and pos[2] < 0.08:
                v = (pos - self.pie_previo[lado]) / self.dt
                fuerza = -piso["arrastre"] * v
                if piso["succion"] and v[2] > 0:
                    fuerza[2] -= piso["succion"]
                if piso["sacudida"]:
                    fuerza[:2] += self.np_random.uniform(-piso["sacudida"], piso["sacudida"], 2)
            self.data.xfrc_applied[self.ids_cuerpo_pies[lado], :3] = fuerza
            self.pie_previo[lado] = pos.copy()

    def piso_bajo_torso(self):
        x = self.data.qpos[0]
        return next((t["tipo"] for t in self.tramos if t["x0"] <= x < t["x1"]), "suelo")

    def _observar(self):
        d = self.data
        izq, der, _ = self.contactos()
        reloj = [np.sin(self.fase()), np.cos(self.fase())] if self.tarea.usa_reloj else [0.0, 0.0]
        ruido = self.adversidad.get("ruido_obs")
        rot = d.xmat[self.id_torso].reshape(3, 3)
        vector = np.concatenate([
            [self.altura_torso() - self.altura_pie],
            rot[2], rot.T @ [np.cos(self.rumbo_objetivo), np.sin(self.rumbo_objetivo), 0.0],
            rot @ d.qvel[:3], d.qvel[3:6] * 0.25,
            self.angulos() - self.postura_inicial,
            d.qvel[self.adr_v] * 0.1,
            self.accion_previa,
            [float(izq), float(der)],
            [self.g / 9.81],
            self.comando, reloj,
        ])
        if ruido:
            vector[:13 + 2 * self.model.nu] += self.np_random.normal(0.0, ruido, 13 + 2 * self.model.nu)
        return np.clip(vector, -10, 10).astype(np.float32)

    def _info(self, desglose=None):
        return {"pasos": self.pasos, "desglose": desglose or {}, "planeta": self.planeta}
