// Visor 3D de Robot Expedition. Solo dibuja: cada episodio lo corre MuJoCo en Python
// (/api/exp/<id>/episodio) y aquí se reproducen sus cuadros.
import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { crearProgreso } from "./progreso.js";
import { crearPlaneta, TEMAS } from "./planetas.js";

const $ = (id) => document.getElementById(id);

const AGENTES = {
  experto: { titulo: "Experto", color: "#39c16c" },
  aprendiz: { titulo: "Aprendiz", color: "#f2b632" },
  sin_entrenar: { titulo: "Sin entrenar", color: "#3fd0e0" },
  aleatorio: { titulo: "Aleatorio", color: "#ff5a5f" },
};
const ICONO = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg>',
  pausa: '<svg viewBox="0 0 24 24"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>',
};
const botonPlay = (jugando) => { $("btn-play").innerHTML = jugando ? ICONO.pausa : ICONO.play; };
const ETIQUETA_PERTURBACION = { ninguna: "ninguna", empujon: "empujón" };
const NOMBRE_MOTOR = {
  cadera_roll: "Cadera (lateral)", cadera_pitch: "Cadera (frontal)", rodilla: "Rodilla",
  cadera_yaw: "Cadera (giro)", tobillo_pitch: "Tobillo (frontal)", tobillo_roll: "Tobillo (lateral)",
};
const NOMBRE_RECOMPENSA = {
  vivo: "Sigue en pie", altura: "Conserva la altura", postura: "Conserva la postura", quieto: "Torso quieto",
  esfuerzo: "Costo de torque", suavidad: "Costo de movimientos bruscos", caida: "Caída",
  pies: "Pies en su sitio", peso: "Peso sobre el pie ordenado", levantar: "Levanta el pie", apoyo: "Pie de apoyo firme",
  velocidad: "Sigue la velocidad", erguido: "Torso erguido", rumbo: "Conserva el rumbo",
  reloj: "Alterna las piernas", paso: "Despega el pie", giro: "Evita giros bruscos",
};

const estado = {
  catalogo: [], exp: null, mundo: null,
  agente: "experto", planeta: "tierra", perturbacion: "ninguna",
  episodio: null, i: 0, tiempo: 0, play: false, velocidad: 1, finClip: null,
};

// ------------------------------------------------------------------ escena
const lienzo = $("lienzo");
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(46, 1, 0.05, 2000);
const controls = new OrbitControls(camera, lienzo);
// El objetivo va desplazado para dejar libre el título, arriba a la izquierda.
controls.target.set(-0.35, 0.72, 0);
camera.position.set(1.6, 1.25, 3.9);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 1.2;
controls.maxDistance = 30;

const hemi = new THREE.HemisphereLight(0xdfefff, 0x3b2c20, 0.9);
scene.add(hemi);
const sol = new THREE.DirectionalLight(0xffffff, 1.8);
sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
Object.assign(sol.shadow.camera, { left: -4, right: 4, top: 4, bottom: -4, near: 1, far: 60 });
sol.shadow.bias = -0.0004;
scene.add(sol);
scene.add(sol.target);
const planeta = crearPlaneta(scene, { sol, hemi });

// Campo de pruebas: plano, con rejilla de 1 m. MuJoCo tiene el piso en z = 0.
const grupoCampo = new THREE.Group();
scene.add(grupoCampo);
function construirCampo() {
  grupoCampo.traverse((o) => { o.geometry?.dispose(); });
  grupoCampo.clear();
  const tema = planeta.tema();
  const lado = new THREE.MeshStandardMaterial({ color: tema.subsuelo });
  const tapa = new THREE.MeshStandardMaterial({ color: tema.colores["."], map: planeta.texRuido, roughness: 0.95 });
  const losa = new THREE.Mesh(new THREE.BoxGeometry(24, 3, 12), [lado, lado, tapa, lado, lado, lado]);
  losa.position.set(6, -1.5, 0);  // la pista se extiende hacia +x, por donde camina
  losa.receiveShadow = true;
  grupoCampo.add(losa);
  const lineas = [];
  for (let i = -6; i <= 18; i++) lineas.push(i, 0.003, -6, i, 0.003, 6);
  for (let j = -6; j <= 6; j++) lineas.push(-6, 0.003, j, 18, 0.003, j);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(lineas, 3));
  grupoCampo.add(new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.14 })));
}

