import numpy as np
from gymnasium.utils.env_checker import check_env

from expedicion import experimentos as X
from expedicion.ambiente import GRAVEDADES, BipedoEnv
from expedicion.evaluar import Aleatorio, SinEntrenar, correr_episodio, generar_escenarios


def exp():
    return X.cargar("exp-101")


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
    env.step(np.zeros(12))
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
    _, r, term, trunc, info = env.step(np.zeros(12))
    assert term and not trunc and r < 0 and "caida" in info["desglose"]


def test_agacharse_no_cuenta_como_estar_de_pie():
    env = BipedoEnv(exp())
    env.reset(seed=0, options={"planeta": "luna"})
    env.data.qpos[2] = env.altura_pie * 0.8
    assert env.step(np.zeros(12))[2]


def test_trunca_a_los_diez_segundos():
    env = BipedoEnv(exp())
    assert env.max_pasos == 500
    env.reset(seed=0, options={"planeta": "luna"})
    env.pasos = env.max_pasos - 1
    env.step(np.zeros(12))
    assert env.pasos == env.max_pasos


def test_el_empujon_mueve_el_torso():
    env = BipedoEnv(exp())
    env.reset(seed=3, options={"planeta": "tierra", "perturbacion": "empujon"})
    env.pasos = env.paso_empujon
    env.step(np.zeros(12))
    assert env.empujado and np.linalg.norm(env.data.qvel[:2]) > 0.2


def test_los_escenarios_son_reproducibles():
    assert generar_escenarios(exp()) == generar_escenarios(exp())


def test_episodio_grabado_entrega_cuadros():
    esc = {"planeta": "marte", "perturbacion": "ninguna", "semilla": 0}
    resumen, cuadros = correr_episodio(exp(), Aleatorio(0), esc, grabar=True)
    assert len(cuadros) > 1 and len(cuadros[0]["cuerpos"]) == 7
    assert cuadros[-1]["t"] == resumen["segundos"]


def test_hielo_baja_la_friccion_del_pie_sobre_el_tramo():
    e = {**exp(), "pisos": {"tramos": [{"tipo": "hielo", "largo": 5}], "inicio_m": -1.0}}
    env = BipedoEnv(e)
    env.reset(seed=0, options={"planeta": "tierra"})
    env.step(np.zeros(12))
    assert env.model.geom_friction[env.ids_pies[0], 0] <= 0.2
    assert env.piso_bajo_torso() == "hielo"


def test_barro_frena_al_pie_que_se_mueve():
    e = {**exp(), "pisos": {"tramos": [{"tipo": "barro", "largo": 5}], "inicio_m": -1.0}}
    env = BipedoEnv(e)
    env.reset(seed=0, options={"planeta": "tierra"})
    env.pie_previo[0] = env.posicion_pie(0) - np.array([0.01, 0, 0])
    env._aplicar_piso()
    assert env.data.xfrc_applied[env.ids_cuerpo_pies[0], 0] < 0


def test_cinco_etapas_del_fracaso_al_dominio():
    from expedicion.evolucion import ETAPAS, _elegir
    filas = [{"exito": e, "puntaje": p} for e, p in
             [(0, .05), (0, .02), (0, .2), (0, .4), (0, .7), (0, .9), (1, 1.03), (1, 1.05), (1, 1.07)]]
    etapas = _elegir(filas)
    assert [e["etapa"] for e in etapas] == ETAPAS
    assert [e["indice"] for e in etapas] == [1, 3, 5, 6, 8]


def test_el_linaje_recorre_los_antecesores_desde_la_raiz():
    from expedicion.evolucion import linaje
    assert [e["id"] for e in linaje(X.cargar("exp-105"))] == ["exp-101", "exp-102", "exp-103", "exp-104"]


def test_balizas_contrato_y_exito_sin_castigo():
    """Exp 8: balizas en el rango pedido, el rumbo pedido apunta a la activa y llegar a todas es éxito sin caída."""
    exp = X.cargar("exp-108")
    env = BipedoEnv(exp)
    for s in range(5):
        env.reset(seed=s)
        assert env.planeta == "marte"
        t = env.tarea
        previo = np.zeros(2)
        for b in t.balizas:
            assert exp["parametros"]["distancia_m"][0] - 1e-9 <= np.linalg.norm(b - previo) <= exp["parametros"]["distancia_m"][1] + 1e-9
            previo = b
    sin_calidad = {**exp, "parametros": {**exp["parametros"], "calidad_min": None}}  # la calidad no se mide en un paso
    env = BipedoEnv(sin_calidad)
    env.reset(seed=0)
    env.step(np.zeros(env.action_space.shape))
    e, _ = env.tarea._error(env)
    assert abs(e) <= np.pi
    # Simula la llegada: con todas las balizas alcanzadas el episodio termina con éxito y sin el castigo por caída.
    env.tarea.alcanzadas = len(env.tarea.balizas) - 1
    env.destino = env.data.qpos[:2].copy()
    env.tarea.balizas[-1] = env.destino
    _, r, term, trunc, info = env.step(np.zeros(env.action_space.shape))
    assert term and env.motivo == "llegó a todas las balizas"
    assert info["exito"] and "caida" not in info["desglose"]
def test_la_esquina_pasa_a_girar_al_llegar():
    e = X.cargar("exp-105")
    env = BipedoEnv(e)
    env.reset(seed=0)
    env.data.qpos[0] = env.x_inicial + e["parametros"]["lado_m"] + 0.1
    env.step(np.zeros(12))
    assert env.tarea.fase_esquina == 1 and env.comando[0] == 0 and env.comando[3] > 0
