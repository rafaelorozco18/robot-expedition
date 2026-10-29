// Aspecto de cada planeta: cielo, paisaje, colores del terreno, luz y clima visual.
// Solo decoración: la física (costos, deslizamiento, atasco, saltos) la decide Python.
import * as THREE from "three";

export const TEMAS = {
  marte: {
    nombre: "Marte",
    colores: { ".": 0xb0553a, a: 0xd08a52, b: 0x6a2c1d, h: 0xeadbd3, B: 0x7f7670, 1: 0xb0553a, 2: 0xb0553a },
    roca: 0x4f251c, muro: 0x8a4630, subsuelo: 0x5e2a1c, charco: { color: 0x4e2015, rugosidad: 1 },
    duna: 0xdc9a5e, hielo: { rugosidad: 0.45, metal: 0.0, opacidad: 1 },
    estratos: ["#8a4630", "#a65a3a", "#7a3b28", "#b86b45", "#6e3322"],
    paisaje: { base: 0xa04a2e, claro: 0xc97a45, oscuro: 0x5e2618, alto: 0x8c4a35 },
    relieve: { colinas: 2.2, crateres: 14, montanas: 34, rocas: 420, arboles: 0 },
    cielo: { arriba: 0x6e4a3c, horizonte: 0xd29b72, halo: 0x9fb8d6, haloFuerza: 0.35, radioSol: 0.012 },
    niebla: { color: 0xc68f6a, cerca: 40, lejos: 260 },
    sol: { color: 0xffe0c0, intensidad: 2.4, posicion: [12, 9, 7] },
    hemi: { cielo: 0xe0a882, suelo: 0x5a2a1a, intensidad: 1.0 },
    tormenta: { color: 0x9a6440, cerca: 6, lejos: 38, sol: 0.55 },
    polvo: { color: 0xc98a5a },
    clima: { despejado: "despejado", lluvia: "polvo en suspensión", tormenta: "tormenta de polvo" },
    precipitacion: { lluvia: { tipo: "polvo", n: 1800 }, tormenta: { tipo: "polvo", n: 7000 } },
    terrenos: { suelo: "regolito", arena: "dunas", barro: "polvo fino", hielo: "escarcha de CO₂", roca: "roca basáltica", muro: "acantilado", grieta: "grieta", base: "plataforma", "baliza 1": "baliza 1", "baliza 2": "baliza 2" },
    extras: "lunas",
  },
  luna: {
    nombre: "Luna",
    colores: { ".": 0x8e8d89, a: 0xa9a8a3, b: 0x5d5c59, h: 0xcfe0ea, B: 0x6f7378, 1: 0x8e8d89, 2: 0x8e8d89 },
    roca: 0x46464a, muro: 0x6c6b68, subsuelo: 0x3e3e3d, charco: { color: 0x4a4947, rugosidad: 1 },
    duna: 0xb3b2ad, hielo: { rugosidad: 0.2, metal: 0.1, opacidad: 0.95 },
    estratos: ["#6c6b68", "#7c7b77", "#5a5957", "#858480", "#4c4b49"],
    paisaje: { base: 0x777672, claro: 0x9a9994, oscuro: 0x3c3c3b, alto: 0x8a8985 },
    relieve: { colinas: 1.4, crateres: 60, montanas: 26, rocas: 520, arboles: 0 },
    cielo: { arriba: 0x000000, horizonte: 0x040508, halo: 0xffffff, haloFuerza: 0.05, radioSol: 0.02 },
    niebla: null,
    sol: { color: 0xffffff, intensidad: 3.2, posicion: [14, 6, 5] },
    hemi: { cielo: 0x9fb4d0, suelo: 0x333333, intensidad: 0.45 },
    tormenta: { color: 0x000000, cerca: 0, lejos: 0, sol: 1 },
    polvo: { color: 0xd8d8d8 },
    clima: { despejado: "despejado", lluvia: "micrometeoritos", tormenta: "tormenta solar" },
    precipitacion: { lluvia: { tipo: "meteoros", n: 50 }, tormenta: { tipo: "meteoros", n: 180 } },
    terrenos: { suelo: "regolito", arena: "polvo", barro: "polvo profundo", hielo: "hielo de cráter", roca: "roca", muro: "risco", grieta: "grieta", base: "plataforma", "baliza 1": "baliza 1", "baliza 2": "baliza 2" },
    extras: "tierra",
  },
  tierra: {
    nombre: "Tierra",
    colores: { ".": 0x8d7550, a: 0xdcc58e, b: 0x5a3e25, h: 0xcfe9f6, B: 0x7b7f84, 1: 0x8d7550, 2: 0x8d7550 },
    roca: 0x7a7d84, muro: 0x666b73, subsuelo: 0x5b4430, charco: { color: 0x3d2a18, rugosidad: 0.15 },
    duna: 0xe6d29c, hielo: { rugosidad: 0.06, metal: 0.25, opacidad: 0.9 },
    estratos: ["#666b73", "#757a82", "#5a5f66", "#80858c", "#50555c"],
    paisaje: { base: 0x5a7d36, claro: 0x7a9a45, oscuro: 0x3e5a26, alto: 0x7c7a74 },
    relieve: { colinas: 3.0, crateres: 0, montanas: 42, rocas: 160, arboles: 260 },
    cielo: { arriba: 0x3a72b8, horizonte: 0xbdd6ec, halo: 0xfff2d8, haloFuerza: 0.5, radioSol: 0.02 },
    niebla: { color: 0xbdd6ec, cerca: 60, lejos: 340 },
    sol: { color: 0xfff4e0, intensidad: 2.3, posicion: [10, 13, 8] },
    hemi: { cielo: 0xcfe4ff, suelo: 0x4a3a28, intensidad: 1.0 },
    tormenta: { color: 0x3c4550, cerca: 10, lejos: 60, sol: 0.45 },
    polvo: { color: 0xffffff },
    clima: { despejado: "despejado", lluvia: "lluvia", tormenta: "tormenta" },
    precipitacion: { lluvia: { tipo: "lluvia", n: 1400 }, tormenta: { tipo: "lluvia", n: 3200 } },
    terrenos: { suelo: "tierra", arena: "arena", barro: "barro", hielo: "hielo", roca: "roca", muro: "muro de granito", grieta: "grieta", base: "base", "baliza 1": "baliza 1", "baliza 2": "baliza 2" },
    extras: "nubes",
  },
};

