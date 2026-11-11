// Acceso a los datos del visor. Con servidor, cada episodio lo corre MuJoCo al pedirlo.
// En la versión estática (expedicion exportar) los episodios ya vienen calculados en archivos.
export const ESTATICO = Boolean(window.VISOR_ESTATICO);

export function archivoEstatico(ruta) {
  const url = new URL(ruta, "http://x");
  const partes = url.pathname.split("/").filter(Boolean);  // api, exp, id, recurso
  if (partes[1] === "experimentos") return "api/experimentos.json";
  const [, , id, recurso] = partes;
  if (recurso !== "episodio") return `api/${id}/${recurso}.json`;
  const q = url.searchParams;
  return `api/${id}/ep-${q.get("agente").replaceAll(":", "_")}-${q.get("semilla")}-${q.get("perturbacion")}.json`;
}

export function api(ruta) {
  return fetch(ESTATICO ? archivoEstatico(ruta) : ruta);
}
