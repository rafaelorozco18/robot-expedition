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
    """Sigue una altura ordenada que cambia durante el episodio."""
    titulo_exito = "Siguió la altura ordenada"

    def iniciar(self, env):
        super().iniciar(env)
        self.errores = []

    def actualizar(self, env):
        periodo = int(self.t["cambio_s"] / env.dt)
        if env.pasos % periodo == 0:
            arriba = (env.pasos // periodo) % 2 == 0
            env.comando[2] = 1.0 if arriba else self.t["altura_baja"]

    def error(self, env):
        return abs(env.altura_torso() - env.comando[2] * env.altura_pie)

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        d["altura"] = self.p["altura"] * np.exp(-((self.error(env) / 0.04) ** 2))
        d["quieto"] = self.p["quieto"] * np.exp(-np.sum(env.data.qvel[:2] ** 2))
        if env.pasos % int(self.t["cambio_s"] / env.dt) > 50:  # 1 s para llegar
            self.errores.append(self.error(env))
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
        d["velocidad"] = self.p["velocidad"] * np.exp(-error / 0.1)
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
            d["paso"] = self.p["paso"] * min(1.0, alto / 0.06)
        d["giro"] = -self.p["giro"] * float(np.sum((env.data.qvel[3:5]) ** 2))
        self.errores.append(np.sqrt(error))
        self.errores_rumbo.append(abs(error_rumbo))
        return d

    def exito(self, env, truncado):
        if not truncado:
            return False
        if "error_ms" in self.t and float(np.mean(self.errores[50:])) >= self.t["error_ms"]:
            return False
        if "error_rumbo" in self.t and float(np.mean(self.errores_rumbo[50:])) >= self.t["error_rumbo"]:
            return False
        if "energia_j" in self.t and env.energia > self.t["energia_j"]:
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


class Levantarse(Tarea):
    """Empieza acostado y debe llegar a la postura de pie."""
    titulo_exito = "Se levantó"

    def iniciar(self, env):
        super().iniciar(env)
        self.mejor = 0

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


TAREAS = {"de_pie": DePie, "sentadilla": Sentadilla, "pasar_peso": PasarPeso, "un_pie": UnPie,
          "marcha": Marcha, "levantarse": Levantarse, "girar": Girar, "ir_a_punto": IrAPunto}
