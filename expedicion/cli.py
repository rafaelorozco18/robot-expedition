"""CLI de Robot Expedition.

    expedicion lista                           experimentos y su estado
    expedicion info exp-001                    espacios de observación y acción
    expedicion escenarios exp-001              genera los escenarios de prueba
    expedicion entrenar exp-001 --semilla 0    entrena una corrida con PPO
    expedicion evaluar exp-001                 compara semillas y elige al campeón
    expedicion progreso exp-001                evalúa cada foto del campeón
    expedicion ver exp-001 --planeta luna      imprime un episodio en la terminal
    expedicion transiciones exp-001            tabla de cinco transiciones
    expedicion registrar exp-001               registra al campeón en MLflow
    expedicion campana exp-002 exp-003         corre experimentos en cadena
    expedicion servir                          visor 3D en http://localhost:8765
"""

import argparse
import json

import numpy as np

from . import experimentos as X
from .ambiente import PERTURBACIONES, PLANETAS, BipedoEnv


def cmd_lista(args):
    for exp in X.listar():
        print(f"{exp['id']}  {exp['titulo']:14s} {exp['estado']:10s} {exp['pregunta']}")


def cmd_info(args):
    env = BipedoEnv(X.cargar(args.exp))
    print("Observación:", env.observation_space)
    print("Acción:", env.action_space, env.nombres_motor)
    print(f"Altura del torso de pie: {env.altura_pie:.3f} m · control a {1 / env.dt:.0f} Hz"
          f" · {env.max_pasos} pasos por episodio")


def cmd_escenarios(args):
    from .evaluar import generar_escenarios
    exp = X.cargar(args.exp)
    esc = generar_escenarios(exp)
    X.carpeta_datos(exp).mkdir(parents=True, exist_ok=True)
    (X.carpeta_datos(exp) / "escenarios.json").write_text(json.dumps(esc, indent=1))
    print(f"{len(esc)} escenarios")


def cmd_entrenar(args):
    from .entrenar import entrenar
    print(json.dumps(entrenar(X.cargar(args.exp), args.semilla, args.pasos, not args.sin_mlflow), indent=2))


def cmd_evaluar(args):
    from .evaluar import evaluar
    exp = X.cargar(args.exp)
    res = evaluar(exp)
    print(f"{'agente':14s} {'éxito':>6s} {'seg':>6s} {'energía J':>10s}")
    for nombre, m in {**res["agentes"], **{f"semilla-{s}": v for s, v in res["semillas"].items()}}.items():
        g = m["global"]
        print(f"{nombre:14s} {g['tasa_exito']:6.0%} {g['segundos_medios']:6.1f} {g['energia_media_j']:10.1f}")
    m = res["semillas"][str(res["campeon"])]
    for k, v in m.items():
        if k != "global":
            print(f"  {k:20s} éxito {v['tasa_exito']:5.0%} · {v['segundos_medios']:5.1f} s")
    print(f"Campeón: semilla {res['campeon']} · aprobado: {res['aprobado']}")


def cmd_progreso(args):
    from .evaluar import evaluar_progreso
    evaluar_progreso(X.cargar(args.exp))


def _agente(exp, nombre, semilla):
    from .servidor import crear_agente
    return crear_agente(exp, nombre, semilla)


def cmd_ver(args):
    from .evaluar import correr_episodio
    exp = X.cargar(args.exp)
    esc = {"planeta": args.planeta, "perturbacion": args.perturbacion, "semilla": args.semilla}
    resumen, cuadros = correr_episodio(exp, _agente(exp, args.agente, args.semilla), esc, grabar=True)
    for c in cuadros[::25]:
        print(f"t {c['t']:5.2f} s · altura {c['altura']:.2f} m · inclinación {c['inclinacion']:5.1f}° "
              f"· pies {'I' if c['pies'][0] else '-'}{'D' if c['pies'][1] else '-'}")
    print(resumen)


def cmd_transiciones(args):
    """Primeras transiciones reales, para el documento de cada experimento."""
    exp = X.cargar(args.exp)
    env = BipedoEnv(exp)
    agente = _agente(exp, args.agente, args.semilla)
    obs, _ = env.reset(seed=args.semilla, options={"planeta": args.planeta, "perturbacion": "ninguna"})
    print("| t (s) | Observación (altura rel., inclinación °) | Acción (media de torques) | Nuevo estado | Recompensa | Fin |")
    print("|---|---|---|---|---|---|")
    for _ in range(args.n):
        antes = f"{obs[0]:+.3f} m · {env.inclinacion_grados():.2f}°"
        t = env.pasos * env.dt
        a = agente.actuar(obs, env)
        obs, r, term, trunc, _ = env.step(a)
        fin = "terminado" if term else "truncado" if trunc else "no"
        print(f"| {t:.2f} | {antes} | {np.mean(np.abs(a)):.2f} | altura {env.altura_torso():.3f} m · "
              f"{env.inclinacion_grados():.2f}° | {r:+.2f} | {fin} |")


def cmd_registrar(args):
    from .registro import registrar
    print(registrar(X.cargar(args.exp)))


def cmd_regresion(args):
    from .evaluar import regresion
    print(regresion(X.cargar(args.exp)))


def cmd_pipeline(args):
    from .pipeline import generar
    print(generar())


def cmd_documentar(args):
    from .documentar import documentar
    print(documentar(X.cargar(args.exp)))


def cmd_campana(args):
    from .campana import campana
    campana(args.exps, args.hasta, args.seguir)


def cmd_servir(args):
    from .servidor import servir
    servir(args.puerto)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="expedicion", description="Robot Expedition")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comando(nombre, funcion):
        s = sub.add_parser(nombre)
        s.set_defaults(f=funcion)
        return s

    def con_exp(nombre, funcion):
        s = comando(nombre, funcion)
        s.add_argument("exp")
        return s

    def condiciones(s):
        s.add_argument("--agente", default="experto")
        s.add_argument("--planeta", default="marte", choices=PLANETAS)
        s.add_argument("--perturbacion", default="ninguna", choices=PERTURBACIONES)
        s.add_argument("--semilla", type=int, default=0)

    comando("lista", cmd_lista)
    con_exp("info", cmd_info)
    con_exp("escenarios", cmd_escenarios)
    s = con_exp("entrenar", cmd_entrenar)
    s.add_argument("--semilla", type=int, default=0)
    s.add_argument("--pasos", type=int)
    s.add_argument("--sin-mlflow", action="store_true")
    con_exp("evaluar", cmd_evaluar)
    con_exp("progreso", cmd_progreso)
    condiciones(con_exp("ver", cmd_ver))
    s = con_exp("transiciones", cmd_transiciones)
    condiciones(s)
    s.add_argument("-n", type=int, default=5)
    con_exp("registrar", cmd_registrar)
    con_exp("regresion", cmd_regresion)
    con_exp("documentar", cmd_documentar)
    comando("pipeline", cmd_pipeline)
    s = comando("campana", cmd_campana)
    s.add_argument("exps", nargs="+")
    s.add_argument("--seguir", action="store_true", help="continúa aunque un experimento no apruebe")
    s.add_argument("--hasta", help="hora HH:MM a partir de la cual no se inicia otro experimento")
    comando("servir", cmd_servir).add_argument("--puerto", type=int, default=8765)

    args = ap.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
