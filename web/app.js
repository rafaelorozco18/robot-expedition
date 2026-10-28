// Visor 3D de Robot Expedition. Solo dibuja: cada episodio lo corre el simulador
// de Python (/api/episodio) y aquí se reproducen sus cuadros paso a paso.
import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { crearProgreso } from "./progreso.js";

const $ = (id) => document.getElementById(id);

const COLOR = {
  ".": 0xd9b98a, a: 0xf0d98c, b: 0x7a5230, h: 0xbfe3f5, R: 0xd9b98a,
  "#": 0x3b4452, B: 0x2e8b4a, 1: 0xd9b98a, 2: 0xd9b98a,
};
const AGENTES = {
  experto: { titulo: "Experto · Q-learning", color: "#39c16c" },
  aprendiz: { titulo: "Aprendiz · Q-learning temprano", color: "#f2b632" },
  codicioso: { titulo: "Codicioso · heurística", color: "#3fd0e0" },
  aleatorio: { titulo: "Aleatorio", color: "#ff5a5f" },
};
const ACCIONES = [
  { sim: "↑", txt: "mover N" }, { sim: "↓", txt: "mover S" }, { sim: "→", txt: "mover E" }, { sim: "←", txt: "mover O" },
  { sim: "⇑", txt: "saltar N" }, { sim: "⇓", txt: "saltar S" }, { sim: "⇒", txt: "saltar E" }, { sim: "⇐", txt: "saltar O" },
  { sim: '<svg viewBox="0 0 24 24"><path d="M12 3v7M7 6l2 5M17 6l-2 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/><path d="M5 12h14l-2 7H7z"/></svg>', txt: "agarrar muestra" },
];
const ICONO = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg>',
  pausa: '<svg viewBox="0 0 24 24"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>',
};
const botonPlay = (jugando) => { $("btn-play").innerHTML = jugando ? ICONO.pausa : ICONO.play; };
const DIRS = [[0, -1], [0, 1], [1, 0], [-1, 0]]; // N S E O en la rejilla
const RAYOS = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
const CIELO = { tierra: 0x24425e, marte: 0x5b2c1f, luna: 0x04060b };
const ALTURA_SALTO = { luna: 1.5, marte: 0.95, tierra: 0.5 };
const ETIQUETA_INCIDENTE = { ninguno: "ninguno", corredor_bloqueado: "corredor bloqueado" };

const estado = {
  mundo: null, agente: "experto", clima: "despejado", gravedad: "tierra", incidente: "ninguno",
  episodio: null, k: 0, t: 0, play: false, velocidad: 1,
};

// ------------------------------------------------------------------ escena
const lienzo = $("lienzo");
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(CIELO.tierra);
scene.fog = new THREE.Fog(CIELO.tierra, 30, 70);

const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 300);
const controls = new OrbitControls(camera, lienzo);
// El objetivo de la cámara va desplazado para dejar el título libre arriba a la izquierda.
controls.target.set(-2.4, 0, -0.2);
camera.position.set(5.2, 16.5, 17.8);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.46;
controls.minDistance = 8;
controls.maxDistance = 45;

const hemi = new THREE.HemisphereLight(0xdfefff, 0x3b2c20, 0.9);
scene.add(hemi);
const sol = new THREE.DirectionalLight(0xffffff, 1.8);
sol.position.set(9, 16, 6);
sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
Object.assign(sol.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 50 });
scene.add(sol);

function material(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0.0, ...extra });
}

function texturaTexto(texto, { color = "#ffffff", fondo = null, ancho = 256, alto = 128, fuente = "800 76px system-ui" } = {}) {
  const c = document.createElement("canvas");
  c.width = ancho; c.height = alto;
  const ctx = c.getContext("2d");
  if (fondo) { ctx.fillStyle = fondo; ctx.fillRect(0, 0, ancho, alto); }
  ctx.fillStyle = color;
  ctx.font = fuente;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(texto, ancho / 2, alto / 2 + 4);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function sprite(texto, escala, color = "#ffffff") {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texturaTexto(texto, { color, ancho: 128, alto: 128, fuente: "900 96px system-ui" }),
    depthTest: false,
  }));
  s.scale.set(escala, escala, 1);
  s.renderOrder = 10;
  return s;
}

const celda = (x, y) => new THREE.Vector3(x - 5.5, 0, y - 5.5);
const SUPERFICIE = 0.1; // altura de la cara superior de las baldosas

// -------------------------------------------------------------------- mapa
const grupoMapa = new THREE.Group();
scene.add(grupoMapa);
let balizas = {};
let anilloBase = null;

