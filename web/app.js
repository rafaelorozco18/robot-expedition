// Visor 3D de Robot Expedition. Solo dibuja: cada episodio lo corre MuJoCo en Python
// (/api/exp/<id>/episodio) y aquí se reproducen sus cuadros.
import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { crearProgreso } from "./progreso.js";
import { crearPlaneta, TEMAS } from "./planetas.js";
import { crearRobot, gestoDe } from "./robot3d.js";
import { crearEfectos, crearSonido } from "./efectos.js";

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
  salto: "Pies en el aire", impulso: "Impulso hacia arriba",
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
controls.target.set(0.1, 0.78, 0.25);
camera.position.set(3.4, 1.15, 2.9);  // de tres cuartos: se ve la cara del robot mientras camina hacia +x
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
const efectos = crearEfectos(scene);
const sonido = crearSonido();

// Campo de pruebas: plano, con rejilla de 1 m. MuJoCo tiene el piso en z = 0.
const rampa = new THREE.Group();
scene.add(rampa);
const grupoCampo = new THREE.Group();
rampa.add(grupoCampo);
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
  const meta = estado.mundo?.meta_m;
  if (meta) construirMeta(meta);
  else construirCirculo();
}

// Experimentos sin distancia: una plataforma circular donde demostrar el control del cuerpo.
function construirCirculo() {
  const piso = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.46, 0.02, 64), new THREE.MeshStandardMaterial({ color: 0x2b3440, roughness: 0.45, metalness: 0.4 }));
  piso.position.y = 0.001;
  piso.receiveShadow = true;
  grupoCampo.add(piso);
  for (const [r, opacidad] of [[1.36, 0.9], [0.92, 0.35]]) {
    const aro = new THREE.Mesh(new THREE.RingGeometry(r - 0.03, r, 64), new THREE.MeshBasicMaterial({ color: 0x3fd0e0, transparent: true, opacity: opacidad }));
    aro.rotation.x = -Math.PI / 2;
    aro.position.y = 0.014;
    grupoCampo.add(aro);
  }
}

function rotulo(texto, escala, color = "#ffffff") {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 96;
  const ctx = c.getContext("2d");
  ctx.fillStyle = color;
  ctx.font = "800 58px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "rgba(0,0,0,.6)";
  ctx.shadowBlur = 8;
  ctx.fillText(texto, 128, 48);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
  m.scale.set(escala * 2.67, escala, 1);
  return m;
}

// Arco de meta y marcas de distancia: la pista cuenta cuánto le falta al robot.
function construirMeta(x) {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 96;
  const ctx = c.getContext("2d");
  for (let i = 0; i < 26; i++) for (let j = 0; j < 5; j++) {
    ctx.fillStyle = (i + j) % 2 ? "#10161d" : "#f4f4f0";
    ctx.fillRect(i * 20, j * 20, 20, 20);
  }
  ctx.fillStyle = "#ff7a1a";
  ctx.fillRect(150, 18, 212, 60);
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 50px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("META", 256, 50);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const poste = new THREE.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4, metalness: 0.5 });
  for (const z of [-2.6, 2.6]) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 2.6, 12), poste);
    m.position.set(x, 1.3, z);
    m.castShadow = true;
    grupoCampo.add(m);
  }
  const banda = new THREE.Mesh(new THREE.PlaneGeometry(5.3, 0.62), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
  banda.rotation.y = Math.PI / 2;
  banda.position.set(x, 2.45, 0);
  grupoCampo.add(banda);
  const linea = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 5.2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 }));
  linea.rotation.x = -Math.PI / 2;
  linea.position.set(x, 0.008, 0);
  grupoCampo.add(linea);
  for (let d = 2; d < x; d += 2) {
    const m = rotulo(`${d} m`, 0.26, "#f2f2ec");
    m.position.set(d, 0.22, 2.75);
    grupoCampo.add(m);
    const raya = new THREE.Mesh(new THREE.PlaneGeometry(0.04, 5.2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.2 }));
    raya.rotation.x = -Math.PI / 2;
    raya.position.set(d, 0.006, 0);
    grupoCampo.add(raya);
  }
}