// ---------------------------------------------------------------- utilidades
function rng(semilla) {
  let a = semilla;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function ruido(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y, octavas = 5) {
  let s = 0, amp = 0.5, f = 1;
  for (let i = 0; i < octavas; i++) { s += amp * ruido(x * f, y * f); f *= 2.03; amp *= 0.5; }
  return s;
}
const suave = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

function texturaRuido() {
  const n = 256, c = document.createElement("canvas");
  c.width = c.height = n;
  const ctx = c.getContext("2d"), img = ctx.createImageData(n, n);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const v = 0.72 + 0.28 * fbm(x / 22, y / 22, 4) + (Math.random() - 0.5) * 0.12;
      const g = Math.max(0, Math.min(255, v * 255));
      const i = (y * n + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = g;
      img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaEstratos(colores) {
  const c = document.createElement("canvas");
  c.width = 64; c.height = 256;
  const ctx = c.getContext("2d");
  let y = 0;
  const r = rng(11);
  while (y < 256) {
    const alto = 6 + r() * 26;
    ctx.fillStyle = colores[Math.floor(r() * colores.length)];
    ctx.fillRect(0, y, 64, alto);
    y += alto;
  }
  for (let i = 0; i < 900; i++) {
    ctx.fillStyle = `rgba(0,0,0,${r() * 0.18})`;
    ctx.fillRect(r() * 64, r() * 256, 1 + r() * 3, 1);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaTierraPlaneta() {
  const n = 256, c = document.createElement("canvas");
  c.width = n * 2; c.height = n;
  const ctx = c.getContext("2d"), img = ctx.createImageData(n * 2, n);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n * 2; x++) {
      const tierraFirme = fbm(x / 40, y / 40, 5) > 0.53;
      const nube = fbm(x / 18 + 40, y / 18, 4) > 0.6;
      const polo = Math.abs(y / n - 0.5) > 0.42;
      let col = tierraFirme ? [70, 120, 60] : [25, 70, 160];
      if (polo) col = [235, 240, 245];
      if (nube) col = [245, 245, 248];
      const i = (y * n * 2 + x) * 4;
      img.data.set([...col, 255], i);
    }
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaPunto() {
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
}

// ------------------------------------------------------------------ cielo
const SOMBREADOR_CIELO = {
  vertexShader: `
    varying vec3 vDir;
    void main() {
      vDir = normalize(position);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: `
    uniform vec3 arriba;
    uniform vec3 horizonte;
    uniform vec3 halo;
    uniform vec3 solDir;
    uniform float haloFuerza;
    uniform float discoCos;
    uniform float velo;
    uniform vec3 veloColor;
    varying vec3 vDir;
    void main() {
      vec3 d = normalize(vDir);
      float h = max(d.y, 0.0);
      vec3 c = mix(horizonte, arriba, pow(h, 0.55));
      float s = max(dot(d, normalize(solDir)), 0.0);
      c += halo * (pow(s, 12.0) * haloFuerza + pow(s, 200.0) * 0.6);
      c += vec3(1.6) * smoothstep(discoCos, mix(discoCos, 1.0, 0.25), s) * (1.0 - velo);
      c = mix(c, veloColor, velo);
      gl_FragColor = vec4(c, 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
};

// --------------------------------------------------------------- planeta
export function crearPlaneta(scene, { sol, hemi }) {
  const texRuido = texturaRuido();
  const cache = {};

  const cieloMat = new THREE.ShaderMaterial({
    ...SOMBREADOR_CIELO,
    uniforms: {
      arriba: { value: new THREE.Color() }, horizonte: { value: new THREE.Color() },
      halo: { value: new THREE.Color() }, solDir: { value: new THREE.Vector3() },
      haloFuerza: { value: 0.3 }, discoCos: { value: 0.9998 },
      velo: { value: 0 }, veloColor: { value: new THREE.Color() },
    },
    side: THREE.BackSide, depthWrite: false, fog: false,
  });
  const cielo = new THREE.Mesh(new THREE.SphereGeometry(800, 32, 16), cieloMat);
  cielo.renderOrder = -1;
  scene.add(cielo);

  // estrellas (siempre existen; visibles donde el cielo es negro)
  const posEstrellas = new Float32Array(2500 * 3);
  const r0 = rng(3);
  for (let i = 0; i < 2500; i++) {
    const v = new THREE.Vector3(r0() - 0.5, r0() * 0.9 + 0.02, r0() - 0.5).normalize().multiplyScalar(700);
    posEstrellas.set([v.x, v.y, v.z], i * 3);
  }
  const geoEstrellas = new THREE.BufferGeometry();
  geoEstrellas.setAttribute("position", new THREE.BufferAttribute(posEstrellas, 3));
  const estrellas = new THREE.Points(geoEstrellas, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, fog: false }));
  scene.add(estrellas);

  // cuerpos celestes
  const fobos = new THREE.Mesh(new THREE.IcosahedronGeometry(9, 1), new THREE.MeshBasicMaterial({ color: 0x8a7468, fog: false }));
  fobos.position.set(150, 40, -600);
  const deimos = new THREE.Mesh(new THREE.IcosahedronGeometry(4, 1), new THREE.MeshBasicMaterial({ color: 0x9a857a, fog: false }));
  deimos.position.set(40, 50, -640);
  const planetaTierra = new THREE.Mesh(new THREE.SphereGeometry(42, 48, 32),
    new THREE.MeshStandardMaterial({ map: texturaTierraPlaneta(), roughness: 1, emissive: 0x0a1a33, fog: false }));
  planetaTierra.position.set(70, 64, -620);
  const atmosfera = new THREE.Mesh(new THREE.SphereGeometry(45, 48, 32),
    new THREE.MeshBasicMaterial({ color: 0x6fa8ff, transparent: true, opacity: 0.18, fog: false }));
  atmosfera.position.copy(planetaTierra.position);
  const nubes = new THREE.Group();
  const matNube = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, transparent: true, opacity: 0.9, fog: false });
  const rN = rng(17);
  for (let i = 0; i < 26; i++) {
    const nube = new THREE.Group();
    for (let j = 0; j < 5; j++) {
      const bola = new THREE.Mesh(new THREE.SphereGeometry(8 + rN() * 8, 12, 8), matNube);
      bola.position.set(j * 9 - 18 + rN() * 4, rN() * 4, rN() * 6);
      bola.scale.y = 0.45;
      nube.add(bola);
    }
    const ang = rN() * Math.PI * 2, dist = 220 + rN() * 280;
    nube.position.set(Math.cos(ang) * dist, 90 + rN() * 60, Math.sin(ang) * dist);
    nubes.add(nube);
  }
  scene.add(fobos, deimos, planetaTierra, atmosfera, nubes);

  // base de la expedición: hábitat junto al inicio (fuera del mapa jugable)
  const habitat = crearHabitat();
  scene.add(habitat);

  // clima visual: polvo (puntos), lluvia y micrometeoritos (trazos)
  const N_POLVO = 7000;
  const posPolvo = new Float32Array(N_POLVO * 3);
  const fase = new Float32Array(N_POLVO);
  for (let i = 0; i < N_POLVO; i++) {
    posPolvo.set([(Math.random() - 0.5) * 30, Math.random() * 7, (Math.random() - 0.5) * 30], i * 3);
    fase[i] = Math.random() * Math.PI * 2;
  }
  const geoPolvo = new THREE.BufferGeometry();
  geoPolvo.setAttribute("position", new THREE.BufferAttribute(posPolvo, 3));
  const matPolvo = new THREE.PointsMaterial({ size: 0.09, map: texturaPunto(), transparent: true, opacity: 0.55, depthWrite: false });
  const polvo = new THREE.Points(geoPolvo, matPolvo);
  polvo.frustumCulled = false;
  scene.add(polvo);

  const N_TRAZOS = 3200;
  const cabeza = new Float32Array(N_TRAZOS * 3);
  const posTrazos = new Float32Array(N_TRAZOS * 6);
  for (let i = 0; i < N_TRAZOS; i++) cabeza.set([(Math.random() - 0.5) * 18, Math.random() * 14, (Math.random() - 0.5) * 18], i * 3);
  const geoTrazos = new THREE.BufferGeometry();
  geoTrazos.setAttribute("position", new THREE.BufferAttribute(posTrazos, 3));
  const matTrazos = new THREE.LineBasicMaterial({ transparent: true, depthWrite: false });
  const trazos = new THREE.LineSegments(geoTrazos, matTrazos);
  trazos.frustumCulled = false;
  scene.add(trazos);

  let tema = TEMAS.marte, clima = "despejado", precip = null, destello = 0, nPolvo = 0, nTrazos = 0;
  let paisaje = null;

  function aplicar(planeta, nuevoClima) {
    tema = TEMAS[planeta];
    clima = nuevoClima;
    if (paisaje) scene.remove(paisaje);
    paisaje = cache[planeta] || (cache[planeta] = construirPaisaje(tema, texRuido, planeta));
    scene.add(paisaje);

    const c = tema.cielo;
    const t = tema.tormenta;
    const intensidadClima = clima === "tormenta" ? 1 : clima === "lluvia" ? 0.45 : 0;
    cieloMat.uniforms.arriba.value.setHex(c.arriba);
    cieloMat.uniforms.horizonte.value.setHex(c.horizonte);
    cieloMat.uniforms.halo.value.setHex(c.halo);
    cieloMat.uniforms.haloFuerza.value = c.haloFuerza;
    cieloMat.uniforms.discoCos.value = Math.cos(c.radioSol);
    cieloMat.uniforms.velo.value = tema.niebla ? intensidadClima * 0.85 : 0;
    cieloMat.uniforms.veloColor.value.setHex(t.color);

    sol.position.set(...tema.sol.posicion);
    cieloMat.uniforms.solDir.value.copy(sol.position).normalize();
    sol.color.setHex(tema.sol.color);
    sol.intensity = tema.sol.intensidad * (tema.niebla ? 1 - intensidadClima * (1 - t.sol) : 1);
    hemi.color.setHex(tema.hemi.cielo);
    hemi.groundColor.setHex(tema.hemi.suelo);
    hemi.intensity = tema.hemi.intensidad;

    if (tema.niebla) {
      const color = new THREE.Color(tema.niebla.color).lerp(new THREE.Color(t.color), intensidadClima);
      scene.fog = new THREE.Fog(color,
        THREE.MathUtils.lerp(tema.niebla.cerca, t.cerca, intensidadClima),
        THREE.MathUtils.lerp(tema.niebla.lejos, t.lejos, intensidadClima));
    } else {
      scene.fog = null;
    }

    estrellas.visible = planeta === "luna";
    fobos.visible = deimos.visible = planeta === "marte";
    planetaTierra.visible = atmosfera.visible = planeta === "luna";
    nubes.visible = planeta === "tierra";

    precip = tema.precipitacion[clima] || null;
    nPolvo = precip?.tipo === "polvo" ? precip.n : 0;
    nTrazos = precip && precip.tipo !== "polvo" ? precip.n : 0;
    geoPolvo.setDrawRange(0, nPolvo);
    geoTrazos.setDrawRange(0, nTrazos * 2);
    matPolvo.color.setHex(tema.polvo.color);
    matPolvo.size = clima === "tormenta" ? 0.07 : 0.05;
    matPolvo.opacity = clima === "tormenta" ? 0.7 : 0.45;
    if (precip?.tipo === "meteoros") { matTrazos.color.setHex(0xfff1c4); matTrazos.opacity = 0.9; }
    else { matTrazos.color.setHex(0xa9d0ff); matTrazos.opacity = 0.28; }
  }

  function animar(dt, tiempo) {
    if (nPolvo) {
      const viento = clima === "tormenta" ? 9 : 2.2;
      for (let i = 0; i < nPolvo; i++) {
        const j = i * 3;
        posPolvo[j] += viento * dt * (0.6 + 0.4 * Math.sin(fase[i]));
        posPolvo[j + 1] += Math.sin(tiempo * 1.3 + fase[i]) * dt * 0.5;
        posPolvo[j + 2] += Math.cos(tiempo * 0.7 + fase[i]) * dt * 0.6;
        if (posPolvo[j] > 15) { posPolvo[j] = -15; posPolvo[j + 1] = Math.random() * 7; }
        if (posPolvo[j + 1] < 0) posPolvo[j + 1] = 6.5;
        if (posPolvo[j + 1] > 7) posPolvo[j + 1] = 0.2;
      }
      geoPolvo.attributes.position.needsUpdate = true;
    }
    if (nTrazos) {
      const meteoros = precip.tipo === "meteoros";
      const viento = meteoros ? 14 : clima === "tormenta" ? 3.5 : 0.6;
      const caida = meteoros ? 30 : clima === "tormenta" ? 16 : 10;
      const largo = meteoros ? 0.06 : 0.035;
      const techo = meteoros ? 30 : 12;
      for (let i = 0; i < nTrazos; i++) {
        const j = i * 3;
        cabeza[j] += viento * dt;
        cabeza[j + 1] -= caida * dt;
        if (cabeza[j + 1] < 0) {
          cabeza[j + 1] = techo * (meteoros ? 0.5 + Math.random() * 0.5 : 1);
          cabeza[j] = (Math.random() - 0.5) * 18 - viento * (meteoros ? 1 : 0.5);
          cabeza[j + 2] = (Math.random() - 0.5) * 18;
        }
        posTrazos.set([cabeza[j], cabeza[j + 1], cabeza[j + 2],
          cabeza[j] - viento * largo, cabeza[j + 1] + caida * largo, cabeza[j + 2]], i * 6);
      }
      geoTrazos.attributes.position.needsUpdate = true;
    }
    // relámpagos (Tierra) y destellos de la tormenta solar (Luna)
    const conDestellos = clima === "tormenta" && (tema === TEMAS.tierra || tema === TEMAS.luna);
    if (conDestellos) {
      if (destello <= 0 && Math.random() < dt * 0.3) destello = 0.18;
      destello -= dt;
      hemi.intensity = destello > 0 ? 3 : tema.hemi.intensidad;
    }
    nubes.rotation.y = tiempo * 0.004;
    planetaTierra.rotation.y = tiempo * 0.02;
  }

  return {
    aplicar,
    animar,
    tema: () => tema,
    texRuido,
    estratos: (planeta) => {
      const clave = `estratos-${planeta}`;
      return cache[clave] || (cache[clave] = texturaEstratos(TEMAS[planeta].estratos));
    },
  };
}

// --------------------------------------------------------------- paisaje
function construirPaisaje(tema, texRuido, semilla) {
  const grupo = new THREE.Group();
  const r = rng(semilla.length * 97);
  const crateres = [];
  for (let i = 0; i < tema.relieve.crateres; i++) {
    const ang = r() * Math.PI * 2, dist = 12 + Math.pow(r(), 0.7) * 150;
    const radio = 1.5 + Math.pow(r(), 2.5) * 16;
    crateres.push({ x: Math.cos(ang) * dist, z: Math.sin(ang) * dist, r: radio, prof: radio * 0.22, borde: radio * 0.09 });
  }
  const R = tema.relieve;
  function altura(x, z) {
    const d = Math.max(Math.abs(x), Math.abs(z));
    if (d < 6) return -3;              // hueco bajo el mapa jugable
    const dist = Math.hypot(x, z);
    const k = suave(7, 30, d);
    let h = -0.02 + k * R.colinas * (fbm(x * 0.035 + 3, z * 0.035 - 7) - 0.45) * 2;
    h += suave(6, 9, d) * (fbm(x * 0.4, z * 0.4, 3) - 0.5) * 0.12;   // granulado cercano
    for (const c of crateres) {
      const q = Math.hypot(x - c.x, z - c.z) / c.r;
      if (q < 1.8) {
        const cuenco = q < 1 ? -c.prof * (1 - q * q) : 0;
        const borde = c.borde * Math.exp(-(((q - 1) / 0.28) ** 2));
        h += (cuenco + borde) * suave(7, 12, d);
      }
    }
    const cresta = 1 - Math.abs(fbm(x * 0.009 + 11, z * 0.009 - 4, 5) * 2 - 1);
    h += suave(70, 190, dist) * R.montanas * cresta * cresta;
    return h;
  }

  const tam = 480, seg = 240;            // 2 m por segmento: alineado con el borde del mapa (±6 m)
  const geo = new THREE.PlaneGeometry(tam, tam, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const colores = new Float32Array(pos.count * 3);
  const base = new THREE.Color(tema.paisaje.base), claro = new THREE.Color(tema.paisaje.claro);
  const oscuro = new THREE.Color(tema.paisaje.oscuro), alto = new THREE.Color(tema.paisaje.alto);
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    const h = altura(x, z);
    pos.setY(i, h);
    c.copy(base).lerp(claro, fbm(x * 0.05 + 50, z * 0.05, 3));
    c.lerp(oscuro, Math.max(0, -h) * 0.25 * (h > -2.5 ? 1 : 0));
    c.lerp(alto, suave(6, 30, h));
    colores.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute("color", new THREE.BufferAttribute(colores, 3));
  geo.computeVertexNormals();
  const tex = texRuido.clone();
  tex.repeat.set(tam / 6, tam / 6);
  tex.needsUpdate = true;
  const suelo = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, map: tex, roughness: 1 }));
  suelo.receiveShadow = true;
  grupo.add(suelo);

  // rocas sueltas
  const zonaLibre = (x, z) => Math.max(Math.abs(x), Math.abs(z)) < 7.5 || (x < -6 && x > -12 && z > 1 && z < 8);
  const geoRoca = new THREE.DodecahedronGeometry(1, 0);
  const colorRoca = new THREE.Color(tema.roca).lerp(new THREE.Color(tema.paisaje.base), 0.55);
  const rocas = new THREE.InstancedMesh(geoRoca, new THREE.MeshStandardMaterial({ color: colorRoca, roughness: 0.95, flatShading: true }), R.rocas);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), s = new THREE.Vector3(), p = new THREE.Vector3();
  let n = 0;
  while (n < R.rocas) {
    const ang = r() * Math.PI * 2, dist = 7 + Math.pow(r(), 1.6) * 70;
    const x = Math.cos(ang) * dist, z = Math.sin(ang) * dist;
    if (zonaLibre(x, z)) continue;
    const t = 0.05 + Math.pow(r(), 4) * (dist < 14 ? 0.3 : 0.9);
    p.set(x, altura(x, z) + t * 0.1, z);
    q.setFromEuler(e.set(r() * 3, r() * 3, r() * 3));
    s.set(t * (1 + r() * 0.5), t * (0.5 + r() * 0.4), t * (1 + r() * 0.5));
    rocas.setMatrixAt(n++, m.compose(p, q, s));
  }
  rocas.castShadow = true;
  grupo.add(rocas);

  // árboles (solo en la Tierra)
  if (R.arboles) {
    const copa = new THREE.InstancedMesh(new THREE.ConeGeometry(1, 2.6, 7), new THREE.MeshStandardMaterial({ color: 0x2f5a2a, roughness: 1, flatShading: true }), R.arboles);
    const tronco = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.12, 0.16, 0.8, 6), new THREE.MeshStandardMaterial({ color: 0x5a3d26 }), R.arboles);
    let k = 0;
    while (k < R.arboles) {
      const ang = r() * Math.PI * 2, dist = 14 + r() * 90;
      const x = Math.cos(ang) * dist, z = Math.sin(ang) * dist;
      if (zonaLibre(x, z) || fbm(x * 0.04, z * 0.04, 3) < 0.45) continue;
      const t = 0.7 + r() * 1.1, h = altura(x, z);
      copa.setMatrixAt(k, m.compose(p.set(x, h + 0.8 * t + 1.3 * t, z), q.identity(), s.set(t, t, t)));
      tronco.setMatrixAt(k, m.compose(p.set(x, h + 0.4 * t, z), q.identity(), s.set(t, t, t)));
      k++;
    }
    copa.castShadow = true;
    grupo.add(copa, tronco);
  }
  return grupo;
}