// Tramos de piso del episodio, tal como los sorteó el simulador (x de MuJoCo = x del visor).
const grupoTramos = new THREE.Group();
scene.add(grupoTramos);
function dibujarTramos(tramos) {
  grupoTramos.traverse((o) => { o.geometry?.dispose(); });
  grupoTramos.clear();
  const tema = planeta.tema();
  const color = { arena: tema.colores.a, barro: tema.colores.b, barro_profundo: tema.charco.color, hielo: tema.colores.h, grava: tema.roca };
  for (const [x0, x1, tipo] of tramos) {
    const malla = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, 0.02, 4), new THREE.MeshStandardMaterial({
      color: color[tipo], map: planeta.texRuido, roughness: tipo === "hielo" ? 0.15 : 0.95,
    }));
    malla.position.set((x0 + x1) / 2, 0.0, 0);
    malla.receiveShadow = true;
    grupoTramos.add(malla);
  }
}

// ------------------------------------------------------------------- robot
// Se construye desde la geometría que entrega el simulador. MuJoCo usa z arriba:
// el grupo raíz gira −90° en x para pasar a y arriba.
const raizRobot = new THREE.Group();
raizRobot.rotation.x = -Math.PI / 2;
scene.add(raizRobot);
let cuerpos = [];

function construirRobot(robot) {
  raizRobot.traverse((o) => { o.geometry?.dispose(); });
  raizRobot.clear();
  const n = Math.max(...robot.geoms.map((g) => g.cuerpo)) + 1;
  cuerpos = Array.from({ length: n }, () => { const g = new THREE.Group(); raizRobot.add(g); return g; });
  for (const g of robot.geoms) {
    let geo;
    if (g.tipo === "esfera") geo = new THREE.SphereGeometry(g.tam[0], 20, 14);
    else if (g.tipo === "capsula") { geo = new THREE.CapsuleGeometry(g.tam[0], g.tam[1] * 2, 6, 14); geo.rotateX(Math.PI / 2); }
    else geo = new THREE.BoxGeometry(g.tam[0] * 2, g.tam[1] * 2, g.tam[2] * 2);
    const color = new THREE.Color().setRGB(...g.rgba.slice(0, 3), THREE.SRGBColorSpace);
    const malla = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.5 }));
    malla.position.set(...g.pos);
    malla.quaternion.set(g.quat[1], g.quat[2], g.quat[3], g.quat[0]);
    malla.castShadow = true;
    cuerpos[g.cuerpo].add(malla);
  }
}

const qA = new THREE.Quaternion(), qB = new THREE.Quaternion();
function posarRobot(A, B, f) {
  cuerpos.forEach((grupo, i) => {
    const a = A.cuerpos[i], b = B.cuerpos[i];
    grupo.position.set(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f);
    qA.set(a[4], a[5], a[6], a[3]);
    qB.set(b[4], b[5], b[6], b[3]);
    grupo.quaternion.copy(qA).slerp(qB, f);
  });
}

// La cámara sigue al robot si se aleja; hará falta desde que camine.
const previo = new THREE.Vector3();
function seguirRobot(dt) {
  const t = cuerpos[0]?.position;
  if (!t) return;
  const suavizado = Math.min(1, dt * 4 * Math.max(1, estado.velocidad));
  const delta = new THREE.Vector3(t.x, 0, -t.y).sub(previo).multiplyScalar(suavizado);
  previo.add(delta);
  controls.target.add(delta);
  camera.position.add(delta);
}

// ------------------------------------------------------------------- panel
function construirSelector() {
  const cont = $("selector");
  cont.innerHTML = "";
  const aprobados = estado.catalogo.filter((e) => e.aprobado).length;
  const intentados = estado.catalogo.filter((e) => e.entrenado).length;
  $("avance").innerHTML = `<b>${aprobados}</b> de ${estado.catalogo.length} experimentos aprobados · ${intentados} entrenados`;
  estado.catalogo.forEach((e, n) => {
    const b = document.createElement("button");
    b.className = `chip-exp ${e.estado} ${e.aprobado ? "aprobado" : e.entrenado ? "fallido" : ""}`;
    b.setAttribute("aria-pressed", e.id === estado.exp);
    b.innerHTML = `<small>Exp ${n + 1}</small>${e.titulo}${e.aprobado ? " ✓" : e.entrenado ? " ✗" : ""}`;
    b.title = e.estado === "pendiente" ? `Pendiente: ${e.pregunta}` : e.pregunta;
    b.onclick = () => abrirExperimento(e.id);
    cont.append(b);
    if (e.id === estado.exp) requestAnimationFrame(() => b.scrollIntoView({ inline: "center", block: "nearest" }));
  });
}