function construirMapa(mapa, celdasIncidente) {
  grupoMapa.traverse((o) => { o.geometry?.dispose(); });
  grupoMapa.clear();
  balizas = {};
  const alto = mapa.length, ancho = mapa[0].length;

  const plataforma = new THREE.Mesh(new THREE.BoxGeometry(ancho + 0.8, 1.2, alto + 0.8), material(0x27313d));
  plataforma.position.set(0, -0.7, 0);
  plataforma.receiveShadow = true;
  grupoMapa.add(plataforma);

  const rng = mulberry32(7);
  for (let y = 0; y < alto; y++) {
    for (let x = 0; x < ancho; x++) {
      const c = mapa[y][x];
      const p = celda(x, y);
      if (c === "G") {
        const fondo = new THREE.Mesh(new THREE.BoxGeometry(1, 0.05, 1),
          material(0x120806, { emissive: 0x3a0c02, emissiveIntensity: 0.9 }));
        fondo.position.set(p.x, -1.2, p.z);
        grupoMapa.add(fondo);
        continue;
      }
      const h = c === "b" ? 0.16 : c === "a" ? 0.24 : 0.2;
      const extra = c === "h" ? { roughness: 0.08, metalness: 0.25, transparent: true, opacity: 0.92 } : {};
      const tono = new THREE.Color(COLOR[c]).offsetHSL(0, 0, (rng() - 0.5) * 0.04);
      const baldosa = new THREE.Mesh(new THREE.BoxGeometry(0.98, h, 0.98), material(tono, extra));
      baldosa.position.set(p.x, SUPERFICIE - h / 2, p.z);
      baldosa.receiveShadow = true;
      grupoMapa.add(baldosa);

      if (c === "a") {   // dunas pequeñas
        for (let i = 0; i < 3; i++) {
          const duna = new THREE.Mesh(new THREE.SphereGeometry(0.16, 8, 6), material(0xe8cc78));
          duna.scale.y = 0.25;
          duna.position.set(p.x + (rng() - 0.5) * 0.6, SUPERFICIE + 0.02, p.z + (rng() - 0.5) * 0.6);
          grupoMapa.add(duna);
        }
      }
      if (c === "b") {   // charco
        const charco = new THREE.Mesh(new THREE.CircleGeometry(0.28, 16),
          material(0x4a3018, { roughness: 0.2, metalness: 0.1 }));
        charco.rotation.x = -Math.PI / 2;
        charco.position.set(p.x + (rng() - 0.5) * 0.3, SUPERFICIE + 0.005, p.z + (rng() - 0.5) * 0.3);
        grupoMapa.add(charco);
      }
      if (c === "R") {
        const roca = new THREE.Mesh(new THREE.DodecahedronGeometry(0.36, 0),
          material(0x8a8f96, { flatShading: true }));
        roca.scale.set(1 + rng() * 0.2, 0.75 + rng() * 0.25, 1 + rng() * 0.2);
        roca.rotation.set(rng(), rng() * 3, rng());
        roca.position.set(p.x, SUPERFICIE + 0.22, p.z);
        roca.castShadow = true;
        grupoMapa.add(roca);
        if (celdasIncidente.some(([ix, iy]) => ix === x && iy === y)) {
          const aviso = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.5, 4, 1),
            new THREE.MeshBasicMaterial({ color: 0xff7a1a }));
          aviso.rotation.set(-Math.PI / 2, 0, Math.PI / 4);
          aviso.position.set(p.x, SUPERFICIE + 0.01, p.z);
          grupoMapa.add(aviso);
          const etiqueta = sprite("!", 0.7, "#ff7a1a");
          etiqueta.position.set(p.x, 1.2, p.z);
          grupoMapa.add(etiqueta);
        }
      }
      if (c === "#") {
        const muro = new THREE.Mesh(new THREE.BoxGeometry(1, 1.1, 1), material(0x3b4452));
        muro.position.set(p.x, SUPERFICIE + 0.55, p.z);
        muro.castShadow = muro.receiveShadow = true;
        grupoMapa.add(muro);
        const tapa = new THREE.Mesh(new THREE.BoxGeometry(1.001, 0.04, 1.001), material(0x56627a));
        tapa.position.set(p.x, SUPERFICIE + 1.11, p.z);
        grupoMapa.add(tapa);
      }
      if (c === "B") {
        const rotulo = new THREE.Mesh(new THREE.PlaneGeometry(0.92, 0.92), new THREE.MeshBasicMaterial({
          map: texturaTexto("BASE", { fondo: "#2e8b4a", fuente: "900 64px system-ui" }), transparent: true,
        }));
        rotulo.rotation.x = -Math.PI / 2;
        rotulo.position.set(p.x, SUPERFICIE + 0.006, p.z);
        grupoMapa.add(rotulo);
        anilloBase = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.58, 32),
          new THREE.MeshBasicMaterial({ color: 0x39c16c, transparent: true, opacity: 0.0 }));
        anilloBase.rotation.x = -Math.PI / 2;
        anilloBase.position.set(p.x, SUPERFICIE + 0.01, p.z);
        grupoMapa.add(anilloBase);
      }
      if (c === "1" || c === "2") balizas[c] = crearBaliza(p, c);
    }
  }

  const norte = sprite("N", 0.8, "#b4c4d2");
  norte.position.set(0, 0.5, -alto / 2 - 1);
  grupoMapa.add(norte);
}

