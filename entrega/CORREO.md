# Correo de entrega (borrador para enviar al docente)

Los campos entre corchetes los completa el equipo antes de enviar (grupo, nombres completos y el usuario de GitHub
del docente, si lo pide). Todo lo demás ya está verificado.

---

**Para:** Julián Zuluaga
**Asunto:** MLOps · Entrega final · Grupo [A o B] · Robot Expedition

Profesor Julián, buenos días.

Le enviamos la entrega final del proyecto de MLOps.

**1. Grupo, escenario e integrantes**
- Grupo: [A o B]
- Escenario: Robot Expedition
- Integrantes: Rafael Orozco [segundo apellido], [nombre completo], [nombre completo], [nombre completo]

**2. Repositorio**
- https://github.com/rafaelorozco18/robot-expedition
- Es privado. [Ya lo invitamos como colaborador de lectura con su usuario de GitHub «[usuario]»] / [Si nos indica su
  usuario de GitHub, lo invitamos de inmediato.]

**3. Aplicación y registro de experimentos**
- Aplicación (Vercel): https://robot-expedition-tawny.vercel.app
- Registro de experimentos y modelos (exportado de MLflow, con manifiestos): https://robot-expedition-tawny.vercel.app/registro.html
- Versión servida y monitoreo de la API: https://robot-expedition-tawny.vercel.app/sim/api/estado
- Base completa de MLflow (`mlflow.db` y artefactos): release `mlflow-registro` del repositorio. Modelos y escenarios (DVC):
  releases `datos-dvc-*`, se descargan con `bash scripts/bajar_modelos.sh`.
- No hace falta instalar nada ni usar contraseñas para revisar la aplicación.

**4. Versión entregada**
- Release y tag: `entrega-final`
- Commit: `[SHA completo: descripción de la release entrega-final]`
- Modelo recomendado: Exp 8 «Llegar a las balizas», `exp-108` semilla 1, run de MLflow `a6328691a8d14623a3b879d2b365f7c4`, `robot-exp-108` alias
  `campeon`. Manifiesto: `manifests/exp-108-semilla-1.json`.
- Modelo histórico (ejemplo): Exp 3 «Caminar bien», `exp-103` semilla 1, run `5288517fb4ff4dd58116e3ae442017c7`, ambiente `robots/bipedo-v2.xml`
  + tarea «marcha». Manifiesto: `manifests/exp-103-semilla-1.json`. Se evalúa en la aplicación abriendo el Exp 3 y
  pulsando «Lanzar episodio».

**5. Dónde está cada cosa en el repositorio**
- README (misión, arquitectura, instalación, ejecución, reproducción): `README.md`
- Mapa de la entrega: `entrega/ENTREGA.md`
- Comparación de experimentos y corridas: `docs/comparacion-experimentos.md`
- Manifiestos de modelos: `manifests/`
- Ficha del ambiente y tres niveles: `docs/ficha-ambiente.md`
- Incidente, intervención y prueba de rollback: `docs/incidente-y-rollback.md`
- Pipeline (Prefect): `pipelines/flujo.py`, con sus ejecuciones en `pipelines/ejecuciones/`
- Informe breve: `docs/informe.md`

**6. Presentación y limitaciones**
- Presentación: https://robot-expedition-tawny.vercel.app/presentacion.html
- Limitaciones conocidas: el robot no tiene sensores de obstáculos (la ruta a la baliza la calcula el ambiente); girar
  sobre barro sigue sin resolverse (documentado como incidente); el frontend es JavaScript con Three.js, sin Vite ni
  TypeScript; el monitoreo de la función de Vercel se reinicia cuando Vercel recicla la instancia.

Quedamos atentos.

[Firmas]