// Tramos de piso del episodio, tal como los sorteó el simulador (x de MuJoCo = x del visor).
const grupoTramos = new THREE.Group();
rampa.add(grupoTramos);
const texturasPiso = {};
function texturaPiso(tipo) {
  if (texturasPiso[tipo]) return texturasPiso[tipo];
  const n = 256, c = document.createElement("canvas");
  c.width = c.height = n;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, n, n);
  const azar = (m) => Math.random() * m;
  if (tipo === "hielo") {
    ctx.strokeStyle = "rgba(90,150,200,.55)";
    for (let i = 0; i < 14; i++) {
      ctx.lineWidth = 1 + azar(1.5);
      ctx.beginPath();
      let x = azar(n), y = azar(n);
      ctx.moveTo(x, y);
      for (let k = 0; k < 5; k++) { x += azar(70) - 35; y += azar(70) - 35; ctx.lineTo(x, y); }
      ctx.stroke();
    }
  } else if (tipo.startsWith("barro")) {
    for (let i = 0; i < 26; i++) {
      ctx.fillStyle = `rgba(0,0,0,${0.12 + azar(0.3)})`;
      ctx.beginPath();
      ctx.ellipse(azar(n), azar(n), 8 + azar(38), 5 + azar(24), azar(3), 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (tipo === "arena") {
    ctx.strokeStyle = "rgba(120,80,30,.28)";
    ctx.lineWidth = 3;
    for (let y = 8; y < n; y += 15) {
      ctx.beginPath();
      for (let x = 0; x <= n; x += 12) ctx[x ? "lineTo" : "moveTo"](x, y + Math.sin(x / 26 + y) * 5);
      ctx.stroke();
    }
  } else {
    for (let i = 0; i < 500; i++) {
      ctx.fillStyle = `rgba(0,0,0,${azar(0.5)})`;
      ctx.beginPath();
      ctx.arc(azar(n), azar(n), 1 + azar(5), 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return (texturasPiso[tipo] = t);
}

function dibujarTramos(tramos) {
  grupoTramos.traverse((o) => { o.geometry?.dispose(); });
  grupoTramos.clear();
  const tema = planeta.tema();
  const color = { arena: tema.colores.a, barro: tema.colores.b, barro_profundo: tema.charco.color, hielo: tema.colores.h, grava: tema.roca };
  const nombre = { arena: "ARENA", barro: "BARRO", barro_profundo: "BARRO PROFUNDO", hielo: "HIELO", grava: "GRAVA" };
  for (const [x0, x1, tipo] of tramos) {
    const largo = x1 - x0;
    const tex = texturaPiso(tipo).clone();
    tex.repeat.set(largo / 2, 2.6);
    tex.needsUpdate = true;
    const malla = new THREE.Mesh(new THREE.BoxGeometry(largo, 0.02, 5.2), new THREE.MeshStandardMaterial({
      color: color[tipo], map: tex, roughness: tipo === "hielo" ? 0.12 : 0.95, metalness: tipo === "hielo" ? 0.25 : 0,
    }));
    malla.position.set((x0 + x1) / 2, 0.0, 0);
    malla.receiveShadow = true;
    grupoTramos.add(malla);
    if (tipo === "grava") {
      const n = Math.round(largo * 60);
      const piedras = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.035, 0), new THREE.MeshStandardMaterial({ color: new THREE.Color(tema.roca).offsetHSL(0, 0, 0.12), flatShading: true }), n);
      const m = new THREE.Matrix4();
      for (let i = 0; i < n; i++) {
        const e = 0.5 + Math.random();
        m.makeScale(e, e * 0.6, e).setPosition(x0 + Math.random() * largo, 0.015, (Math.random() - 0.5) * 5);
        piedras.setMatrixAt(i, m);
      }
      piedras.castShadow = true;
      grupoTramos.add(piedras);
    }
    const r = rotulo(nombre[tipo], 0.3, "#ffffff");
    r.position.set((x0 + x1) / 2, 0.3, -2.75);
    grupoTramos.add(r);
  }
}

// ------------------------------------------------------------------- robot
// Se construye desde el modelo que entrega el simulador. Ver robot3d.js.
let robot = null;

function construirRobot(datos) {
  robot?.destruir();
  robot = crearRobot(datos);
  rampa.add(robot.raiz);
}

// La cámara sigue al robot si se aleja; hará falta desde que camine.
const previo = new THREE.Vector3();
const mundoLider = new THREE.Vector3();
function seguirRobot(dt) {
  const lider = estado.carrera ? estado.carrera.lider.r : robot;
  if (!lider) return;
  lider.cuerpos[0].getWorldPosition(mundoLider);
  mundoLider.y -= 0.85;  // sigue al piso bajo el robot: en una rampa, la cámara sube con él
  const suavizado = Math.min(1, dt * 4 * Math.max(1, estado.velocidad));
  const delta = mundoLider.clone().sub(previo).multiplyScalar(suavizado);
  previo.add(delta);
  controls.target.add(delta);
  camera.position.add(delta);
  // La luz viaja con el robot: las sombras cubren un área limitada.
  sol.target.position.copy(previo);
  sol.position.set(...planeta.tema().sol.posicion).add(previo);
}

// ------------------------------------------------------------------- panel
function construirSelector() {
  const cont = $("selector");
  cont.innerHTML = "";
  const aprobados = estado.catalogo.filter((e) => e.aprobado).length;
  const intentados = estado.catalogo.filter((e) => e.entrenado).length;
  $("avance").innerHTML = `<b>${aprobados}</b> de ${estado.catalogo.length} experimentos aprobados · ${intentados} entrenados`;
  const mapa = $("mapa");
  mapa.innerHTML = "";
  estado.catalogo.forEach((e, n) => {
    const d = document.createElement("button");
    d.className = `punto-mapa ${e.aprobado ? "aprobado" : e.entrenado ? "fallido" : ""}`;
    d.title = `Exp ${n + 1}: ${e.titulo}`;
    d.textContent = n + 1;
    d.setAttribute("aria-pressed", e.id === estado.exp);
    d.onclick = () => abrirExperimento(e.id);
    mapa.append(d);
  });
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
  if (i === cuadros.length - 1 && !reel) mostrarResultado(); else $("resultado").hidden = true;
}

function mostrarResultado() {
  const r = estado.episodio.resumen;
  const el = $("resultado");
  el.className = `resultado ${r.exito ? "exito" : "fracaso"}`;
  el.innerHTML = `<small>${nombreVersion()}</small><b>${r.exito ? `¡${r.titulo_exito}!` : "Todavía no"}</b>
    ${r.exito ? `${r.segundos.toFixed(0)} s` : `a los ${r.segundos.toFixed(1)} s: ${r.motivo}`}${r.detalle ? `<br>${r.detalle}` : ""}<br>
    inclinación máxima ${r.inclinacion_max.toFixed(1)}° · energía ${r.energia_j.toFixed(0)} J`;
  el.hidden = false;
}

// Guía de la orden: anillo a la altura pedida o resaltado del pie que debe cargar el peso.
const guia = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.012, 10, 64), new THREE.MeshBasicMaterial({ color: 0x3fd0e0, transparent: true, opacity: 0.9 }));
guia.rotation.x = Math.PI / 2;
guia.visible = false;
rampa.add(guia);

function actualizarGuia(f) {
  const tarea = estado.mundo?.tarea;
  guia.visible = !estado.carrera && (tarea === "sentadilla" || tarea === "pasar_peso" || tarea === "un_pie");
  if (!guia.visible) return;
  if (tarea === "sentadilla") {
    guia.scale.setScalar(1);
    guia.position.set(f.cuerpos[0][0], f.altura_orden + 0.22, -f.cuerpos[0][1]);
  } else {
    const lado = Math.sign(f.pie_orden) || 1;
    guia.scale.setScalar(0.5);
    guia.position.set(f.cuerpos[0][0], 0.03, -(f.cuerpos[0][1] + lado * 0.09));
  }
}

function aplicarPlaneta() {
  planeta.aplicar(estado.planeta, estado.mundo?.clima_visual || "despejado");
  sol.target.position.copy(previo);
  construirCampo();
}

// ------------------------------------------------------------- experimentos
async function abrirExperimento(id) {
  detenerAprendizaje();
  aprendizaje = null;  // hasta cargar las etapas de este experimento
  $("aprendizaje").hidden = true;
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
  $("pendiente").hidden = !pendiente;
  $("pendiente-texto").textContent = `Este experimento agregará: ${e.agrega}. Se aprueba cuando: ${e.criterio}.`;
  if (pendiente) {
    guia.visible = false;
    estado.play = false;
    estado.episodio = null;
    if (robot) robot.raiz.visible = false;
    $("resultado").hidden = true;
    return;
  }
  estado.episodio = null;
  if (robot) robot.raiz.visible = false;
  estado.mundo = await (await fetch(`/api/exp/${id}/mundo`)).json();
  if (!estado.mundo.agentes.find((a) => a.id === estado.agente)?.disponible) estado.agente = "sin_entrenar";
  construirRobot(estado.mundo.robot);
  robot.raiz.visible = false;
  efectos.limpiar();
  aplicarPlaneta();
  // La rampa se simula inclinando la gravedad; aquí se inclina el piso y el robot para verla.
  rampa.rotation.z = THREE.MathUtils.degToRad(estado.mundo.pendiente_grados);
  rampa.add(grupoCampo, grupoTramos, robot.raiz);
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
  // Cada episodio empieza en el origen: la cámara vuelve a él en vez de recorrer la pista.
  controls.target.sub(previo);
  camera.position.sub(previo);
  previo.set(0, 0, 0);
  robot.raiz.visible = true;
  robot.fijarGesto("normal");
  efectos.limpiar();
  ocultarBurbuja();
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

$("btn-sonido").onclick = (e) => {
  sonido.iniciar();
  e.currentTarget.classList.toggle("apagado", !sonido.alternar());
};
$("btn-carrera").onclick = () => { if (aprendizaje) iniciarCarrera(aprendizaje.planetas[estado.planeta]); };
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
  $("btn-aprendizaje").innerHTML = activo ? "Detener" : `${ICONO_VER}<span>Ver cómo aprendió</span>`;
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
    li.style.setProperty("--c", colorNivel(i, plan.hitos.length));
    li.innerHTML = `<button><span class="h-num">${i + 1}</span><span class="h-cuerpo"><b>${h.etiqueta}</b><span>${h.texto}</span>${tasa}</span><i class="estrellas">${estrellas(h)}</i></button>`;
    li.querySelector("button").onclick = () => { detenerAprendizaje(); reproducirEtapa(plan, i, false); };
    cont.append(li);
  });
  $("aprendizaje-nota").textContent = plan.mejora < 0.05
    ? `En ${planeta.tema().nombre} ya lo lograba desde el inicio: el contraste está en ${TEMAS[otroPlaneta()].nombre}.`
    : `${plan.hitos.length} etapas en ${planeta.tema().nombre}, desde que no sabía nada, todas en la misma prueba de este experimento.`;
}

