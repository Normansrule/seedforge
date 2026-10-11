// M4 auxiliary tail forming (experimental): clamp a wet blank, sweep it around a former,
// hold while it dries, release. Tail curvature is a RECONSTRUCTED reference, not a measured target.
import * as THREE from "three";
import type { Anim } from "./player";
import { C, ThreeBase, k, mat } from "./three-base";

const L = 30, N = 60, TH = 0.5, W = 2.5, RF = 9, WRAP = (150 * Math.PI) / 180;

export class TailAnim extends ThreeBase implements Anim {
  duration = 12;
  phases = [
    { t: 0, text: "Wet tail blank placed against the former (T01/T02)." },
    { t: 1, text: "Blank clamp (T04, PCA9685 CH3) closes on the root end." },
    { t: 2.2, text: "Sweep shoe (T03, CH2) rotates around the former and wraps the blank." },
    { t: 6.4, text: "Hold in the former while it dries (M5 conditions logged)." },
    { t: 9, text: "Release: measure springback and dried shape; Phase 3 needs >= 20 repeatable tails." },
  ];
  private segs: THREE.Mesh[] = [];
  private segMat = mat(C.wood, { roughness: 0.8 });
  private shoe = new THREE.Group();
  private clamp = new THREE.Mesh(new THREE.BoxGeometry(8, 3, 6), mat(C.silicone));

  mount(stage: HTMLElement) {
    this.mountRenderer(stage);
    const s = this.scene;
    const former = new THREE.Mesh(new THREE.CylinderGeometry(RF - TH / 2, RF - TH / 2, 5, 64, 1, false, 0, Math.PI * 2),
      mat(C.printed));
    former.rotation.x = Math.PI / 2;
    former.position.set(0, -RF, 0);
    s.add(former);
    const base = new THREE.Mesh(new THREE.BoxGeometry(40, 4, 8), mat(C.printed));
    base.position.set(-12, -RF - 12, 0);
    s.add(base);
    const anvil = new THREE.Mesh(new THREE.BoxGeometry(12, 3, 6), mat(C.printed));
    anvil.position.set(-6, -1.75, 0);
    s.add(anvil);
    this.clamp.position.set(-6, 5, 0);
    s.add(this.clamp);
    for (let i = 0; i < N; i++) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(L / N + 0.05, TH, W), this.segMat);
      this.segs.push(m);
      s.add(m);
    }
    const shoeBody = new THREE.Mesh(new THREE.BoxGeometry(4, 3, 6), mat(C.accent));
    shoeBody.position.y = RF + 2;
    this.shoe.add(shoeBody);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, RF + 1, 3), mat(C.dark));
    arm.position.set(0, (RF + 1) / 2, -3.5);
    this.shoe.add(arm);
    s.add(this.shoe);
    this.camera.fov = 30;
    this.camera.position.set(4, 4, 70);
    this.camera.lookAt(4, -8, 0);
  }

  /** Position and heading of the strip centre-line at arc length u for wrap angle theta. */
  private pose(u: number, theta: number, kappaScale: number) {
    const r = RF / kappaScale;
    const wrapLen = r * theta;
    if (u <= 0) return { x: u, y: 0, a: 0 };
    if (u <= wrapLen) {
      const f = u / r;
      return { x: r * Math.sin(f), y: -r * (1 - Math.cos(f)), a: -f };
    }
    const f = theta;
    const x0 = r * Math.sin(f), y0 = -r * (1 - Math.cos(f));
    const d = u - wrapLen;
    return { x: x0 + d * Math.cos(f), y: y0 - d * Math.sin(f), a: -f };
  }

  render(t: number) {
    this.clamp.position.y = 5 - 3.25 * k(t, 1, 1.8) * (1 - k(t, 9.2, 9.8));
    const theta = WRAP * k(t, 2.2, 6.2);
    const spring = 1 - 0.12 * k(t, 9.6, 10.6);
    const wet = 1 - k(t, 6.4, 9);
    this.segMat.color.setHex(C.woodDry).lerp(new THREE.Color(C.wood), wet);
    for (let i = 0; i < N; i++) {
      const u = -4 + ((i + 0.5) / N) * (L);
      const p = this.pose(u, theta, spring);
      const m = this.segs[i];
      m.position.set(p.x, p.y, 0);
      m.rotation.z = p.a;
    }
    this.shoe.position.set(0, -RF, 0);
    this.shoe.rotation.z = -theta;
    this.shoe.visible = t < 9.4;
    this.draw();
  }
}
