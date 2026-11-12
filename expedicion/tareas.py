"""Tareas: qué premia cada experimento, cuándo termina y qué cuenta como éxito.

Todas comparten la misma observación y las mismas salidas, para que un modelo pueda
heredarse de un experimento al siguiente. Lo que cambia se pasa por `env.comando`:
[velocidad x, velocidad y, altura relativa, lado], más un reloj de marcha.
"""

import numpy as np


class Tarea:
    titulo_exito = "Se mantuvo de pie"
    usa_reloj = False

    def __init__(self, exp):
        self.exp = exp
        self.p = exp["recompensa"]
        self.t = exp.get("parametros", {})

    def iniciar(self, env):
        env.comando = np.array([0.0, 0.0, 1.0, 0.0])

    def actualizar(self, env):
        pass

    def comunes(self, env, accion, previa):
        return {
            "vivo": self.p["vivo"],
            "esfuerzo": -self.p["esfuerzo"] * float(np.mean(env.torques_relativos() ** 2)),
            "suavidad": -self.p["suavidad"] * float(np.mean((accion - previa) ** 2)),
        }

    def fin(self, env):
        a = env.exp["ambiente"]
        if env.toca_piso_con_cuerpo():
            return "tocó el piso con el cuerpo"
        if env.altura_torso() < a["altura_minima"] * env.altura_pie:
            return "se agachó o cayó"
        if env.inclinacion_grados() > a["inclinacion_maxima"]:
            return "se inclinó demasiado"
        return None

    def exito(self, env, truncado):
        return truncado

    def resumen(self, env):
        return ""

    def avance(self, env):
        return min(1.0, env.pasos / env.max_pasos)

    def orden(self, env):
        return "quedarse de pie"


class DePie(Tarea):
    def iniciar(self, env):
        super().iniciar(env)
        self.pies_inicio = [env.posicion_pie(0)[:2].copy(), env.posicion_pie(1)[:2].copy()]

    def desplazamiento(self, env):
        return max(float(np.linalg.norm(env.posicion_pie(i)[:2] - self.pies_inicio[i])) for i in (0, 1))

    def exito(self, env, truncado):
        limite = self.t.get("pies_fijos_m")
        return truncado and (not limite or self.desplazamiento(env) < limite)

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - env.altura_pie) / 0.05) ** 2))
        d["postura"] = self.p["postura"] * np.exp(-np.sum((env.angulos() - env.postura_inicial) ** 2))
        d["quieto"] = self.p["quieto"] * np.exp(-np.sum(env.data.qvel[:3] ** 2) - 0.5 * np.sum(env.data.qvel[3:6] ** 2))
        if self.t.get("pies_fijos_m"):
            d["pies"] = self.p["pies"] * np.exp(-((self.desplazamiento(env) / self.t["pies_fijos_m"]) ** 2))
        return d


class Sentadilla(Tarea):
    """Sigue una altura ordenada que sube y baja de forma continua."""
    titulo_exito = "Siguió la altura ordenada"

    def iniciar(self, env):
        super().iniciar(env)
        self.errores = []

    def actualizar(self, env):
        fase = 2 * np.pi * env.pasos * env.dt / self.t["periodo_s"]
        env.comando[2] = 1.0 - (1.0 - self.t["altura_baja"]) * (1 - np.cos(fase)) / 2

    def error(self, env):
        return abs(env.altura_torso() - env.comando[2] * env.altura_pie)

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        e = self.error(env)
        d["altura"] = self.p["altura"] * (0.7 * np.exp(-((e / 0.03) ** 2)) + 0.3 * np.exp(-((e / 0.15) ** 2)))
        d["quieto"] = self.p["quieto"] * np.exp(-np.sum(env.data.qvel[:2] ** 2))
        self.errores.append(e)
        return d

    def exito(self, env, truncado):
        return truncado and float(np.mean(self.errores)) < self.t["error_m"]

    def resumen(self, env):
        return f"error medio {np.mean(self.errores) * 100:.1f} cm" if self.errores else ""

    def orden(self, env):
        return f"altura {env.comando[2] * 100:.0f} %"


