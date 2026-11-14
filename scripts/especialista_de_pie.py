"""Maestro de De pie con el filtro de servos actual (0,6), para la destilación del Exp 5.

Parte del campeón del Exp 1 y entrena solo De pie con el control de los experimentos 3 en adelante.
Resultado (2026-11-14, 2 M de pasos, semilla 0): 8 de 12 en el examen del Exp 1 y 35 de 40 (87 %) en episodios
nuevos (semillas 3000+). Se guardó como models/maestros/de-pie-filtro06.zip (versionado con DVC).

Uso: python scripts/especialista_de_pie.py PASOS
"""
import sys
from expedicion import experimentos as X
from expedicion.entrenar import entrenar
from expedicion.evaluar import examen_previo
base = X.cargar("exp-101")
exp = {**base, "id": "prueba-de-pie-f06", "parte_de": "exp-101",
       "control": {"rango": 0.8, "filtro": 0.6},
       "entrenamiento": {**base["entrenamiento"], "procesos": 4, "pasos": int(sys.argv[1]),
                         "pasos_minimos": int(sys.argv[1])}}
entrenar(exp, 0, usar_mlflow=False)
ruta = X.carpeta_modelos(exp) / "semilla-0" / "experto.zip"
print("RESULTADO examen De pie con filtro 0,6:", examen_previo(exp, ruta, ["exp-101"]), flush=True)
