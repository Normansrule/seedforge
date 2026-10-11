// Interactive GLB viewer: rotate / zoom (OrbitControls), reset, explode, show/hide parts,
// labels, fullscreen. Models are the CAD exports from tools/build_cad.py (millimetres, Y up).
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";

export interface ViewerOptions {
  src: string;
  title?: string;
  note?: string;
  explode?: boolean;
  parts?: boolean;
  labels?: boolean;
  azimuth?: number; // degrees
  elevation?: number;
  prettyName?: (node: string) => string;
}

interface Part {
  obj: THREE.Object3D;
  home: THREE.Vector3;
  dir: THREE.Vector3;
  label?: CSS2DObject;
}

const loader = new GLTFLoader();

export class Viewer {
  readonly root: HTMLElement;
  private stage: HTMLElement;
  private renderer?: THREE.WebGLRenderer;
  private labelRenderer?: CSS2DRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(35, 1, 0.1, 50000);
  private controls?: OrbitControls;
  private parts: Part[] = [];
  private home = { pos: new THREE.Vector3(), target: new THREE.Vector3() };
  private size = 1;
  private loaded = false;
  private running = false;
  private visible = false;
  private explodeFactor = 0;
  private labelsOn = false;
  private partsPanel?: HTMLElement;

  constructor(host: HTMLElement, private opts: ViewerOptions) {
    this.root = document.createElement("div");
    this.root.className = "viewer";
    this.root.innerHTML = `
      <div class="viewer-stage" role="img" aria-label="${opts.title ?? "3D model"}">
        <div class="viewer-loading">Loading 3D model...</div>
      </div>
      <div class="viewer-bar">
        <button data-act="reset" title="Reset view">Reset</button>
        ${opts.explode !== false ? `<label class="explode">Explode <input type="range" min="0" max="100" value="0" data-act="explode"></label>` : ""}
        ${opts.parts !== false ? `<button data-act="parts" aria-expanded="false">Parts</button>` : ""}
        ${opts.labels !== false ? `<button data-act="labels" aria-pressed="false">Labels</button>` : ""}
        <button data-act="fullscreen" title="Fullscreen">Fullscreen</button>
        ${opts.note ? `<span class="viewer-note">${opts.note}</span>` : ""}
      </div>
      <div class="viewer-parts" hidden></div>`;
    host.appendChild(this.root);
    this.stage = this.root.querySelector(".viewer-stage") as HTMLElement;
    this.partsPanel = this.root.querySelector(".viewer-parts") as HTMLElement;
    this.bindUi();
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        this.visible = e.isIntersecting;
        if (e.isIntersecting && !this.loaded) this.load();
        if (e.isIntersecting) this.start();
      }
    }, { rootMargin: "200px" });
    io.observe(this.root);
  }

  private bindUi() {
    this.root.querySelector('[data-act="reset"]')?.addEventListener("click", () => this.reset());
    const ex = this.root.querySelector('[data-act="explode"]') as HTMLInputElement | null;
    ex?.addEventListener("input", () => this.setExplode(Number(ex.value) / 100));
    const pb = this.root.querySelector('[data-act="parts"]') as HTMLButtonElement | null;
    pb?.addEventListener("click", () => {
      const p = this.partsPanel!;
      p.hidden = !p.hidden;
      pb.setAttribute("aria-expanded", String(!p.hidden));
    });
    const lb = this.root.querySelector('[data-act="labels"]') as HTMLButtonElement | null;
    lb?.addEventListener("click", () => {
      this.labelsOn = !this.labelsOn;
      lb.setAttribute("aria-pressed", String(this.labelsOn));
      for (const p of this.parts) if (p.label) p.label.visible = this.labelsOn && p.obj.visible;
    });
    this.root.querySelector('[data-act="fullscreen"]')?.addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else this.root.requestFullscreen?.();
    });
    document.addEventListener("fullscreenchange", () => this.resize());
  }

  private initRenderer() {
    const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.05;
    this.stage.appendChild(r.domElement);
    this.renderer = r;
    const lr = new CSS2DRenderer();
    lr.domElement.className = "viewer-labels";
    this.stage.appendChild(lr.domElement);
    this.labelRenderer = lr;
    this.controls = new OrbitControls(this.camera, r.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f96, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(1, 2, 1.5);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.7);
    fill.position.set(-1.5, 0.5, -1);
    this.scene.add(fill);
    window.addEventListener("resize", () => this.resize());
    new ResizeObserver(() => this.resize()).observe(this.stage);
  }

  private async load() {
    this.loaded = true;
    this.initRenderer();
    try {
      const gltf = await loader.loadAsync(this.opts.src);
      const model = gltf.scene;
      model.rotation.x = -Math.PI / 2;     // CAD exports are Z-up millimetres
      this.scene.add(model);
      model.updateMatrixWorld(true);
      const toLocal = model.quaternion.clone().invert();
      const box = new THREE.Box3().setFromObject(model);
      const centre = box.getCenter(new THREE.Vector3());
      this.size = box.getSize(new THREE.Vector3()).length();
      for (const child of [...model.children]) {
        const cb = new THREE.Box3().setFromObject(child);
        if (cb.isEmpty()) continue;
        const c = cb.getCenter(new THREE.Vector3());
        const dir = c.clone().sub(centre);
        if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
        dir.applyQuaternion(toLocal);
        const part: Part = { obj: child, home: child.position.clone(), dir };
        if (this.opts.labels !== false) {
          const el = document.createElement("div");
          el.className = "viewer-label";
          el.textContent = this.pretty(child.name);
          const lab = new CSS2DObject(el);
          lab.position.copy(c);
          lab.visible = false;
          this.scene.add(lab);
          part.label = lab;
        }
        this.parts.push(part);
      }
      this.buildPartsPanel();
      const az = THREE.MathUtils.degToRad(this.opts.azimuth ?? 35);
      const el = THREE.MathUtils.degToRad(this.opts.elevation ?? 25);
      const dist = (this.size / 2) / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2)) * 0.95;
      this.home.target.copy(centre);
      this.home.pos.set(centre.x + dist * Math.cos(el) * Math.sin(az), centre.y + dist * Math.sin(el),
        centre.z + dist * Math.cos(el) * Math.cos(az));
      this.camera.near = this.size / 500;
      this.camera.far = this.size * 50;
      this.reset();
      this.stage.querySelector(".viewer-loading")?.remove();
      this.resize();
    } catch (err) {
      const l = this.stage.querySelector(".viewer-loading");
      if (l) l.textContent = "Could not load the 3D model (" + String(err) + ").";
    }
  }

  private pretty(name: string) {
    return this.opts.prettyName ? this.opts.prettyName(name) : name.replace(/_/g, " ");
  }

  private buildPartsPanel() {
    const p = this.partsPanel;
    if (!p) return;
    p.innerHTML = `<div class="parts-head"><button data-all="1">Show all</button><button data-all="0">Hide all</button></div>`;
    const list = document.createElement("div");
    list.className = "parts-list";
    this.parts.forEach((part, i) => {
      const id = `pv-${Math.random().toString(36).slice(2)}-${i}`;
      const row = document.createElement("label");
      row.htmlFor = id;
      row.innerHTML = `<input type="checkbox" id="${id}" checked> ${this.pretty(part.obj.name)}`;
      const cb = row.querySelector("input") as HTMLInputElement;
      cb.addEventListener("change", () => this.setVisible(part, cb.checked));
      list.appendChild(row);
    });
    p.appendChild(list);
    p.querySelectorAll("[data-all]").forEach((b) => b.addEventListener("click", () => {
      const on = (b as HTMLElement).dataset.all === "1";
      list.querySelectorAll("input").forEach((cb, i) => { (cb as HTMLInputElement).checked = on; this.setVisible(this.parts[i], on); });
    }));
  }

  private setVisible(part: Part, on: boolean) {
    part.obj.visible = on;
    if (part.label) part.label.visible = on && this.labelsOn;
  }

  setExplode(f: number) {
    this.explodeFactor = f;
    for (const p of this.parts) {
      p.obj.position.copy(p.home).addScaledVector(p.dir, f * 1.2);
      if (p.label) {
        const b = new THREE.Box3().setFromObject(p.obj);
        if (!b.isEmpty()) b.getCenter(p.label.position);
      }
    }
  }

  reset() {
    this.camera.position.copy(this.home.pos);
    this.controls?.target.copy(this.home.target);
    this.controls?.update();
  }

  private resize() {
    if (!this.renderer) return;
    const w = this.stage.clientWidth, h = this.stage.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.labelRenderer?.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  private start() {
    if (this.running) return;
    this.running = true;
    const tick = () => {
      if (!this.visible && !document.fullscreenElement) { this.running = false; return; }
      this.controls?.update();
      if (this.renderer) {
        this.renderer.render(this.scene, this.camera);
        this.labelRenderer?.render(this.scene, this.camera);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  get exploded() { return this.explodeFactor; }
}