function crearBaliza(p, num) {
  const g = new THREE.Group();
  const matLuz = material(0x2ec4d6, { emissive: 0x2ec4d6, emissiveIntensity: 0.8 });
  const pie = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.26, 0.08, 20), material(0x2b3a4a));
  pie.position.y = SUPERFICIE + 0.04;
  const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.09, 0.7, 12), material(0x2b3a4a));
  poste.position.y = SUPERFICIE + 0.43;
  const faro = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.26, 0.26), matLuz);
  faro.position.y = SUPERFICIE + 0.9;
  faro.castShadow = true;
  const anillo = new THREE.Mesh(new THREE.RingGeometry(0.36, 0.46, 32),
    new THREE.MeshBasicMaterial({ color: 0x3fd0e0, transparent: true, opacity: 0.8 }));
  anillo.rotation.x = -Math.PI / 2;
  anillo.position.y = SUPERFICIE + 0.01;
  const etiqueta = sprite(num, 0.55);
  etiqueta.position.y = SUPERFICIE + 1.35;
  g.add(pie, poste, faro, anillo, etiqueta);
  g.position.set(p.x, 0, p.z);
  grupoMapa.add(g);
  return { faro, anillo, matLuz };
}

function marcarBalizas(etapa, tiempo) {
  for (const [num, b] of Object.entries(balizas)) {
    const hecha = etapa >= Number(num);
    const actual = etapa === Number(num) - 1;
    const color = hecha ? 0x39c16c : 0x2ec4d6;
    b.matLuz.color.setHex(color);
    b.matLuz.emissive.setHex(color);
    b.anillo.material.color.setHex(color);
    b.anillo.material.opacity = actual ? 0.5 + 0.4 * Math.sin(tiempo * 4) : hecha ? 0.6 : 0.25;
    b.faro.rotation.y = tiempo * (actual ? 1.6 : 0.3);
  }
  if (anilloBase) anilloBase.material.opacity = etapa >= 2 ? 0.5 + 0.4 * Math.sin(tiempo * 4) : 0;
}

// ------------------------------------------------------------------- robot
function crearRobot() {
  const g = new THREE.Group();
  const cuerpo = new THREE.Group();
  const chasis = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.2, 0.42), material(0xf1efe9, { roughness: 0.5 }));
  chasis.position.y = 0.3;
  const franja = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.05, 0.44), material(0xff7a1a));
  franja.position.y = 0.3;
  const carga = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.1, 0.24), material(0x8a8f96));
  carga.position.set(0.12, 0.45, 0);
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.32), material(0x333a44));
  mastil.position.set(-0.14, 0.56, 0);
  const cabeza = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.1, 0.2), material(0x1d2530));
  cabeza.position.set(-0.12, 0.76, 0);
  const ojo = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8),
    material(0x3fd0e0, { emissive: 0x3fd0e0, emissiveIntensity: 1.5 }));
  ojo.position.set(-0.05, 0.76, 0);
  const luz = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 8),
    material(0x39c16c, { emissive: 0x39c16c, emissiveIntensity: 1.6 }));
  luz.position.set(-0.12, 0.86, 0);
  for (const m of [chasis, franja, carga, mastil, cabeza]) m.castShadow = true;
  cuerpo.add(chasis, franja, carga, mastil, cabeza, ojo, luz);
  const ruedas = [];
  for (const [rx, rz] of [[0.19, 0.24], [-0.19, 0.24], [0.19, -0.24], [-0.19, -0.24]]) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.08, 16), material(0x1b1f24));
    r.rotation.x = Math.PI / 2;
    r.position.set(rx, 0.13, rz);
    r.castShadow = true;
    cuerpo.add(r);
    ruedas.push(r);
  }
  g.add(cuerpo);
  scene.add(g);
  return { g, cuerpo, luz, ruedas };
}
const robot = crearRobot();

const grupoRayos = new THREE.Group();
scene.add(grupoRayos);
const rayos = RAYOS.map(() => {
  const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
  const linea = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x5fe3f0, transparent: true, opacity: 0.75 }));
  const punta = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 6), new THREE.MeshBasicMaterial({ color: 0x5fe3f0 }));
  grupoRayos.add(linea, punta);
  return { linea, punta };
});