function segmentado(id, valores, etiqueta) {
  const cont = $(id);
  cont.innerHTML = "";
  for (const v of valores) {
    const b = document.createElement("button");
    b.textContent = etiqueta(v);
    b.setAttribute("aria-pressed", estado[id] === v);
    b.dataset.valor = v;
    b.onclick = () => {
      detenerAprendizaje();
      estado[id] = v;
      for (const o of cont.children) o.setAttribute("aria-pressed", o === b);
      if (id === "planeta") { aplicarPlaneta(); dibujarHitos(); }
      lanzar();
    };
    cont.append(b);
  }
}

function construirAgentes() {
  const cont = $("agentes");
  cont.innerHTML = "";
  for (const a of estado.mundo.agentes) {
    const info = AGENTES[a.id];
    const b = document.createElement("button");
    b.className = "agente";
    b.dataset.id = a.id;
    b.style.setProperty("--c", info.color);
    b.disabled = !a.disponible;
    b.setAttribute("aria-pressed", a.id === estado.agente);
    b.innerHTML = `<span class="punto"></span><b>${info.titulo}</b><small>${a.disponible ? a.descripcion : "Este experimento todavía no tiene modelo entrenado."}</small>`;
    b.onclick = () => { detenerAprendizaje(); estado.agente = a.id; marcarVersion(); lanzar(); };
    cont.append(b);
  }
}

function construirMotores() {
  const m = estado.mundo.robot;
  const cont = $("motores");
  cont.innerHTML = "";
  m.motores.forEach((n, i) => {
    const lado = n.endsWith("_i") ? "izq." : "der.";
    const d = document.createElement("div");
    d.className = "motor";
    d.title = `Torque máximo ${m.torque_max[i]} N·m`;
    d.innerHTML = `<span class="m-nombre">${NOMBRE_MOTOR[n.slice(0, -2)]} ${lado}</span>
      <span class="m-barra"><i id="m-b-${i}"></i></span><span class="m-valor" id="m-v-${i}">—</span>`;
    cont.append(d);
  });
}

function marcarVersion() {
  for (const b of $("agentes").children) b.setAttribute("aria-pressed", b.dataset.id === estado.agente);
  if (!estado.agente.includes(":")) progreso.soltar();
}

function nombreVersion() {
  const a = estado.agente;
  if (a.startsWith("paso:")) return `Foto en ${Number(a.slice(5)).toLocaleString("es")} pasos`;
  if (a.startsWith("foto:")) return `Foto de un experimento anterior`;
  return AGENTES[a].titulo;
}

const fmt = (v, d = 1) => (v >= 0 ? "+" : "") + v.toFixed(d);
const grados = (rad) => `${(rad * 180 / Math.PI).toFixed(0)}°`;

function mostrar(i) {
  const cuadros = estado.episodio.cuadros;
  const f = cuadros[i];
  f.torques.forEach((t, m) => {
    const barra = $(`m-b-${m}`);
    barra.style.width = `${Math.abs(t) * 50}%`;
    barra.style.left = t >= 0 ? "50%" : `${50 - Math.abs(t) * 50}%`;
    $(`m-v-${m}`).textContent = grados(f.angulos[m]);
  });
  const g = estado.mundo.gravedades[estado.planeta];
  $("v-g").textContent = `${planeta.tema().nombre} · ${g} m/s²`;
  $("v-peso").textContent = `${(g * estado.mundo.robot.masa).toFixed(0)} N`;
  $("v-altura").textContent = `${f.altura.toFixed(2)} m (${(f.altura_rel * 100).toFixed(0)} %)`;
  const inc = $("v-inclinacion");
  inc.textContent = `${f.inclinacion.toFixed(1)}°`;
  inc.className = f.inclinacion > 20 ? "alerta" : "";
  $("v-velocidad").textContent = `${f.velocidad.toFixed(2)} m/s`;
  $("v-pies").textContent = [f.pies[0] && "izquierdo", f.pies[1] && "derecho"].filter(Boolean).join(" y ") || "ninguno";
  $("v-comando").textContent = f.orden;
  $("v-distancia").textContent = `${f.distancia.toFixed(2)} m`;
  $("v-piso").textContent = planeta.tema().terrenos[f.piso] || f.piso.replace("_", " ");
  $("v-r").textContent = fmt(f.recompensa, 2);
  $("v-rt").textContent = fmt(f.total, 1);
  $("desglose").innerHTML = Object.entries(f.desglose).map(([k, v]) =>
    `<li><span>${NOMBRE_RECOMPENSA[k] || k}</span><b>${fmt(v, 2)}</b></li>`).join("");
  $("barra").value = i;
  $("contador").textContent = `${f.t.toFixed(1)} / ${cuadros[cuadros.length - 1].t.toFixed(1)} s`;
  if (f.empujon) {
    const aviso = $("aviso-empujon");
    aviso.hidden = false;
    clearTimeout(aviso.temporizador);
    aviso.temporizador = setTimeout(() => { aviso.hidden = true; }, 900);
  }
  if (i === cuadros.length - 1) mostrarResultado(); else $("resultado").hidden = true;
}

