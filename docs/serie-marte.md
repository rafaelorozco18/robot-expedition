# Serie Marte: del equilibrio al dominio de la marcha

Robot Expedition · MLOps Autonomous Lab. Serie definida el 2026-11-11.

Un bípedo de 12 articulaciones (`robots/bipedo-v2.xml`) aprende, solo en Marte (3,71 m/s²), a
sostenerse, caminar, resistir el viento, caminar con buena técnica, girar y moverse en curva.
Cada experimento agrega **una sola dificultad** y parte del modelo del anterior.

La serie anterior (plan de 50 experimentos, tres planetas) queda archivada en
`experimentos/plan-50/` y en los tags `exp-001` a `exp-028`.

## Los 9 experimentos

Orden vigente desde el 2026-11-13 (pedido del usuario): un experimento a la vez, y solo se avanza con un robot
mejor. El viento queda para el final.

| # | Experimento | Parte de | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|---|
| 1 | De pie | — | Articulaciones y gravedad de Marte, arrancando desequilibrado | Aguanta 10 s en ≥ 80 % |
| 2 | Caminar | 1 | Recompensa por velocidad y reloj de marcha | 10 m sin caer en ≥ 80 % |
| 3 | Caminar bien | 2 | Pasos largos y pausados, pie levantado, torso erguido, servos suaves | 10 m con calidad ≥ 55/100 en ≥ 80 % |
| 4 | Terreno difícil | 3 | Arena, grava y barro al azar, y listones de 3,5 cm | 10 m con calidad ≥ 55/100 en ≥ 75 % |
| 5 | Girar en la esquina | 4 | Caminar 3 m, detenerse, girar 90° sobre su eje y caminar 3 m | Completa la esquina con calidad ≥ 55/100 en ≥ 80 % |
| 6 | Caminar en curva | 5 | Avanzar y girar a la vez: círculo de 2 m de radio | 324° del círculo, desvío < 0,4 m y calidad ≥ 55/100, en ≥ 75 % |
| 7 | Dominio en terreno duro | 6 | Rectas, giros y curvas en orden aleatorio sobre pisos mezclados | 24 s siguiendo velocidad y rumbo, calidad ≥ 55/100, en ≥ 70 % |
| 8 | De pie con viento | 7 | Viento de 3 a 8 N en cualquier dirección, más ráfagas de 3 a 8 N | Aguanta 10 s en ≥ 90 % |
| 9 | Caminar con viento | 8 | El mismo viento, caminando | 10 m sin caer, con calidad ≥ 55/100, en ≥ 80 % |

Del 4 en adelante la calidad mínima es la que exige el Exp 3: aprender algo nuevo no puede empeorar la marcha.
La serie anterior, con el viento en los puestos 3 y 4, quedó en los tags `serie-marte-v1` y `serie-marte-v2`.

La configuración de cada uno está en `experimentos/exp-1NN.yaml` y la ficha con los 8 puntos de la
guía del profesor, generada con datos reales, en `docs/experimentos/exp-1NN.md`.

## Cómo se mide «caminar bien»

Además de llegar, cada episodio recibe una **calidad de movimiento** de 0 a 100: el promedio de cinco
indicadores, calculados por el simulador (`BipedoEnv.estadisticas`).

| Indicador | Qué premia | Valor ideal |
|---|---|---|
| Suavidad | Que las órdenes a las articulaciones no salten de un paso de control al siguiente | Cambio medio pequeño |
| Erguido | Torso vertical | Inclinación media cercana a 0° |
| Zancada | Largo de paso humano para su tamaño | 30 cm |
| Elevación | Levantar el pie en vez de arrastrarlo | ≥ 5 cm |
| Ritmo | Ni temblar ni ir en cámara lenta | 1,6 pasos por segundo |

En los ejercicios de equilibrio la calidad combina suavidad, torso erguido y quietud. Para obtener la
marcha pausada, el Exp 5 agrega recompensas por zancada, despeje del pie, articulaciones lentas y pie de
apoyo firme. El ambiente también filtra las órdenes (filtro de primer orden, 30 %), como un servo real.

## Las cinco etapas de cada experimento

En el visor, «Ver cómo aprendió» reproduce cinco momentos del aprendizaje, todos en el mismo escenario
fijo de Marte para que la comparación sea justa (`expedicion/evolucion.py`). Se prueban el robot sin
entrenar, fotos de sus antecesores y todas las fotos del entrenamiento, guardadas con más frecuencia al
inicio, que es cuando más cambia.

