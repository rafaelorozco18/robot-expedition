# Robot Expedition: plan de los primeros 50 experimentos

Un robot aprende a controlar su cuerpo en mundos hostiles, desde sostenerse de pie hasta
completar una misión en Marte. Cada experimento agrega **una sola dificultad**: si algo falla,
se sabe qué lo causó.

## Reglas del plan

- **Orden:** se avanza cuando se aprueba el experimento anterior. El modelo aprobado es el punto de partida del siguiente.
- **Regresión:** cada modelo nuevo repite las pruebas de los experimentos anteriores, para detectar habilidades olvidadas.
- **Planetas:** salvo que se indique otra cosa, cada experimento se prueba en la Luna, Marte y la Tierra.
- **Exámenes:** los experimentos 16, 29, 44 y 50 no agregan una habilidad: combinan las del bloque para comprobar que funcionan juntas.
- **Criterios:** son propuestas iniciales y se calibrarán con los primeros resultados.
- **Un fracaso también es un resultado:** queda versionado y se investiga en corridas nuevas antes de avanzar.

## Versiones del robot

| Versión | Cuerpo | Desde |
|---|---|---|
| v1 | Torso y dos piernas, 10 articulaciones | Exp 1 |
| v2 | Agrega rotación de cadera, 12 articulaciones, necesaria para girar | Exp 18 |
| v3 | Agrega brazos y manos | Exp 45 |

## Bloque 1: Equilibrio

| # | Experimento | Dificultad que agrega | Se aprueba cuando (éxito por planeta) |
|---|---|---|---|
| 1 | De pie | Articulaciones y tres gravedades | Aguanta 10 s en ≥ 95 % |
| 2 | Empujón leve | Empujón de 0.2 m/s | Sigue de pie moviendo los pies menos de 15 cm en ≥ 90 % |
| 3 | Empujón medio | Empujón de 0.4 m/s | Sigue de pie en ≥ 85 % |
| 4 | Sentadilla | Orden de altura | Baja a 80 % de su altura y sube, con error < 3 cm |
| 5 | Pasar el peso | Equilibrio lateral | Alterna el peso entre pies en ≥ 90 % |
| 6 | Un solo pie | Apoyo mínimo | 3 s sobre un pie en ≥ 80 % |

## Bloque 2: Caminar

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 7 | Un paso | Mover un pie y recuperar la postura | Lo logra en ≥ 85 % |
| 8 | Paso de recuperación | Empujón de 0.8 m/s | Da un paso y no cae en ≥ 80 % |
| 9 | Varios pasos | Alternar las piernas | 3 m sin caer en ≥ 80 % |
| 10 | Caminar recto | Distancia sostenida | 10 m sin caer en ≥ 80 % |
| 11 | Velocidad ordenada | Velocidad entre 0.3 y 1 m/s | Error < 0.1 m/s |
| 12 | Arrancar y detenerse | Órdenes en plena marcha | Responde en < 1 s en ≥ 85 % |
| 13 | Retroceder | Marcha hacia atrás | 3 m sin caer en ≥ 80 % |
| 14 | Caminar de lado | Marcha lateral | 2 m sin caer en ≥ 80 % |
| 15 | Ahorrar energía | Menor consumo | ≥ 20 % menos energía que el Exp 10 con igual éxito |
| 16 | **Examen:** gravedad nueva | Gravedad al azar entre 1 y 12 m/s² | 10 m en ≥ 75 %, con valores nunca vistos |
| 17 | Levantarse | Empieza en el suelo | Se pone de pie en ≥ 70 % |

## Bloque 3: Girar (robot v2)

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 18 | Cuerpo nuevo | Transferir lo aprendido al robot v2 | Repite el Exp 10 |
| 19 | Girar en el sitio | Orden de giro de 90° | Error < 10° en ≥ 85 % |
| 20 | Seguir un rumbo | Caminar en curva | Se desvía < 0.5 m en ≥ 80 % |
| 21 | Ir a un punto | Destino a 5 m | Llega a < 0.3 m en ≥ 80 % |

## Bloque 4: Pisos, uno por experimento

