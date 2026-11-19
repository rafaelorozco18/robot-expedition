"""Exp 9: mundo con solución, sensores válidos y rocas sólidas en MuJoCo."""
import mujoco
import numpy as np

from expedicion import experimentos as X
from expedicion import mundo as M
from expedicion.ambiente import BipedoEnv


def test_mundos_con_solucion_y_sensores_validos():
    t = X.cargar("exp-109")["parametros"]
    for s in range(15):
        w = M.generar(np.random.default_rng(s), t)
        assert len(w["balizas"]) == t["balizas"]
        assert M.hay_camino(w["rocas"], [np.zeros(2), *w["balizas"]], w["lado"])
        assert all(r in M.RADIOS_ROCA for _, _, r in w["rocas"])
        obs = M.observacion(np.zeros(2), 0.0, w["balizas"][0], w["rocas"], w["lado"], 3)
        assert obs.shape == (M.N_OBS,) and np.all(obs >= -1) and np.all(obs <= 1)


def test_una_roca_delante_es_solida():
    """Con una roca pegada a las piernas, MuJoCo registra el choque (antes los geoms fijos movidos se atravesaban)."""
    exp = X.cargar("exp-109")
    exp = {**exp, "navegador": {**exp["navegador"], "modelo": "regla:directo"}}
    env = BipedoEnv(exp)
    env.reset(seed=0)
    hueco = env.huecos_roca[M.RADIOS_ROCA[0]][0]
    env.data.mocap_pos[hueco] = [0.2, 0.0, exp["parametros"]["alto_roca_m"] / 2]
    mujoco.mj_forward(env.model, env.data)
    assert env.choca_con_roca()
    assert env.tarea.fin(env) == "chocó con una roca"