const otroPlaneta = () => Object.keys(aprendizaje.planetas).find((p) => p !== estado.planeta);

const estrellas = (h) => "★".repeat(h.exito ? 3 : h.avance > 0.4 ? 2 : 1).padEnd(3, "☆");

async function reproducirEtapa(plan, i, seguir) {
  const h = plan.hitos[i];
  estado.agente = h.agente;
  estado.perturbacion = aprendizaje.perturbacion;
  for (const b of $("perturbacion").children) b.setAttribute("aria-pressed", b.dataset.valor === estado.perturbacion);
  $("semilla").value = plan.semilla;
  marcarVersion();
  dibujarHitos(i);
  mostrarEtapa(`Nivel ${i + 1} de ${plan.hitos.length}`, h.etiqueta, h.texto, h.exito, estrellas(h));
  dibujarNiveles(plan, i);
  sonido.sonar("nivel");
  $("resultado").hidden = true;
  estado.velocidad = 1;
  $("velocidad").value = "1";
  estado.hito = h;
  controls.autoRotate = Boolean(seguir);
  await lanzar(h.clip);
  decir("Aquí voy…", 1.4);
  if (seguir && reel) reel.i = i;
}

function mostrarEtapa(arriba, titulo, texto, logrado, marca = "") {
  const a = $("etapa");
  a.className = `etapa ${logrado ? "logrado" : ""}`;
  void a.offsetWidth;  // reinicia la animación de entrada
  a.classList.add("entra");
  a.innerHTML = `<small>${arriba}</small><b>${titulo}</b><span>${texto}</span>${marca ? `<i class="estrellas">${marca}</i>` : ""}`;
  a.hidden = false;
}

