// M3 sequence as implemented in the firmware: CLAMP -> CUT -> DEMOLD (support closes,
// relative axial retraction, support opens, clamp opens) -> COMPLETE.
import * as THREE from "three";
import type { Anim } from "./player";
import { C, ThreeBase, helixRibbon, k, mat } from "./three-base";

const D = 0.8, TH = 0.5, W = 2.5, P = 5.0, X0 = 3, TURNS = 8;

export class DemoldAnim extends ThreeBase implements Anim {
  duration = 13;
  phases = [
    { t: 0, text: "Wound coil on the mandrel, strip still attached to the guide." },
    { t: 1, text: "CLAMP (PCA9685 CH0): soft jaws grip only the sacrificial turn." },
    { t: 2.6, text: "CUT (CH1): guarded purchased micro shear cuts the strip; guard switch must stay closed." },
    { t: 4.2, text: "DEMOLD 1 (CH6): compliant split support closes lightly around the wet coil." },
    { t: 5.6, text: "DEMOLD 2: relative axial retraction (SET_DEMOLD, 2 mm/s): the coil slides off the free mandrel end." },
    { t: 8.8, text: "DEMOLD 3-4: support opens, clamp opens; the wet body is released without dragging." },
    { t: 10.6, text: "COMPLETE: body goes to free drying (M5). Phase 2 must show 20/20 clean releases." },
  ];
  private carrier = new THREE.Group();   // coil + support + clamp, moved together during retraction
  private coil = new THREE.Group();
  private jawA = new THREE.Mesh(new THREE.BoxGeometry(5, 3, 6), mat(C.silicone));
  private jawB = new THREE.Mesh(new THREE.BoxGeometry(5, 3, 6), mat(C.silicone));
  private supA = new THREE.Mesh();
  private supB = new THREE.Mesh();
  private blade = new THREE.Group();
  private feed = new THREE.Mesh(new THREE.BoxGeometry(18, TH, W), mat(C.wood, { roughness: 0.8 }));
  private tray = new THREE.Mesh(new THREE.BoxGeometry(60, 2, 24), mat(C.printed));

  mount(stage: HTMLElement) {
    this.mountRenderer(stage);
    const s = this.scene;
    const chuck = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 4.2, 10, 48), mat(C.dark, { metalness: 0.6, roughness: 0.35 }));
    chuck.rotation.z = Math.PI / 2; chuck.position.x = -6; s.add(chuck);
    const mandrel = new THREE.Mesh(new THREE.CylinderGeometry(D / 2, D / 2, 52, 24), mat(C.metal, { metalness: 0.85, roughness: 0.25 }));
    mandrel.rotation.z = Math.PI / 2; mandrel.position.x = 25; s.add(mandrel);   // free end at x = 51 (W05 removed)
    const rib = helixRibbon(D, TH, W, P, TURNS, X0, 64);
    this.coil.add(new THREE.Mesh(rib.geometry, mat(C.wood, { roughness: 0.75, side: THREE.DoubleSide })));
    this.carrier.add(this.coil);
    // clamp jaws around the last (sacrificial) turn
    const xc = X0 + P * (TURNS - 0.5);
    this.jawA.position.set(xc, 6, 0); this.jawB.position.set(xc, -6, 0);
    this.carrier.add(this.jawA, this.jawB);
    // split support: two half shells around the active turns
    const half = (sign: number) => {
      const g = new THREE.CylinderGeometry(2.6, 2.6, P * 7, 32, 1, true, sign > 0 ? 0 : Math.PI, Math.PI);
      const m = new THREE.Mesh(g, mat(C.silicone, { side: THREE.DoubleSide, transparent: true, opacity: 0.75 }));
      m.rotation.z = Math.PI / 2;
      return m;
    };
    this.supA = half(1); this.supB = half(-1);
    this.carrier.add(this.supA, this.supB);
    s.add(this.carrier);
    // feed strip to the guide and the cutter
    this.feed.position.set(xc + 2, 0.65, 10);
    this.feed.rotation.y = -Math.atan2(2 * Math.PI * 0.65, P);
    s.add(this.feed);
    const bladeBody = new THREE.Mesh(new THREE.BoxGeometry(1, 12, 5), mat(C.metal, { metalness: 0.9, roughness: 0.2 }));
    bladeBody.position.y = 6;
    this.blade.add(bladeBody);
    const guard = new THREE.Mesh(new THREE.BoxGeometry(9, 16, 9), mat(0x9fc3d6, { transparent: true, opacity: 0.25 }));
    guard.position.y = 7;
    this.blade.add(guard);
    this.blade.position.set(xc + 3, 2, 6);
    s.add(this.blade);
    this.tray.position.set(70, -14, 0);
    s.add(this.tray);
    this.camera.fov = 30;
    this.camera.position.set(48, 60, 165);
    this.camera.lookAt(48, -4, 0);
  }

  render(t: number) {
    const clamp = k(t, 1, 2.2) * (1 - k(t, 9.6, 10.4));
    this.jawA.position.y = 6 - 3.6 * clamp;
    this.jawB.position.y = -6 + 3.6 * clamp;
    const cut = k(t, 2.8, 3.5) * (1 - k(t, 3.6, 4.1));
    this.blade.position.y = 2 - 4 * cut;
    const cutDone = t > 3.5;
    this.feed.visible = !cutDone;
    const sup = k(t, 4.3, 5.4) * (1 - k(t, 8.9, 9.6));
    const xa = X0 + P * 3.5;
    this.supA.position.set(xa, 0, 5 - 5 * sup);
    this.supB.position.set(xa, 0, -5 + 5 * sup);
    this.supA.visible = this.supB.visible = t > 4.2 && t < 9.8;
    // relative axial retraction: coil + support + clamp move +x off the free end
    const ret = k(t, 5.7, 8.6);
    const drop = k(t, 10.2, 11.2);
    this.carrier.position.set(55 * ret, -11.5 * drop, 0);
    this.jawA.visible = this.jawB.visible = t < 10.4;
    this.draw();
  }
}
