# Incidente controlado, intervención y rollback

## 1. Incidente: el piso deja de ser firme

**Perturbación.** El campeón del Exp 7 (Recorrido: rectas, giros y curvas encadenados) se entrenó y se aprobó sobre piso
firme. El incidente cambia la condición de operación: el mismo recorrido, con las mismas órdenes y el mismo criterio
(≥ 70 % de recorridos completos con calidad ≥ 55), pero con **grava, arena y barro** mezclados al azar bajo el robot.
En el código es el experimento `exp-107` (`experimentos/exp-107.yaml`, `pisos.tramos`), que solo agrega el bloque de
pisos sobre `exp-107a`.

**Medición antes y después** (40 recorridos nuevos por condición, semillas 3000+, `scripts/medir40.py`):

| Modelo | Piso firme | Pisos sueltos | Exámenes anteriores |
|---|---|---|---|
| Campeón del Exp 7a (servido, `exp-107a` semilla 3) | **37 de 40 (92 %)** | **10 de 40 (25 %)** | no olvida nada |

**Degradación: de 92 % a 25 %** (−67 puntos). El diagnóstico (`docs/serie-marte.md`, noche del 2026-11-17) separó la
causa por tipo de piso: con un solo tipo de piso en todo el recorrido, arena 39 de 40, grava 24 y **barro 9 de 40**.
En el barro el robot no se cae: va más lento de lo pedido (error de velocidad 0,26–0,29 m/s, máximo 0,25) o se inclina
más de 40° al girar.

## 2. Intervención

**Hipótesis:** entrenar con pisos de intensidad al azar (de suelo firme a la intensidad del examen) da señal para
aprender los pisos duros. Es un cambio solo de entrenamiento: `pisos.intensidad_entrenando`; el examen no cambia.

| Candidato | Qué cambia | Piso firme | Pisos sueltos | Exámenes anteriores | Decisión |
|---|---|---|---|---|---|
| Exp 7 semillas 4 → 7 (PPO) | intensidad 0–1, después 0,5–1 y 0,75–1 | 33 de 40 | **26 de 40 (65 %)** | olvida la curva (25 % en el examen) | rechazado |
| Exp 7 semilla 10 (destilado desde el campeón del 6) | maestro: semilla 7 | 33 de 40 | **28 de 40 (70 %)** | no olvida; examen oficial del recorrido 50 % y De pie 75 % | rechazado |

La intervención **recupera buena parte del desempeño sobre pisos sueltos (de 25 % a 65–70 %)**, pero ningún candidato
cumple a la vez el criterio del recorrido en el examen oficial y no olvidar lo anterior. Se rechaza: el modelo servido
sigue siendo el campeón del Exp 7a, y el recorrido sobre pisos sueltos queda documentado como límite conocido.
Toda la evidencia está conservada: corridas en MLflow (experimento `exp-107-dominio-en-terreno-duro`), modelos en DVC,
manifiestos `manifests/exp-107-semilla-6.json` y `manifests/exp-107-semilla-10.json`, y la tabla completa en
`docs/comparacion-experimentos.md`.

## 3. Monitoreo

- `GET /sim/api/estado` (Vercel) devuelve la versión servida de cada experimento (carpeta publicada, campeón,
  SHA-256 del modelo original y del actor exportado), episodios servidos, errores y latencia de inferencia.
- El visor marca cada episodio como «Evaluación en vivo» (corrido ahora en el servidor), «Replay grabado» (precalculado
  al publicar) o «Error del servicio». Un error nunca se reemplaza por un replay.
- La regresión de cada campeón (exámenes anteriores) se publica junto al modelo y el visor la muestra en
  «¿Olvidó lo anterior?».

## 4. Prueba de rollback (ejecutada el 2026-11-19)

Escenario: un candidato rechazado se promueve por error como versión servida del Exp 8. El monitoreo lo detecta y el
flujo de rollback vuelve a la versión anterior y comprueba que funciona. Cada paso es un flujo de Prefect y deja su
registro en `pipelines/ejecuciones/` (archivos `20261119-0400*`).

| Paso | Comando | Versión servida | Semilla | SHA-256 del modelo | Éxito en episodios nuevos (7000+) |
|---|---|---|---|---|---|
| 1. Monitoreo inicial | `flujo.py exp-108 --monitorear` | `exp-108-1795078763825659466` | 1 (campeón) | `2083930f7bb0…` | 15 de 20 |
| 2. Promoción por error | `scripts/promover.py exp-108 2` | `exp-108-1795078834288728653` | 2 (rechazado) | `6b1b5d06f30b…` | — |
| 3. Monitoreo: degradación | `flujo.py exp-108 --monitorear` | `exp-108-1795078834288728653` | 2 | `6b1b5d06f30b…` | **7 de 20** |
| 4. Rollback | `flujo.py exp-108 --rollback` | vuelve a `exp-108-1795078763825659466` | 1 | `2083930f7bb0…` | 7 de 10 (verificación del rollback) |
| 5. Monitoreo final | `flujo.py exp-108 --monitorear` | `exp-108-1795078763825659466` | 1 | `2083930f7bb0…` | **15 de 20** |

- Promover **no sobrescribe** nada: cada publicación es una carpeta nueva en `publicado/.versiones/` y el enlace
  `publicado/exp-108` cambia de un solo golpe. El rollback mueve el enlace a la versión publicada anterior.
- El rollback se comprueba por identidad (el SHA-256 vuelve a ser el del campeón y la semilla servida es la 1) y por
  funcionamiento (episodios nuevos).
- En MLflow el campeón está identificado por el alias `campeon` de `robot-exp-108` (versión 4); la promoción por error
  no lo tocó, y el registro es idempotente: volver a registrar el mismo run reutiliza su versión.
- Rollback del código y la configuración: cada experimento tiene su tag (`git checkout exp-107a`), y
  `bash scripts/bajar_modelos.sh` (`dvc pull`) trae los modelos que ese commit referencia.