function dibujarNiveles(plan, activo) {
  const cont = $("niveles");
  cont.hidden = false;
  cont.innerHTML = plan.hitos.map((h, i) =>
    `<span class="${i < activo ? "pasado" : i === activo ? "actual" : ""}" style="--c:${colorNivel(i, plan.hitos.length)}">${i + 1}</span>`).join("<i></i>");
}

const colorNivel = (i, n) => `hsl(${Math.round((i / Math.max(1, n - 1)) * 135)}, 75%, 52%)`;

// ------------------------------------------------- reacciones del robot a la física
const FRASES = {
  cae: ["¡Ay!", "¡Uy!", "¡Auch!", "Eso dolió…", "¡Otra vez no!"],
  casi: ["Casi…", "Ya mero", "Sigo practicando"],
  bien: ["¡Lo logré!", "¡Mírame!", "¡Soy un crack!", "¡Sí!"],
};
const alAzar = (l) => l[Math.floor(Math.random() * l.length)];
let burbujaHasta = 0;

function decir(texto, segundos = 2) {
  const b = $("burbuja");
  b.textContent = texto;
  b.hidden = false;
  burbujaHasta = reloj.elapsedTime + segundos;
}
function ocultarBurbuja() { $("burbuja").hidden = true; }

function colocarSobre(el, v3) {
  const p = v3.clone().project(camera);
  const { clientWidth: w, clientHeight: h } = $("escena");
  el.style.transform = `translate(calc(${((p.x + 1) / 2 * w).toFixed(0)}px - 50%), calc(${((1 - p.y) / 2 * h).toFixed(0)}px - 100%))`;
}