El robot no recibe el tipo de piso: lo descubre por cómo responden sus pies.

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 22 | Arena | Piso blando con poco empuje | Cruza 5 m en ≥ 80 % |
| 23 | Barro blando | Viscosidad y hundimiento leve | Cruza 5 m en ≥ 75 % |
| 24 | Barro profundo | Hundimiento y succión variables | Cruza 5 m en ≥ 70 % |
| 25 | Grava suelta | Apoyo que se desplaza | Cruza 5 m en ≥ 75 % |
| 26 | Hielo | Fricción baja y variable | Cruza 5 m en ≥ 70 % |
| 27 | Cambio de piso | Dos pisos seguidos en orden fijo | Completa la pista en ≥ 70 % |
| 28 | Pista mixta | Pisos en orden y largo aleatorios | Completa la pista en ≥ 60 % |
| 29 | **Examen:** pista nueva | Pistas nunca vistas | Completa la pista en ≥ 60 %, en cada planeta |

## Bloque 5: Relieve y obstáculos

Desde el Exp 33 el robot recibe un sensor de altura del terreno frente a sus pies.

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 30 | Subir una rampa | Pendiente de 5° | Sube 5 m en ≥ 80 % |
| 31 | Bajar una rampa | Control al descender | Baja 5 m en ≥ 80 % |
| 32 | Pendiente fuerte | Hasta 15° | Sube y baja en ≥ 70 % |
| 33 | Escalón | Escalón de 5 cm y sensor de altura | Lo supera en ≥ 80 % |
| 34 | Escalera | Escalones de 15 cm | Sube 5 escalones en ≥ 65 % |
| 35 | Terreno irregular | Relieve al azar | Cruza 10 m en ≥ 70 % |
| 36 | Rocas bajas | Obstáculos que debe pasar o rodear | Cruza 10 m sin chocar en ≥ 70 % |
| 37 | Salto vertical | Separar ambos pies del piso | Salta y aterriza de pie en ≥ 70 % |
| 38 | Saltar una grieta | Salto con avance | Cruza 0.5 m en ≥ 65 % |

## Bloque 6: Adversidades

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 39 | Sensores con ruido | Lecturas imperfectas | Pierde < 10 % de éxito frente al Exp 35 |
| 40 | Retardo de control | 20 a 60 ms de demora | Pierde < 10 % de éxito |
| 41 | Viento constante | Fuerza lateral sostenida | 10 m en ≥ 70 % |
| 42 | Ráfagas | Viento repentino | 10 m en ≥ 65 % |
| 43 | Motor debilitado | Una articulación con 30 % menos fuerza | 10 m en ≥ 60 % |
| 44 | **Examen:** tormenta de polvo | Viento, ruido y pisos mixtos en Marte | Completa la pista en ≥ 55 % |

## Bloque 7: Brazos (robot v3)

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 45 | Cuerpo con brazos | Transferir lo aprendido y usar los brazos para equilibrarse | Repite el Exp 10 |
| 46 | Alcanzar | Llevar la mano a un punto | Error < 5 cm en ≥ 85 % |
| 47 | Agarrar | Tomar una muestra del suelo | La sostiene 3 s en ≥ 70 % |
| 48 | Caminar con carga | Masa en la mano | 10 m sin soltarla en ≥ 65 % |

## Bloque 8: La misión

| # | Experimento | Dificultad que agrega | Se aprueba cuando |
|---|---|---|---|
| 49 | Administrar batería | Cada movimiento gasta energía | Va a una baliza y vuelve con batería en ≥ 65 % |
| 50 | **Examen final:** misión completa | Dos balizas en orden, agarrar, volver a la base, en terreno hostil de Marte | Completa la misión en ≥ 50 % |

## Después del Exp 50

Quedan abiertos, entre otros: correr, trabajar con dos brazos, cooperar con otro robot, usar
cámara en vez de sensores directos, mapas generados al azar, explorar sin destino dado y fallas
múltiples de motores.

## Riesgos conocidos

- Los bloques 5 a 8 son los más inciertos: agarrar objetos y saltar con entrenamiento en CPU pueden exigir más tiempo, otro algoritmo o una GPU.
- El barro, la grava y la arena no existen en MuJoCo: se modelarán con fuerzas propias, que son aproximaciones.
- El orden, los criterios y los tiempos pueden cambiar según lo que muestren los primeros experimentos.
