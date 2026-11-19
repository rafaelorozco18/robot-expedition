# Informe breve · Robot Expedition

Universidad Externado de Colombia · MLOps (Visualización 2) · Escenario: **Robot Expedition**.

## 1. Problema y decisión principal

El escenario pide un robot que llegue a balizas. Decidimos hacerlo con un **robot bípedo de 12 articulaciones en 3D, en
la gravedad de Marte**, en lugar de un robot con ruedas. Es más difícil de entrenar, pero es el tipo de robot que puede
explorar terreno donde una rueda no pasa. Por eso la misión se aprende por partes, como pidió el docente: **una
dificultad nueva por experimento**, siempre partiendo del campeón anterior y sin olvidar lo aprendido.

## 2. Decisiones técnicas

| Decisión | Por qué | Evidencia |
|---|---|---|
| MuJoCo + Gymnasium; Python es la autoridad | Física de contacto realista; la web solo dibuja cuadros | `expedicion/ambiente.py`, `docs/ficha-ambiente.md` |
| La red pide ángulos y un servo PD da el torque | Con torque directo PPO no aprendió a sostenerse en 500 mil pasos | `docs/serie-marte.md` |
| PPO (Stable-Baselines3), CPU, 4 procesos | Referencia del curso; recompensa escalada ×0,05 para que el crítico no sature | `experimentos/base.yaml` |
| Aprobar exige no olvidar (`sin_olvidar`), **desde el Exp 5** | En los Exps 2 a 4 los campeones perdían De pie (0 a 42 %), y PPO desarma lo viejo al aprender lo nuevo (el Exp 6 bajó el terreno a 42 %). El examen del Exp 2 queda fuera: la marcha del Exp 3 reemplazó su ritmo | `metrics/exp-NNN/regresion.json`, `docs/comparacion-experimentos.md` |
| Destilación DAgger desde el campeón anterior | Partir del modelo que sabe lo viejo y enseñarle lo nuevo con maestros del mismo linaje | Exps 5, 6 y 7: aprueban sin olvidar |
| Elegir con episodios nuevos (5000+), confirmar con otros (3000+) | El examen fijo de 12 episodios es ruidoso; nunca se usa para elegir | `scripts/medir40.py` |
| Evaluar con el ruido de la política, sembrado por episodio | En la serie la media sola no se sostiene; cada episodio es repetible | `expedicion/evaluar.py` |
| Partir el Exp 7 en dos (decisión del equipo) | Agregaba dos cosas a la vez: órdenes cambiantes y pisos sueltos | Exp 7a aprobado; Exp 7 de terreno como incidente |
| Evaluación en vivo en Vercel sin PyTorch | PyTorch no cabe en una función; el actor se exporta a numpy y se prueba su equivalencia | `tests/test_politica_numpy.py` |

## 3. Resultados

Examen oficial: 12 episodios fijos en la condición que decide la aprobación, más 12 por cada examen anterior.

| Exp | Pregunta | Campeón | Examen propio | Mínimo |
|---|---|---|---|---|
| 1 | De pie | semilla 0 | 83 % | 80 % |
| 2 | Caminar 10 m | semilla 1 | 100 % | 80 % |
| 3 | Caminar bien | semilla 1 | 100 % | 80 % |
| 4 | Terreno difícil | semilla 0 | 75 % | 75 % |
| 5 | Esquina | semilla 25 | 100 % | 80 % |
| 6 | Curva | semilla 5 | 75 % | 75 % |
| 7 | Recorrido (`exp-107a`) | semilla 3 | 100 % | 70 % |
| 8 | Balizas | semilla 1 | 83 % | 70 % |

**Referencias (`data/<exp>/trayectorias.jsonl`):** el agente aleatorio y la regla sin red (el servo sosteniendo la
postura) no completan ninguna tarea de marcha (0 de 24), y la regla solo aguanta de pie 3 de 24 veces. El modelo
aprendido del Exp 1 lo logra 20 de 24.

### Comparación principal (Exp 8)