class PasarPeso(Tarea):
    """Lleva el centro de masa sobre el pie ordenado, alternando."""
    titulo_exito = "Pasó el peso de un pie a otro"

    def iniciar(self, env):
        super().iniciar(env)
        env.comando[3] = 1.0
        self.aciertos = []

    def actualizar(self, env):
        periodo = int(self.t["cambio_s"] / env.dt)
        if env.pasos % periodo == 0:
            env.comando[3] = 1.0 if (env.pasos // periodo) % 2 == 0 else -1.0

    def distancia(self, env):
        pie = env.posicion_pie(0 if env.comando[3] > 0 else 1)
        return abs(env.centro_masa()[1] - pie[1])

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        dist = self.distancia(env)
        d["peso"] = self.p["peso"] * np.exp(-((dist / 0.05) ** 2))
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - env.altura_pie) / 0.06) ** 2))
        if env.pasos % int(self.t["cambio_s"] / env.dt) > 40:
            self.aciertos.append(dist < self.t["distancia_m"])
        return d

    def exito(self, env, truncado):
        return truncado and float(np.mean(self.aciertos)) > self.t["tasa_acierto"]

    def resumen(self, env):
        return f"sobre el pie ordenado {np.mean(self.aciertos) * 100:.0f} % del tiempo" if self.aciertos else ""

    def orden(self, env):
        return f"peso sobre el pie {'izquierdo' if env.comando[3] > 0 else 'derecho'}"


class UnPie(Tarea):
    """Levanta el pie ordenado y se sostiene sobre el otro."""
    titulo_exito = "Se sostuvo sobre un pie"

    def iniciar(self, env):
        super().iniciar(env)
        env.comando[3] = 1.0 if env.np_random.random() < 0.5 else -1.0
        self.racha = self.mejor = 0

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        apoyo = 0 if env.comando[3] > 0 else 1   # pie que debe quedar en el piso
        contactos = env.contactos()
        alto = env.posicion_pie(1 - apoyo)[2]
        d["levantar"] = self.p["levantar"] * min(1.0, alto / 0.08)
        d["apoyo"] = self.p["apoyo"] * float(contactos[apoyo])
        d["peso"] = self.p["peso"] * np.exp(-((abs(env.centro_masa()[1] - env.posicion_pie(apoyo)[1]) / 0.05) ** 2))
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - env.altura_pie) / 0.08) ** 2))
        self.racha = self.racha + 1 if contactos[apoyo] and not contactos[1 - apoyo] else 0
        self.mejor = max(self.mejor, self.racha)
        return d

    def exito(self, env, truncado):
        return truncado and self.mejor * env.dt >= self.t["segundos"]

    def resumen(self, env):
        return f"mejor racha en un pie {self.mejor * env.dt:.1f} s"

    def orden(self, env):
        return f"levantar el pie {'derecho' if env.comando[3] > 0 else 'izquierdo'}"