const grupoRastro = new THREE.Group();
scene.add(grupoRastro);
const geoRastro = new THREE.CircleGeometry(0.06, 10);
const matRastro = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 });

// -------------------------------------------------------------------- clima
const N_GOTAS = 3200;
const gotasXYZ = new Float32Array(N_GOTAS * 3);   // posición de la cabeza de cada gota
const posGotas = new Float32Array(N_GOTAS * 6);   // segmentos cabeza → cola
for (let i = 0; i < N_GOTAS; i++) {
  gotasXYZ.set([(Math.random() - 0.5) * 16, Math.random() * 12, (Math.random() - 0.5) * 16], i * 3);
}
const geoGotas = new THREE.BufferGeometry();
geoGotas.setAttribute("position", new THREE.BufferAttribute(posGotas, 3));
const gotas = new THREE.LineSegments(geoGotas, new THREE.LineBasicMaterial({
  color: 0xa9d0ff, transparent: true, opacity: 0.28, depthWrite: false,
}));
gotas.frustumCulled = false;
scene.add(gotas);

const geoEstrellas = new THREE.BufferGeometry();
const posEstrellas = new Float32Array(1500 * 3);
for (let i = 0; i < 1500; i++) {
  const v = new THREE.Vector3().randomDirection().multiplyScalar(120);
  v.y = Math.abs(v.y) + 5;
  posEstrellas.set([v.x, v.y, v.z], i * 3);
}
geoEstrellas.setAttribute("position", new THREE.BufferAttribute(posEstrellas, 3));
const estrellas = new THREE.Points(geoEstrellas, new THREE.PointsMaterial({ color: 0xffffff, size: 0.5, fog: false }));
scene.add(estrellas);

let relampago = 0;
let nGotas = 0;
function aplicarAmbiente() {
  const { clima, gravedad } = estado;
  const cielo = new THREE.Color(CIELO[gravedad]);
  if (clima !== "despejado") cielo.lerp(new THREE.Color(0x1a1f26), clima === "lluvia" ? 0.45 : 0.7);
  scene.background = cielo;
  scene.fog.color = cielo;
  scene.fog.near = clima === "tormenta" ? 14 : clima === "lluvia" ? 20 : 30;
  scene.fog.far = clima === "tormenta" ? 40 : clima === "lluvia" ? 52 : 70;
  nGotas = clima === "tormenta" ? N_GOTAS : clima === "lluvia" ? 1400 : 0;
  geoGotas.setDrawRange(0, nGotas * 2);
  estrellas.visible = gravedad === "luna" && clima === "despejado";
  sol.intensity = clima === "despejado" ? 1.8 : clima === "lluvia" ? 1.0 : 0.6;
  sol.color.setHex(gravedad === "marte" ? 0xffd2b0 : 0xffffff);
}

function animarClima(dt) {
  if (nGotas > 0) {
    const viento = estado.clima === "tormenta" ? 3.5 : 0.6;
    const caida = estado.clima === "tormenta" ? 16 : 10;
    const largo = 0.035;  // segundos de recorrido que dibuja cada trazo
    for (let i = 0; i < nGotas; i++) {
      const j = i * 3;
      gotasXYZ[j] += viento * dt;
      gotasXYZ[j + 1] -= caida * dt;
      if (gotasXYZ[j + 1] < 0) {
        gotasXYZ[j + 1] = 12;
        gotasXYZ[j] = (Math.random() - 0.5) * 16 - viento;
      }
      posGotas.set([gotasXYZ[j], gotasXYZ[j + 1], gotasXYZ[j + 2],
        gotasXYZ[j] - viento * largo, gotasXYZ[j + 1] + caida * largo, gotasXYZ[j + 2]], i * 6);
    }
    geoGotas.attributes.position.needsUpdate = true;
  }
  if (estado.clima === "tormenta") {
    if (relampago <= 0 && Math.random() < dt * 0.25) relampago = 0.18;
    relampago -= dt;
    hemi.intensity = relampago > 0 ? 3.2 : 0.7;
  } else {
    hemi.intensity = 0.9;
  }
}

// --------------------------------------------------------------- animación
const suave = (t) => t * t * (3 - 2 * t);
let rumbo = 0;

function rumboDeAccion(a) {
  if (a === null || a === undefined || a === 8) return null;
  const [dx, dy] = DIRS[a % 4];
  return Math.atan2(-dy, dx);
}

