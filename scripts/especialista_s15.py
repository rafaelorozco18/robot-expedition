"""Maestros con el estilo de marcha de la semilla 15 del Exp 5, para la destilación.

La semilla 19 mostró que un maestro con otro estilo (el campeón del Exp 4 en terreno) confunde al alumno.
Cada maestro parte de la semilla 15 del Exp 5 y entrena solo una tarea anterior con el control del Exp 5.

Resultados (2026-11-14):
- Terreno (exp-104, 4 M): la foto de 2,5 M hace 63 de 80 en episodios nuevos (el campeón del Exp 4, 58).
  Guardada como models/maestros/terreno-s15.zip.

Uso: python scripts/especialista_s15.py exp-NNN PASOS
"""
import shutil
import sys
from expedicion import experimentos as X
from expedicion.entrenar import entrenar
from expedicion.evaluar import examen_previo
tarea, pasos = sys.argv[1], int(sys.argv[2])
base = X.cargar(tarea)
nombre = {"exp-104": "terreno", "exp-101": "de-pie"}.get(tarea, tarea)
exp = {**base, "id": f"prueba-{nombre}-s15", "control": X.cargar("exp-105")["control"],
       "entrenamiento": {**base["entrenamiento"], "procesos": 4, "pasos": pasos, "pasos_minimos": pasos,
                         "continuar_de": {1: 0}}}
origen = X.carpeta_modelos(exp) / "semilla-0"
origen.mkdir(parents=True, exist_ok=True)
shutil.copy(X.RAIZ / "models/exp-105/semilla-15/experto.zip", origen / "experto.zip")
entrenar(exp, 1, usar_mlflow=False)
ruta = X.carpeta_modelos(exp) / "semilla-1" / "experto.zip"
print(f"RESULTADO examen {tarea}:", examen_previo(exp, ruta, [tarea]), flush=True)