| Etapa | Cómo se elige |
|---|---|
| 1. Fracaso absoluto | El intento con menor avance |
| 2. Fracaso, pero mejor | Un intento fallido a mitad de camino entre el peor y el mejor fallido |
| 3. Punto de inflexión | El mejor intento que todavía falla |
| 4. Cumplido | El primero que cumple el objetivo |
| 5. Perfeccionado | El que lo cumple con la mejor calidad de movimiento |

Cada etapa se recorta al tramo que muestra el contraste: la caída, la esquina o el círculo completo.

## Versionado

| Qué | Cómo |
|---|---|
| Código | git, un commit y un tag por experimento (`exp-101` … `exp-109`); series anteriores en `serie-marte-v1` y `serie-marte-v2` |
| Dataset | DVC: escenarios de prueba congelados (`data/exp-1NN/escenarios.json`) y trayectorias grabadas |
| Pipeline | `dvc.yaml`, generado por `expedicion pipeline`, y `dvc.lock` con los hashes |
| Experimento | MLflow: un experimento por pregunta y una corrida por semilla (`mlflow.db`) |
| Modelo | DVC (`models/exp-1NN/`) y MLflow Model Registry (`robot-exp-1NN`, alias `campeon`) |
| Robot | `robots/bipedo-v2.xml` |
| Visor | Copia autosuficiente por experimento en `publicado/`, que no se rompe al reentrenar |

Todo lo anterior lo produce `expedicion campana exp-101 … exp-109`: entrena, evalúa, prueba cada foto,
repite las pruebas anteriores (regresión), calcula las etapas, registra en MLflow, documenta, publica,
hace commit y pone el tag.

## Resultados (2026-11-13, serie en orden)

| # | Experimento | Resultado | Éxito en el examen | Calidad | Intentos |
|---|---|---|---|---|---|
| 1 | De pie | Aprobado | 83 % | 29/100 | Conservado de la serie anterior |
| 2 | Caminar | Aprobado | 100 % | 26/100 | Conservado de la serie anterior |
| 3 | Caminar bien | Aprobado | 100 % | 82/100 | 2: 75 % con 6 M de pasos, 100 % con 9 M |
| 4 | Terreno difícil | Aprobado (justo) | 75 % | 78/100 | 2: el primero se atascaba en los listones |
| 5 | Girar en la esquina | No aprobado | 67 % (≈ 75 % en 40 episodios nuevos) | 77/100 | 4 |
| 6 a 9 | Curva, dominio y viento | Pendientes | — | — | — |

El examen tiene 12 episodios por condición: un episodio son 8 puntos. Por eso cada candidato se probó además en
40 episodios nuevos antes de decidir el siguiente ajuste.

## Decisiones tomadas el 2026-11-13

- **Un experimento a la vez.** Se entrena uno, se revisa por qué falla, se ajusta una sola cosa y se reintenta.
  Solo se avanza con un robot aprobado.
- **Ruido que baja.** La exploración baja hasta `log_std_final` en el 70 % del entrenamiento: la marcha deja de
  depender del ruido y vibra menos.
- **Exp 3:** la suavidad pesa 15, el reloj de marcha 4 y levantar el pie 1,5. Con 2, 2 y 0,8 la calidad se
  quedaba en 44 a 50/100 (articulaciones que vibran y 3,5 pasos por segundo). Con 9 M de pasos aprobó: 100 % y
  calidad 82/100.
- **Exp 4:** al entrenar, los listones tienen altura al azar entre 0 y 3,5 cm. Con la altura completa el robot se
  atascaba en el primero y no cumplía ningún episodio. El examen usa siempre 3,5 cm.
- **Exp 5:** se probó más entrenamiento (9 M: 33 %), giros de práctica más rápidos (0,5 a 0,9 rad/s: 58 %) y
  continuar el mejor intento (4 M más: 50 %). Ninguno superó a la semilla 0 (67 %). Sus fallas: cae al retomar la
  marcha justo después del giro.
- **Calidad mínima 55/100 desde el Exp 4:** aprender algo nuevo no puede empeorar la marcha del Exp 3.

## Limitaciones conocidas

- El viento es una fuerza horizontal sobre el torso: no hay aerodinámica.
- Arena, grava y barro son fuerzas sobre los pies, no suelo que se deforma.
- En la esquina y la curva, el rumbo y la velocidad que se piden los calcula el ambiente: el robot
  aprende a ejecutar los movimientos, no a planificar la ruta.
- Cada experimento se entrena con una sola semilla por falta de tiempo de cómputo.
