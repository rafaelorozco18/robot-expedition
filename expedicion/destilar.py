"""Destilación de políticas (DAgger): el alumno aprende de varios maestros sin olvidar.

PPO con repaso hace que las tareas se turnen: cuando una mejora, otra empeora. Aquí el alumno recorre
episodios de cada tarea con su propio ruido y aprende, de forma supervisada (error cuadrático sobre la
media de la acción), lo que haría el maestro de esa tarea en esos mismos estados. Después de cada ronda se
valida en episodios nuevos (semillas 5000+, distintas de las del examen) y se queda la mejor ronda.

Configuración en `entrenamiento.destilar`:
    maestros: {exp-NNN: ruta del modelo relativa a la raíz, o una lista de rutas: un conjunto cuya acción
              es el promedio de las medias (dos maestros de terreno del mismo linaje caen menos juntos)}
    episodios: {exp-NNN: episodios por ronda}
    rondas: número de rondas
    validar: episodios de validación por tarea
"""

import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from . import experimentos as X
from .ambiente import BipedoEnv

_cache = {}


def _cargar(ruta):
    from stable_baselines3 import PPO
    if ruta not in _cache:
        _cache[ruta] = PPO.load(ruta, device="cpu").policy
    return _cache[ruta]


def _media_maestro(rutas, obs):
    return np.mean([_media_y_desvio(_cargar(r), obs)[0] for r in rutas], axis=0)


def _media_y_desvio(politica, obs):
    import torch
    with torch.no_grad():
        d = politica.get_distribution(politica.obs_to_tensor(obs)[0]).distribution
        return d.mean.numpy()[0], d.stddev.numpy()[0]


def _recolectar(args):
    """Un episodio del alumno (con su ruido) en la tarea; cada estado lleva la media del maestro."""
    import torch
    torch.set_num_threads(1)
    tarea, ruta_maestro, ruta_alumno, control, semilla = args
    from stable_baselines3 import PPO
    alumno = PPO.load(ruta_alumno, device="cpu").policy
    env = BipedoEnv({**X.cargar(tarea), "control": control}, entrenando=True)
    rng = np.random.default_rng(semilla)
    obs, _ = env.reset(seed=semilla)
    xs, ys, hecho = [], [], False
    while not hecho:
        xs.append(obs.copy())
        ys.append(_media_maestro(ruta_maestro, obs))
        media, desvio = _media_y_desvio(alumno, obs)
        obs, _, term, trunc, _ = env.step(np.clip(media + desvio * rng.standard_normal(media.shape), -1, 1))
        hecho = term or trunc
    return tarea, np.array(xs, dtype=np.float32), np.array(ys, dtype=np.float32)


def _validar(args):
    import torch
    torch.set_num_threads(1)
    from .evaluar import Politica, correr_episodio
    ruta, tarea, control, k = args
    exp = {**X.cargar(tarea), "control": control}
    return tarea, correr_episodio(exp, Politica(Path(ruta)), {"planeta": "marte", "perturbacion": "ninguna",
                                                             "semilla": 5000 + k})[0]["exito"]


def _ajustar(modelo, x, y, epocas=4, lr=1e-4):
    """Ajuste supervisado de la media de la acción (no toca la función de valor ni el ruido)."""
    import torch
    pol = modelo.policy
    params = list(pol.mlp_extractor.policy_net.parameters()) + list(pol.action_net.parameters())
    opt = torch.optim.Adam(params, lr=lr)
    xt, yt = torch.tensor(x), torch.tensor(y)
    perdidas = []
    for _ in range(epocas):
        perm = torch.randperm(len(xt))
        for i in range(0, len(xt), 2048):
            idx = perm[i:i + 2048]
            feats = pol.extract_features(xt[idx], pol.pi_features_extractor)
            media = pol.action_net(pol.mlp_extractor.forward_actor(feats))
            loss = ((media - yt[idx]) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            perdidas.append(loss.item())
    return float(np.mean(perdidas[-50:]))


def destilar(modelo, exp, semilla, carpeta, procesos):
    """Destila en el modelo (se modifica y se devuelve con los pesos de la mejor ronda)."""
    cfg = exp["entrenamiento"]["destilar"]
    control = exp["control"]
    maestros = {t: [str(X.RAIZ / x) for x in ([r] if isinstance(r, str) else r)] for t, r in cfg["maestros"].items()}
    minimos = {t: X.cargar(t)["aprobar"]["tasa_exito"] for t in maestros}
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "alumno-0.zip"
    modelo.save(ruta)
    datos = {t: ([], []) for t in maestros}
    historia, mejor, n = [], None, 0
    with ProcessPoolExecutor(procesos) as pool:
        for r in range(1, cfg["rondas"] + 1):
            t0 = time.time()
            trabajos = []
            for t, k in cfg["episodios"].items():
                for _ in range(k):
                    trabajos.append((t, maestros[t], str(ruta), control, semilla * 100000 + n))
                    n += 1
            for t, xs, ys in pool.map(_recolectar, trabajos):
                datos[t][0].append(xs)
                datos[t][1].append(ys)
            x = np.concatenate([np.concatenate(datos[t][0]) for t in maestros])
            y = np.concatenate([np.concatenate(datos[t][1]) for t in maestros])
            perdida = _ajustar(modelo, x, y)
            ruta = carpeta / f"alumno-{r}.zip"
            modelo.save(ruta)
            res = {}
            for t, ex in pool.map(_validar, [(str(ruta), t, control, k) for t in maestros
                                             for k in range(cfg["validar"])]):
                res.setdefault(t, []).append(ex)
            tasas = {t: round(float(np.mean(v)), 3) for t, v in res.items()}
            margen = min(tasas[t] - minimos[t] for t in maestros)
            fila = {"ronda": r, "perdida": round(perdida, 5), "validacion": tasas, "margen": round(margen, 3),
                    "muestras": len(x), "segundos": round(time.time() - t0)}
            historia.append(fila)
            print(fila, flush=True)
            if mejor is None or margen > mejor[1]:
                mejor = (r, margen)
    (carpeta / "destilacion.json").write_text(json.dumps({"mejor_ronda": mejor[0], "rondas": historia}, indent=1))
    from stable_baselines3 import PPO
    elegido = PPO.load(carpeta / f"alumno-{mejor[0]}.zip", device="cpu")
    modelo.policy.load_state_dict(elegido.policy.state_dict())
    return modelo
