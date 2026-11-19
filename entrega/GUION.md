# Guion de la presentación (10 minutos, 4 integrantes)

Presentación: https://robot-expedition-tawny.vercel.app/presentacion.html (flechas del teclado para avanzar).
Cada bloque dura unos 2 a 2,5 minutos. Los nombres de los integrantes 2 a 4 los define el equipo.
Regla para todos: hablar de lo que se midió, con los números de la diapositiva; si el profe pregunta algo de otro bloque,
cualquiera debe poder responder (la guía exige que todos entiendan el ambiente, el versionado y el despliegue).

---

## Integrante 1 · Rafael Orozco — Problema, ambiente y niveles (diapositivas 1 a 4, ~2,5 min)

**Diapositiva 1 · Portada.**
«Somos el equipo de Robot Expedition. Nuestro agente es un robot bípedo de 12 articulaciones que aprende, en la gravedad
de Marte y de a una dificultad por vez, a sostenerse, caminar, girar, llegar a balizas y, al final, a explorar entre
rocas. Aprobamos 8 de 9 experimentos; el noveno está en curso y les vamos a mostrar por qué.»

**Diapositiva 2 · Problema.**
«El escenario pedía un robot que llegue a balizas. Elegimos patas en vez de ruedas: es más difícil, pero es el robot que
puede explorar donde una rueda no pasa. El valor no está solo en llegar, sino en un proceso donde cada habilidad nueva se
aprende sin perder las anteriores y cada modelo se puede reproducir, comparar y restaurar. Seguimos la regla del
profesor: una dificultad nueva por experimento.»

**Diapositiva 3 · Ambiente.**
«La física la calcula MuJoCo en Python; la web solo dibuja. El robot observa 58 valores: postura, velocidades, ángulos,
contacto de los pies, la gravedad, la orden y un reloj de marcha. Ve la gravedad pero no el piso: el terreno lo descubre
por cómo responden sus pies. Su acción son 12 ángulos objetivo y un servo por articulación da el torque; con torque directo
no aprendió ni a sostenerse. El episodio termina en fallo si se cae, se inclina más de 40° o choca; en éxito si cumple la
tarea con calidad de marcha de al menos 55 sobre 100; y se trunca si se acaba el tiempo. La recompensa premia seguir la
velocidad y el rumbo pedidos con una marcha humana, y castiga vibrar, arrastrar el pie y caerse.»

**Diapositiva 4 · Evolución de la dificultad.**
«Nivel 1: de pie, caminar y caminar bien. Nivel 2: terreno difícil, esquina, curva y un recorrido con órdenes al azar.
Nivel 3: llegar a balizas y explorar entre rocas. Cada experimento parte del campeón anterior y, desde el quinto, solo
aprueba si sigue aprobando todos los exámenes anteriores. Esa regla nació porque en los experimentos 2 a 4 el robot se
olvidaba de sostenerse.»

---

## Integrante 2 — Algoritmo, hipótesis y lo que no funcionó (diapositivas 5 a 7, ~2,5 min)

**Diapositiva 5 · Algoritmo.**
«Usamos PPO de Stable-Baselines3. El problema real fue el olvido: al aprender la curva, el terreno bajó de 83 % a 42 %.
La solución fue destilar: partir del campeón anterior, que sabe lo viejo, y enseñarle lo nuevo con maestros del mismo
linaje. Elegimos modelos con 40 episodios nuevos y confirmamos con otros 40; el examen fijo nunca se usa para elegir.
Como referencias: un agente aleatorio y una regla sin red no caminan; el modelo aprendido se sostiene 20 de 24 veces.»

**Diapositiva 6 · Hipótesis del Exp 8.**
«Para llegar a balizas, nuestra hipótesis fue que el robot ya sabía todo: el campeón anterior, sin reentrenar, llega a las
tres balizas en 37 de 40 episodios. Probamos un candidato con tres semillas de ajuste fino y las tres empeoraron, 24, 25 y
34 de 40, y además olvidaron el terreno. Decisión: quedarnos con la línea base. El rechazo también es evidencia.»

