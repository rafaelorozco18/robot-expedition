import gymnasium as gym
import numpy as np
from gymnasium.utils.env_checker import check_env

import expedicion  # noqa: F401  (registra RobotExpedition-v0)
from expedicion import config as C
from expedicion.ambiente import ExpedicionEnv


def nuevo(**opciones):
    env = ExpedicionEnv()
    env.reset(seed=0, options={"clima": "despejado", "gravedad": "tierra", **opciones})
    return env


def test_cumple_api_gymnasium():
    check_env(gym.make("RobotExpedition-v0").unwrapped, skip_render_check=True)


def test_chocar_con_el_limite_no_mueve_y_penaliza():
    env = nuevo()
    _, r, term, trunc, info = env.step(3)  # Oeste desde la base (0, 11): límite del mapa
    assert info["posicion"] == (0, 11)
    assert r < 0 and not term and not trunc
    assert any("choque" in e for e in info["eventos"])


def test_agarrar_fuera_de_la_baliza_es_invalido():
    env = nuevo()
    _, r, *_ , info = env.step(C.AGARRAR)
    assert info["etapa"] == 0 and r < 0


def test_baliza_solo_paga_una_vez_y_en_orden():
    env = nuevo()
    env.pos = env.objetivos[1]          # baliza 2 antes que la 1: no cuenta
    _, r, *_, info = env.step(C.AGARRAR)
    assert info["etapa"] == 0 and r < 0
    env.pos = env.objetivos[0]
    _, r1, *_, info = env.step(C.AGARRAR)
    assert info["etapa"] == 1 and r1 > 5
    _, r2, *_, info = env.step(C.AGARRAR)  # repetir: inválido
    assert info["etapa"] == 1 and r2 < 0


def test_caer_en_grieta_termina():
    env = nuevo()
    env.pos = (4, 5)                     # justo al norte de la grieta (4, 6)
    _, r, term, _, info = env.step(1)
    assert term and not info["exito"] and r <= C.RECOMPENSAS["caida"] + 1


def test_saltar_por_encima_de_una_roca():
    env = nuevo()
    env.pos = (2, 4)                     # roca en (3, 4), suelo en (4, 4)
    _, _, term, _, info = env.step(6)    # saltar E
    assert info["posicion"][0] >= 4 and not term


def test_dar_vueltas_no_genera_recompensa():
    env = nuevo()
    total = 0.0
    for _ in range(20):                  # ir y volver entre (0,11) y (1,11)
        for a in (2, 3):
            total += env.step(a)[1]
    assert total < 0


def test_truncamiento_por_tiempo():
    env = ExpedicionEnv(max_pasos=5)
    env.reset(seed=0)
    for _ in range(4):
        assert not env.step(C.AGARRAR)[3]
    assert env.step(C.AGARRAR)[3]


def test_mision_completa_con_ruta_manual():
    env = nuevo()
    # base (0,11) → baliza 1 (7,8) por la fila 10; luego subida por x=9/10 y regreso.
    ruta = "N" + "E" * 7 + "NN" + "A" + "SS" + "EE" + "NNNNN" + "E" + "NNNNN" + "E" + "A"
    ruta += "O" + "SSSSS" + "O" + "SSSSS" + "OO" + "O" * 7 + "S"
    idx = {"N": 0, "S": 1, "E": 2, "O": 3, "A": C.AGARRAR}
    env.clima = "despejado"
    for paso in ruta:
        env.np_random = np.random.default_rng(1)  # rng fijo; con suerte no patina
        *_, term, trunc, info = env.step(idx[paso])
        if term:
            break
    assert term and info["exito"]
