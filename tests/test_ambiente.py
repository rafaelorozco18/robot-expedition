import numpy as np
from gymnasium.utils.env_checker import check_env

from expedicion import experimentos as X
from expedicion.ambiente import GRAVEDADES, BipedoEnv
from expedicion.evaluar import Aleatorio, SinEntrenar, correr_episodio, generar_escenarios


def exp():
    return X.cargar("exp-001")


def test_cumple_api_gymnasium():
    check_env(BipedoEnv(exp()), skip_render_check=True)


def test_cada_planeta_aplica_su_gravedad():
    env = BipedoEnv(exp())
    for nombre, g in GRAVEDADES.items():
        obs, _ = env.reset(seed=0, options={"planeta": nombre})
        assert env.model.opt.gravity[2] == -g
        assert np.isclose(obs[-7], g / 9.81)


def test_empieza_de_pie_con_los_pies_en_el_piso():
    env = BipedoEnv(exp())
    env.reset(seed=0, options={"planeta": "tierra"})
    assert abs(env.altura_torso() / env.altura_pie - 1) < 0.01
    assert env.inclinacion_grados() < 5
    env.step(np.zeros(10))
    assert any(env.contactos()[:2])
    assert not env.toca_piso_con_cuerpo()


def test_sin_red_se_cae_antes_en_la_tierra_que_en_la_luna():
    esc = {"perturbacion": "ninguna", "semilla": 1}
    tierra = correr_episodio(exp(), SinEntrenar(), {**esc, "planeta": "tierra"})[0]
    luna = correr_episodio(exp(), SinEntrenar(), {**esc, "planeta": "luna"})[0]
    assert not tierra["exito"]
    assert tierra["segundos"] < luna["segundos"]


def test_caer_castiga_y_termina():
    env = BipedoEnv(exp())
    env.reset(seed=0, options={"planeta": "tierra"})
    env.data.qpos[2] = 0.3                # torso muy por debajo de la altura mínima
    _, r, term, trunc, info = env.step(np.zeros(10))
    assert term and not trunc and r < 0 and "caida" in info["desglose"]


def test_agacharse_no_cuenta_como_estar_de_pie():
    env = BipedoEnv(exp())
    env.reset(seed=0, options={"planeta": "luna"})
    env.data.qpos[2] = env.altura_pie * 0.8
    assert env.step(np.zeros(10))[2]


def test_trunca_a_los_diez_segundos():
    env = BipedoEnv(exp())
    assert env.max_pasos == 500
    env.reset(seed=0, options={"planeta": "luna"})
    env.pasos = env.max_pasos - 1
    env.step(np.zeros(10))
    assert env.pasos == env.max_pasos


def test_el_empujon_mueve_el_torso():
    env = BipedoEnv(exp())
    env.reset(seed=3, options={"planeta": "tierra", "perturbacion": "empujon"})
    env.pasos = env.paso_empujon
    env.step(np.zeros(10))
    assert env.empujado and np.linalg.norm(env.data.qvel[:2]) > 0.2


def test_los_escenarios_son_reproducibles():
    assert generar_escenarios(exp()) == generar_escenarios(exp())


def test_episodio_grabado_entrega_cuadros():
    esc = {"planeta": "marte", "perturbacion": "ninguna", "semilla": 0}
    resumen, cuadros = correr_episodio(exp(), Aleatorio(0), esc, grabar=True)
    assert len(cuadros) > 1 and len(cuadros[0]["cuerpos"]) == 7
    assert cuadros[-1]["t"] == resumen["segundos"]