function poseRobot(k, t) {
  const cuadros = estado.episodio.cuadros;
  const A = cuadros[k];
  const B = cuadros[Math.min(k + 1, cuadros.length - 1)];
  const pA = celda(...A.posicion), pB = celda(...B.posicion);
  const s = k + 1 >= cuadros.length ? 1 : t;
  const pos = pA.clone().lerp(pB, suave(s));
  let y = SUPERFICIE - 0.02, inclinacion = 0, balanceo = 0;
  const ev = B.eventos || [];
  if (k + 1 < cuadros.length) {
    const r = rumboDeAccion(B.accion);
    if (r !== null) rumbo = r;
    if (ev.includes("salto")) y += ALTURA_SALTO[estado.gravedad] * 4 * s * (1 - s) * Math.min(1, pA.distanceTo(pB) / 2);
    if (ev.includes("atascado en barro")) { pos.x += Math.sin(s * 50) * 0.04; y -= 0.04; }
    if (ev.some((e) => e.startsWith("choque") || e === "salto bloqueado")) {
      const [dx, dy] = DIRS[B.accion % 4];
      const empuje = 0.28 * Math.sin(Math.PI * s);
      pos.x += dx * empuje; pos.z += dy * empuje;
    }
    if (ev.includes("patinó en hielo")) balanceo = Math.sin(s * Math.PI * 4) * 0.25 * (1 - s);
    if (ev.includes("agarró baliza 1") || ev.includes("agarró baliza 2")) inclinacion = Math.sin(s * Math.PI) * 0.35;
  }
  const ultimo = cuadros[cuadros.length - 1];
  const cae = ultimo.condiciones.terreno === "grieta";
  if (cae && (k + 1 === cuadros.length - 1 && s > 0.5 || k + 1 >= cuadros.length)) {
    const u = k + 1 >= cuadros.length ? 1 : (s - 0.5) * 2;
    y -= 1.2 * u * u;
    balanceo += 0.6 * u;
  }
  return { pos, y, inclinacion, balanceo };
}

function ubicarRobot(tiempo) {
  if (!estado.episodio) return;
  const { pos, y, inclinacion, balanceo } = poseRobot(estado.k, estado.t);
  robot.g.position.set(pos.x, y, pos.z);
  let delta = rumbo - robot.g.rotation.y;
  delta = Math.atan2(Math.sin(delta), Math.cos(delta));
  robot.g.rotation.y += delta * 0.25;
  robot.cuerpo.rotation.z = inclinacion;
  robot.cuerpo.rotation.x = balanceo;
  robot.ruedas.forEach((r) => { r.rotation.y = tiempo * (estado.play ? 6 : 0); });

  const f = cuadroVisible();
  const lecturas = f.obs.rayos;
  const origen = new THREE.Vector3(pos.x, y + 0.76, pos.z);
  rayos.forEach(({ linea, punta }, i) => {
    const [dx, dy] = RAYOS[i];
    const dir = new THREE.Vector3(dx, 0, dy).normalize();
    const fin = origen.clone().addScaledVector(dir, lecturas[i]);
    fin.y = SUPERFICIE + 0.25;
    linea.geometry.setFromPoints([origen, fin]);
    punta.position.copy(fin);
  });
  const bat = f.bateria;
  const c = bat > 50 ? 0x39c16c : bat > 20 ? 0xf2b632 : 0xff5a5f;
  robot.luz.material.color.setHex(c);
  robot.luz.material.emissive.setHex(c);
  marcarBalizas(f.etapa, tiempo);
}

function cuadroVisible() {
  const c = estado.episodio.cuadros;
  return c[Math.min(estado.k + (estado.t > 0 ? 1 : 0), c.length - 1)];
}

function reconstruirRastro(hasta) {
  grupoRastro.clear();
  const cuadros = estado.episodio.cuadros;
  for (let i = 0; i <= hasta && i < cuadros.length; i++) agregarRastro(cuadros[i]);
}
function agregarRastro(f) {
  const p = celda(...f.posicion);
  const punto = new THREE.Mesh(geoRastro, matRastro);
  punto.rotation.x = -Math.PI / 2;
  punto.position.set(p.x + (Math.random() - 0.5) * 0.12, SUPERFICIE + 0.012, p.z + (Math.random() - 0.5) * 0.12);
  grupoRastro.add(punto);
}