- **Hipótesis de la línea base:** el campeón del Exp 7a ya sabe girar, caminar recto y en curva, así que llegar a balizas
  no exige movimientos nuevos. Sin entrenar, llega a las 3 balizas en **37 de 40** episodios nuevos (5000+).
- **Hipótesis del candidato:** un ajuste fino con PPO en la tarea (tasa 3e-5, 1 M de pasos, con repaso) reduce las caídas.
  Tres semillas de entrenamiento independientes: **24, 25 y 34 de 40**. Las tres empeoran: el ajuste fino perturba una
  marcha que ya era buena. En el examen oficial sacan 50, 75 y 58 % en balizas (línea base: 83 %) y además **olvidan el
  terreno** (8, 33 y 0 %; mínimo 75 %) y De pie (75 %; mínimo 80 %).
- **Decisión: rechazar el candidato y quedarse con la línea base**, que además no olvida ningún examen anterior.
  Todos los candidatos quedan conservados en MLflow, DVC y la tabla de comparación.

### Exp 9: exploración entre rocas (en curso)

Rocas de 0,35 a 0,70 m que no se pueden cruzar, parches de arena, grava y barro y tres balizas. Diseño jerárquico: un
**navegador** nuevo (15 sensores de distancia y la baliza → 7 direcciones, una decisión por segundo) aprende la ruta y el
caminante del Exp 8 la ejecuta. En MuJoCo, con 24 episodios nuevos:

- Referencias: ir directo a la baliza **0 de 24** (21 choques); navegador aleatorio **0 de 24**.
- Navegador base 1 de 24 → variante «suave» (castiga invertir giros) 5 de 24, las caídas bajan de 12 a 3 → variante
  «robusta» (alcance real del robot y física aleatorizada) **6 de 24**, los choques bajan de 16 a 5. Tres semillas de la
  robusta: 6, 3 y 2 de 24.
- Ajustar el caminante con PPO en la exploración no redujo las caídas.
- Dos hallazgos de la noche: las rocas se atravesaban (MuJoCo no actualiza las envolventes de geoms fijos movidos;
  ahora son cuerpos mocap) y el robot ocupa más de lo supuesto (un pie llegó a 0,67 m del centro).
- **No aprueba** (25 % frente a un mínimo de 60 % fijado antes de entrenar). Siguiente hipótesis: combinar las dos
  mejoras y ajustar el navegador directamente en MuJoCo.

### Incidente controlado

Pisos sueltos (grava, arena y barro) bajo el recorrido del Exp 7: el campeón servido baja de **92 % a 25 %**. La
intervención (pisos de intensidad variable al entrenar) sube a **65–70 %**, pero ningún candidato cumple el examen y a la vez
no olvida: se rechaza y se documenta como límite. Detalle en `docs/incidente-y-rollback.md`.

## 4. Límites conocidos

- El robot no ve obstáculos: el Exp 8 no tiene obstáculos y la ruta hacia la baliza la calcula el ambiente.
- Girar sobre barro sigue sin resolverse (solo barro: 9 de 40 recorridos).
- Arena, grava y barro son fuerzas sobre los pies, no suelo deformable. Solo Marte.
- El examen fijo es pequeño (12 episodios): por eso se valida con 40 + 40 episodios nuevos.
- La función de Vercel guarda su monitoreo en memoria: se reinicia cuando Vercel recicla la instancia.
- El frontend es JavaScript con Three.js sin Vite ni TypeScript: no hay paso de compilación (decisión para servir lo
  mismo en local, en el enlace de Claude y en Vercel).

## 5. Contribuciones

| Integrante | Contribución |
|---|---|
| Rafael Orozco | Diseño del ambiente y la serie, entrenamiento de los experimentos, despliegue |
| _(completar)_ | |
| _(completar)_ | |
| _(completar)_ | |

Usamos un asistente de código (Claude Code) para implementar y documentar. Las decisiones, los criterios de aprobación
y los cambios de diseño (por ejemplo, partir el Exp 7 y definir el Exp 8) fueron del equipo, y cada resultado del
informe se puede verificar con los archivos citados.