function mostrarResultado() {
  const r = estado.episodio.resumen;
  const el = $("resultado");
  el.className = `resultado ${r.exito ? "exito" : "fracaso"}`;
  el.innerHTML = `<small>${nombreVersion()}</small><b>${r.exito ? r.titulo_exito : "No lo logró"}</b>
    ${r.exito ? `${r.segundos.toFixed(0)} s` : `a los ${r.segundos.toFixed(1)} s: ${r.motivo}`}${r.detalle ? `<br>${r.detalle}` : ""}<br>
    inclinación máxima ${r.inclinacion_max.toFixed(1)}° · energía ${r.energia_j.toFixed(0)} J`;
  el.hidden = false;
}

function aplicarPlaneta() {
  planeta.aplicar(estado.planeta, "despejado");
  sol.target.position.set(0, 0, 0);
  construirCampo();
}

// ------------------------------------------------------------- experimentos
async function abrirExperimento(id) {
  detenerAprendizaje();
  estado.exp = id;
  const e = estado.catalogo.find((x) => x.id === id);
  const n = estado.catalogo.indexOf(e) + 1;
  construirSelector();
  $("exp-eyebrow").textContent = `Experimento ${n}: ${e.titulo}`;
  $("mision").textContent = e.pregunta;
  $("exp-titulo").textContent = `Experimento ${n} · ${e.titulo}`;
  $("exp-pregunta").textContent = e.pregunta;
  $("exp-agrega").textContent = `Agrega: ${e.agrega}.`;
  const sello = $("exp-sello");
  sello.hidden = false;
  sello.className = `sello ${e.aprobado ? "ok" : ""}`;
  sello.textContent = e.estado === "pendiente" ? `Pendiente · Para aprobar: ${e.criterio}.`
    : !e.entrenado ? "Todavía sin entrenar."
      : e.aprobado ? "Aprobado" : "Entrenado, todavía no aprueba";

  const pendiente = e.estado === "pendiente";
  $("contenido").hidden = pendiente;
  if (pendiente) {
    estado.play = false;
    estado.episodio = null;
    raizRobot.visible = false;
    $("resultado").hidden = true;
    return;
  }
  estado.episodio = null;
  raizRobot.visible = false;
  estado.mundo = await (await fetch(`/api/exp/${id}/mundo`)).json();
  if (!estado.mundo.agentes.find((a) => a.id === estado.agente)?.disponible) estado.agente = "sin_entrenar";
  construirRobot(estado.mundo.robot);
  construirAgentes();
  construirMotores();
  await cargarAprendizaje(id);
  segmentado("planeta", Object.keys(estado.mundo.gravedades), (v) => `${TEMAS[v].nombre} · ${estado.mundo.gravedades[v]}`);
  segmentado("perturbacion", estado.mundo.perturbaciones, (v) => ETIQUETA_PERTURBACION[v] || v);
  await progreso.cargar(id);
  const reg = Object.entries(estado.mundo.regresion || {});
  $("seccion-regresion").hidden = reg.length < 2;
  $("regresion").innerHTML = reg.map(([k, v]) => `<div class="reg-fila"><span>${estado.mundo.titulos[k]}</span>
    <span class="m-barra"><i style="left:0;width:${v * 100}%;background:var(--verde)"></i></span><b>${Math.round(v * 100)}%</b></div>`).join("");
  const ev = estado.mundo.evaluacion;
  $("pie").innerHTML = ev
    ? `Modelo <code>${id}</code> · campeón: semilla ${ev.campeon} · robot <code>${estado.mundo.robot.modelo}</code>`
    : `Robot <code>${estado.mundo.robot.modelo}</code>`;
  await lanzar();
}