class Marcha(Tarea):
    """Sigue una velocidad y un rumbo ordenados, con un reloj que alterna las piernas."""
    titulo_exito = "Caminó hasta la meta"
    usa_reloj = True

    def _sortear(self, env):
        vx, vy = self.t.get("vx", [0.5, 0.5]), self.t.get("vy", [0.0, 0.0])
        env.comando[0] = env.np_random.uniform(*vx)
        env.comando[1] = env.np_random.uniform(*vy)
        env.comando[3] = env.np_random.uniform(*self.t.get("giro", [0.0, 0.0]))
        cero = self.t.get("prob_detenerse", 0.0)
        if cero and env.np_random.random() < cero:
            env.comando[:2] = 0.0

    def iniciar(self, env):
        super().iniciar(env)
        self._sortear(env)
        self.errores = []
        self.errores_rumbo = []
        self.pasos_vistos = 0

    def avance(self, env):
        """Progreso de 0 a 1 hacia la meta, para comparar intentos fallidos."""
        meta = self.t.get("distancia_m")
        return min(1.0, max(env.recorrido(), 0.0) / meta) if meta else min(1.0, env.pasos / env.max_pasos)

    def actualizar(self, env):
        cada = self.t.get("cambia_cada_s")
        if cada and env.pasos and env.pasos % int(cada / env.dt) == 0:
            self._sortear(env)
        env.rumbo_objetivo += env.comando[3] * env.dt

    def _velocidad_objetivo(self, env):
        c, s = np.cos(env.rumbo_objetivo), np.sin(env.rumbo_objetivo)
        return np.array([c * env.comando[0] - s * env.comando[1], s * env.comando[0] + c * env.comando[1]])

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        error = float(np.sum((env.data.qvel[:2] - self._velocidad_objetivo(env)) ** 2))
        error_rumbo = env.error_rumbo()
        d["velocidad"] = self.p["velocidad"] * np.exp(-error / self.t.get("sigma_v", 0.1))
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - 0.97 * env.altura_pie) / 0.08) ** 2))
        d["erguido"] = self.p["erguido"] * env.arriba_del_torso()[2] ** 4
        d["rumbo"] = self.p["rumbo"] * np.exp(-((error_rumbo / 0.3) ** 2))
        # Reloj: en cada media fase debe apoyar una pierna y levantar la otra.
        izq, der, _ = env.contactos()
        fase = np.sin(env.fase())
        apoyo_i, apoyo_d = fase >= 0, fase < 0
        if np.linalg.norm(env.comando[:2]) < 0.05 and abs(env.comando[3]) < 0.05:
            d["reloj"] = self.p["reloj"] * float(izq and der)
        else:
            d["reloj"] = self.p["reloj"] * 0.5 * (float(izq == apoyo_i) + float(der == apoyo_d))
            alto = env.posicion_pie(1 if apoyo_i else 0)[2]
            d["paso"] = self.p["paso"] * min(1.0, alto / self.t.get("despeje_m", 0.06))
        d["giro"] = -self.p["giro"] * float(np.sum((env.data.qvel[3:5]) ** 2))
        if self.p.get("guinada"):  # sigue la velocidad de giro ordenada
            d["guinada"] = self.p["guinada"] * np.exp(-(((env.data.qvel[5] - env.comando[3]) / 0.3) ** 2))
        self._estetica(env, d, izq, der)
        self.errores.append(np.sqrt(error))
        self.errores_rumbo.append(abs(error_rumbo))
        return d

    def _estetica(self, env, d, izq, der):
        """Términos de «caminar bien»: zancada humana, articulaciones sin vibrar, pie de apoyo firme."""
        p = self.p
        if p.get("zancada"):
            n = len(env.est["pasos"])
            if n > getattr(self, "pasos_vistos", 0):
                largo = env.est["pasos"][-1]
                d["zancada"] = p["zancada"] * np.exp(-(((largo - self.t.get("zancada_m", 0.3)) / 0.2) ** 2))
                if p.get("vuelo"):  # pie en el aire ~0,45 s por paso: ritmo humano, no temblor
                    d["vuelo"] = p["vuelo"] * np.exp(-(((env.est["ultimo_vuelo"] - 0.45) / 0.15) ** 2))
            self.pasos_vistos = n
        if self.t.get("erguido_estricto"):
            # Mezcla estricta y suave: lejos de vertical la recompensa todavía orienta.
            i = env.inclinacion_grados()
            d["erguido"] = p["erguido"] * (0.6 * np.exp(-((i / 10) ** 2)) + 0.4 * np.exp(-((i / 30) ** 2)))
        if p.get("vel_articular"):
            d["vel_articular"] = -p["vel_articular"] * float(np.mean((env.data.qvel[env.adr_v] * 0.1) ** 2))
        if p.get("deslizamiento"):
            v = env.vel_pies
            d["deslizamiento"] = -p["deslizamiento"] * float(v[0] * izq + v[1] * der)

    def calidad_ok(self, env):
        minimo = self.t.get("calidad_min")
        return not minimo or env.estadisticas()["calidad"] >= minimo

    def exito(self, env, truncado):
        if not truncado or not self.calidad_ok(env):
            return False
        if "error_ms" in self.t and float(np.mean(self.errores[50:])) >= self.t["error_ms"]:
            return False
        if "error_rumbo" in self.t and float(np.mean(self.errores_rumbo[50:])) >= self.t["error_rumbo"]:
            return False
        if "energia_j" in self.t and env.energia > self.t["energia_j"][env.planeta]:
            return False
        return env.recorrido() >= self.t.get("distancia_m", 0.0)

    def resumen(self, env):
        return f"recorrió {env.recorrido():.1f} m · error de velocidad {np.mean(self.errores):.2f} m/s"

    def orden(self, env):
        partes = []
        if np.linalg.norm(env.comando[:2]) > 0.01:
            partes.append(f"ir a {np.linalg.norm(env.comando[:2]):.2f} m/s")
        if abs(env.comando[3]) > 0.01:
            partes.append(f"girar {np.degrees(env.comando[3]):.0f}°/s")
        return " · ".join(partes) or "detenerse"