function reaccionar(r, A, B, conSonido = true) {
  [0, 1].forEach((p) => {
    if (B.pies[p] && !A.pies[p]) {
      const v = r.pieEnMundo(p);
      efectos.polvo(v, planeta.tema().polvo.color, 4);
      efectos.huella(v, 0);
      if (conSonido) sonido.sonar("paso");
    }
  });
  if (B.empujon) {
    efectos.polvo(r.cabeza(), 0xff7a1a, 6, 1.2);
    if (conSonido) { sonido.sonar("empujon"); decir("¡Epa!", 1.2); }
  }
  r.fijarGesto(gestoDe(B));
}

function caer(r, conEfectos = true) {
  r.fijarGesto("mareado");
  if (!conEfectos) return;
  efectos.polvo(r.cabeza().setY(0.05), planeta.tema().polvo.color, 14, 2.2);
  temblor = 0.4;
  sonido.sonar("caida");
}

function celebrar(r, grande) {
  r.fijarGesto("feliz");
  if (grande) { efectos.confeti(r.cabeza()); sonido.sonar("exito"); }
}

function finDeEpisodio() {
  const { resumen: r, cuadros } = estado.episodio;
  const alFinal = estado.i >= cuadros.length - 1;
  const ultimaEtapa = reel && reel.i === reel.plan.hitos.length - 1;
  if (r.exito) {
    celebrar(robot, !reel || ultimaEtapa);
    decir(alAzar(FRASES.bien));
  } else if (alFinal && r.motivo !== "no cumplió la meta") {
    caer(robot);
    decir(alAzar(FRASES.cae));
  } else {
    decir(alAzar(FRASES.casi));
  }
  alTerminarEpisodio();
}