async function lanzar(clip = null) {
  estado.finClip = null;
  const semilla = Number($("semilla").value) || 0;
  const q = new URLSearchParams({ agente: estado.agente, planeta: estado.planeta, perturbacion: estado.perturbacion, semilla });
  const resp = await fetch(`/api/exp/${estado.exp}/episodio?${q}`);
  const datos = await resp.json();
  if (!resp.ok) { alert(datos.error); return; }
  estado.episodio = datos;
  raizRobot.visible = true;
  dibujarTramos(datos.resumen.tramos || []);
  estado.i = 0; estado.tiempo = 0; estado.play = true;
  $("barra").max = datos.cuadros.length - 1;
  if (clip) {
    estado.tiempo = clip[0];
    estado.finClip = clip[1];
    estado.i = Math.max(0, datos.cuadros.findIndex((c) => c.t >= clip[0]));
  }
  mostrar(estado.i);
  botonPlay(true);
}

function irA(i) {
  estado.i = Math.max(0, Math.min(i, estado.episodio.cuadros.length - 1));
  estado.tiempo = estado.episodio.cuadros[estado.i].t;
  mostrar(estado.i);
}

function alternarPlay() {
  if (!estado.episodio) return;
  if (estado.i >= estado.episodio.cuadros.length - 1) irA(0);
  estado.play = !estado.play;
  botonPlay(estado.play);
}

$("btn-play").onclick = () => { detenerAprendizaje(); alternarPlay(); };
$("btn-reiniciar").onclick = () => { if (estado.episodio) { detenerAprendizaje(); irA(0); } };
$("barra").oninput = (e) => { detenerAprendizaje(); estado.play = false; botonPlay(false); irA(Number(e.target.value)); };
$("velocidad").onchange = (e) => { estado.velocidad = Number(e.target.value); };
$("btn-lanzar").onclick = () => { detenerAprendizaje(); lanzar(); };
$("btn-dado").onclick = () => { detenerAprendizaje(); $("semilla").value = Math.floor(Math.random() * 10000); lanzar(); };
$("semilla").onchange = () => { detenerAprendizaje(); lanzar(); };
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.code === "Space") { e.preventDefault(); alternarPlay(); }
});

// ---------------------------------------------------- progreso del entrenamiento
const progreso = crearProgreso({
  alElegir: (p) => { detenerAprendizaje(); verFoto(p); },
});
function verFoto(p) {
  estado.agente = `paso:${p}`;
  marcarVersion();
  return lanzar();
}

// ------------------------------------------------------- cómo aprendió, por etapas
let aprendizaje = null;  // etapas calculadas por el simulador (metrics/exp-NNN/evolucion.json)
let reel = null;         // { plan, i, espera } mientras se reproduce la secuencia
const ICONO_VER = '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg>';

async function cargarAprendizaje(id) {
  const r = await fetch(`/api/exp/${id}/evolucion`);
  aprendizaje = r.ok ? await r.json() : null;
  $("aprendizaje").hidden = !aprendizaje;
  if (!aprendizaje) return;
  estado.planeta = aprendizaje.recomendado;
  aplicarPlaneta();
  dibujarHitos();
}

function textoBoton(activo) {
  $("btn-aprendizaje").innerHTML = activo ? "Detener" : `${ICONO_VER}<span>Ver su aprendizaje</span>`;
}

function dibujarHitos(activo = -1) {
  if (!aprendizaje) return;
  const plan = aprendizaje.planetas[estado.planeta];
  textoBoton(Boolean(reel));
  const cont = $("hitos");
  cont.innerHTML = "";
  plan.hitos.forEach((h, i) => {
    const li = document.createElement("li");
    li.className = `hito ${h.exito ? "logrado" : ""} ${i === activo ? "activo" : ""}`;
    const tasa = h.tasa === null ? "" : `<small>En las pruebas: ${Math.round(h.tasa * 100)} %</small>`;
    li.innerHTML = `<button><span class="h-num">${i + 1}</span><span class="h-cuerpo"><b>${h.etiqueta}</b><span>${h.texto}</span>${tasa}</span></button>`;
    li.querySelector("button").onclick = () => { detenerAprendizaje(); reproducirEtapa(plan, i, false); };
    cont.append(li);
  });
  $("aprendizaje-nota").textContent = plan.mejora < 0.05
    ? `En ${planeta.tema().nombre} ya lo lograba desde el inicio: el contraste está en ${TEMAS[otroPlaneta()].nombre}.`
    : `${plan.hitos.length} etapas en ${planeta.tema().nombre}, desde que no sabía nada, todas en la misma prueba de este experimento.`;
}