// ------------------------------------------------------------------- panel
function construirPanel() {
  const m = estado.mundo;
  const contAgentes = $("agentes");
  contAgentes.innerHTML = "";
  for (const a of m.agentes) {
    const info = AGENTES[a.id];
    const b = document.createElement("button");
    b.className = "agente";
    b.style.setProperty("--c", info.color);
    b.disabled = !a.disponible;
    b.setAttribute("aria-pressed", a.id === estado.agente);
    b.innerHTML = `<span class="punto"></span><b>${info.titulo}</b><small>${a.disponible ? a.descripcion : "Sin modelo: ejecuta «expedicion entrenar»."}</small>`;
    b.onclick = () => { detenerRecorrido(); estado.agente = a.id; marcar(contAgentes, b); marcarVersion(); lanzar(); };
    contAgentes.append(b);
  }
  segmentado("clima", Object.keys(m.climas), (v) => v);
  segmentado("gravedad", Object.keys(m.gravedades), (v) => `${v[0].toUpperCase() + v.slice(1)} · ${m.gravedades[v]}`);
  segmentado("incidente", Object.keys(m.incidentes), (v) => ETIQUETA_INCIDENTE[v] || v);

  const contAcc = $("acciones");
  contAcc.innerHTML = "";
  ACCIONES.forEach((a, i) => {
    const d = document.createElement("div");
    d.className = "accion" + (i === 8 ? " agarrar" : "");
    d.innerHTML = `<div class="q"></div><span class="sim">${a.sim}</span><span>${a.txt}</span>`;
    contAcc.append(d);
  });

  const mod = m.modelo;
  $("pie").innerHTML = mod
    ? `Modelo <code>${mod.nombre}</code> v${mod.version} · ${mod.episodios.toLocaleString("es")} episodios · código <code>${mod.git_commit}</code>${mod.mlflow_run_id ? ` · run MLflow <code>${mod.mlflow_run_id.slice(0, 8)}</code>` : ""}`
    : "Sin modelo entrenado todavía.";
}

function segmentado(id, valores, etiqueta) {
  const cont = $(id);
  cont.innerHTML = "";
  for (const v of valores) {
    const b = document.createElement("button");
    b.textContent = etiqueta(v);
    b.setAttribute("aria-pressed", estado[id] === v);
    b.onclick = () => { estado[id] = v; marcar(cont, b); aplicarAmbiente(); lanzar(); };
    cont.append(b);
  }
}
function marcar(cont, activo) {
  for (const b of cont.children) b.setAttribute("aria-pressed", b === activo);
}

const fmt = (v, d = 1) => (v >= 0 ? "+" : "") + v.toFixed(d);

function mostrar(idx) {
  const cuadros = estado.episodio.cuadros;
  const f = cuadros[idx];
  const c = f.condiciones;

  // acciones: la elegida y los valores Q del estado donde se eligió
  const qs = (idx > 0 ? cuadros[idx - 1].q : cuadros[0].q);
  const celdas = $("acciones").children;
  const min = qs ? Math.min(...qs) : 0, max = qs ? Math.max(...qs) : 1;
  [...celdas].forEach((el, i) => {
    el.classList.toggle("activa", idx > 0 && f.accion === i);
    el.querySelector(".q").style.opacity = qs ? 0.06 + 0.5 * ((qs[i] - min) / (max - min || 1)) : 0;
    el.title = qs ? `Q = ${qs[i].toFixed(2)}` : "";
  });
  $("nota-q").textContent = qs
    ? "Brillo = valor Q de cada acción en el estado donde decidió. Borde naranja = acción ejecutada."
    : "Este agente no usa tabla Q. Borde naranja = acción ejecutada.";

  const bat = f.bateria;
  $("v-bateria").textContent = `${bat.toFixed(1)}%`;
  const barra = $("bateria");
  barra.style.width = `${bat}%`;
  barra.style.background = bat > 50 ? "var(--verde)" : bat > 20 ? "var(--amarillo)" : "var(--rojo)";

  for (const s of $("etapas").querySelectorAll("span")) {
    const e = Number(s.dataset.e);
    s.classList.toggle("hecha", e === 0 || e <= f.etapa);
    s.classList.toggle("actual", e === f.etapa + 1);
  }
  $("v-pos").textContent = `(${f.posicion[0]}, ${f.posicion[1]}) m`;
  $("v-vel").textContent = `${f.obs.velocidad.toFixed(0)} m/s`;
  $("v-obj").textContent = `(${f.obs.objetivo[0]}, ${f.obs.objetivo[1]}) → ${f.objetivo}`;
  $("v-ruta").textContent = `${f.ruta_restante.toFixed(0)} m`;

  const terreno = $("v-terreno");
  terreno.textContent = c.terreno;
  terreno.className = c.terreno === "hielo" || c.terreno === "barro" ? "alerta" : c.terreno === "grieta" ? "peligro" : "";
  $("v-clima").textContent = c.clima;
  $("v-g").textContent = `${c.gravedad} · ${c.g} m/s²`;
  const desl = $("v-desl");
  desl.textContent = `${(c.prob_deslizar * 100).toFixed(0)}%`;
  desl.className = c.terreno === "hielo" ? "alerta" : "";
  const atasco = $("v-atasco");
  atasco.textContent = c.prob_atasco > 0 ? `${(c.prob_atasco * 100).toFixed(0)}%` : "0% (fuera)";
  atasco.className = c.prob_atasco > 0 ? "alerta" : "";
  $("v-salto").textContent = `${c.costo_salto.toFixed(1)}% · +1 m ${(c.prob_sobrevuelo * 100).toFixed(0)}%`;
  $("v-ruido").textContent = `σ = ${c.ruido_sensor.toFixed(2)} m`;
  const inc = $("v-incidente");
  inc.textContent = ETIQUETA_INCIDENTE[c.incidente] || c.incidente;
  inc.className = c.incidente !== "ninguno" ? "alerta" : "";
  dibujarRadar(f.obs.rayos);

  $("v-r").textContent = fmt(f.recompensa, 2);
  $("v-rt").textContent = fmt(f.recompensa_total, 2);

  const lista = $("bitacora");
  lista.innerHTML = "";
  for (let i = idx; i >= Math.max(1, idx - 40); i--) {
    const g = cuadros[i];
    const li = document.createElement("li");
    const ev = g.eventos.length ? ` · ${g.eventos.join(", ")}` : "";
    li.innerHTML = `<b>t${g.paso}</b><span>${g.accion_nombre}${ev} · ${fmt(g.recompensa, 2)}</span>`;
    if (g.eventos.some((e) => e.startsWith("agarró"))) li.className = "buena";
    else if (g.recompensa < -0.5) li.className = "mala";
    lista.append(li);
  }

  $("barra").value = idx;
  $("contador").textContent = `${idx} / ${cuadros.length - 1}`;
  if (idx === cuadros.length - 1) mostrarResultado(); else $("resultado").hidden = true;
}