function alTerminarEpisodio() {
  if (!reel) return;
  reel.espera = setTimeout(() => {
    if (!reel) return;
    const { plan, i } = reel;
    if (i + 1 < plan.hitos.length) { reproducirEtapa(plan, i + 1, true); return; }
    reel = null;
    controls.autoRotate = false;
    dibujarHitos();
    iniciarCarrera(plan);
  }, 1900);
}

function detenerAprendizaje() {
  if (reel) clearTimeout(reel.espera);
  reel = null;
  estado.finClip = null;
  estado.hito = null;
  controls.autoRotate = false;
  $("etapa").hidden = true;
  $("niveles").hidden = true;
  terminarCarrera();
  if (aprendizaje) textoBoton(false);
}

$("btn-aprendizaje").onclick = () => {
  sonido.iniciar();
  if (reel) { detenerAprendizaje(); dibujarHitos(); return; }
  detenerAprendizaje();
  const plan = aprendizaje.planetas[estado.planeta];
  reel = { plan, i: 0, espera: null };
  reproducirEtapa(plan, 0, true);
};

// ------------------------------------------------- carrera de todas las versiones
async function iniciarCarrera(plan) {
  sonido.iniciar();
  detenerAprendizaje();
  const hitos = plan.hitos, n = hitos.length;
  mostrarEtapa("Carrera de versiones", "Preparando los carriles…", "Cada carril es un momento del aprendizaje, en la misma prueba.", true);
  const episodios = await Promise.all(hitos.map(async (h) => {
    const q = new URLSearchParams({ agente: h.agente, planeta: estado.planeta, perturbacion: aprendizaje.perturbacion, semilla: plan.semilla });
    return (await fetch(`/api/exp/${estado.exp}/episodio?${q}`)).json();
  }));
  if (episodios.some((e) => e.error) || !aprendizaje) { $("etapa").hidden = true; return; }
  estado.play = false;
  robot.raiz.visible = false;
  efectos.limpiar();
  dibujarTramos(episodios[0].resumen.tramos || []);
  const cont = $("etiquetas");
  cont.innerHTML = "";
  const corredores = hitos.map((h, i) => {
    const color = new THREE.Color(colorNivel(i, n));
    const r = crearRobot(estado.mundo.robot, { acento: color.getHex() });
    r.raiz.position.z = (i - (n - 1) / 2) * 0.95;
    rampa.add(r.raiz);
    const tag = document.createElement("span");
    tag.className = "etiqueta-carrera";
    tag.style.setProperty("--c", colorNivel(i, n));
    tag.textContent = `${i + 1} · ${h.etiqueta.split(/[,·]/)[0].trim()}`;
    cont.append(tag);
    r.posar(episodios[i].cuadros[0], episodios[i].cuadros[0], 0);
    return { r, c: episodios[i].cuadros, res: episodios[i].resumen, i: 0, tag, fin: false };
  });
  const fin = Math.min(13, Math.max(...corredores.map((k) => k.c[k.c.length - 1].t)));
  estado.carrera = { corredores, t: -1.2, fin, lider: corredores[0] };
  camera.position.copy(controls.target.set(previo.x, 0.72, 0)).add(new THREE.Vector3(5.2 + n * 0.25, 1.9, 1.3));  // de frente: vienen hacia la cámara
  dibujarNiveles(plan, n);
  mostrarEtapa("Carrera de versiones", "¡Ya!", "Del robot que no sabía nada al experto, lado a lado.", true);
  sonido.sonar("nivel");
  setTimeout(() => { if (estado.carrera && !estado.carrera.cerrada) $("etapa").hidden = true; }, 2600);
}

