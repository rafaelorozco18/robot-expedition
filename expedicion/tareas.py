"""Tareas: qué premia cada experimento y cuándo termina el episodio."""

import numpy as np


class DePie:
    """Exp 1: conservar la postura de pie."""

    def recompensa(self, env, accion, accion_previa):
        p = env.exp["recompensa"]
        altura = np.exp(-(((env.altura_torso() - env.altura_pie) / 0.05) ** 2))
        postura = np.exp(-np.sum((env.angulos() - env.postura_inicial) ** 2))
        quieto = np.exp(-np.sum(env.data.qvel[:3] ** 2) - 0.5 * np.sum(env.data.qvel[3:6] ** 2))
        desglose = {
            "vivo": p["vivo"],
            "altura": p["altura"] * altura,
            "postura": p["postura"] * postura,
            "quieto": p["quieto"] * quieto,
            "esfuerzo": -p["esfuerzo"] * float(np.mean(env.data.ctrl ** 2)),
            "suavidad": -p["suavidad"] * float(np.mean((accion - accion_previa) ** 2)),
        }
        return desglose

    def fin(self, env):
        """Devuelve el motivo de caída o None. El truncamiento lo decide el ambiente."""
        a = env.exp["ambiente"]
        if env.toca_piso_con_cuerpo():
            return "tocó el piso con el cuerpo"
        if env.altura_torso() < a["altura_minima"] * env.altura_pie:
            return "se agachó o cayó"
        if env.inclinacion_grados() > a["inclinacion_maxima"]:
            return "se inclinó demasiado"
        return None


TAREAS = {"de_pie": DePie}
