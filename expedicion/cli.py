"""CLI de Robot Expedition.

    expedicion info                       espacios de observación y acción
    expedicion escenarios                 genera el dataset de evaluación
    expedicion entrenar                   Q-learning + registro en MLflow
    expedicion evaluar                    métricas por agente y trayectorias
    expedicion progreso                   evalúa cada checkpoint del entrenamiento
    expedicion ver --agente experto       mira un episodio en la terminal
    expedicion transiciones               tabla de cinco transiciones
    expedicion mapa                       dibuja el mapa en SVG
    expedicion servir                     visor 3D en http://localhost:8765
"""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from . import config as C


def cargar_params(ruta="params.yaml"):
    if Path(ruta).exists():
        return yaml.safe_load(Path(ruta).read_text())
    return {"ambiente": dict(C.PARAMETROS_AMBIENTE), "entrenamiento": {}, "evaluacion": {}}


def cmd_info(args, p):
    from .ambiente import ExpedicionEnv
    env = ExpedicionEnv(**p["ambiente"])
    print("Robot Expedition v0.1 —", "12 m × 12 m, paso = 1 s")
    print("\nAcciones:", env.action_space)
    for i, n in enumerate(C.NOMBRES_ACCION):
        print(f"  {i}: {n}")
    print("\nObservación:")
    for k, v in env.observation_space.spaces.items():
        print(f"  {k:20s} {v}")
    print("\nParámetros:", json.dumps(env.p))


def cmd_escenarios(args, p):
    from .evaluar import generar_escenarios
    esc = generar_escenarios(p["evaluacion"])
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text(json.dumps(esc, indent=1))
    print(f"{len(esc)} escenarios → {args.salida}")


def cmd_entrenar(args, p):
    from .entrenar import entrenar
    pe = dict(p["entrenamiento"])
    if args.episodios:
        pe["episodios"] = args.episodios
    resumen = entrenar(p["ambiente"], pe, args.modelos, args.metricas, usar_mlflow=not args.sin_mlflow)
    print(json.dumps(resumen, indent=2))


def cmd_evaluar(args, p):
    from .evaluar import evaluar
    escenarios = json.loads(Path(args.escenarios).read_text())
    res = evaluar(escenarios, p["ambiente"], p["evaluacion"], args.modelos,
                  args.trayectorias, args.salida)
    print(f"{'agente':10s} {'misión':>7s} {'balizas':>8s} {'batería':>8s} {'pasos':>6s} "
          f"{'choques':>8s} {'caídas':>7s} │ {'misión c/incidente':>18s}")
    for nombre, m in res.items():
        g = m["global"]
        print(f"{nombre:10s} {g['tasa_mision']:7.0%} {g['balizas_medias']:8.2f} "
              f"{g['bateria_final_exito']:7.1f}% {g['pasos_exito']:6.1f} {g['choques_medios']:8.2f} "
              f"{g['tasa_caida']:7.0%} │ {m['corredor_bloqueado']['tasa_mision']:18.0%}")
    _registrar_evaluacion_mlflow(args.modelos, res, p)


def cmd_progreso(args, p):
    from .evaluar import evaluar_progreso
    escenarios = json.loads(Path(args.escenarios).read_text())
    filas = evaluar_progreso(escenarios, p["ambiente"], p["evaluacion"], args.modelos, args.salida)
    print(f"{'episodio':>9s} {'misión':>7s} {'balizas':>8s} {'batería':>8s} {'choques':>8s} │ {'c/incidente':>11s}")
    for f in filas:
        print(f"{f['episodio']:9d} {f['ninguno.tasa_mision']:7.0%} {f['ninguno.balizas_medias']:8.2f} "
              f"{f['ninguno.bateria_final_exito']:7.1f}% {f['ninguno.choques_medios']:8.2f} │ "
              f"{f['corredor_bloqueado.tasa_mision']:11.0%}")


def _registrar_evaluacion_mlflow(carpeta_modelos, res, p):
    tarjeta = Path(carpeta_modelos) / "modelo.json"
    if not tarjeta.exists():
        return
    run_id = json.loads(tarjeta.read_text()).get("mlflow_run_id")
    if not run_id:
        return
    import mlflow
    mlflow.set_tracking_uri(p["entrenamiento"].get("mlflow_uri", "sqlite:///mlflow.db"))
    with mlflow.start_run(run_id=run_id):
        for nombre, m in res.items():
            for grupo in ("global", "ninguno", "corredor_bloqueado"):
                for k in ("tasa_mision", "bateria_final_exito", "choques_medios", "tasa_caida"):
                    mlflow.log_metric(f"eval.{nombre}.{grupo}.{k}", m[grupo][k])