function animarCarrera(dt) {
  const k = estado.carrera;
  k.t += dt;
  let lider = k.lider;
  for (const c of k.corredores) {
    if (k.t >= 0) {
      while (c.i < c.c.length - 1 && c.c[c.i + 1].t <= k.t) {
        c.i += 1;
        reaccionar(c.r, c.c[c.i - 1], c.c[c.i], c === k.corredores[k.corredores.length - 1]);
      }
    }
    const A = c.c[c.i], B = c.c[Math.min(c.i + 1, c.c.length - 1)];
    const f = B.t > A.t ? Math.max(0, Math.min(1, (k.t - A.t) / (B.t - A.t))) : 0;
    c.r.posar(A, B, f);
    if (!c.fin && c.i >= c.c.length - 1) {
      c.fin = true;
      if (c.res.exito) celebrar(c.r, false);
      else if (c.res.motivo !== "no cumplió la meta") caer(c.r);
    }
    if (c.r.cuerpos[0].position.x > lider.r.cuerpos[0].position.x) lider = c;
    colocarSobre(c.tag, c.r.cabeza().add(new THREE.Vector3(0, 0.14, 0)));
  }
  k.lider = lider;
  $("contador").textContent = `${Math.max(0, Math.min(k.t, k.fin)).toFixed(1)} / ${k.fin.toFixed(1)} s`;
  if (k.t >= k.fin && !k.cerrada) {
    k.cerrada = true;
    const z = k.corredores[k.corredores.length - 1], a = k.corredores[0];
    const hitos = aprendizaje.planetas[estado.planeta].hitos;
    if (z.res.exito) celebrar(z.r, true);
    mostrarEtapa("De principio a fin", hitos[hitos.length - 1].etiqueta.split(" · ")[0], `${hitos[0].texto} → ${hitos[hitos.length - 1].texto}`, z.res.exito, estrellas(hitos[hitos.length - 1]));
  }
}

function terminarCarrera() {
  if (!estado.carrera) return;
  for (const c of estado.carrera.corredores) c.r.destruir();
  estado.carrera = null;
  $("etiquetas").innerHTML = "";
  if (robot) robot.raiz.visible = Boolean(estado.episodio);
}

// ------------------------------------------------------------------ bucle
function redimensionar() {
  const { clientWidth: w, clientHeight: h } = $("escena");
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(redimensionar).observe($("escena"));

const reloj = new THREE.Clock();
let temblor = 0;
function bucle() {
  const dt = Math.min(reloj.getDelta(), 0.1);
  if (estado.carrera) {
    animarCarrera(dt);
    seguirRobot(dt);
  } else if (estado.episodio) {
    const c = estado.episodio.cuadros;
    if (estado.play) {
      // cámara lenta en el último instante de una caída
      const ultimo = c[c.length - 1].t;
      const cae = !estado.episodio.resumen.exito && estado.episodio.resumen.motivo !== "no cumplió la meta";
      const lento = cae && estado.tiempo > ultimo - 0.8;
      estado.tiempo += dt * estado.velocidad * (lento ? 0.35 : 1);
      while (estado.i < c.length - 1 && c[estado.i + 1].t <= estado.tiempo) {
        estado.i += 1;
        mostrar(estado.i);
        reaccionar(robot, c[estado.i - 1], c[estado.i]);
      }
      if (estado.i >= c.length - 1 || (estado.finClip !== null && estado.tiempo >= estado.finClip)) {
        estado.finClip = null;
        estado.play = false;
        botonPlay(false);
        finDeEpisodio();
      }
    }
    const A = c[estado.i], B = c[Math.min(estado.i + 1, c.length - 1)];
    const f = B.t > A.t ? Math.min(1, (estado.tiempo - A.t) / (B.t - A.t)) : 0;
    robot.posar(A, B, Math.max(0, f));
    actualizarGuia(A);
    seguirRobot(dt);
    if (!$("burbuja").hidden) {
      colocarSobre($("burbuja"), robot.cabeza().add(new THREE.Vector3(0, 0.12, 0)));
      if (reloj.elapsedTime > burbujaHasta) ocultarBurbuja();
    }
  }
  if (temblor > 0) {
    temblor -= dt;
    camera.position.x += (Math.random() - 0.5) * 0.03;
    camera.position.y += (Math.random() - 0.5) * 0.03;
  }
  efectos.actualizar(dt);
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
