"""Maestros con el estilo de marcha de la semilla 15 del Exp 5, para la destilación.

La semilla 19 mostró que un maestro con otro estilo (el campeón del Exp 4 en terreno) confunde al alumno.
Cada maestro parte de la semilla 15 del Exp 5 y entrena solo una tarea anterior con el control del Exp 5.

Resultados (2026-11-14):
- Terreno (exp-104, 4 M): la foto de 2,5 M hace 63 de 80 en episodios nuevos (el campeón del Exp 4, 58).
  Guardada como models/maestros/terreno-s15.zip.

- De pie (exp-101, 2 M): la foto de 1,5 M hace 38 y 37 de 40 (el especialista anterior, 38 y 35).
  Guardada como models/maestros/de-pie-s15.zip.

Uso: python scripts/especialista_s15.py exp-NNN PASOS [NOMBRE ORIGEN.zip ALTO_MIN ALTO_MAX]
Con ORIGEN sigue ese modelo en vez de la semilla 15; ALTO_MIN y ALTO_MAX cambian la altura de los listones al
practicar (solo el maestro: el examen no cambia). Variables de entorno opcionales: SEMILLA (semilla de PPO, 1 por
omisión), LR (tasa de aprendizaje) y PROCESOS (4 por omisión).
"""
import os
import shutil
import sys
from expedicion import experimentos as X
from expedicion.entrenar import entrenar
from expedicion.evaluar import examen_previo
tarea, pasos = sys.argv[1], int(sys.argv[2])
base = X.cargar(tarea)
nombre = {"exp-104": "terreno", "exp-101": "de-pie"}.get(tarea, tarea)
origen_zip = X.RAIZ / "models/exp-105/semilla-15/experto.zip"
if len(sys.argv) > 3:
    nombre, origen_zip = sys.argv[3], X.RAIZ / sys.argv[4]
    base = {**base, "listones": {**base["listones"], "alto_entrenando": [float(sys.argv[5]), float(sys.argv[6])]}}
semilla = int(os.environ.get("SEMILLA", 1))
ent = {**base["entrenamiento"], "procesos": int(os.environ.get("PROCESOS", 4)), "pasos": pasos,
       "pasos_minimos": pasos, "continuar_de": {semilla: 0}}
if "LR" in os.environ:
    ent["learning_rate"] = float(os.environ["LR"])
exp = {**base, "id": f"prueba-{nombre}-s15", "control": X.cargar("exp-105")["control"], "entrenamiento": ent}
origen = X.carpeta_modelos(exp) / "semilla-0"
origen.mkdir(parents=True, exist_ok=True)
shutil.copy(origen_zip, origen / "experto.zip")
entrenar(exp, semilla, usar_mlflow=False)
ruta = X.carpeta_modelos(exp) / f"semilla-{semilla}" / "experto.zip"
print(f"RESULTADO examen {tarea}:", examen_previo(exp, ruta, [tarea]), flush=True)