def cmd_ver(args, p):
    from .agentes import cargar_agente
    from .ambiente import ExpedicionEnv
    env = ExpedicionEnv(render_mode="ansi", **p["ambiente"])
    agente = cargar_agente(args.agente, args.modelos, semilla=args.semilla)
    obs, info = env.reset(seed=args.semilla, options={
        "clima": args.clima, "gravedad": args.gravedad, "incidente": args.incidente})
    total, fin = 0.0, False
    while not fin:
        sys.stdout.write("\033[2J\033[H")
        print(f"\033[1mROBOT EXPEDITION\033[0m · agente: {args.agente} · recompensa {total:7.2f}\n")
        print(env.render())
        time.sleep(args.pausa)
        obs, r, term, trunc, info = env.step(agente.actuar(obs))
        total += r
        fin = term or trunc
    sys.stdout.write("\033[2J\033[H")
    print(f"\033[1mROBOT EXPEDITION\033[0m · agente: {args.agente} · recompensa {total:7.2f}\n")
    print(env.render())
    print(f"\nFin: {env.motivo} en {info['pasos']} pasos · batería {info['bateria']:.1f}%")


def cmd_transiciones(args, p):
    from .agentes import cargar_agente
    from .ambiente import ETAPAS, ExpedicionEnv
    env = ExpedicionEnv(**p["ambiente"])
    agente = cargar_agente(args.agente, args.modelos, semilla=args.semilla)
    obs, info = env.reset(seed=args.semilla, options={
        "clima": args.clima, "gravedad": args.gravedad, "incidente": args.incidente})
    print(f"Clima {args.clima}, gravedad {args.gravedad}, semilla {args.semilla}, agente {args.agente}\n")
    print("| t | observación (objetivo dx,dy · batería · terreno · rayo N/E/S/O) | acción "
          "| nuevo estado (x,y · etapa · batería) | recompensa | eventos | fin |")
    print("|---|---|---|---|---|---|---|")
    for t in range(args.n):
        o = obs
        rayos = "/".join(f"{o['rayos'][i]:.1f}" for i in (0, 2, 4, 6))
        terreno = C.TERRENOS[C.CODIGOS_TERRENO[o["terreno"]]]["nombre"]
        a = agente.actuar(obs)
        obs, r, term, trunc, info = env.step(a)
        x, y = info["posicion"]
        fin = "terminado" if term else "truncado" if trunc else "no"
        print(f"| {t} | ({o['objetivo'][0]},{o['objetivo'][1]}) · {o['bateria'][0]:.1f}% · {terreno} · {rayos} "
              f"| {C.NOMBRES_ACCION[a]} | ({x},{y}) · {ETAPAS[min(info['etapa'], 2)]} · {info['bateria']:.1f}% "
              f"| {r:+.2f} | {', '.join(info['eventos']) or '—'} | {fin} |")
        if term or trunc:
            break


def cmd_mapa(args, p):
    from .dibujo import mapa_svg
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text(mapa_svg())
    print(f"Mapa → {args.salida}")


def cmd_servir(args, p):
    from .servidor import servir
    servir(p["ambiente"], args.modelos, args.puerto)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="expedicion", description="Robot Expedition v0.1")
    ap.add_argument("--params", default="params.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def condiciones(s):
        s.add_argument("--agente", default="experto",
                       choices=["experto", "aprendiz", "codicioso", "aleatorio"])
        s.add_argument("--clima", default="despejado", choices=C.NOMBRES_CLIMA)
        s.add_argument("--gravedad", default="tierra", choices=C.NOMBRES_GRAVEDAD)
        s.add_argument("--incidente", default="ninguno", choices=list(C.INCIDENTES))
        s.add_argument("--semilla", type=int, default=0)
        s.add_argument("--modelos", default="models")

    sub.add_parser("info").set_defaults(f=cmd_info)

    s = sub.add_parser("escenarios")
    s.add_argument("--salida", default="data/escenarios.json")
    s.set_defaults(f=cmd_escenarios)

    s = sub.add_parser("entrenar")
    s.add_argument("--episodios", type=int)
    s.add_argument("--modelos", default="models")
    s.add_argument("--metricas", default="metrics")
    s.add_argument("--sin-mlflow", action="store_true")
    s.set_defaults(f=cmd_entrenar)

    s = sub.add_parser("evaluar")
    s.add_argument("--escenarios", default="data/escenarios.json")
    s.add_argument("--modelos", default="models")
    s.add_argument("--trayectorias", default="data/trayectorias.jsonl")
    s.add_argument("--salida", default="metrics/evaluacion.json")
    s.set_defaults(f=cmd_evaluar)

    s = sub.add_parser("progreso")
    s.add_argument("--escenarios", default="data/escenarios.json")
    s.add_argument("--modelos", default="models")
    s.add_argument("--salida", default="metrics/progreso.json")
    s.set_defaults(f=cmd_progreso)

    s = sub.add_parser("ver")
    condiciones(s)
    s.add_argument("--pausa", type=float, default=0.25)
    s.set_defaults(f=cmd_ver)

    s = sub.add_parser("transiciones")
    condiciones(s)
    s.add_argument("-n", type=int, default=5)
    s.set_defaults(f=cmd_transiciones)

    s = sub.add_parser("mapa")
    s.add_argument("--salida", default="docs/mapa-v0.1.svg")
    s.set_defaults(f=cmd_mapa)

    s = sub.add_parser("servir")
    s.add_argument("--puerto", type=int, default=8765)
    s.add_argument("--modelos", default="models")
    s.set_defaults(f=cmd_servir)

    args = ap.parse_args(argv)
    args.f(args, cargar_params(args.params))


if __name__ == "__main__":
    main()