function dibujarRadar(lecturas) {
  const R = 50, max = estado.mundo.parametros.alcance_sensor;
  const pts = lecturas.map((d, i) => {
    const [dx, dy] = RAYOS[i];
    const n = Math.hypot(dx, dy);
    return [(dx / n) * (d / max) * R, (dy / n) * (d / max) * R];
  });
  const anillos = [0.33, 0.66, 1].map((f) => `<circle r="${R * f}" fill="none" stroke="#1f3448"/>`).join("");
  const lineas = pts.map(([x, y]) => `<line x1="0" y1="0" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#3fd0e0" stroke-opacity=".6"/>`).join("");
  const poli = `<polygon points="${pts.map((p) => p.map((v) => v.toFixed(1)).join(",")).join(" ")}" fill="#3fd0e033" stroke="#3fd0e0"/>`;
  const etiquetas = estado.mundo.rayos.map((n, i) => {
    const [dx, dy] = RAYOS[i]; const k = Math.hypot(dx, dy);
    return i % 2 ? "" : `<text x="${(dx / k) * (R + 7)}" y="${(dy / k) * (R + 7) + 3}" font-size="9" fill="#7b91a6" text-anchor="middle">${n}</text>`;
  }).join("");
  $("radar").innerHTML = anillos + lineas + poli + `<circle r="4" fill="#ff7a1a"/>` + etiquetas;
}

function mostrarResultado() {
  const r = estado.episodio.resumen;
  const el = $("resultado");
  el.className = "resultado " + (r.exito ? "exito" : r.motivo === "tiempo agotado" ? "tiempo" : "fracaso");
  el.innerHTML = `<small>${nombreVersion()}</small><b>${r.exito ? "Misión completa" : r.motivo[0].toUpperCase() + r.motivo.slice(1)}</b>
    ${r.pasos} pasos · batería ${r.bateria_final.toFixed(1)}% · balizas ${r.balizas}/2<br>
    recompensa total ${fmt(r.recompensa, 1)} · choques ${r.choques}`;
  el.hidden = false;
}

// ------------------------------------------------------------- episodios
async function lanzar() {
  const semilla = Number($("semilla").value) || 0;
  const q = new URLSearchParams({ agente: estado.agente, clima: estado.clima, gravedad: estado.gravedad, incidente: estado.incidente, semilla });
  const resp = await fetch(`/api/episodio?${q}`);
  const datos = await resp.json();
  if (!resp.ok) { alert(datos.error); return; }
  const mapa = estado.mundo.mapa.map((fila) => fila.split(""));
  const cambios = estado.mundo.incidentes[estado.incidente];
  for (const [x, y, c] of cambios) mapa[y][x] = c;
  construirMapa(mapa, cambios);
  estado.episodio = datos;
  estado.k = 0; estado.t = 0; estado.play = true;
  rumbo = 0; robot.g.rotation.y = 0;
  $("barra").max = datos.cuadros.length - 1;
  reconstruirRastro(0);
  mostrar(0);
  botonPlay(true);
}

