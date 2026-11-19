# Ficha del ambiente · Robot Expedition (Serie Marte)

Un robot bípedo de 12 articulaciones aprende a moverse en Marte y, al final, a llegar a balizas.
La física la calcula **MuJoCo** desde Python (Gymnasium). El visor Three.js solo dibuja los cuadros que devuelve
la simulación, así que la velocidad de animación no cambia las reglas ni el paso físico.

- Código del ambiente: `expedicion/ambiente.py` (clase `BipedoEnv`); tareas y recompensas: `expedicion/tareas.py`.
- Cuerpo del robot (MJCF, versión propia): `robots/bipedo-v2.xml`.
- Perfil de cada experimento: `experimentos/base.yaml` más lo que cambia en `experimentos/exp-NNN.yaml`.
- Ficha detallada de cada experimento (8 puntos de la guía): `docs/experimentos/exp-NNN.md`.

## 1. Misión y contexto

**Misión final (Exp 8):** llegar, una tras otra, a tres balizas puestas al azar alrededor del robot, sin caerse y
con una marcha de calidad. Para llegar ahí, la serie sube la dificultad de a una cosa por experimento: sostenerse,
caminar, caminar bien, caminar sobre terreno difícil, girar en una esquina, caminar en curva, encadenar órdenes
(recorrido) y por último ir a balizas.

**Valor:** un robot con patas puede explorar terreno que una rueda no cruza. El aporte del proyecto es el
proceso: cada habilidad nueva se aprende sin olvidar las anteriores, y cada modelo es recuperable y comparable.

## 2. Contrato Gymnasium

```python
env = BipedoEnv(X.cargar("exp-108"))
obs, info = env.reset(seed=42)
obs, recompensa, terminated, truncated, info = env.step(accion)   # info["exito"] al terminar
```

| Elemento | Valor |
|---|---|
| Paso físico de MuJoCo | 0,004 s |
| Pasos físicos por decisión (`frame_skip`) | 5 |
| Frecuencia de decisión | 50 Hz (cada 0,02 s) |
| Gravedad | Marte, 3,71 m/s² |
| Duración máxima del episodio | 10 a 45 s según el experimento (`ambiente.duracion_s`) |
| Semillas | `reset(seed=…)` fija la posición inicial, el ruido y los sorteos de la tarea |

### Observación (58 valores, `float32`, recortados a ±10)

| Orden | Contenido | Dim. | Unidades |
|---|---|---|---|
| 1 | Altura del torso menos la altura de pie | 1 | m |
| 2 | Eje vertical del mundo visto desde el torso | 3 | adimensional |
| 3 | Rumbo pedido visto desde el torso (cos, sin, 0) | 3 | adimensional |
| 4 | Velocidad lineal del torso | 3 | m/s |
| 5 | Velocidad angular del torso × 0,25 | 3 | rad/s |
| 6 | Ángulo de cada articulación menos la postura de pie | 12 | rad |
| 7 | Velocidad de cada articulación × 0,1 | 12 | rad/s |
| 8 | Acción del paso anterior | 12 | [-1, 1] |
| 9 | Contacto de cada pie con el piso | 2 | 0 o 1 |
| 10 | Gravedad / 9,81 | 1 | adimensional |
| 11 | Comando: velocidad x, velocidad y, altura pedida, giro pedido | 4 | m/s, m/s, fracción, rad/s |
| 12 | Reloj de marcha (sin, cos de la fase; 0 si la tarea no usa reloj) | 2 | adimensional |

**El robot ve la gravedad, pero no el piso.** El tipo de piso lo descubre por cómo responden sus pies.
**En el Exp 8 ve la meta a través del comando:** el rumbo pedido apunta a la baliza activa y la velocidad pedida baja
a cero al llegar. No hay sensores de obstáculos (ver Limitaciones).

**Normalización:** ninguna (sin `VecNormalize`). Las escalas fijas de la tabla y el recorte a ±10 son parte del
ambiente, así que viajan con el código y no hace falta un archivo de normalización junto al modelo.

### Acción (12 valores, `float32`, en [-1, 1])

Un ángulo objetivo por articulación (cadera de giro, cadera lateral, cadera frontal, rodilla, tobillo frontal y tobillo
lateral, en cada pierna): `objetivo = postura de pie + acción × 0,8 rad`. Un filtro de primer orden (0,6 desde el Exp 3)
suaviza la orden y un servo PD por articulación la convierte en torque, con ganancias bajas. Con torque directo PPO no
aprendió a sostenerse en 500 mil pasos: por eso la red pide ángulos y no torques.

### Fin del episodio