**Diapositiva 7 · Exp 9, exploración entre rocas.**
«El noveno agrega rocas que no se pueden cruzar, arena y grava en la ruta y tres balizas repartidas en un campo de 7 por 7
metros. Para esquivar hay que ver: separamos navegar de caminar. Un navegador nuevo, con 15 sensores de distancia y la
baliza, elige cada segundo hacia dónde ir, y el caminante del experimento 8 lo ejecuta. Es una familia de modelos nueva.
Ir directo a la baliza choca casi siempre: 0 de 24. Nuestro mejor navegador llega en alrededor del 21 % (10 de 48 episodios nuevos) de los mundos. Encontramos
dos errores que corregimos: las rocas se podían atravesar en MuJoCo y el pie del robot llega a 0,67 m de su centro.
No aprueba aún: el criterio es 60 %.»

---

## Integrante 3 — Incidente, versionado y pipeline (diapositivas 8 a 10, ~2,5 min)

**Diapositiva 8 · Incidente controlado.**
«Cambiamos la condición de operación: el recorrido del experimento 7 sobre grava, arena y barro. El campeón bajó de 92 %
a 25 %. La causa medida fue girar sobre barro. La intervención, entrenar con pisos de intensidad variable, recuperó hasta
65–70 %, pero ningún candidato cumplía el examen sin olvidar: la rechazamos y la documentamos como límite.»

**Diapositiva 9 · Versionado.**
«Todo deja huella. Código y robot en git, con un tag por experimento. Escenarios de examen y trayectorias por episodio en
DVC. Cada semilla es un run de MLflow con su hipótesis, parámetros y commit. Cada modelo tiene un manifiesto con su
SHA-256, su contrato de entrada y salida y el modelo del que partió. Verificamos la reproducción desde un clon limpio: los
modelos bajan con el mismo SHA-256 y la evaluación da el mismo resultado.»

**Diapositiva 10 · Pipeline, monitoreo y rollback.**
«Prefect orquesta ocho etapas: validar, pruebas, entrenar o reutilizar, evaluar, registrar, seleccionar, publicar y
verificar; DVC decide qué recalcular. Hicimos una prueba de rollback: promovimos por error un candidato rechazado, el
monitoreo vio que bajaba de 15 a 7 éxitos en 20, y el rollback restauró la versión anterior comprobando su SHA-256.»

---

## Integrante 4 — Despliegue, demostración y cierre (diapositivas 11 a 13, ~2,5 min)

**Diapositiva 11 · Despliegue.**
«Todo vive en una sola URL de Vercel. El visor muestra los experimentos, cómo aprendió cada uno y si olvidó algo. Lo
importante: el botón Lanzar episodio corre un episodio nuevo en MuJoCo en ese momento, en una función de Python en
Vercel. PyTorch no cabe allí, así que exportamos la red a numpy y una prueba comprueba que actúa igual. Cada episodio dice
si es evaluación en vivo, replay grabado o error del servicio.»

**Diapositiva 12 · Demostración** (en vivo, ~1 min).
1. Abrir el Exp 8 y pulsar «Lanzar episodio» con una semilla cualquiera: el robot va a las balizas numeradas 1, 2 y 3.
2. Abrir el Exp 3 y lanzar un episodio: es un modelo histórico corriendo con sus reglas originales.
3. Abrir el Exp 9 y lanzar uno: el navegador rodea las rocas.
4. Mostrar la página de registro: cada modelo con su run, commit y SHA-256.

**Diapositiva 13 · Cierre.**
«Límites: el navegador llega en alrededor del 21 % (10 de 48 episodios nuevos) de los mundos con rocas; girar sobre barro sigue sin resolverse; los pisos son
fuerzas sobre los pies, no suelo deformable. Aprendizajes: aprender sin olvidar hay que medirlo en cada modelo, y agregar
una sola cosa por experimento importa: cuando el experimento 7 agregó dos, se estancó. Siguiente hipótesis: seguir
ajustando el navegador dentro de MuJoCo, que ya duplicó sus llegadas en el mapa nuevo. Gracias.»

---

## Preguntas probables y quién responde

| Pregunta | Responde | Dónde está la evidencia |
|---|---|---|
| ¿Cómo sé que el modelo servido es el que dicen? | Integrante 3 | `/sim/api/estado` (SHA-256) y `manifests/` |
| ¿Por qué no aprueba el Exp 9? | Integrante 2 | `docs/serie-marte.md`, MLflow `exp-109-navegador` |
| ¿Cómo reconstruyo una evaluación? | Integrante 3 | `entrega/ENTREGA.md`, «Cómo revisarlo» |
| ¿Qué observa el robot y qué hace? | Integrante 1 | `docs/ficha-ambiente.md` |
| ¿El replay es real? | Integrante 4 | la etiqueta del visor dice replay o en vivo |