function irA(k) {
  estado.k = Math.max(0, Math.min(k, estado.episodio.cuadros.length - 1));
  estado.t = 0;
  reconstruirRastro(estado.k);
  mostrar(estado.k);
}

function alternarPlay() {
  if (!estado.episodio) return;
  if (estado.k >= estado.episodio.cuadros.length - 1) irA(0);
  estado.play = !estado.play;
  botonPlay(estado.play);
}

$("btn-play").onclick = alternarPlay;
$("btn-reiniciar").onclick = () => { if (estado.episodio) { irA(0); } };
$("btn-paso").onclick = () => { if (estado.episodio) { estado.play = false; botonPlay(false); irA(estado.k + 1); } };
$("barra").oninput = (e) => { estado.play = false; botonPlay(false); irA(Number(e.target.value)); };
$("velocidad").onchange = (e) => { estado.velocidad = Number(e.target.value); };
$("btn-lanzar").onclick = lanzar;
$("btn-dado").onclick = () => { $("semilla").value = Math.floor(Math.random() * 10000); lanzar(); };
$("semilla").onchange = lanzar;
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.code === "Space") { e.preventDefault(); alternarPlay(); }
});

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
  const tiempo = reloj.elapsedTime;
  if (estado.episodio && estado.play) {
    const n = estado.episodio.cuadros.length;
    if (estado.k < n - 1) {
      if (estado.t === 0) mostrar(estado.k + 1);
      estado.t += dt * estado.velocidad / 0.42;
      if (estado.t >= 1) {
        estado.k += 1;
        estado.t = 0;
        agregarRastro(estado.episodio.cuadros[estado.k]);
        if (estado.k >= n - 1) { estado.play = false; botonPlay(false); alTerminarEpisodio(); }
      }
    }
  }
  animarClima(dt);
  ubicarRobot(tiempo);
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(bucle);
}

function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------- progreso del entrenamiento
const progreso = crearProgreso({
  alElegir: (ep) => { detenerRecorrido(); verCheckpoint(ep); },
});
let recorrido = null;   // { fotos, i, espera }

function nombreVersion() {
  const a = estado.agente;
  if (a.startsWith("ep:")) return `Versión: foto del episodio ${Number(a.slice(3)).toLocaleString("es")}`;
  return `Versión: ${AGENTES[a].titulo}`;
}
function marcarVersion() {
  if (estado.agente.startsWith("ep:")) {
    for (const b of $("agentes").children) b.setAttribute("aria-pressed", false);
  } else {
    progreso.soltar();
  }
}
function verCheckpoint(ep) {
  estado.agente = `ep:${ep}`;
  marcarVersion();
  return lanzar();
}
function alTerminarEpisodio() {
  if (!recorrido) return;
  recorrido.espera = setTimeout(siguienteFoto, 1200);
}
async function siguienteFoto() {
  if (!recorrido) return;
  recorrido.i += 1;
  if (recorrido.i >= recorrido.fotos.length) return detenerRecorrido();
  const ep = recorrido.fotos[recorrido.i];
  progreso.elegir(ep, false);
  $("aviso-recorrido").innerHTML = `Recorrido ${recorrido.i + 1}/${recorrido.fotos.length} · episodio ${ep.toLocaleString("es")} <button id="btn-parar">Detener</button>`;
  $("btn-parar").onclick = detenerRecorrido;
  await verCheckpoint(ep);
}
function detenerRecorrido() {
  if (!recorrido) return;
  clearTimeout(recorrido.espera);
  recorrido = null;
  $("aviso-recorrido").hidden = true;
  $("btn-recorrido").textContent = "Recorrer el progreso (8 fotos)";
}
$("btn-recorrido").onclick = () => {
  if (recorrido) return detenerRecorrido();
  recorrido = { fotos: progreso.recorrido(), i: -1, espera: null };
  if (estado.velocidad < 8) { estado.velocidad = 8; $("velocidad").value = "8"; }
  $("aviso-recorrido").hidden = false;
  $("btn-recorrido").textContent = "Detener recorrido";
  siguienteFoto();
};

async function iniciar() {
  estado.mundo = await (await fetch("/api/mundo")).json();
  $("mision").textContent = estado.mundo.mision;
  if (!estado.mundo.agentes.find((a) => a.id === "experto")?.disponible) estado.agente = "codicioso";
  construirPanel();
  await progreso.cargar();
  progreso.soltar();
  botonPlay(false);
  aplicarAmbiente();
  redimensionar();
  bucle();
  lanzar();
}
iniciar();
