// Panel "Progreso del entrenamiento": curva de aprendizaje + selector de fotos del modelo.
// Dos series en un solo eje (tasa de éxito, 0–100 %):
//   entrenamiento → éxito con exploración, últimos 100 episodios
//   prueba        → éxito sin exploración de cada foto, en escenarios fijos

import { api, vivo } from "./api.js";
const $ = (id) => document.getElementById(id);
const SERIE = { entrenamiento: "#1f9fae", prueba: "#dd6a24" };
const W = 360, H = 200, M = { t: 22, r: 14, b: 34, l: 34 };
const miles = (n) => n.toLocaleString("es");
const pct = (v) => `${Math.round(v * 100)}%`;

export function crearProgreso({ alElegir }) {
  let datos = null;
  let elegido = null;
  const svg = $("grafico-svg");
  const tip = $("grafico-tip");

  const pasos = () => datos.fotos.map((f) => f.paso);
  const x = (p) => M.l + (p / datos.experto) * (W - M.l - M.r);
  const y = (v) => M.t + (1 - v) * (H - M.t - M.b);
  const fotoDe = (p) => datos.fotos.find((f) => f.paso === p);
  const masCercano = (p, lista) => lista.reduce((a, b) => (Math.abs(b - p) < Math.abs(a - p) ? b : a));
  const etiqueta = (p) => (p === datos.experto ? " · experto" : p === datos.aprendiz ? " · aprendiz" : p === 0 ? " · sin entrenar" : "");

  function dibujar() {
    const ancho = W - M.l - M.r;
    let g = "";
    for (const v of [0, 0.5, 1]) {
      g += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}" class="rejilla"/>`;
      g += `<text x="${M.l - 6}" y="${y(v) + 4}" class="eje" text-anchor="end">${pct(v)}</text>`;
    }
    const salto = 10 ** Math.floor(Math.log10(datos.experto));
    const marca = datos.experto / salto >= 3 ? salto : salto / 2;
    for (let p = 0; p <= datos.experto; p += marca) {
      g += `<text x="${x(p)}" y="${H - M.b + 15}" class="eje" text-anchor="middle">${p ? `${p / 1e6} M` : "0"}</text>`;
    }
    g += `<text x="${M.l + ancho / 2}" y="${H - 4}" class="eje" text-anchor="middle">pasos de entrenamiento</text>`;
    g += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(0)}" y2="${y(0)}" class="base"/>`;

    for (const [p, nombre] of [[datos.aprendiz, "aprendiz"], [datos.experto, "experto"]]) {
      const fin = nombre === "experto";
      g += `<line x1="${x(p)}" x2="${x(p)}" y1="${M.t - 4}" y2="${y(0)}" class="hito"/>`;
      g += `<text x="${x(p) + (fin ? -4 : 4)}" y="${M.t - 8}" class="eje" text-anchor="${fin ? "end" : "start"}">${nombre}</text>`;
    }

    const curva = datos.curva.map((f) => `${x(f.paso).toFixed(1)},${y(f.tasa_exito).toFixed(1)}`).join(" ");
    g += `<polyline points="${curva}" fill="none" stroke="${SERIE.entrenamiento}" stroke-width="2" stroke-linejoin="round"/>`;
    const linea = datos.fotos.map((f) => `${x(f.paso).toFixed(1)},${y(f.tasa_exito).toFixed(1)}`).join(" ");
    g += `<polyline points="${linea}" fill="none" stroke="${SERIE.prueba}" stroke-width="2" stroke-linejoin="round"/>`;
    for (const f of datos.fotos) {
      g += `<circle cx="${x(f.paso)}" cy="${y(f.tasa_exito)}" r="4" fill="${SERIE.prueba}" stroke="var(--panel)" stroke-width="2"/>`;
    }
    if (elegido != null) {
      const f = fotoDe(elegido);
      g += `<line x1="${x(elegido)}" x2="${x(elegido)}" y1="${M.t}" y2="${y(0)}" class="elegido"/>`;
      g += `<circle cx="${x(elegido)}" cy="${y(f.tasa_exito)}" r="6" fill="none" stroke="var(--tinta)" stroke-width="2"/>`;
    }
    g += `<line id="cruz" y1="${M.t}" y2="${y(0)}" class="cruz" visibility="hidden"/>`;
    g += `<rect x="${M.l}" y="${M.t}" width="${ancho}" height="${y(0) - M.t}" fill="transparent" id="zona"/>`;
    svg.innerHTML = g;

    const zona = svg.querySelector("#zona");
    const cruz = svg.querySelector("#cruz");
    const pasoDesdeEvento = (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      return masCercano(((px - M.l) / ancho) * datos.experto, pasos());
    };
    zona.onpointermove = (e) => {
      const p = pasoDesdeEvento(e);
      const f = fotoDe(p);
      const c = datos.curva.length ? datos.curva.reduce((a, b) => (Math.abs(b.paso - p) < Math.abs(a.paso - p) ? b : a)) : null;
      cruz.setAttribute("x1", x(p)); cruz.setAttribute("x2", x(p));
      cruz.setAttribute("visibility", "visible");
      tip.innerHTML = `<b>${miles(p)} pasos${etiqueta(p)}</b>
        <span><i style="background:${SERIE.prueba}"></i>Prueba ${pct(f.tasa_exito)}</span>
        <span><i style="background:${SERIE.entrenamiento}"></i>Entrenando ${c ? pct(c.tasa_exito) : "—"}</span>
        <small>clic para ver esta versión</small>`;
      tip.hidden = false;
      const r = svg.getBoundingClientRect();
      tip.style.left = `${Math.min(r.width - 150, Math.max(0, (x(p) / W) * r.width - 75))}px`;
    };
    zona.onpointerleave = () => { cruz.setAttribute("visibility", "hidden"); tip.hidden = true; };
    zona.onclick = (e) => elegir(pasoDesdeEvento(e), vivo());
  }

  function describir(p) {
    const f = fotoDe(p);
    const planetas = datos.planetas.map((n) => `${n} ${pct(f[`exito_${n}`])}`).join(" · ");
    return `<b>${miles(p)} pasos${etiqueta(p)}</b> · ${planetas}`;
  }

  function elegir(p, lanzar) {
    elegido = p;
    $("checkpoint").value = pasos().indexOf(p);
    $("cp-info").innerHTML = describir(p);
    dibujar();
    if (lanzar) alElegir(p);
  }

  function tabla() {
    const cab = datos.planetas.map((n) => `<th>${n}</th>`).join("");
    const filas = datos.fotos.map((f) => `<tr><td>${miles(f.paso)}${etiqueta(f.paso)}</td>
      <td>${pct(f.tasa_exito)}</td>
      ${datos.planetas.map((n) => `<td>${pct(f[`exito_${n}`])}</td>`).join("")}</tr>`).join("");
    $("tabla-progreso").innerHTML = `<thead><tr><th>Pasos</th><th>Éxito</th>${cab}</tr></thead><tbody>${filas}</tbody>`;
  }

  return {
    async cargar(idExp) {
      const r = await api(`/api/exp/${idExp}/progreso`);
      datos = r.ok ? await r.json() : null;
      elegido = null;
      $("progreso").hidden = !datos;
      if (!datos) return;
      $("n-eval").textContent = datos.episodios_por_foto;
      const barra = $("checkpoint");
      barra.max = datos.fotos.length - 1;
      barra.oninput = () => elegir(datos.fotos[Number(barra.value)].paso, false);
      barra.onchange = () => { if (vivo()) alElegir(datos.fotos[Number(barra.value)].paso); };
      tabla();
      this.soltar();
    },
    elegir,
    soltar() {
      if (!datos) return;
      elegido = null;
      $("cp-info").textContent = "Elige un punto del gráfico o mueve el control para ver esa versión.";
      dibujar();
    },
  };
}
