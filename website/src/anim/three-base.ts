// Small Three.js scaffolding shared by the 3D animations.
import * as THREE from "three";

export const C = {
  wood: 0xc8a165,
  woodDark: 0x9c7442,
  woodDry: 0xb08850,
  metal: 0xb8bec6,
  dark: 0x4a5560,
  printed: 0xe9ecef,
  accent: 0x2f6f4f,
  silicone: 0x7fb8a2,
  seed: 0x6b4a2b,
  tip: 0x8a9a5b,
  red: 0xb03a2e,
  amber: 0xd39b2a,
};

export function mat(color: number, opts: Partial<THREE.MeshStandardMaterialParameters> = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.05, ...opts });
}

export class ThreeBase {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(30, 16 / 9, 0.1, 5000);
  renderer?: THREE.WebGLRenderer;

  mountRenderer(stage: HTMLElement) {
    const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    stage.appendChild(r.domElement);
    this.renderer = r;
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x7d848c, 1.7));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(30, 60, 50);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.6);
    fill.position.set(-40, 10, -30);
    this.scene.add(fill);
  }

  resize(w: number, h: number) {
    if (!this.renderer || !w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  draw() { this.renderer?.render(this.scene, this.camera); }
}

/** Piecewise-linear interpolation helper: k(t, t0, t1) -> 0..1 with smoothstep easing. */
export function k(t: number, t0: number, t1: number) {
  const x = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
  return x * x * (3 - 2 * x);
}

/**
 * Helical ribbon (veneer strip) around the X axis.
 * Centre-line radius R = (d + t)/2, pitch p per revolution, width w, thickness th.
 * Cross-section: width along the in-surface direction perpendicular to the helix tangent.
 */
export function helixRibbon(d: number, th: number, w: number, p: number, turns: number, x0 = 0, seg = 64) {
  const R = (d + th) / 2;
  const n = Math.max(2, Math.round(turns * seg));
  const pos: number[] = [];
  const idx: number[] = [];
  const lead = p / (2 * Math.PI);
  for (let i = 0; i <= n; i++) {
    const s = (i / n) * turns;
    const a = 2 * Math.PI * s;
    const c = new THREE.Vector3(x0 + p * s, R * Math.cos(a), R * Math.sin(a));
    const T = new THREE.Vector3(lead, -R * Math.sin(a), R * Math.cos(a)).normalize();
    const N = new THREE.Vector3(0, Math.cos(a), Math.sin(a));
    const B = new THREE.Vector3().crossVectors(T, N).normalize();
    for (const [sw, sn] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      const v = c.clone().addScaledVector(B, (sw * w) / 2).addScaledVector(N, (sn * th) / 2);
      pos.push(v.x, v.y, v.z);
    }
  }
  for (let i = 0; i < n; i++) {
    const a = i * 4, b = (i + 1) * 4;
    for (let q = 0; q < 4; q++) {
      const q1 = (q + 1) % 4;
      idx.push(a + q, b + q, b + q1, a + q, b + q1, a + q1);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return { geometry: g, segments: n, indicesPerSegment: 24, R };
}

/** Straight strip (box) between two points with a given width direction hint. */
export function stripBetween(a: THREE.Vector3, b: THREE.Vector3, w: number, th: number, material: THREE.Material) {
  const len = a.distanceTo(b);
  const m = new THREE.Mesh(new THREE.BoxGeometry(len, th, w), material);
  m.position.copy(a).add(b).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), b.clone().sub(a).normalize());
  return m;
}
