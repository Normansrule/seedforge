// M6 seed / tip / three-tail assembly (experimental development tooling).
// Shapes follow the RECONSTRUCTED reference carrier; this shows the intended sequence only.
import * as THREE from "three";
import type { Anim } from "./player";
import { C, ThreeBase, helixRibbon, k, mat } from "./three-base";

export class AssemblyAnim extends ThreeBase implements Anim {
  duration = 14;
  phases = [
    { t: 0, text: "Dry body is placed upright in the three-tail assembly nest (S04)." },
    { t: 1.8, text: "Auxiliary tails 1, 2, 3 are presented in grooves 120 degrees apart." },
    { t: 5.2, text: "A small, controlled adhesive amount goes on the inactive joining region only - never on active coils." },
    { t: 6.0, text: "The assembly is lifted; exactly one seed is presented below the body (S01-S03 singulator)." },
    { t: 8.4, text: "The biodegradable seed-containing tip is formed (S05-S08 syringe + silicone mould)." },
    { t: 11, text: "Cure with a seed-safe process, then final QA: one seed, three tails, intact tip, clean coils." },
  ];
  private body = new THREE.Group();
  private tails: THREE.Mesh[] = [];
  private glue: THREE.Mesh[] = [];
  private seed = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), mat(C.seed, { roughness: 0.6 }));
  private tip = new THREE.Mesh();

  mount(stage: HTMLElement) {
    this.mountRenderer(stage);
    const s = this.scene;
    // nest with three grooves
    const nest = new THREE.Mesh(new THREE.CylinderGeometry(26, 26, 4, 64), mat(C.printed));
    nest.position.y = -2; s.add(nest);
    for (let i = 0; i < 3; i++) {
      const g = new THREE.Mesh(new THREE.BoxGeometry(24, 0.6, 3.4), mat(0xc9ced4));
      const a = (i * 2 * Math.PI) / 3;
      g.position.set(Math.cos(a) * 13, 0.05, -Math.sin(a) * 13);
      g.rotation.y = a;
      s.add(g);
    }
    // body: 7 coils, 2.5 x 0.5 mm, pitch 5 mm, vertical
    const rib = helixRibbon(0.8, 0.5, 2.5, 5, 7, 0, 64);
    const coil = new THREE.Mesh(rib.geometry, mat(C.woodDry, { roughness: 0.8, side: THREE.DoubleSide }));
    coil.rotation.z = Math.PI / 2;
    this.body.add(coil);
    s.add(this.body);
    // tails: planar curling arcs from the body base outward
    for (let i = 0; i < 3; i++) {
      const a0 = (i * 2 * Math.PI) / 3;
      const len = [27, 29.5, 32.5][i];
      const pts: THREE.Vector3[] = [];
      for (let j = 0; j <= 24; j++) {
        const u = j / 24;
        const r = 1.2 + u * len * 0.75;
        const a = a0 + u * 0.9;
        pts.push(new THREE.Vector3(Math.cos(a) * r, 1.2 + Math.sin(u * Math.PI) * 2.5, -Math.sin(a) * r));
      }
      const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, 0.55, 8),
        mat(C.woodDry, { roughness: 0.8 }));
      this.tails.push(tube);
      s.add(tube);
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.75, 16, 12), mat(0xe8e2a0, { roughness: 0.3 }));
      dot.position.set(Math.cos(a0) * 1.6, 1.6, -Math.sin(a0) * 1.6);
      this.glue.push(dot);
      s.add(dot);
    }
    this.seed.scale.set(1.8, 2.4, 1.25);
    s.add(this.seed);
    const prof: THREE.Vector2[] = [];
    for (let j = 0; j <= 20; j++) {
      const u = j / 20;
      prof.push(new THREE.Vector2(Math.sin(u * Math.PI) * 3.2 * (1 - 0.55 * u) + 0.01, -14 * u));
    }
    this.tip = new THREE.Mesh(new THREE.LatheGeometry(prof, 48), mat(C.tip, { roughness: 0.9, transparent: true, opacity: 0.85 }));
    s.add(this.tip);
    this.camera.fov = 30;
    this.camera.position.set(66, 70, 118);
    this.camera.lookAt(0, 17, 0);
  }

  render(t: number) {
    // body lowers into the nest
    const down = k(t, 0, 1.6);
    const lift = k(t, 6.0, 6.8) * 16;     // assembly lifted for tip forming
    this.body.position.y = 40 * (1 - down) + lift;
    this.tails.forEach((m, i) => {
      const a0 = (i * 2 * Math.PI) / 3;
      const p = k(t, 1.9 + i * 1.0, 2.9 + i * 1.0);
      m.position.set(Math.cos(a0) * 30 * (1 - p), lift, -Math.sin(a0) * 30 * (1 - p));
      m.visible = t > 1.8;
    });
    this.glue.forEach((g, i) => {
      g.visible = t > 5.2 + i * 0.4;
      g.position.y = 1.6 + lift;
    });
    const sd = k(t, 6.9, 8.2);
    this.seed.visible = t > 6.8;
    this.seed.position.set(26 * (1 - sd), lift - 6, 0);
    const tp = k(t, 8.5, 10.8);
    this.tip.visible = t > 8.4;
    this.tip.scale.set(Math.max(0.01, tp), Math.max(0.01, tp), Math.max(0.01, tp));
    this.tip.position.y = lift + 0.5;
    this.draw();
  }
}
