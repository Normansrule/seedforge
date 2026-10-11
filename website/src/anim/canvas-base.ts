// 2D canvas scaffolding: a fixed virtual coordinate system (VW x VH) scaled to the stage.
export class CanvasBase {
  protected canvas = document.createElement("canvas");
  protected ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D;
  protected VW = 1000;
  protected VH = 560;
  protected dark = false;

  mount(stage: HTMLElement) {
    stage.appendChild(this.canvas);
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    const theme = () => {
      const forced = document.documentElement.dataset.theme;
      this.dark = forced ? forced === "dark" : !!mq?.matches;
    };
    theme();
    mq?.addEventListener?.("change", theme);
    new MutationObserver(theme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  resize(w: number, h: number) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.max(1, Math.round(w * dpr));
    this.canvas.height = Math.max(1, Math.round(h * dpr));
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
  }

  /** Begin a frame: clear and set the virtual-coordinate transform. */
  protected begin() {
    const c = this.ctx, W = this.canvas.width, H = this.canvas.height;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, W, H);
    const s = Math.min(W / this.VW, H / this.VH);
    c.setTransform(s, 0, 0, s, (W - this.VW * s) / 2, (H - this.VH * s) / 2);
    return c;
  }

  protected get ink() { return this.dark ? "#e6ebf0" : "#14273a"; }
  protected get muted() { return this.dark ? "#9aa7b4" : "#5b6b7a"; }
  protected get panel() { return this.dark ? "#1d2833" : "#f3f5f7"; }
  protected get line() { return this.dark ? "#3a4856" : "#c9d1d9"; }

  protected text(s: string, x: number, y: number, size = 14, color = this.ink, align: CanvasTextAlign = "left", weight = "500") {
    const c = this.ctx;
    c.font = `${weight} ${size}px Inter, system-ui, sans-serif`;
    c.fillStyle = color;
    c.textAlign = align;
    c.textBaseline = "middle";
    c.fillText(s, x, y);
  }

  protected rrect(x: number, y: number, w: number, h: number, r: number) {
    const c = this.ctx;
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }
}

export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const ease = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
