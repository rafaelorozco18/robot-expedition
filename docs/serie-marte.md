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

## Resultados (2026-11-13, 15:00, serie en orden)

| # | Experimento | Resultado | Éxito en el examen | Calidad | Intentos |
|---|---|---|---|---|---|
| 1 | De pie | Aprobado | 83 % | 29/100 | Conservado de la serie anterior |
| 2 | Caminar | Aprobado | 100 % | 26/100 | Conservado de la serie anterior |
| 3 | Caminar bien | Aprobado | 100 % | 82/100 | 2: 75 % con 6 M de pasos, 100 % con 9 M |
| 4 | Terreno difícil | Aprobado (justo) | 75 % | 78/100 | 2: el primero se atascaba en los listones |
| 5 | Girar en la esquina | Aprobado | 100 % (35 de 40 en episodios nuevos) | 80/100 | 6: aprobó al retomar la marcha con una rampa de 1,5 s |
| 6 | Caminar en curva | Aprobado | 100 % | 81/100 | 1 |
| 7 a 9 | Dominio y viento | Pendientes | — | — | — |

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
  continuar el mejor intento (4 M más: 50 %). Todas las caídas eran al retomar la marcha justo después del giro,
  cuando la orden saltaba de 0 a 0,5 m/s. Desde la semilla 4 la velocidad pedida sube en 1,5 s (también en el
  examen). La semilla 5 aprobó: 100 % en el examen y 35 de 40 en episodios nuevos, calidad 80/100. La semilla 4,
  con la misma configuración, logró 42 %: la diferencia entre semillas es grande.
- **Calidad mínima 55/100 desde el Exp 4:** aprender algo nuevo no puede empeorar la marcha del Exp 3.

## Olvido de lo aprendido y repaso

Cada modelo repite los exámenes de los experimentos anteriores (regresión). La técnica de marcha se conserva:
todos siguen aprobando «Caminar bien» con calidad de 77 a 82/100, porque su recompensa sigue activa. Pero las
habilidades de cada tarea se olvidan al aprender la siguiente (olvido catastrófico):

| Modelo | Caminar bien (3) | Terreno (4) | Esquina (5) | Su examen |
|---|---|---|---|---|
| Exp 4 (terreno) | 100 % | — | — | 75 % |
| Exp 5 (esquina) | 92 % | 0 % | — | 100 % |
| Exp 6 (curva) | 100 % | 8 % | 0 % | 100 % |

**Solución, implementada el 2026-11-13 para la próxima vuelta desde el Exp 5:**
- **Repaso** (`entrenamiento.repaso`): el 30 % de los robots de cada proceso practica tareas anteriores mientras
  el resto aprende la nueva.
- **No olvidar** (`aprobar.sin_olvidar`): un experimento solo aprueba si su campeón sigue aprobando los exámenes
  anteriores indicados. Con esta regla, los Exps 5 y 6 de hoy no aprobarían.
- La regresión ahora prueba con el filtro de servos del robot evaluado: los Exps 1 y 2 usaban otro filtro y la
  comparación con ellos no era justa.

## Noche del 2026-11-14: el Exp 5 sin olvidar

Cambios en el código:
- **El campeón no puede olvidar:** `evaluar` corre, para cada semilla, los exámenes de `aprobar.sin_olvidar`.
  Gana la semilla que aprueba todo; si ninguna lo logra, el experimento no aprueba y la campaña reintenta.
- **El repaso no funcionaba:** el índice de los robots es global, así que solo el primer proceso repasaba
  (5 de 80 robots, 6 % en vez de 30 %). Corregido.
- **De pie entra al repaso y a sin_olvidar:** desde el Exp 3 ningún robot lo conservaba. El Exp 2 no entra:
  su ritmo (0,8 s, 0,5 a 0,6 m/s) lo reemplazó la marcha del Exp 3, y el robot camina sus 22 s con calidad 76
  sin llegar a 10 m.
- **Curva:** en entrenamiento la meta es el 90 % del ángulo alcanzable en el episodio. Con radios de hasta 4 m
  no cabían 0,9 vueltas en 30 s y la tasa de éxito de entrenamiento era engañosa. El examen no cambia.

Intentos del Exp 5 (examen de 12 episodios; mínimos: esquina 80 %, De pie 80 %, Caminar bien 80 %, Terreno 75 %):

| Semilla | Cómo | Esquina | De pie | Caminar bien | Terreno |
|---|---|---|---|---|---|
| 5 (antes) | sin repaso | 100 % | 8 % | 92 % | 0 % |
| 6 | desde el Exp 4, repaso 30 %, 6 M | 50 % | 50 % | 83 % | 58 % |
| 7 | igual, 9 M | 100 % | 0 % | 100 % | 0 % |
| 8 | desde la 7, repaso 50 % (el corte temprano paró a los 2 M) | 42 % | 75 % | 83 % | 58 % |
| 9 | desde la 7, repaso 50 %, 6 M | 92 % | 50 % | 100 % | 75 % |
| **10** | desde la 9, más De pie, 4 M | **92 %** | **58 %** | **100 %** | **92 %** |
| 11 | desde la 10, aún más De pie | 92 % | 67 % | 100 % | 42 % |
| 12 | desde la 10, De pie y Terreno parejos, 6 M | 58 % | 58 % | 75 % | 42 % |
| 13 | desde la 10, tasa de aprendizaje 1e-4, 4 M | 0 % | 75 % | 100 % | 42 % |
| 14 | repite la receta de la 10 desde la 10 | 25 % | 50 % | 100 % | 25 % |

- Con 40 episodios nuevos, la semilla 10 hace 34 de 40 en la esquina (85 %) y 22 de 40 en De pie (55 %).
- **De pie con los servos actuales:** desde el Exp 3 el filtro de servos es 0,6 (el Exp 1 usaba 0,3). Con ese
  filtro, el propio campeón del Exp 1 hace 67 % en su examen. El 80 % de De pie quizá no se alcanza con este
  cuerpo: decidir si el mínimo para sin_olvidar debe ser lo que logra el campeón original con el mismo control.
- Campeón: semilla 10 (no aprueba: falla De pie). Su regresión: De pie 58 %, Caminar 0 %, Caminar bien 100 %,
  Terreno 92 %, Esquina 92 %.
- Las tareas se turnan: cuando una mejora, otra empeora. La consolidación (seguir una semilla buena con más
  repaso) funcionó mejor que empezar desde el Exp 4.

## Limitaciones conocidas

- El viento es una fuerza horizontal sobre el torso: no hay aerodinámica.
- Arena, grava y barro son fuerzas sobre los pies, no suelo que se deforma.
- En la esquina y la curva, el rumbo y la velocidad que se piden los calcula el ambiente: el robot
  aprende a ejecutar los movimientos, no a planificar la ruta.
- Cada experimento se entrena con una sola semilla por falta de tiempo de cómputo.