function crearHabitat() {
  const g = new THREE.Group();
  const blanco = new THREE.MeshStandardMaterial({ color: 0xe9e6df, roughness: 0.55 });
  const gris = new THREE.MeshStandardMaterial({ color: 0x5b6470, roughness: 0.6 });
  const panelMat = new THREE.MeshStandardMaterial({ color: 0x1b2f5a, roughness: 0.25, metalness: 0.6 });
  const domo = new THREE.Mesh(new THREE.SphereGeometry(1.25, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2), blanco);
  domo.position.set(0, 0, 0);
  const anillo = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.3, 0.25, 28), gris);
  anillo.position.y = 0.12;
  const modulo = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 1.8, 18), blanco);
  modulo.rotation.z = Math.PI / 2;
  modulo.position.set(1.9, 0.45, 0.3);
  const ventana = new THREE.Mesh(new THREE.CircleGeometry(0.18, 16), new THREE.MeshStandardMaterial({ color: 0x3fd0e0, emissive: 0x2a8fa0, emissiveIntensity: 1.2 }));
  ventana.position.set(0.55, 0.75, 1.1);
  ventana.lookAt(0.55 * 3, 0.75, 1.1 * 3);
  g.add(domo, anillo, modulo, ventana);
  for (let i = 0; i < 3; i++) {
    const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.7), gris);
    poste.position.set(-1.9, 0.35, -1.2 + i * 1.2);
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.03, 1.0), panelMat);
    panel.position.set(-1.9, 0.72, -1.2 + i * 1.2);
    panel.rotation.z = 0.5;
    g.add(poste, panel);
  }
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.6), gris);
  mastil.position.set(0.9, 1.6, -0.6);
  const antena = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 8, 0, Math.PI * 2, 0, Math.PI / 3), blanco);
  antena.position.set(0.9, 2.3, -0.6);
  antena.rotation.x = -0.9;
  g.add(mastil, antena);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.position.set(-9.2, -0.02, 4.4);
  g.rotation.y = 0.4;
  return g;
}