class Girar(Marcha):
    """Gira un ángulo ordenado sin desplazarse."""
    titulo_exito = "Giró en el sitio"

    def iniciar(self, env):
        super().iniciar(env)
        self.signo = 1.0 if env.np_random.random() < 0.5 else -1.0
        self.total = 0.0

    def actualizar(self, env):
        paso = min(self.t["rad_s"] * env.dt, abs(self.t["angulo_rad"]) - self.total)
        self.total += max(0.0, paso)
        env.comando[3] = self.signo * self.t["rad_s"] if self.total < abs(self.t["angulo_rad"]) else 0.0
        env.rumbo_objetivo = self.signo * self.total

    def exito(self, env, truncado):
        return truncado and abs(env.error_rumbo()) < np.radians(10)

    def resumen(self, env):
        return f"error final de rumbo {np.degrees(abs(env.error_rumbo())):.0f}°"


class IrAPunto(Marcha):
    """Llega a un destino. El rumbo y la velocidad se derivan de su posición, sin navegación aprendida."""
    titulo_exito = "Llegó al destino"

    def iniciar(self, env):
        super().iniciar(env)
        ang = env.np_random.uniform(-1.2, 1.2)
        d = self.t["distancia_destino_m"]
        env.destino = np.array([d * np.cos(ang), d * np.sin(ang)])

    def actualizar(self, env):
        hacia = env.destino - env.data.qpos[:2]
        lejos = np.linalg.norm(hacia)
        deseado = np.arctan2(hacia[1], hacia[0])
        env.rumbo_objetivo = deseado if lejos > 0.3 else env.rumbo_objetivo
        env.comando[0] = 0.5 if lejos > 0.3 else 0.0
        env.comando[3] = 0.0

    def exito(self, env, truncado):
        return truncado and np.linalg.norm(env.destino - env.data.qpos[:2]) < self.t["radio_m"]

    def resumen(self, env):
        return f"terminó a {np.linalg.norm(env.destino - env.data.qpos[:2]):.2f} m del destino"


class Salto(Tarea):
    """Despega ambos pies y aterriza de pie."""
    titulo_exito = "Saltó y aterrizó de pie"

    def iniciar(self, env):
        super().iniciar(env)
        self.aire = self.mejor = 0

    def fin(self, env):
        a = env.exp["ambiente"]
        if env.toca_piso_con_cuerpo():
            return "tocó el piso con el cuerpo"
        if env.inclinacion_grados() > a["inclinacion_maxima"]:
            return "se inclinó demasiado"
        return None

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        izq, der, _ = env.contactos()
        self.aire = self.aire + 1 if not (izq or der) else 0
        self.mejor = max(self.mejor, self.aire)
        alto = max(0.0, min(env.posicion_pie(0)[2], env.posicion_pie(1)[2]) - 0.04)
        d["salto"] = self.p["salto"] * min(1.0, alto / 0.1)
        d["impulso"] = self.p["impulso"] * max(0.0, float(env.data.qvel[2]))
        d["erguido"] = self.p["erguido"] * env.arriba_del_torso()[2] ** 4
        return d

    def exito(self, env, truncado):
        return truncado and self.mejor * env.dt >= self.t["aire_s"] and env.altura_torso() > 0.8 * env.altura_pie

    def resumen(self, env):
        return f"{self.mejor * env.dt:.2f} s en el aire"

    def orden(self, env):
        return "saltar"


