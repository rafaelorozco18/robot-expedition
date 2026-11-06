// Efectos visuales y sonoros. No afectan la simulación: reaccionan a lo que trae cada cuadro.
import * as THREE from "three";

function texturaBola() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 2, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,.9)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export function crearEfectos(scene) {
  const grupo = new THREE.Group();
  const huellas = new THREE.Group();
  scene.add(grupo, huellas);
  const bola = texturaBola();
  const nubes = [];
  const geoHuella = new THREE.PlaneGeometry(0.22, 0.1);
  const matHuella = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.22, depthWrite: false });

  // confeti: un solo sistema de puntos reutilizable
  const N = 260;
  const pos = new Float32Array(N * 3), col = new Float32Array(N * 3), vel = new Float32Array(N * 3);
  const geoConfeti = new THREE.BufferGeometry();
  geoConfeti.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geoConfeti.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const confeti = new THREE.Points(geoConfeti, new THREE.PointsMaterial({ size: 0.055, vertexColors: true, transparent: true }));
  confeti.visible = false;
  confeti.frustumCulled = false;
  scene.add(confeti);
  let vidaConfeti = 0;
  const paleta = [0xff7a1a, 0x3fd0e0, 0x39c16c, 0xf2b632, 0xff5a7a, 0xffffff].map((c) => new THREE.Color(c));

  return {
    polvo(p, color, n = 5, fuerza = 1) {
      for (let i = 0; i < n; i++) {
        const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: bola, color, transparent: true, opacity: 0.6, depthWrite: false }));
        s.position.set(p.x + (Math.random() - 0.5) * 0.12, 0.04, p.z + (Math.random() - 0.5) * 0.12);
        s.scale.setScalar(0.08);
        grupo.add(s);
        nubes.push({ s, vida: 0.7 * fuerza, total: 0.7 * fuerza, v: new THREE.Vector3((Math.random() - 0.5) * 0.5 * fuerza, (0.2 + Math.random() * 0.3) * fuerza, (Math.random() - 0.5) * 0.5 * fuerza) });
      }
    },
    huella(p, rumbo) {
      const m = new THREE.Mesh(geoHuella, matHuella);
      m.rotation.set(-Math.PI / 2, 0, rumbo);
      m.position.set(p.x, 0.006, p.z);
      huellas.add(m);
      if (huellas.children.length > 70) huellas.remove(huellas.children[0]);
    },
    confeti(p) {
      for (let i = 0; i < N; i++) {
        pos.set([p.x, p.y + 0.4, p.z], i * 3);
        const a = Math.random() * Math.PI * 2, r = 1 + Math.random() * 2.5;
        vel.set([Math.cos(a) * r, 2.5 + Math.random() * 3.5, Math.sin(a) * r], i * 3);
        const c = paleta[i % paleta.length];
        col.set([c.r, c.g, c.b], i * 3);
      }
      geoConfeti.attributes.color.needsUpdate = true;
      confeti.visible = true;
      confeti.material.opacity = 1;
      vidaConfeti = 3;
    },
    limpiar() {
      huellas.clear();
      nubes.length = 0;
      grupo.clear();
    },
    actualizar(dt) {
      for (let i = nubes.length - 1; i >= 0; i--) {
        const n = nubes[i];
        n.vida -= dt;
        n.s.position.addScaledVector(n.v, dt);
        n.s.scale.addScalar(dt * 0.7);
        n.s.material.opacity = 0.6 * Math.max(0, n.vida / n.total);
        if (n.vida <= 0) { grupo.remove(n.s); n.s.material.dispose(); nubes.splice(i, 1); }
      }
      if (vidaConfeti > 0) {
        vidaConfeti -= dt;
        for (let i = 0; i < N; i++) {
          const j = i * 3;
          vel[j + 1] -= 6 * dt;
          pos[j] += vel[j] * dt; pos[j + 1] += vel[j + 1] * dt; pos[j + 2] += vel[j + 2] * dt;
          if (pos[j + 1] < 0.02) { pos[j + 1] = 0.02; vel[j] = vel[j + 1] = vel[j + 2] = 0; }
        }
        geoConfeti.attributes.position.needsUpdate = true;
        confeti.material.opacity = Math.min(1, vidaConfeti);
        if (vidaConfeti <= 0) confeti.visible = false;
      }
    },
  };
}

// Sonidos sintetizados: no requieren archivos.
export function crearSonido() {
  let ctx = null;
  let activo = true;
  const tono = (f, t0, dur, tipo = "sine", vol = 0.12) => {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = tipo;
    o.frequency.value = f;
    g.gain.setValueAtTime(vol, ctx.currentTime + t0);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t0 + dur);
    o.connect(g).connect(ctx.destination);
    o.start(ctx.currentTime + t0);
    o.stop(ctx.currentTime + t0 + dur);
  };
  const SONIDOS = {
    paso: () => tono(110, 0, 0.06, "triangle", 0.05),
    caida: () => { tono(160, 0, 0.3, "sawtooth", 0.14); tono(70, 0.08, 0.4, "sine", 0.2); },
    empujon: () => tono(420, 0, 0.18, "square", 0.05),
    nivel: () => { tono(520, 0, 0.1); tono(780, 0.09, 0.14); },
    exito: () => [523, 659, 784, 1047].forEach((f, i) => tono(f, i * 0.1, 0.25, "triangle", 0.13)),
  };
  return {
    iniciar() { ctx ??= new (window.AudioContext || window.webkitAudioContext)(); ctx.resume(); },
    sonar(n) { if (activo && ctx) SONIDOS[n](); },
    alternar() { activo = !activo; return activo; },
  };
}
