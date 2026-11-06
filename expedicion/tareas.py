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


class DePie(Tarea):
    def iniciar(self, env):
        super().iniciar(env)
        self.pies_inicio = [env.posicion_pie(0)[:2].copy(), env.posicion_pie(1)[:2].copy()]

    def exito(self, env, truncado):
        limite = self.t.get("pies_fijos_m")
        if truncado and limite:
            return max(float(np.linalg.norm(env.posicion_pie(i)[:2] - self.pies_inicio[i])) for i in (0, 1)) < limite
        return truncado

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - env.altura_pie) / 0.05) ** 2))
        d["postura"] = self.p["postura"] * np.exp(-np.sum((env.angulos() - env.postura_inicial) ** 2))
        d["quieto"] = self.p["quieto"] * np.exp(-np.sum(env.data.qvel[:3] ** 2) - 0.5 * np.sum(env.data.qvel[3:6] ** 2))
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


class Marcha(Tarea):
    """Sigue una velocidad ordenada con un reloj que alterna las piernas."""
    titulo_exito = "Caminó hasta la meta"
    usa_reloj = True

    def _sortear(self, env):
        vx, vy = self.t.get("vx", [0.5, 0.5]), self.t.get("vy", [0.0, 0.0])
        env.comando[0] = env.np_random.uniform(*vx)
        env.comando[1] = env.np_random.uniform(*vy)
        cero = self.t.get("prob_detenerse", 0.0)
        if cero and env.np_random.random() < cero:
            env.comando[:2] = 0.0

    def iniciar(self, env):
        super().iniciar(env)
        self._sortear(env)
        self.errores = []

    def actualizar(self, env):
        cada = self.t.get("cambia_cada_s")
        if cada and env.pasos and env.pasos % int(cada / env.dt) == 0:
            self._sortear(env)

    def recompensa(self, env, accion, previa):
        d = self.comunes(env, accion, previa)
        v = env.data.qvel[:2]
        error = float(np.sum((v - env.comando[:2]) ** 2))
        d["velocidad"] = self.p["velocidad"] * np.exp(-error / 0.1)
        d["altura"] = self.p["altura"] * np.exp(-(((env.altura_torso() - 0.97 * env.altura_pie) / 0.08) ** 2))
        d["erguido"] = self.p["erguido"] * env.arriba_del_torso()[2] ** 4
        d["rumbo"] = self.p["rumbo"] * env.mundo_x_en_torso()[0] ** 2
        # Reloj: en cada media fase debe apoyar una pierna y levantar la otra.
        izq, der, _ = env.contactos()
        fase = np.sin(env.fase())
        apoyo_i, apoyo_d = fase >= 0, fase < 0
        if np.linalg.norm(env.comando[:2]) < 0.05:
            d["reloj"] = self.p["reloj"] * float(izq and der)
        else:
            d["reloj"] = self.p["reloj"] * 0.5 * (float(izq == apoyo_i) + float(der == apoyo_d))
            alto = env.posicion_pie(1 if apoyo_i else 0)[2]
            d["paso"] = self.p["paso"] * min(1.0, alto / 0.06)
        d["giro"] = -self.p["giro"] * float(np.sum(env.data.qvel[3:6] ** 2))
        self.errores.append(np.sqrt(error))
        return d

    def exito(self, env, truncado):
        if not truncado:
            return False
        if "error_ms" in self.t:
            return float(np.mean(self.errores[50:])) < self.t["error_ms"]
        if "energia_j" in self.t:
            return env.recorrido() >= self.t["distancia_m"] and env.energia <= self.t["energia_j"]
        return env.recorrido() >= self.t["distancia_m"]

    def resumen(self, env):
        return f"recorrió {env.recorrido():.1f} m · error de velocidad {np.mean(self.errores):.2f} m/s"


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
          "marcha": Marcha, "levantarse": Levantarse}
