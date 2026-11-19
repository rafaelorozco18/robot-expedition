"""Navegador del Exp 9: aprende por dónde rodear las rocas para llegar a las balizas.

Entrena en `Explorador`, un simulador cinemático rápido del mismo mundo (expedicion/mundo.py): el robot avanza y gira
como el caminante real, con la velocidad, el giro y el ruido medidos en MuJoCo (experimentos/calibracion-caminante.json),
incluido el arranque más lento después de cambiar de maniobra. Después se evalúa en MuJoCo completo, donde la tarea
«exploracion» le pasa sus decisiones al caminante del Exp 8.

    python -m expedicion navegador exp-109        # entrena y guarda models/exp-109/navegador/
"""
import json
import time

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from . import mundo as M
from .experimentos import RAIZ, carpeta_modelos


class Explorador(gym.Env):
    """Ambiente del navegador. Observación: 15 sensores + meta + dirección anterior (25). Acción: 7 direcciones.

    Cada `decision_s` el navegador fija un rumbo deseado (relativo al robot); en pasos de 0,1 s corre el controlador
    del Exp 8 sobre el rumbo pedido, y el robot lo sigue con el retraso y las velocidades medidas en MuJoCo."""
    SUB = 0.1     # s por subpaso
    TAU = 0.45    # s: el rumbo real sigue al pedido con este retraso

    def __init__(self, exp):
        self.t = exp["parametros"]
        self.n = exp["navegador"]
        cal = json.loads((RAIZ / self.n["calibracion"]).read_text())
        self.vel = {"recto": (cal["recto"]["v"], cal["recto"]["v_sd"]),
                    "curva": ((cal["curva a la izquierda"]["v"] + cal["curva a la derecha"]["v"]) / 2,
                              (cal["curva a la izquierda"]["v_sd"] + cal["curva a la derecha"]["v_sd"]) / 2),
                    "giro+": (cal["giro a la izquierda"]["v"], cal["giro a la izquierda"]["v_sd"]),
                    "giro-": (cal["giro a la derecha"]["v"], cal["giro a la derecha"]["v_sd"])}
        self.decision = float(self.t["decision_s"])
        self.max_decisiones = int(exp["ambiente"]["duracion_s"] / self.decision)
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(M.N_OBS,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(M.DIRECCIONES))

    def _obs(self):
        meta = self.mundo["balizas"][self.alcanzadas]
        return M.observacion(self.pos, self.rumbo, meta, self.mundo["rocas"], self.mundo["lado"], self.previa)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.mundo = M.generar(self.np_random, self.t)
        self.pos, self.rumbo = np.zeros(2), 0.0
        self.pedido, self.modo = 0.0, "recto"
        self.ultimo_giro, self.desde_giro = 0.0, 99.0
        # Variante robusta: cada episodio el «caminante» del simulador es un poco distinto (retraso, velocidad, giro)
        # para que el navegador no dependa de una calibración exacta y deje margen ante la física real.
        r = self.n.get("robusto", False)
        self.tau = float(self.np_random.uniform(0.3, 0.8)) if r else self.TAU
        self.f_v = float(self.np_random.uniform(0.75, 1.2)) if r else 1.0
        self.f_w = float(self.np_random.uniform(0.8, 1.2)) if r else 1.0
        self.ruido_rumbo = 0.03 if r else 0.0
        self.alcanzadas, self.previa, self.k = 0, int(np.argmin(np.abs(M.DIRECCIONES))), 0
        self.dist = np.linalg.norm(self.mundo["balizas"][0] - self.pos)
        return self._obs(), {}

    def step(self, accion):
        accion = int(accion)
        cambio = accion != self.previa
        deseado = self.rumbo + M.DIRECCIONES[accion]
        recompensa = -self.n["tiempo"] - (self.n["cambio"] if cambio else 0.0)
        motivo = None
        meta = self.mundo["balizas"][self.alcanzadas]
        for _ in range(int(round(self.decision / self.SUB))):
            e = np.arctan2(np.sin(deseado - self.pedido), np.cos(deseado - self.pedido))
            previo = self.modo
            self.modo, _, w = M.controlador(e, self.modo)
            if self.modo == "giro":
                # El caminante sufre al invertir un giro (de izquierda a derecha o al revés) y al girar sobre su eje.
                if previo == "giro" and np.sign(w) != np.sign(self.ultimo_giro) or \
                        previo != "giro" and self.desde_giro < 2.0 and np.sign(w) != np.sign(self.ultimo_giro):
                    recompensa -= self.n.get("inversion", 0.0)
                recompensa -= self.n.get("giro", 0.0) * self.SUB
                self.ultimo_giro, self.desde_giro = w, 0.0
            else:
                self.desde_giro += self.SUB
            self.pedido += w * self.SUB
            atraso = np.arctan2(np.sin(self.pedido - self.rumbo), np.cos(self.pedido - self.rumbo))
            self.rumbo += self.f_w * atraso * min(1.0, self.SUB / self.tau) + self.np_random.normal(0, self.ruido_rumbo)
            clave = self.modo if self.modo != "giro" else ("giro+" if w > 0 else "giro-")
            media, sd = self.vel[clave]
            v = max(0.0, self.f_v * media + self.np_random.normal(0, sd * 0.5))
            self.pos = self.pos + v * self.SUB * np.array([np.cos(self.rumbo), np.sin(self.rumbo)])
            if M.choca(self.pos, self.mundo["rocas"], M.RADIO_ROBOT + self.n.get("margen", 0.0)):
                motivo = "chocó con una roca"
                break
            if np.max(np.abs(self.pos)) > self.mundo["lado"]:
                motivo = "salió del campo"
                break
            if np.linalg.norm(meta - self.pos) < self.t["radio_m"]:
                break
        self.previa, self.k = accion, self.k + 1
        if motivo:
            return self._obs(), recompensa - self.n["choque"], True, False, {"motivo": motivo, "exito": False}
        dist = np.linalg.norm(meta - self.pos)
        recompensa += self.n["progreso"] * (self.dist - dist)
        self.dist = dist
        if dist < self.t["radio_m"]:
            recompensa += self.n["meta"]
            self.alcanzadas += 1
            if self.alcanzadas == len(self.mundo["balizas"]):
                return self.observacion_vacia(), recompensa, True, False, {"motivo": "llegó a todas las balizas", "exito": True}
            self.dist = np.linalg.norm(self.mundo["balizas"][self.alcanzadas] - self.pos)
        truncado = self.k >= self.max_decisiones
        return self._obs(), recompensa, False, truncado, {"exito": False, "motivo": "se acabó el tiempo" if truncado else None}

    def observacion_vacia(self):
        return np.zeros(M.N_OBS, np.float32)