const otroPlaneta = () => Object.keys(aprendizaje.planetas).find((p) => p !== estado.planeta);

async function reproducirEtapa(plan, i, seguir) {
  const h = plan.hitos[i];
  estado.agente = h.agente;
  estado.perturbacion = aprendizaje.perturbacion;
  for (const b of $("perturbacion").children) b.setAttribute("aria-pressed", b.dataset.valor === estado.perturbacion);
  $("semilla").value = plan.semilla;
  marcarVersion();
  dibujarHitos(i);
  const aviso = $("etapa");
  aviso.className = `etapa ${h.exito ? "logrado" : ""}`;
  aviso.innerHTML = `<small>Etapa ${i + 1} de ${plan.hitos.length}</small><b>${h.etiqueta}</b><span>${h.texto}</span>`;
  aviso.hidden = false;
  $("resultado").hidden = true;
  estado.velocidad = 1;
  $("velocidad").value = "1";
  await lanzar(h.clip);
  if (seguir && reel) reel.i = i;
}

function alTerminarEpisodio() {
  if (!reel) return;
  reel.espera = setTimeout(() => {
    if (!reel) return;
    const { plan, i } = reel;
    if (i + 1 < plan.hitos.length) { reproducirEtapa(plan, i + 1, true); return; }
    const a = plan.hitos[0], z = plan.hitos[plan.hitos.length - 1];
    const aviso = $("etapa");
    aviso.className = `etapa ${z.exito ? "logrado" : ""}`;
    aviso.innerHTML = `<small>De principio a fin</small><b>${a.texto}</b><span>→ ${z.texto}</span>`;
    reel = null;
    dibujarHitos();
  }, 1300);
}

function detenerAprendizaje() {
  if (reel) clearTimeout(reel.espera);
  reel = null;
  estado.finClip = null;
  $("etapa").hidden = true;
  if (aprendizaje) textoBoton(false);
}

$("btn-aprendizaje").onclick = () => {
  if (reel) { detenerAprendizaje(); dibujarHitos(); return; }
  const plan = aprendizaje.planetas[estado.planeta];
  reel = { plan, i: 0, espera: null };
  reproducirEtapa(plan, 0, true);
};

// ------------------------------------------------------------------ bucle
function redimensionar() {
  const { clientWidth: w, clientHeight: h } = $("escena");
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(redimensionar).observe($("escena"));

const reloj = new THREE.Clock();
function bucle() {
  const dt = Math.min(reloj.getDelta(), 0.1);
  if (estado.episodio) {
    const c = estado.episodio.cuadros;
    if (estado.play) {
      estado.tiempo += dt * estado.velocidad;
      while (estado.i < c.length - 1 && c[estado.i + 1].t <= estado.tiempo) {
        estado.i += 1;
        mostrar(estado.i);
      }
      if (estado.i >= c.length - 1 || (estado.finClip !== null && estado.tiempo >= estado.finClip)) {
        estado.finClip = null;
        estado.play = false;
        botonPlay(false);
        alTerminarEpisodio();
      }
    }
    const A = c[estado.i], B = c[Math.min(estado.i + 1, c.length - 1)];
    const f = B.t > A.t ? Math.min(1, (estado.tiempo - A.t) / (B.t - A.t)) : 0;
    posarRobot(A, B, Math.max(0, f));
    seguirRobot(dt);
  }
  planeta.animar(dt, reloj.elapsedTime);
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(bucle);
}

async function iniciar() {
  estado.catalogo = await (await fetch("/api/experimentos")).json();
  botonPlay(false);
  aplicarPlaneta();
  redimensionar();
  bucle();
  const primero = estado.catalogo.find((e) => e.estado !== "pendiente") || estado.catalogo[0];
  await abrirExperimento(primero.id);
}
iniciar();
