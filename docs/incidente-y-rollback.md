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

## 4. Rollback

Ver la sección «Prueba de rollback» más abajo: se ejecuta con el flujo de Prefect `robot-expedition-rollback`
(`pipelines/flujo.py --rollback`), que vuelve el enlace `publicado/<exp>` a la versión publicada anterior
(`publicado/.versiones/`), verifica el SHA-256 del modelo servido y corre un episodio de prueba. En MLflow, el alias
`campeon` del Model Registry identifica la versión recomendada y puede moverse a la versión anterior.