class Levantarse(Tarea):
    """Empieza acostado y debe llegar a la postura de pie."""
    titulo_exito = "Se levantó"

    def iniciar(self, env):
        super().iniciar(env)
        self.mejor = 0
        env.data.qpos[2] = 0.2
        env.data.qpos[3:7] = [0.7071, 0.0, 0.7071, 0.0]  # boca abajo
        env.data.qvel[:] = 0.0
        import mujoco
        mujoco.mj_forward(env.model, env.data)

    def fin(self, env):
        return None

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        d["altura"] = self.p["altura"] * min(1.0, env.altura_torso() / env.altura_pie) ** 2
        d["erguido"] = self.p["erguido"] * (env.arriba_del_torso()[2] + 1) / 2
        arriba = env.altura_torso() > 0.9 * env.altura_pie and env.inclinacion_grados() < 25
        self.mejor = self.mejor + 1 if arriba else 0
        return d

    def exito(self, env, truncado):
        return truncado and self.mejor * env.dt >= self.t["segundos"]


class Esquina(Marcha):
    """Camina recto, se detiene, gira 90° sobre su eje y vuelve a caminar recto."""
    titulo_exito = "Dobló la esquina"

    def iniciar(self, env):
        super().iniciar(env)
        self.fase_esquina = 0
        self.lado = 1.0 if self.t.get("lado", "izquierda") == "izquierda" else -1.0
        self.L, self.w = self.t["lado_m"], self.t["giro_rad_s"]
        v = self.t.get("variar_entrenando")
        if v and env.entrenando:
            # Practica más giros: esquinas a ambos lados, tramos cortos y giros más lentos.
            self.lado = env.np_random.choice([-1.0, 1.0])
            self.L = float(env.np_random.uniform(v["lado_m"][0], v["lado_m"][1]))
            self.w = float(env.np_random.uniform(v["giro_rad_s"][0], v["giro_rad_s"][1]))
        env.comando[:] = [self.t["velocidad_ms"], 0.0, 1.0, 0.0]
        self.origen = np.array([env.x_inicial, env.y_inicial])
        self.esquina = None

    def actualizar(self, env):
        L, vx, w = self.L, self.t["velocidad_ms"], self.w
        pos = env.data.qpos[:2]
        if self.fase_esquina == 0 and pos[0] - self.origen[0] >= L:
            self.fase_esquina, self.esquina = 1, pos.copy()
            env.comando[0], env.comando[3] = 0.0, self.lado * w
        if self.fase_esquina == 1:
            objetivo = self.lado * np.pi / 2
            env.rumbo_objetivo += env.comando[3] * env.dt
            if abs(env.rumbo_objetivo) >= abs(objetivo):
                env.rumbo_objetivo, env.comando[3] = objetivo, 0.0
                if abs(env.error_rumbo()) < 0.2:
                    self.fase_esquina = 2
                    env.comando[0] = vx

    def tramo2(self, env):
        if self.esquina is None:
            return 0.0
        return float(self.lado * (env.data.qpos[1] - self.esquina[1]))

    def avance(self, env):
        L = self.L
        t1 = min(1.0, max(0.0, env.data.qpos[0] - self.origen[0]) / L)
        giro = min(1.0, abs(env.rumbo()) / (np.pi / 2)) if self.fase_esquina >= 1 else 0.0
        t2 = min(1.0, max(0.0, self.tramo2(env)) / L)
        return (t1 + giro + t2) / 3

    def exito(self, env, truncado):
        return (truncado and self.calidad_ok(env) and self.fase_esquina == 2
                and self.tramo2(env) >= self.L and abs(env.error_rumbo()) < 0.35)

    def resumen(self, env):
        return (f"tramo 1 {min(env.data.qpos[0] - self.origen[0], 99):.1f} m · giró {np.degrees(abs(env.rumbo())):.0f}° · "
                f"tramo 2 {self.tramo2(env):.1f} m")

    def orden(self, env):
        return ["caminar recto", "girar 90° sobre su eje", "caminar recto otra vez"][self.fase_esquina]