class ExploradorMuJoCo(gym.Env):
    """El mismo problema del navegador, pero con la física real: cada decisión avanza `decision_s` de MuJoCo con el
    caminante del Exp 8 (actor exportado a numpy, con su ruido sembrado por episodio). Caerse o chocar termina el
    episodio y se castiga, así el navegador aprende qué órdenes hacen caer o chocar al robot de verdad."""

    CAMINANTE = "models/exp-109/caminante/exp-108-semilla-1.npz"  # fuera de las salidas de DVC del Exp 8

    def __init__(self, exp):
        from .ambiente import BipedoEnv
        from .evaluar import PoliticaNumpy
        self.n = exp["navegador"]
        self.exp = {**exp, "navegador": {**exp["navegador"], "modelo": "externo"}}
        self.env = BipedoEnv(self.exp, entrenando=False)
        self.caminante = PoliticaNumpy(RAIZ / self.CAMINANTE)
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(M.N_OBS,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(M.DIRECCIONES))

    def _obs(self):
        t = self.env.tarea
        return M.observacion(self.env.data.qpos[:2].copy(), self.env.rumbo(), self.env.destino, t.rocas,
                             t.mundo["lado"], t.direccion)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        s = int(self.np_random.integers(1 << 30))
        self.o, _ = self.env.reset(seed=s)
        self.actor = self.caminante.para_episodio(s)
        t = self.env.tarea
        self.dist = np.linalg.norm(self.env.destino - self.env.data.qpos[:2])
        self.alcanzadas = t.alcanzadas
        return self._obs(), {}

    def step(self, accion):
        t = self.env.tarea
        cambio = int(accion) != t.direccion
        t.elegir(self.env, accion)
        recompensa = -self.n["tiempo"] - (self.n["cambio"] if cambio else 0.0)
        fin = trunc = False
        for _ in range(t.cada):
            self.o, _, fin, trunc, info = self.env.step(self.actor.actuar(self.o, self.env))
            if fin or trunc:
                break
        if t.alcanzadas > self.alcanzadas:
            recompensa += self.n["meta"] * (t.alcanzadas - self.alcanzadas)
            self.alcanzadas = t.alcanzadas
            self.dist = np.linalg.norm(self.env.destino - self.env.data.qpos[:2])
        else:
            dist = np.linalg.norm(self.env.destino - self.env.data.qpos[:2])
            recompensa += self.n["progreso"] * (self.dist - dist)
            self.dist = dist
        exito = bool(fin and t.exito(self.env, False))
        if fin and not exito:
            recompensa -= self.n["choque"]  # caerse o chocar
        return self._obs(), recompensa, fin, trunc, {"exito": exito, "motivo": self.env.motivo}


