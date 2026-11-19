# exp-107a: Recorrido

**Pregunta:** ¿Encadena rectas, giros y curvas sobre piso firme?
**Dificultad que agrega:** Órdenes que cambian cada pocos segundos (recto, giro y curva), en orden al azar
**Para aprobar:** 24 s siguiendo velocidad y rumbo, calidad ≥ 55/100, en ≥ 70 %
**Resultado:** Aprobado (semilla 3, 401,408 pasos, 57 min, código `441dbef`)
**Hereda de:** exp-106 · **Robot:** `robots/bipedo-v2.xml`

## 1. Mapa

Campo plano de MuJoCo de 60 m × 60 m. Inicio en el origen, de pie.
Gravedad: marte 3.71 m/s².


## 2. Estado y observación

- **Estado del mundo:** posiciones y velocidades de todo el cuerpo, contactos y gravedad.
- **Observación (58 valores):** altura relativa, orientación del torso, velocidades del torso,
  ángulos y velocidades de 12 articulaciones, última acción, contacto de cada pie, gravedad, comando y reloj de marcha.
- **Acción (12 valores):** ángulo objetivo por articulación, hasta ±0.8 rad de la postura de pie.

## 3. Variables

| Variable | Unidad | Valor |
|---|---|---|
| Duración máxima | s | 24 |
| Control | Hz | 50 |
| Altura de pie del torso | m | 0.851 |
| Altura mínima | fracción | 0.75 |
| Inclinación máxima | grados | 40 |
| Empujón | m/s | 0.4 |

Parámetros de la tarea:

| Parámetro | Valor |
|---|---|
| vx | [0.45, 0.55] |
| distancia_m | 0 |
| periodo_s | 0.68 |
| despeje_m | 0.07 |
| zancada_m | 0.5 |
| sigma_v | 0.05 |
| calidad_min | 55 |
| tramo_s | 4 |
| error_ms | 0.25 |
| error_rumbo | 0.4 |
| erguido_estricto | True |

## 4. Dinámica

La red decide a 50 Hz. Cada servo convierte el ángulo objetivo en torque con límite propio y MuJoCo
simula 5 subpasos de 4 ms. La gravedad se sortea por episodio entre los planetas.

## 5. Recompensa y fin del episodio

| Término | Peso |
|---|---|
| vivo | 0.3 |
| altura | 0.5 |
| postura | 0 |
| quieto | 0 |
| esfuerzo | 0.05 |
| suavidad | 15.0 |
| caida | 30.0 |
| velocidad | 2.0 |
| erguido | 1.5 |
| rumbo | 1.0 |
| reloj | 4.0 |
| paso | 1.5 |
| giro | 0.02 |
| vel_articular | 1.0 |
| zancada | 15.0 |
| deslizamiento | 2.0 |
| guinada | 1.0 |
| vuelo | 15.0 |

Termina al caer: cuerpo contra el piso, altura bajo el mínimo o inclinación excesiva. Se trunca a los 24 s.

## 6. Métricas y perturbación

Perturbación evaluada: empujón horizontal de 0.4 m/s. Criterio medido con perturbación `ninguna`.

| Condición | Éxito | Segundos | Energía (J) |
|---|---|---|---|
| marte · ninguna | 100 % | 24.0 | 1864 |
| marte · empujon | 50 % | 18.4 | 1419 |

Líneas base, en todos los escenarios:

| Agente | Éxito | Segundos |
|---|---|---|
| sin_entrenar | 0 % | 19.1 |
| aleatorio | 0 % | 2.1 |

## 7. Cinco transiciones reales

Marte, experto, semilla 3.

| t (s) | Observación | Acción | Nuevo estado | Recompensa | Fin |
|---|---|---|---|---|---|
| 0.00 | altura 0.850 m · inclinación 0.0° | objetivos ±1.00 × 0.8 rad | altura 0.851 m · inclinación 0.3° | +2.52 | no |
| 0.02 | altura 0.851 m · inclinación 0.3° | objetivos ±1.00 × 0.8 rad | altura 0.852 m · inclinación 0.7° | +7.22 | no |
| 0.04 | altura 0.852 m · inclinación 0.7° | objetivos ±1.00 × 0.8 rad | altura 0.855 m · inclinación 1.1° | +8.12 | no |
| 0.06 | altura 0.855 m · inclinación 1.1° | objetivos ±1.00 × 0.8 rad | altura 0.860 m · inclinación 1.5° | +8.43 | no |
| 0.08 | altura 0.860 m · inclinación 1.5° | objetivos ±1.00 × 0.8 rad | altura 0.865 m · inclinación 2.1° | +7.95 | no |

## 8. Trampas y decisiones pendientes

- **Trampa:** Memorizar una secuencia: el orden de las órdenes cambia en cada episodio.
- **Pendiente:** Primera mitad del antiguo Exp 7 (pedido del usuario, 2026-11-18): el mismo recorrido y el mismo criterio, sin pisos sueltos. Antecedente: modelos del Exp 7 entrenados con pisos suaves cumplen 34 a 36 de 40 recorridos sobre piso firme. Semilla 1: PPO desde el campeón del Exp 6 (tasa 1e-4, 3 M, con repaso); será el maestro del recorrido para destilar. Semilla 1 (3 M de PPO): la foto final hace 28 de 40 recorridos nuevos (5000+). Como maestro del recorrido rinde más la semilla 4 del Exp 7 (entrenada con pisos suaves, del mismo linaje): 38 y 35 de 40 sobre piso firme (91 %). Semilla 2: parte del campeón del Exp 6 y destila (48 recorridos por ronda, 12 rondas) con la semilla 4 del Exp 7 en el recorrido y el campeón del Exp 6 en lo anterior; luego PPO con la política congelada (400 mil pasos).
