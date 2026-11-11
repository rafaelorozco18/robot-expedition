// Acceso a los datos del visor. Con servidor, cada episodio lo corre MuJoCo al pedirlo.
// En la versión estática (expedicion exportar) cada experimento viene en un solo archivo
// api/<id>.json con todas sus respuestas ya calculadas.
export const ESTATICO = Boolean(window.VISOR_ESTATICO);

const paquetes = {};

export function claveEstatica(ruta) {
  const url = new URL(ruta, "http://x");
  const partes = url.pathname.split("/").filter(Boolean);  // api, exp, id, recurso
  if (partes[1] === "experimentos") return ["catalogo", "experimentos"];
  const [, , id, recurso] = partes;
  if (recurso !== "episodio") return [id, recurso];
  const q = url.searchParams;
  return [id, `ep-${q.get("agente").replaceAll(":", "_")}-${q.get("semilla")}-${q.get("perturbacion")}`];
}

async function desdePaquete(ruta) {
  const [paquete, clave] = claveEstatica(ruta);
  paquetes[paquete] ??= fetch(`api/${paquete}.json`).then((r) => (r.ok ? r.json() : {}));
  const datos = (await paquetes[paquete])[clave];
  return datos === undefined
    ? new Response(JSON.stringify({ error: "Esta vista no está incluida en la versión publicada." }), { status: 404 })
    : new Response(JSON.stringify(datos), { status: 200 });
}

export function api(ruta) {
  return ESTATICO ? desdePaquete(ruta) : fetch(ruta);
}
