// Panel "Progreso del entrenamiento": curva de aprendizaje + selector de checkpoints.
// Dos series en un solo eje (tasa de misión, 0–100 %):
//   entrenamiento  → éxito con exploración ε, ventana móvil de 500 episodios
//   evaluación     → éxito voraz (sin exploración) de cada foto de la tabla Q

const $ = (id) => document.getElementById(id);
const SERIE = { entrenamiento: "#1f9fae", evaluacion: "#dd6a24" };
const W = 360, H = 200, M = { t: 22, r: 14, b: 34, l: 34 };
const miles = (n) => n.toLocaleString("es");
const pct = (v) => `${Math.round(v * 100)}%`;

export function crearProgreso({ alElegir }) {
  let datos = null;
  let elegido = null;
  const svg = $("grafico-svg");
  const tip = $("grafico-tip");

  const x = (ep) => M.l + (ep / (datos.experto || 1)) * (W - M.l - M.r);
  const y = (v) => M.t + (1 - v) * (H - M.t - M.b);
  const evalDe = (ep) => datos.evaluacion.find((f) => f.episodio === ep);
  const masCercano = (ep) => datos.checkpoints.reduce((a, b) => (Math.abs(b - ep) < Math.abs(a - ep) ? b : a));
  const etiquetaVersion = (ep) => (ep === datos.experto ? " · experto" : ep === datos.aprendiz ? " · aprendiz" : ep === 0 ? " · sin entrenar" : "");

  function dibujar() {
    const ancho = W - M.l - M.r;
    let g = "";
    for (const v of [0, 0.5, 1]) {
      g += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}" class="rejilla"/>`;
      g += `<text x="${M.l - 6}" y="${y(v) + 4}" class="eje" text-anchor="end">${pct(v)}</text>`;
    }
    const pasoX = datos.experto >= 20000 ? 10000 : 5000;
    for (let ep = 0; ep <= datos.experto; ep += pasoX) {
      g += `<text x="${x(ep)}" y="${H - M.b + 15}" class="eje" text-anchor="middle">${ep ? `${ep / 1000}k` : "0"}</text>`;
    }
    g += `<text x="${M.l + ancho / 2}" y="${H - 4}" class="eje" text-anchor="middle">episodios de entrenamiento</text>`;
    g += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(0)}" y2="${y(0)}" class="base"/>`;

    // hitos: aprendiz y experto
    for (const [ep, nombre] of [[datos.aprendiz, "aprendiz"], [datos.experto, "experto"]]) {
      if (ep == null) continue;
      g += `<line x1="${x(ep)}" x2="${x(ep)}" y1="${M.t - 4}" y2="${y(0)}" class="hito"/>`;
      g += `<text x="${x(ep) + (nombre === "experto" ? -4 : 4)}" y="${M.t - 8}" class="eje" text-anchor="${nombre === "experto" ? "end" : "start"}">${nombre}</text>`;
    }

    const curva = datos.curva.map((f) => `${x(f.episodio).toFixed(1)},${y(f.tasa_exito).toFixed(1)}`).join(" ");
    g += `<polyline points="${curva}" fill="none" stroke="${SERIE.entrenamiento}" stroke-width="2" stroke-linejoin="round"/>`;
    const ev = datos.evaluacion.map((f) => `${x(f.episodio).toFixed(1)},${y(f["ninguno.tasa_mision"]).toFixed(1)}`).join(" ");
    g += `<polyline points="${ev}" fill="none" stroke="${SERIE.evaluacion}" stroke-width="2" stroke-linejoin="round"/>`;
    for (const f of datos.evaluacion) {
      g += `<circle cx="${x(f.episodio)}" cy="${y(f["ninguno.tasa_mision"])}" r="4" fill="${SERIE.evaluacion}" stroke="var(--panel)" stroke-width="2"/>`;
    }

    // checkpoint elegido
    if (elegido != null) {
      const f = evalDe(elegido);
      g += `<line x1="${x(elegido)}" x2="${x(elegido)}" y1="${M.t}" y2="${y(0)}" class="elegido"/>`;
      if (f) g += `<circle cx="${x(elegido)}" cy="${y(f["ninguno.tasa_mision"])}" r="6" fill="none" stroke="var(--tinta)" stroke-width="2"/>`;
    }
    g += `<line id="cruz" y1="${M.t}" y2="${y(0)}" class="cruz" visibility="hidden"/>`;
    g += `<rect x="${M.l}" y="${M.t}" width="${ancho}" height="${y(0) - M.t}" fill="transparent" id="zona"/>`;
    svg.innerHTML = g;

    const zona = svg.querySelector("#zona");
    const cruz = svg.querySelector("#cruz");
    const epDesdeEvento = (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      return Math.max(0, Math.min(datos.experto, ((px - M.l) / ancho) * datos.experto));
    };
    zona.onpointermove = (e) => {
      const ep = masCercano(epDesdeEvento(e));
      const f = evalDe(ep);
      const c = datos.curva.reduce((a, b) => (Math.abs(b.episodio - ep) < Math.abs(a.episodio - ep) ? b : a), datos.curva[0]);
      cruz.setAttribute("x1", x(ep)); cruz.setAttribute("x2", x(ep));
      cruz.setAttribute("visibility", "visible");
      tip.innerHTML = `<b>Episodio ${miles(ep)}${etiquetaVersion(ep)}</b>
        <span><i style="background:${SERIE.evaluacion}"></i>Evaluación ${f ? pct(f["ninguno.tasa_mision"]) : "—"}</span>
        <span><i style="background:${SERIE.entrenamiento}"></i>Entrenando ${ep ? pct(c.tasa_exito) : "—"}</span>
        <small>clic para ver esta versión</small>`;
      tip.hidden = false;
      const r = svg.getBoundingClientRect();
      const izq = (x(ep) / W) * r.width;
      tip.style.left = `${Math.min(r.width - 150, Math.max(0, izq - 75))}px`;
    };
    zona.onpointerleave = () => { cruz.setAttribute("visibility", "hidden"); tip.hidden = true; };
    zona.onclick = (e) => elegir(masCercano(epDesdeEvento(e)), true);
  }

  function describir(ep) {
    const f = evalDe(ep);
    if (!f) return `Episodio ${miles(ep)}`;
    return `<b>Episodio ${miles(ep)}${etiquetaVersion(ep)}</b> · misión ${pct(f["ninguno.tasa_mision"])}` +
      ` · balizas ${f["ninguno.balizas_medias"].toFixed(1)}/2 · batería final ${f["ninguno.bateria_final_exito"].toFixed(0)}%` +
      ` · choques ${f["ninguno.choques_medios"].toFixed(1)} · caídas ${pct(f["ninguno.tasa_caida"])}` +
      ` · con derrumbe ${pct(f["corredor_bloqueado.tasa_mision"])}`;
  }

  function elegir(ep, lanzar) {
    elegido = ep;
    $("checkpoint").value = datos.checkpoints.indexOf(ep);
    $("cp-info").innerHTML = describir(ep);
    dibujar();
    if (lanzar) alElegir(ep);
  }

  function tabla() {
    const filas = datos.evaluacion.map((f) => `<tr><td>${miles(f.episodio)}${etiquetaVersion(f.episodio)}</td>
      <td>${pct(f["ninguno.tasa_mision"])}</td><td>${f["ninguno.balizas_medias"].toFixed(2)}</td>
      <td>${f["ninguno.bateria_final_exito"].toFixed(0)}%</td><td>${f["ninguno.choques_medios"].toFixed(1)}</td>
      <td>${pct(f["corredor_bloqueado.tasa_mision"])}</td></tr>`).join("");
    $("tabla-progreso").innerHTML = `<thead><tr><th>Episodio</th><th>Misión</th><th>Balizas</th><th>Batería</th><th>Choques</th><th>Derrumbe</th></tr></thead><tbody>${filas}</tbody>`;
  }

  return {
    async cargar() {
      datos = await (await fetch("/api/progreso")).json();
      const listo = datos.checkpoints.length && datos.evaluacion.length && datos.curva.length;
      $("progreso").hidden = !listo;
      if (!listo) return false;
      $("n-eval").textContent = datos.episodios_por_checkpoint;
      const barra = $("checkpoint");
      barra.max = datos.checkpoints.length - 1;
      barra.oninput = () => elegir(datos.checkpoints[Number(barra.value)], false);
      barra.onchange = () => alElegir(datos.checkpoints[Number(barra.value)]);
      tabla();
      elegir(datos.experto, false);
      return true;
    },
    elegir,
    soltar() { elegido = null; $("cp-info").innerHTML = "Elige un punto del gráfico o mueve el control para ver esa versión."; dibujar(); },
    // Recorrido: ~8 fotos repartidas desde 0 hasta el experto.
    recorrido() {
      const cps = datos.checkpoints;
      const n = Math.min(8, cps.length);
      return [...new Set(Array.from({ length: n }, (_, i) => cps[Math.round((i * (cps.length - 1)) / (n - 1))]))];
    },
  };
}
