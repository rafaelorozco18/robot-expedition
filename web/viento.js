// Viento visible: estelas de polvo que viajan con la fuerza que aplica el simulador y una manga
// de viento junto al robot. La fuerza viene en cada cuadro del episodio (N, ejes de MuJoCo).
import * as THREE from "three";

export function crearViento(scene) {
  const N = 700, CAJA = 9, ALTO = 2.6;
  const cabeza = new Float32Array(N * 3);
  const pos = new Float32Array(N * 6);
  for (let i = 0; i < N; i++) cabeza.set([(Math.random() - 0.5) * CAJA, Math.random() * ALTO, (Math.random() - 0.5) * CAJA], i * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const estelas = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0xf3d2b0, transparent: true, opacity: 0, depthWrite: false }));
  estelas.frustumCulled = false;
  scene.add(estelas);

  // Manga de viento: un poste y un cono a franjas que se orienta y se infla con la fuerza.
  const manga = new THREE.Group();
  const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.025, 1.6, 8), new THREE.MeshStandardMaterial({ color: 0x9aa3ad, metalness: 0.6, roughness: 0.4 }));
  poste.position.y = 0.8;
  const c = document.createElement("canvas");
  c.width = 64; c.height = 8;
  const ctx = c.getContext("2d");
  for (let k = 0; k < 4; k++) { ctx.fillStyle = k % 2 ? "#ffffff" : "#ff6a1a"; ctx.fillRect(k * 16, 0, 16, 8); }
  const tela = new THREE.CanvasTexture(c);
  tela.colorSpace = THREE.SRGBColorSpace;
  const cono = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.05, 0.6, 16, 1, true), new THREE.MeshStandardMaterial({ map: tela, side: THREE.DoubleSide, roughness: 0.8 }));
  cono.geometry.rotateZ(-Math.PI / 2);
  cono.geometry.translate(0.3, 0, 0);
  const pivote = new THREE.Group();
  pivote.position.y = 1.55;
  pivote.add(cono);
  manga.add(poste, pivote);
  manga.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  manga.visible = estelas.visible = false;
  scene.add(manga);

  const direccion = new THREE.Vector3(1, 0, 0);
  let fuerza = 0, aleteo = 0;

  return {
    // f: [fx, fy] en N (MuJoCo). centro: posición del robot en la escena.
    actualizar(dt, f, centro) {
      const activo = Boolean(f) && Math.hypot(f[0], f[1]) > 0.5;
      estelas.visible = manga.visible = activo;
      if (!activo) return;
      const objetivo = new THREE.Vector3(f[0], 0, -f[1]);
      fuerza += (objetivo.length() - fuerza) * Math.min(1, dt * 6);
      direccion.lerp(objetivo.normalize(), Math.min(1, dt * 5)).normalize();
      const v = 1.5 + fuerza * 0.35;
      estelas.material.opacity = Math.min(0.75, 0.15 + fuerza / 40);
      const largo = 0.08 + fuerza * 0.012;
      for (let i = 0; i < N; i++) {
        const j = i * 3;
        cabeza[j] += direccion.x * v * dt;
        cabeza[j + 2] += direccion.z * v * dt;
        cabeza[j + 1] += Math.sin(aleteo + i) * dt * 0.3;
        // recicla las partículas que salen de la caja que rodea al robot
        for (const [eje, k] of [[0, "x"], [2, "z"]]) {
          const rel = cabeza[j + eje] - centro[k];
          if (rel > CAJA / 2) cabeza[j + eje] -= CAJA;
          if (rel < -CAJA / 2) cabeza[j + eje] += CAJA;
        }
        if (cabeza[j + 1] < 0.05 || cabeza[j + 1] > ALTO) cabeza[j + 1] = 0.1 + Math.random() * (ALTO - 0.2);
        pos.set([cabeza[j], cabeza[j + 1], cabeza[j + 2],
          cabeza[j] - direccion.x * largo, cabeza[j + 1], cabeza[j + 2] - direccion.z * largo], i * 6);
      }
      geo.attributes.position.needsUpdate = true;
      aleteo += dt * (4 + fuerza * 0.3);
      manga.position.set(centro.x + 1.1, 0, centro.z - 1.1);
      pivote.rotation.y = Math.atan2(-direccion.z, direccion.x);
      const inflado = Math.min(1, fuerza / 20);
      pivote.rotation.z = -(1 - inflado) * 1.2 + Math.sin(aleteo) * 0.05 * inflado;
      cono.scale.set(1, 0.6 + 0.4 * inflado, 0.6 + 0.4 * inflado);
    },
    ocultar() { estelas.visible = manga.visible = false; },
  };
}
