// Aspecto del robot. La física sigue siendo la del simulador: cada pieza decorativa cuelga
// de un cuerpo de MuJoCo, y su posición viene de los cuadros del episodio.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/RoundedBoxGeometry.js";

const CERAMICA = 0xece9e2, GRAFITO = 0x20262e;

function mat(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness: 0.08, ...extra });
}

function dibujarCara(ctx, gesto, color) {
  const n = 128;
  ctx.fillStyle = "#07121b";
  ctx.fillRect(0, 0, n, n);
  ctx.strokeStyle = ctx.fillStyle = color;
  ctx.lineWidth = 9;
  ctx.lineCap = "round";
  const ojo = (x, f) => { ctx.beginPath(); f(x); ctx.stroke(); };
  const redondo = (x, r) => { ctx.beginPath(); ctx.arc(x, 56, r, 0, Math.PI * 2); ctx.fill(); };
  if (gesto === "feliz") {
    for (const x of [40, 88]) ojo(x, (c) => ctx.arc(c, 62, 15, Math.PI * 1.1, Math.PI * 1.9));
    ojo(64, (c) => ctx.arc(c, 74, 24, Math.PI * 0.15, Math.PI * 0.85));
  } else if (gesto === "asustado") {
    redondo(40, 15); redondo(88, 15);
    ctx.fillStyle = "#07121b"; redondo(40, 7); redondo(88, 7);
    ctx.fillStyle = color;
    ojo(64, (c) => ctx.arc(c, 98, 9, 0, Math.PI * 2));
  } else if (gesto === "mareado") {
    for (const x of [40, 88]) {
      ctx.beginPath();
      ctx.moveTo(x - 13, 43); ctx.lineTo(x + 13, 69);
      ctx.moveTo(x + 13, 43); ctx.lineTo(x - 13, 69);
      ctx.stroke();
    }
    ojo(64, (c) => ctx.arc(c, 108, 18, Math.PI * 1.15, Math.PI * 1.85));
  } else if (gesto === "esfuerzo") {
    for (const x of [40, 88]) { ctx.beginPath(); ctx.moveTo(x - 15, 56); ctx.lineTo(x + 15, 56); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(50, 92); ctx.lineTo(78, 92); ctx.stroke();
  } else {
    redondo(40, 11); redondo(88, 11);
    ctx.beginPath(); ctx.moveTo(52, 90); ctx.lineTo(76, 90); ctx.stroke();
  }
}

export function crearRobot(datos, { acento = 0xff7a1a, colorCara = "#5fe3f0" } = {}) {
  const raiz = new THREE.Group();
  raiz.rotation.x = -Math.PI / 2;  // MuJoCo usa z arriba
  const cuerpos = datos.cuerpos.map(() => { const g = new THREE.Group(); raiz.add(g); return g; });
  const color = new THREE.Color(acento);
  const pieza = (padre, geo, material, pos = [0, 0, 0]) => {
    const m = new THREE.Mesh(geo, material);
    m.position.set(...pos);
    m.castShadow = true;
    padre.add(m);
    return m;
  };
  const blanco = mat(CERAMICA), oscuro = mat(GRAFITO, { roughness: 0.6 }), detalle = mat(color, { roughness: 0.35 });
  const brillo = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 1.6 });

  const lienzo = document.createElement("canvas");
  lienzo.width = lienzo.height = 128;
  const ctx = lienzo.getContext("2d");
  const textura = new THREE.CanvasTexture(lienzo);
  textura.colorSpace = THREE.SRGBColorSpace;
  let gestoActual = null;
  const fijarGesto = (gesto) => {
    if (gesto === gestoActual) return;
    gestoActual = gesto;
    dibujarCara(ctx, gesto, colorCara);
    textura.needsUpdate = true;
  };
  fijarGesto("normal");

  const decorar = {
    torso(g) {
      pieza(g, new RoundedBoxGeometry(0.17, 0.27, 0.39, 4, 0.035), blanco, [0, 0, 0.22]);
      pieza(g, new RoundedBoxGeometry(0.03, 0.2, 0.17, 2, 0.012), detalle, [0.083, 0, 0.27]);
      const nucleo = pieza(g, new THREE.CircleGeometry(0.034, 24), brillo, [0.1, 0, 0.27]);
      nucleo.rotation.y = Math.PI / 2;
      pieza(g, new RoundedBoxGeometry(0.1, 0.19, 0.27, 3, 0.02), oscuro, [-0.12, 0, 0.26]);
      for (const y of [-0.05, 0.05]) {
        const tobera = pieza(g, new THREE.CylinderGeometry(0.022, 0.03, 0.05, 12), detalle, [-0.12, y, 0.1]);
        tobera.rotation.x = Math.PI / 2;
      }
      for (const y of [-0.15, 0.15]) pieza(g, new THREE.SphereGeometry(0.052, 16, 12), detalle, [0, y, 0.37]);
      for (const y of [-0.09, 0.09]) pieza(g, new THREE.SphereGeometry(0.06, 16, 12), oscuro, [0, y, 0]);
      const cuello = pieza(g, new THREE.CylinderGeometry(0.035, 0.045, 0.06, 12), oscuro, [0, 0, 0.43]);
      cuello.rotation.x = Math.PI / 2;
      pieza(g, new THREE.SphereGeometry(0.098, 28, 20), blanco, [0, 0, 0.51]);
      const pantalla = pieza(g, new THREE.CircleGeometry(0.075, 28), new THREE.MeshStandardMaterial({
        map: textura, emissive: 0xffffff, emissiveMap: textura, emissiveIntensity: 1.1,
      }), [0.0855, 0, 0.51]);
      pantalla.castShadow = false;
      pantalla.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(
        new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(1, 0, 0)));
      const aro = pieza(g, new THREE.TorusGeometry(0.076, 0.008, 10, 32), detalle, [0.084, 0, 0.51]);
      aro.quaternion.copy(pantalla.quaternion);
      const antena = pieza(g, new THREE.CylinderGeometry(0.005, 0.007, 0.1, 8), oscuro, [-0.03, 0.05, 0.64]);
      antena.rotation.x = Math.PI / 2;
      pieza(g, new THREE.SphereGeometry(0.017, 12, 10), brillo, [-0.03, 0.05, 0.695]);
    },
    muslo(g) {
      const hueso = pieza(g, new THREE.CapsuleGeometry(0.045, 0.32, 6, 16), blanco, [0, 0, -0.2]);
      hueso.rotation.x = Math.PI / 2;
      const placa = pieza(g, new THREE.CylinderGeometry(0.056, 0.049, 0.14, 16), detalle, [0, 0, -0.17]);
      placa.rotation.x = Math.PI / 2;
    },
    pantorrilla(g) {
      pieza(g, new THREE.SphereGeometry(0.056, 16, 12), oscuro);
      const hueso = pieza(g, new THREE.CapsuleGeometry(0.04, 0.32, 6, 16), blanco, [0, 0, -0.2]);
      hueso.rotation.x = Math.PI / 2;
      const placa = pieza(g, new THREE.CylinderGeometry(0.05, 0.043, 0.15, 16), oscuro, [0, 0, -0.16]);
      placa.rotation.x = Math.PI / 2;
    },
    pie(g) {
      pieza(g, new THREE.SphereGeometry(0.04, 14, 10), oscuro);
      pieza(g, new RoundedBoxGeometry(0.22, 0.1, 0.04, 3, 0.016), oscuro, [0.03, 0, -0.04]);
      pieza(g, new RoundedBoxGeometry(0.2, 0.088, 0.012, 2, 0.004), detalle, [0.03, 0, -0.058]);
    },
  };
  datos.cuerpos.forEach((nombre, i) => decorar[nombre.split("_")[0]]?.(cuerpos[i]));

  const qA = new THREE.Quaternion(), qB = new THREE.Quaternion();
  const robot = {
    raiz, cuerpos, fijarGesto,
    indicesPies: [datos.cuerpos.indexOf("pie_i"), datos.cuerpos.indexOf("pie_d")],
    posar(A, B, f) {
      cuerpos.forEach((grupo, i) => {
        const a = A.cuerpos[i], b = B.cuerpos[i];
        grupo.position.set(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f);
        qA.set(a[4], a[5], a[6], a[3]);
        qB.set(b[4], b[5], b[6], b[3]);
        grupo.quaternion.copy(qA).slerp(qB, f);
      });
    },
    cabeza() { return cuerpos[0].localToWorld(new THREE.Vector3(0, 0, 0.62)); },
    pieEnMundo(i) { return cuerpos[robot.indicesPies[i]].localToWorld(new THREE.Vector3(0.03, 0, -0.06)); },
    destruir() {
      raiz.parent?.remove(raiz);
      raiz.traverse((o) => { o.geometry?.dispose(); });
      textura.dispose();
    },
  };
  return robot;
}

// Gesto según lo que el simulador dice que está pasando.
export function gestoDe(f, final) {
  if (final) return final;
  if (f.empujon || f.inclinacion > 20) return "asustado";
  if (Math.max(...f.torques.map(Math.abs)) > 0.7) return "esfuerzo";
  return "normal";
}
