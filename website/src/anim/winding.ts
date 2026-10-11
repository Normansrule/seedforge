// Synchronized winding: the mandrel turns while the guide traverses one pitch per revolution.
// Geometry is to scale (paper-reference recipe: 0.8 mm mandrel, 2.5 x 0.5 mm strip, 5.0 mm/rev).
import * as THREE from "three";
import type { Anim } from "./player";
import { C, ThreeBase, helixRibbon, k, mat } from "./three-base";

const D = 0.8, TH = 0.5, W = 2.5, P = 5.0, TURNS = 8, X0 = 3;
const T_WIND0 = 2, T_WIND1 = 13, T_ACC = 1.6;

/** Trapezoidal motion profile: turns completed at time t. */
export function turnsAt(t: number) {
  if (t <= T_WIND0) return 0;
  if (t >= T_WIND1) return TURNS;
  const T = T_WIND1 - T_WIND0, v = TURNS / (T - T_ACC), a = v / T_ACC, u = t - T_WIND0;
  if (u < T_ACC) return 0.5 * a * u * u;
  if (u > T - T_ACC) { const r = T - u; return TURNS - 0.5 * a * r * r; }
  return 0.5 * a * T_ACC * T_ACC + v * (u - T_ACC);
}

export class WindingAnim extends ThreeBase implements Anim {
  duration = 16;
  phases = [
    { t: 0, text: "HOME + PRETENSION: carriage at the start position, strip held by the guide." },
    { t: T_WIND0, text: "WIND: Timer1 Bresenham keeps 3200 rotation microsteps per 400 x pitch linear microsteps." },
    { t: T_WIND1, text: "VERIFY: the overhead camera checks pitch, gaps/overlap and turn count before release." },
  ];
  private spin = new THREE.Group();
  private coil?: THREE.Mesh;
  private segs = 0;
  private feed = new THREE.Mesh(new THREE.BoxGeometry(1, TH, W), mat(C.wood, { roughness: 0.8 }));
  private guide = new THREE.Group();

  mount(stage: HTMLElement) {
    this.mountRenderer(stage);
    const s = this.scene;
    // chuck (fixed body + rotating jaw marker) and mandrel
    const chuck = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 4.2, 10, 48), mat(C.dark, { metalness: 0.6, roughness: 0.35 }));
    chuck.rotation.z = Math.PI / 2; chuck.position.x = -6; s.add(chuck);
    const nose = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 3.4, 4, 48), mat(C.dark, { metalness: 0.6, roughness: 0.35 }));
    nose.rotation.z = Math.PI / 2; nose.position.x = 1; this.spin.add(nose);
    const flag = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.8, 1.2), mat(C.red));
    flag.position.set(-6, 4.4, 0); this.spin.add(flag);
    const mandrel = new THREE.Mesh(new THREE.CylinderGeometry(D / 2, D / 2, 72, 24), mat(C.metal, { metalness: 0.85, roughness: 0.25 }));
    mandrel.rotation.z = Math.PI / 2; mandrel.position.x = 30; this.spin.add(mandrel);
    const rib = helixRibbon(D, TH, W, P, TURNS, X0, 72);
    this.segs = rib.segments;
    this.coil = new THREE.Mesh(rib.geometry, mat(C.wood, { roughness: 0.75, side: THREE.DoubleSide }));
    this.spin.add(this.coil);
    s.add(this.spin);
    // far support (W05) and traverse rail (schematic)
    const w05 = new THREE.Mesh(new THREE.BoxGeometry(6, 14, 10), mat(C.printed));
    w05.position.set(64, -4, 0); s.add(w05);
    const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 80, 16), mat(C.metal, { metalness: 0.8, roughness: 0.3 }));
    rail.rotation.z = Math.PI / 2; rail.position.set(28, -16, 24); s.add(rail);
    // guide (F06/F07 on W12) riding the traverse
    const body = new THREE.Mesh(new THREE.BoxGeometry(8, 3.2, 7), mat(C.accent));
    this.guide.add(body);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 12), mat(C.printed));
    arm.position.set(0, -1.5, 6);
    const post = new THREE.Mesh(new THREE.BoxGeometry(2, 14, 2), mat(C.printed));
    post.position.set(0, -8, 11);
    this.guide.add(post); this.guide.add(arm);
    s.add(this.guide);
    s.add(this.feed);
    this.camera.fov = 28;
    this.camera.position.set(34, 42, 108);
    this.camera.lookAt(30, 0, 6);
  }

  render(t: number) {
    const n = turnsAt(t);
    const done = Math.min(this.segs, Math.round((n / TURNS) * this.segs));
    this.coil!.geometry.setDrawRange(0, done * 24);
    this.spin.rotation.x = -2 * Math.PI * n;
    // contact point is always at the top of the mandrel; feed leaves along the helix tangent
    const R = (D + TH) / 2;
    const contact = new THREE.Vector3(X0 + P * n, R, 0);
    const T = new THREE.Vector3(P / (2 * Math.PI), 0, R).normalize();
    const L = 22;
    const end = contact.clone().addScaledVector(T, L);
    this.feed.scale.set(L, 1, 1);
    this.feed.position.copy(contact).addScaledVector(T, L / 2);
    this.feed.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), T);
    this.guide.position.copy(end).add(new THREE.Vector3(0, 0, 3.5));
    this.guide.quaternion.copy(this.feed.quaternion);
    // VERIFY flash
    const v = k(t, T_WIND1, T_WIND1 + 0.4) * (1 - k(t, this.duration - 0.6, this.duration));
    (this.coil!.material as THREE.MeshStandardMaterial).emissive.setRGB(0.05 * v, 0.18 * v, 0.1 * v);
    this.draw();
  }

  hud(t: number) {
    const n = turnsAt(t);
    return `<span>turn <b>${Math.min(TURNS, Math.floor(n + 1e-6))}</b> / ${TURNS}</span>
      <span>rotation <b>${Math.round(n * 3200)}</b> usteps</span>
      <span>linear <b>${Math.round(n * P * 400)}</b> usteps</span>
      <span>carriage <b>${(5 + P * n).toFixed(2)}</b> mm from home</span>`;
  }
}
