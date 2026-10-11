// Manufacturing flow (illustrative): carriers move through the ten modules.
import type { Anim } from "./player";
import { CanvasBase, clamp01, lerp } from "./canvas-base";

interface Node { id: string; name: string; x: number; y: number; kind: "core" | "exp" | "concept" | "lab" }

const NODES: Node[] = [
  { id: "M0", name: "Prepared veneer", x: 75, y: 170, kind: "lab" },
  { id: "M1", name: "Feed + tension", x: 215, y: 170, kind: "core" },
  { id: "M2", name: "Winding", x: 355, y: 170, kind: "core" },
  { id: "M3", name: "Clamp/cut/demold", x: 495, y: 170, kind: "core" },
  { id: "M4", name: "Tail forming", x: 635, y: 170, kind: "exp" },
  { id: "M5", name: "Free drying", x: 775, y: 170, kind: "exp" },
  { id: "M6", name: "Seed/tip/tails", x: 915, y: 170, kind: "exp" },
  { id: "M7", name: "Vision QA", x: 915, y: 390, kind: "core" },
  { id: "M8", name: "Output tray", x: 700, y: 390, kind: "exp" },
  { id: "M10", name: "Drone cassette", x: 420, y: 390, kind: "concept" },
];
const SEG = 1.3;              // seconds per hop
const HOPS = 8;               // M0 ... M8
const SPAWN = 2;              // seconds between carriers
const LOOP = 20;

export class FlowAnim extends CanvasBase implements Anim {
  duration = LOOP;
  phases = [
    { t: 0, text: "Every carrier gets an ID at M2 and a row in carriers.csv; faults divert to the reject bin at M7." },
  ];

  private node(id: string) { return NODES.find((n) => n.id === id)!; }

  render(t: number) {
    const c = this.begin();
    this.text("Illustrative flow - not a throughput claim", 500, 28, 15, this.muted, "center", "600");
    // links
    c.lineWidth = 3;
    for (let i = 0; i < NODES.length - 1; i++) {
      const a = NODES[i], b = NODES[i + 1];
      c.strokeStyle = this.line;
      c.setLineDash(b.kind === "concept" ? [8, 7] : []);
      c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke();
    }
    c.setLineDash([4, 6]);
    c.beginPath(); c.moveTo(915, 390); c.lineTo(915, 505); c.stroke();
    c.setLineDash([]);
    this.text("M9 optional XY transfer between stations", 560, 300, 13, this.muted, "center");
    // reject bin
    c.fillStyle = this.dark ? "#3a2622" : "#f6e3e0";
    this.rrect(860, 495, 110, 44, 8); c.fill();
    this.text("reject bin", 915, 506, 12, "#b03a2e", "center", "600");
    // stations
    for (const n of NODES) {
      const col = n.kind === "core" ? "#2f6f4f" : n.kind === "exp" ? "#a6761d" : this.muted;
      c.fillStyle = this.panel;
      c.strokeStyle = col;
      c.lineWidth = n.kind === "core" ? 3 : 2;
      c.setLineDash(n.kind === "concept" || n.kind === "lab" ? [6, 5] : []);
      this.rrect(n.x - 62, n.y - 38, 124, 76, 10); c.fill(); c.stroke();
      c.setLineDash([]);
      this.text(n.id, n.x, n.y - 14, 16, col, "center", "700");
      this.text(n.name, n.x, n.y + 10, 12.5, this.ink, "center");
    }
    // legend
    const leg: [string, string, boolean][] = [["#2f6f4f", "v0.3 build target", false], ["#a6761d", "experimental", false], [this.muted, "concept / separate lab process", true]];
    leg.forEach(([col, s, dash], i) => {
      c.strokeStyle = col; c.lineWidth = 3; c.setLineDash(dash ? [6, 5] : []);
      this.rrect(40 + i * 230, 520, 26, 16, 4); c.stroke(); c.setLineDash([]);
      this.text(s, 74 + i * 230, 528, 13, this.muted);
    });
    // carriers
    for (let j = 0; j < LOOP / SPAWN; j++) {
      const age = (t - j * SPAWN + LOOP * 2) % LOOP;
      const reject = j % 4 === 2;
      const toDrone = j % 3 === 0 && !reject;
      const total = (reject ? 7 : toDrone ? HOPS + 1 : HOPS) * SEG + 0.8;
      if (age > total + (reject ? SEG : 0)) continue;
      let hop = Math.floor(age / SEG), u = clamp01((age - hop * SEG) / SEG);
      let x: number, y: number;
      if (reject && hop >= 7) {
        const m7 = this.node("M7");
        const r = clamp01((age - 7 * SEG) / SEG);
        x = m7.x; y = lerp(m7.y + 50, 528, r);
      } else {
        const last = toDrone ? HOPS + 1 : HOPS;
        if (hop >= last) { hop = last; u = 0; }
        const a = NODES[Math.min(hop, NODES.length - 1)], b = NODES[Math.min(hop + 1, NODES.length - 1)];
        x = lerp(a.x, b.x, u); y = lerp(a.y, b.y, u);
      }
      const stage = hop + u;
      const inBin = reject && hop >= 7;
      this.carrier(x, inBin ? y : y + (stage < 7 ? -52 : 50), stage, reject && stage > 6.6);
    }
  }

  private carrier(x: number, y: number, stage: number, bad: boolean) {
    const c = this.ctx;
    if (stage < 1.5) {   // strip
      c.fillStyle = "#c8a165"; c.fillRect(x - 14, y - 3, 28, 6); return;
    }
    const dry = stage > 4.5;
    c.strokeStyle = bad ? "#b03a2e" : dry ? "#b08850" : "#9c7442";
    c.lineWidth = 3;
    c.beginPath();
    for (let i = 0; i <= 28; i++) {
      const px = x - 14 + i, py = y + Math.sin(i * 0.9) * 5;
      if (i) c.lineTo(px, py); else c.moveTo(px, py);
    }
    c.stroke();
    if (stage > 3.5) {   // tails
      c.lineWidth = 2;
      for (let k = 0; k < 3; k++) { c.beginPath(); c.moveTo(x + 14, y); c.quadraticCurveTo(x + 22, y - 8 + k * 8, x + 30, y - 10 + k * 10); c.stroke(); }
    }
    if (stage > 5.5) {   // tip with seed
      c.fillStyle = "#8a9a5b"; c.beginPath(); c.moveTo(x - 14, y - 5); c.lineTo(x - 26, y); c.lineTo(x - 14, y + 5); c.fill();
    }
  }
}