| Señal | Causa | Valor en el examen |
|---|---|---|
| `terminated` (fallo) | Toca el piso con el cuerpo | — |
| `terminated` (fallo) | El torso baja de `altura_minima` × altura de pie | 0,75 desde el Exp 3 |
| `terminated` (fallo) | Se inclina más de `inclinacion_maxima` | 40° desde el Exp 3 |
| `terminated` (éxito) | Exp 8: llegó a la última baliza | radio 0,5 m |
| `truncated` | Se agota `duracion_s` | según el experimento |

El éxito lo decide cada tarea (`Tarea.exito`); en las tareas de marcha exige llegar al final del tiempo, cumplir la
distancia u órdenes y una **calidad de marcha ≥ 55/100** (zancada, ritmo, despeje del pie, torso erguido y suavidad).

### Recompensa (versionada en el yaml de cada experimento)

Suma de términos que se ven por separado en el visor («Recompensa»). En el entrenamiento se escala por 0,05.

| Término | Qué premia o castiga |
|---|---|
| `vivo` | Seguir en pie |
| `velocidad` | Seguir la velocidad pedida: exp(−error² / σ) |
| `rumbo` | Mirar hacia el rumbo pedido |
| `altura`, `erguido` | Torso a la altura de pie y vertical |
| `reloj`, `paso` | Apoyar y levantar la pierna que toca según la fase; despeje del pie |
| `guinada` | Girar a la velocidad pedida |
| `zancada`, `vuelo` | Pasos de ~50 cm y ~0,45 s en el aire (marcha humana) |
| `suavidad`, `vel_articular`, `esfuerzo` | Castigo a acciones bruscas, vibración y torque |
| `deslizamiento` | Castigo a arrastrar el pie de apoyo |
| `caida` | Castigo único (−30) al terminar por fallo; no se aplica al terminar con éxito |

**Corrección del 2026-11-18:** hasta el Exp 7a, el castigo `caida` se cobraba en cualquier `terminated`. En esas tareas
`terminated` solo ocurría al caer, así que no cambiaba nada. El Exp 8 es la primera tarea que termina antes por éxito,
y ahí se corrigió para no castigar la llegada.

## 3. Tres niveles de dificultad

| Nivel | Experimentos | Decisión nueva que toma el agente | Cómo se mide |
|---|---|---|---|
| **N1 · Misión base** | 1 De pie · 2 Caminar · 3 Caminar bien | Sostener el cuerpo; coordinar las piernas con un reloj; marcha de calidad | % de episodios que aguantan 10 s o caminan 10 m (con calidad ≥ 55) |
| **N2 · Más decisiones** | 4 Terreno difícil · 5 Esquina · 6 Curva · 7 Recorrido | Adaptar el paso al piso que siente; detenerse, girar y retomar; avanzar y girar a la vez; cambiar de modo cuando cambia la orden | % de éxito en cada examen, sin olvidar los anteriores |
| **N3 · Operación exigente** | 8 Llegar a las balizas · incidente: recorrido sobre pisos sueltos (Exp 7 de terreno) | Decidir cuándo girar, caminar y detenerse según dónde está la meta; operar con pisos sueltos (perturbación) | % de episodios que llegan a las 3 balizas; degradación del campeón al cambiar el piso |

**Regla de la serie:** cada experimento parte del campeón del anterior (`parte_de`). Desde el Exp 5, para aprobar, el
campeón debe seguir aprobando los exámenes anteriores (`aprobar.sin_olvidar`): en los Exps 2 a 4 los campeones habían
perdido De pie (0 a 42 %), y la regla se adoptó por eso. El examen del Exp 2 no entra: su ritmo lo reemplazó la marcha del Exp 3. Los niveles anteriores siguen accesibles en el visor y
en la API. Todos los modelos de la serie son de la **misma familia compatible**: mismo robot, 58 observaciones y 12
acciones con el mismo significado, así que cualquier modelo antiguo se puede evaluar en el ambiente de su experimento.

## 4. Simplificaciones y límites

- Arena, grava y barro son fuerzas sobre los pies (fricción, arrastre, succión, sacudida), no suelo deformable.
- El robot no tiene sensores de obstáculos: el Exp 8 no tiene obstáculos y la ruta hacia la baliza la calcula el
  ambiente (rumbo directo). El robot aprende a ejecutar giros, rectas y curvas; no a planificar.
- Solo Marte. La serie anterior (plan de 50, tres planetas) quedó archivada en los tags `exp-001` a `exp-028`.
- El examen oficial tiene 24 episodios por experimento (12 por examen previo): con una tasa real cerca del mínimo,
  aprobar depende en parte del azar. Por eso cada candidato se valida antes con 40 episodios nuevos (semillas 5000+)
  y se confirma con otros 40 (3000+). El examen fijo nunca se usa para elegir.
