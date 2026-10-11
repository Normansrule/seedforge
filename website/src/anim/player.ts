// Timeline player shared by all animations: play/pause, scrub, phase captions, speed.
// Each animation implements `Anim`; the player owns the clock and the DOM controls.

export interface Phase { t: number; text: string }

export interface Anim {
  duration: number;               // seconds per loop
  phases: Phase[];
  mount(stage: HTMLElement): void;
  render(t: number): void;        // t in [0, duration]
  resize?(w: number, h: number): void;
  hud?(t: number): string;        // optional readout (HTML)
}

export interface PlayerOptions {
  title: string;
  label?: string;                 // mandatory disclaimer banner for conceptual animations
  description?: string;
  aspect?: number;                // width / height
}

export class Player {
  readonly root: HTMLElement;
  private t = 0;
  private playing = true;
  private speed = 1;
  private last = 0;
  private visible = false;
  private rafOn = false;
  private scrub: HTMLInputElement;
  private caption: HTMLElement;
  private hudEl: HTMLElement;
  private playBtn: HTMLButtonElement;
  private mounted = false;
  private stage: HTMLElement;
  private reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

  constructor(host: HTMLElement, private anim: Anim, opts: PlayerOptions) {
    this.root = document.createElement("figure");
    this.root.className = "anim";
    this.root.innerHTML = `
      ${opts.label ? `<div class="anim-label">${opts.label}</div>` : ""}
      <div class="anim-stage" style="aspect-ratio:${opts.aspect ?? 16 / 9}"></div>
      <div class="anim-hud" aria-live="off"></div>
      <div class="anim-bar">
        <button class="anim-play" aria-label="Pause">Pause</button>
        <input class="anim-scrub" type="range" min="0" max="1000" value="0" aria-label="Timeline">
        <select class="anim-speed" aria-label="Speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="2">2x</option></select>
      </div>
      <figcaption><strong>${opts.title}</strong> <span class="anim-caption"></span>
        ${opts.description ? `<span class="anim-desc">${opts.description}</span>` : ""}</figcaption>`;
    host.appendChild(this.root);
    this.stage = this.root.querySelector(".anim-stage") as HTMLElement;
    this.scrub = this.root.querySelector(".anim-scrub") as HTMLInputElement;
    this.caption = this.root.querySelector(".anim-caption") as HTMLElement;
    this.hudEl = this.root.querySelector(".anim-hud") as HTMLElement;
    this.playBtn = this.root.querySelector(".anim-play") as HTMLButtonElement;
    this.playBtn.addEventListener("click", () => this.setPlaying(!this.playing));
    this.scrub.addEventListener("input", () => {
      this.t = (Number(this.scrub.value) / 1000) * this.anim.duration;
      this.setPlaying(false);
      this.draw();
    });
    (this.root.querySelector(".anim-speed") as HTMLSelectElement).addEventListener("change", (e) => {
      this.speed = Number((e.target as HTMLSelectElement).value);
    });
    if (this.reduced) this.setPlaying(false);
    new IntersectionObserver((es) => {
      for (const e of es) {
        this.visible = e.isIntersecting;
        if (this.visible && !this.mounted) { this.mounted = true; this.anim.mount(this.stage); this.fit(); this.draw(); }
        if (this.visible) this.loop();
      }
    }, { rootMargin: "100px" }).observe(this.root);
    new ResizeObserver(() => this.fit()).observe(this.stage);
  }

  private fit() {
    if (!this.mounted) return;
    this.anim.resize?.(this.stage.clientWidth, this.stage.clientHeight);
    this.draw();
  }

  setPlaying(on: boolean) {
    this.playing = on;
    this.playBtn.textContent = on ? "Pause" : "Play";
    this.playBtn.setAttribute("aria-label", on ? "Pause" : "Play");
    if (on) this.loop();
  }

  /** Jump to time t (used by the README GIF capture and tests). */
  seek(t: number) { this.t = t; this.draw(); }

  private draw() {
    const d = this.anim.duration;
    this.anim.render(this.t);
    this.scrub.value = String(Math.round((this.t / d) * 1000));
    let txt = "";
    for (const p of this.anim.phases) if (this.t >= p.t) txt = p.text;
    this.caption.textContent = txt;
    if (this.anim.hud) this.hudEl.innerHTML = this.anim.hud(this.t);
  }

  private loop() {
    if (this.rafOn) return;
    this.rafOn = true;
    this.last = performance.now();
    const step = (now: number) => {
      if (!this.visible) { this.rafOn = false; return; }
      const dt = Math.min(0.1, (now - this.last) / 1000);
      this.last = now;
      if (this.playing) {
        this.t = (this.t + dt * this.speed) % this.anim.duration;
        this.draw();
      }
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}