def ajustar_en_mujoco(exp, semilla, parte_de, pasos, salida, procesos=8):
    """Sigue entrenando un navegador con la física real (ExploradorMuJoCo)."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv
    import mlflow
    import torch
    from .entrenar import URI_MLFLOW, git_commit

    torch.set_num_threads(1)
    venv = make_vec_env(ExploradorMuJoCo, n_envs=procesos, seed=semilla, vec_env_cls=SubprocVecEnv, env_kwargs={"exp": exp})
    modelo = PPO.load(RAIZ / parte_de, env=venv, device="cpu", seed=semilla,
                      custom_objects={"learning_rate": 1e-4, "n_steps": 64, "batch_size": 256})
    salida = RAIZ / salida
    (salida / "fotos").mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(URI_MLFLOW)
    mlflow.set_experiment(f"{exp['id']}-navegador")
    t0 = time.time()
    with mlflow.start_run(run_name=f"navegador-mujoco-semilla-{semilla}") as run:
        mlflow.set_tags({"git_commit": git_commit(), "variante": "mujoco", "parte_de": parte_de,
                         "hipotesis": "Ajustar el navegador con la física real (caminante en el circuito) le enseña qué "
                                      "órdenes hacen caer o chocar al robot y cierra la brecha del simulador cinemático."})
        mlflow.log_params({"pasos": pasos, "procesos": procesos, "learning_rate": 1e-4, "parte_de": parte_de})
        tramo = max(pasos // 6, 1)
        for _ in range(6):
            modelo.learn(tramo, reset_num_timesteps=False)
            modelo.save(salida / "fotos" / f"paso-{int(modelo.num_timesteps):09d}.zip")
            print({"paso": int(modelo.num_timesteps), "segundos": round(time.time() - t0)}, flush=True)
        modelo.save(salida / "experto.zip")
        corrida = {"semilla": semilla, "pasos": int(modelo.num_timesteps), "segundos": round(time.time() - t0, 1),
                   "parte_de": parte_de, "mlflow_run_id": run.info.run_id}
    (salida / "corrida.json").write_text(json.dumps(corrida, indent=1, ensure_ascii=False))
    venv.close()
    return corrida


def evaluar_cinematico(exp, modelo, episodios=200, semilla=9000):
    env = Explorador(exp)
    exitos, motivos = 0, {}
    for k in range(episodios):
        obs, _ = env.reset(seed=semilla + k)
        fin = False
        while not fin:
            a, _ = modelo.predict(obs, deterministic=True)
            obs, r, term, trunc, info = env.step(a)
            fin = term or trunc
        exitos += info["exito"]
        motivos[info["motivo"]] = motivos.get(info["motivo"], 0) + 1
    return exitos / episodios, motivos


def entrenar_navegador(exp, semilla=0, usar_mlflow=True, variante=None):
    """Sin variante: el navegador oficial del yaml (models/<exp>/navegador). Con variante: una configuración a comparar
    (navegador.variantes.<nombre> sobreescribe parámetros), en models/<exp>/navegadores/<variante>-s<semilla>."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    import torch

    torch.set_num_threads(1)
    base = {k: v for k, v in exp["navegador"].items() if k != "variantes"}
    n = {**base, **(exp["navegador"].get("variantes", {}).get(variante, {}) if variante else {})}
    exp = {**exp, "navegador": n}
    salida = carpeta_modelos(exp) / ("navegador" if variante is None else f"navegadores/{variante}-s{semilla}")
    salida.mkdir(parents=True, exist_ok=True)
    from stable_baselines3.common.vec_env import SubprocVecEnv
    venv = make_vec_env(Explorador, n_envs=8, seed=semilla, vec_env_cls=SubprocVecEnv, env_kwargs={"exp": exp})
    if n.get("parte_de"):  # sigue entrenando un navegador anterior: no pierde lo aprendido
        modelo = PPO.load(RAIZ / n["parte_de"], env=venv, device="cpu", seed=semilla,
                          custom_objects={"learning_rate": n.get("learning_rate", 1e-4)})
    else:
        modelo = PPO("MlpPolicy", venv, seed=semilla, verbose=0, device="cpu", n_steps=256, batch_size=512, n_epochs=8,
                     learning_rate=3e-4, gamma=0.99, gae_lambda=0.95, ent_coef=0.01,
                     policy_kwargs={"net_arch": n["red"]})
    run = None
    if usar_mlflow:
        import mlflow
        from .entrenar import URI_MLFLOW, git_commit
        mlflow.set_tracking_uri(URI_MLFLOW)
        mlflow.set_experiment(f"{exp['id']}-navegador")
        run = mlflow.start_run(run_name=f"navegador-{variante or 'oficial'}-semilla-{semilla}")
        mlflow.log_params({f"nav.{k}": v for k, v in n.items() if k not in ("modelo", "hipotesis")})
        mlflow.log_params({f"mundo.{k}": v for k, v in exp["parametros"].items() if k in (
            "lado_m", "rocas", "rocas_en_ruta", "radio_roca_m", "parches", "decision_s", "distancia_m", "balizas")})
        mlflow.set_tags({"git_commit": git_commit(), "variante": variante or "oficial",
                         "hipotesis": n.get("hipotesis", "Un navegador PPO con sensores de distancia aprende a rodear "
                                        "rocas; entrenado en un simulador cinemático calibrado, transfiere a MuJoCo."),
                         "familia": "navegador: 25 observaciones, 7 direcciones"})
    curva, t0, total = [], time.time(), int(n["pasos"])
    tramo = total // 10
    for k in range(10):
        modelo.learn(tramo, reset_num_timesteps=False)
        tasa, motivos = evaluar_cinematico(exp, modelo, episodios=100)
        curva.append({"paso": int(modelo.num_timesteps), "tasa_exito": tasa, "motivos": motivos})
        print({"paso": int(modelo.num_timesteps), "tasa_exito": tasa, "motivos": motivos}, flush=True)
        if run:
            import mlflow
            mlflow.log_metric("cinematico.tasa_exito", tasa, step=int(modelo.num_timesteps))
        modelo.save(salida / "fotos" / f"paso-{int(modelo.num_timesteps):09d}.zip")
    modelo.save(salida / "experto.zip")
    final, motivos = evaluar_cinematico(exp, modelo, episodios=300, semilla=8000)
    corrida = {"semilla": semilla, "pasos": int(modelo.num_timesteps), "segundos": round(time.time() - t0, 1),
               "tasa_cinematico_300": final, "motivos": motivos}
    if run:
        import mlflow
        mlflow.log_metric("cinematico.tasa_final_300", final)
        corrida["mlflow_run_id"] = run.info.run_id
        mlflow.end_run()
    (salida / "corrida.json").write_text(json.dumps(corrida, indent=1, ensure_ascii=False))
    (salida / "curva.json").write_text(json.dumps(curva, indent=1, ensure_ascii=False))
    return corrida
