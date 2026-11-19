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

// Evaluación en vivo: si la página define window.API_REMOTA (servidor Python con MuJoCo, p. ej. el Space de
// Hugging Face), los episodios que pide el usuario se corren allí. Todo lo demás sale del paquete estático.
export const API_REMOTA = (window.API_REMOTA || "").replace(/\/$/, "");
let enVivo = !ESTATICO;
let estadoRemoto = null;
export const vivo = () => enVivo;
export const servidor = () => estadoRemoto;

export async function conectar() {
  if (!ESTATICO || !API_REMOTA) return enVivo;
  try {
    const r = await fetch(`${API_REMOTA}/api/estado`, { signal: AbortSignal.timeout(25000) });
    enVivo = r.ok;
    estadoRemoto = r.ok ? await r.json() : null;
  } catch {
    enVivo = false;
  }
  return enVivo;
}

// replay: true pide la versión grabada aunque haya servidor (etapas de aprendizaje, apertura).
export async function api(ruta, { replay = false } = {}) {
  if (!ESTATICO) return fetch(ruta);
  if (enVivo && !replay && ruta.includes("/episodio")) {
    try {
      return await fetch(API_REMOTA + ruta, { signal: AbortSignal.timeout(180000) });
    } catch (e) {
      return new Response(JSON.stringify({ error: `El servidor de evaluación no respondió (${e.message}). No se muestra un replay en su lugar.` }), { status: 503 });
    }
  }
  return desdePaquete(ruta);
}