class Curva(Marcha):
    """Camina en círculo: velocidad constante y giro constante."""
    titulo_exito = "Completó el círculo"

    def iniciar(self, env):
        super().iniciar(env)
        R, vx = self.t["radio_m"], self.t["velocidad_ms"]
        self.signo = 1.0
        v = self.t.get("variar_entrenando")
        if v and env.entrenando:
            # Curvas a ambos lados y de radio variable, de amplias a cerradas.
            self.signo = env.np_random.choice([-1.0, 1.0])
            R = float(env.np_random.uniform(v["radio_m"][0], v["radio_m"][1]))
        self.R = R
        env.comando[:] = [vx, 0.0, 1.0, self.signo * vx / R]
        self.centro = np.array([env.x_inicial, env.y_inicial + self.signo * R])
        self.angulo = 0.0
        self.previo = None
        self.radios = []

    def actualizar(self, env):
        env.rumbo_objetivo += env.comando[3] * env.dt
        rel = env.data.qpos[:2] - self.centro
        a = float(np.arctan2(rel[1], rel[0]))
        if self.previo is not None:
            self.angulo += self.signo * float(np.arctan2(np.sin(a - self.previo), np.cos(a - self.previo)))
        self.previo = a
        self.radios.append(float(np.linalg.norm(rel)))

    def error_radio(self):
        return float(np.mean(np.abs(np.array(self.radios) - self.R))) if self.radios else 9.9

    def avance(self, env):
        return min(1.0, max(0.0, self.angulo) / (2 * np.pi * self.t["vueltas"]))

    def exito(self, env, truncado):
        return (truncado and self.calidad_ok(env) and self.angulo >= 2 * np.pi * self.t["vueltas"]
                and self.error_radio() < self.t["error_radio_m"])

    def resumen(self, env):
        return f"recorrió {np.degrees(max(self.angulo, 0)):.0f}° del círculo · se desvió {self.error_radio():.2f} m del radio"

    def orden(self, env):
        return f"caminar en círculo de {self.t['radio_m']} m de radio"


class Recorrido(Marcha):
    """Encadena tramos rectos, giros sobre su eje y curvas, en orden aleatorio."""
    titulo_exito = "Completó el recorrido"
    MODOS = {"recto": (0.5, 0.0), "giro": (0.0, 0.8), "curva": (0.45, 0.25)}

    def iniciar(self, env):
        super().iniciar(env)
        self.cola = []
        self.modo, self.hasta = None, 0
        self._siguiente(env)

    def _siguiente(self, env):
        if not self.cola:
            self.cola = list(env.np_random.permutation(["recto", "giro", "curva", "recto"]))
        self.modo = str(self.cola.pop(0))
        vx, w = self.MODOS[self.modo]
        signo = env.np_random.choice([-1.0, 1.0])
        env.comando[:] = [vx, 0.0, 1.0, signo * w]
        duracion = (np.pi / 2) / w if self.modo == "giro" else self.t["tramo_s"]
        self.hasta = env.pasos + int(duracion / env.dt)

    def actualizar(self, env):
        if env.pasos >= self.hasta:
            self._siguiente(env)
        env.rumbo_objetivo += env.comando[3] * env.dt

    def orden(self, env):
        nombres = {"recto": "caminar recto", "giro": "girar sobre su eje", "curva": "caminar en curva"}
        return nombres[self.modo]


TAREAS = {"de_pie": DePie, "sentadilla": Sentadilla, "pasar_peso": PasarPeso, "un_pie": UnPie,
          "marcha": Marcha, "levantarse": Levantarse, "girar": Girar, "ir_a_punto": IrAPunto, "salto": Salto,
          "esquina": Esquina, "curva": Curva, "recorrido": Recorrido}
