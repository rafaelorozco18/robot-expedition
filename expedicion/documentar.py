"""Genera docs/experimentos/exp-NNN.md con los 8 puntos de la guía, usando datos reales."""

import json

from . import experimentos as X
from .ambiente import GRAVEDADES, BipedoEnv
from .evaluar import Politica, campeon


def _pct(v):
    return f"{v * 100:.0f} %"


def transiciones(exp, n=5):
    env = BipedoEnv(exp)
    agente = Politica(X.carpeta_modelos(exp) / f"semilla-{campeon(exp)}" / "experto.zip")
    obs, _ = env.reset(seed=3, options={"planeta": "marte", "perturbacion": "ninguna"})
    filas = []
    for _ in range(n):
        antes = f"altura {env.altura_torso():.3f} m · inclinación {env.inclinacion_grados():.1f}°"
        a = agente.actuar(obs, env)
        t = env.pasos * env.dt
        obs, r, term, trunc, _ = env.step(a)
        fin = "terminado" if term else "truncado" if trunc else "no"
        filas.append(f"| {t:.2f} | {antes} | objetivos ±{max(abs(a)):.2f} × {exp['control']['rango']} rad | "
                     f"altura {env.altura_torso():.3f} m · inclinación {env.inclinacion_grados():.1f}° | {r:+.2f} | {fin} |")
    return "\n".join(filas)


def documentar(exp):
    ev = json.loads((X.carpeta_metricas(exp) / "evaluacion.json").read_text())
    campeon = ev["semillas"][str(ev["campeon"])]
    corrida = json.loads((X.carpeta_modelos(exp) / f"semilla-{ev['campeon']}" / "corrida.json").read_text())
    env = BipedoEnv(exp)
    a, ap = exp["ambiente"], exp["aprobar"]
    resultados = "\n".join(f"| {k.replace('.', ' · ')} | {_pct(v['tasa_exito'])} | {v['segundos_medios']:.1f} | {v['energia_media_j']:.0f} |"
                           for k, v in campeon.items() if k != "global")
    bases = "\n".join(f"| {n} | {_pct(v['global']['tasa_exito'])} | {v['global']['segundos_medios']:.1f} |"
                      for n, v in ev["agentes"].items())
    recompensa = "\n".join(f"| {k} | {v} |" for k, v in exp["recompensa"].items())
    parametros = "\n".join(f"| {k} | {v} |" for k, v in exp.get("parametros", {}).items()) or "| — | — |"
    texto = f"""# {exp['id']}: {exp['titulo']}

**Pregunta:** {exp['pregunta']}
**Dificultad que agrega:** {exp['agrega']}
**Para aprobar:** {exp['criterio']}
**Resultado:** {'Aprobado' if ev['aprobado'] else 'No aprobado'} (semilla {ev['campeon']}, {corrida['pasos']:,} pasos, {corrida['segundos'] / 60:.0f} min, código `{corrida['git_commit']}`)
**Hereda de:** {exp['parte_de'] or 'nadie, parte de cero'} · **Robot:** `{exp['robot']}`

## 1. Mapa

Campo plano de MuJoCo de 60 m × 60 m (el visor dibuja 12 m × 12 m). Inicio en el origen, de pie.
Gravedad: {', '.join(f'{k} {v} m/s²' for k, v in GRAVEDADES.items())}.

## 2. Estado y observación

- **Estado del mundo:** posiciones y velocidades de todo el cuerpo, contactos y gravedad.
- **Observación ({env.observation_space.shape[0]} valores):** altura relativa, orientación del torso, velocidades del torso,
  ángulos y velocidades de {env.model.nu} articulaciones, última acción, contacto de cada pie, gravedad, comando y reloj de marcha.
- **Acción ({env.action_space.shape[0]} valores):** ángulo objetivo por articulación, hasta ±{exp['control']['rango']} rad de la postura de pie.

## 3. Variables

| Variable | Unidad | Valor |
|---|---|---|
| Duración máxima | s | {a['duracion_s']} |
| Control | Hz | {1 / env.dt:.0f} |
| Altura de pie del torso | m | {env.altura_pie:.3f} |
| Altura mínima | fracción | {a['altura_minima']} |
| Inclinación máxima | grados | {a['inclinacion_maxima']} |
| Empujón | m/s | {a['empujon_ms']} |

Parámetros de la tarea:

| Parámetro | Valor |
|---|---|
{parametros}

## 4. Dinámica

La red decide a 50 Hz. Cada servo convierte el ángulo objetivo en torque con límite propio y MuJoCo
simula 5 subpasos de 4 ms. La gravedad se sortea por episodio entre los planetas.

## 5. Recompensa y fin del episodio

| Término | Peso |
|---|---|
{recompensa}

Termina al caer: cuerpo contra el piso, altura bajo el mínimo o inclinación excesiva. Se trunca a los {a['duracion_s']} s.

## 6. Métricas y perturbación

Perturbación evaluada: empujón horizontal de {a['empujon_ms']} m/s. Criterio medido con perturbación `{ap['perturbacion']}`.

| Condición | Éxito | Segundos | Energía (J) |
|---|---|---|---|
{resultados}

Líneas base, en todos los escenarios:

| Agente | Éxito | Segundos |
|---|---|---|
{bases}

## 7. Cinco transiciones reales

Marte, experto, semilla 3.

| t (s) | Observación | Acción | Nuevo estado | Recompensa | Fin |
|---|---|---|---|---|---|
{transiciones(exp)}

## 8. Trampas y decisiones pendientes

- **Trampa:** {exp.get('trampa', 'Por identificar.')}
- **Pendiente:** {exp.get('pendiente', 'Calibrar coeficientes y criterios con más semillas.')}
"""
    ruta = X.RAIZ / "docs" / "experimentos" / f"{exp['id']}.md"
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text(texto)
    return ruta
