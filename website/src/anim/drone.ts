// Conceptual deployment architecture: three aircraft, three pre-assigned non-overlapping sectors,
// unique point IDs, intent logged before release, uncertain points never auto-retried.
import type { Anim } from "./player";
import { CanvasBase, lerp } from "./canvas-base";

type State = "PLANNED" | "INTENT" | "RELEASED" | "UNCERTAIN";
interface Pt { id: string; x: number; y: number }
interface Visit { pt: Pt; tArrive: number; tDone: number; uncertain: boolean }

const SECTORS = [
  { name: "A", x0: 60, x1: 300, colour: "#2f6f4f" },
  { name: "B", x0: 320, x1: 560, colour: "#3b6ea5" },
  { name: "C", x0: 580, x1: 820, colour: "#a6761d" },
];
const HOP = 0.75, DROP = 0.45, START = 1.2;

function sectorPoints(s: typeof SECTORS[number]): Pt[] {
  const pts: Pt[] = [];
  let n = 1;
  for (let r = 0; r < 4; r++) {
    const row: Pt[] = [];
    for (let q = 0; q < 3; q++) {
      const jx = ((n * 37) % 11) - 5, jy = ((n * 53) % 9) - 4;
      row.push({ id: `${s.name}-${String(n).padStart(2, "0")}`, x: s.x0 + 45 + q * 75 + jx, y: 110 + r * 95 + jy });
      n++;
    }
    pts.push(...(r % 2 ? row.reverse() : row));     // lawn-mower order
  }
  return pts;
}

export class DroneAnim extends CanvasBase implements Anim {
  duration = 24;
  phases = [
    { t: 0, text: "Ground coordinator assigns each aircraft one sector and a list of unique point IDs." },
    { t: START, text: "At each point the payload controller logs INTENT, opens one cell, then confirms RELEASED." },
    { t: 8, text: "No confirmation -> UNCERTAIN. The point is never retried automatically; a human resolves it." },
    { t: 17, text: "Completed IDs return to the coordinator. No two aircraft can claim the same point." },
  ];
  private plans: { sector: typeof SECTORS[number]; pts: Pt[]; visits: Visit[] }[] = [];

  constructor() {
    super();
    SECTORS.forEach((s, i) => {
      const pts = sectorPoints(s);
      const visits: Visit[] = [];
      let tt = START + i * 0.35;
      pts.forEach((p, j) => {
        tt += HOP;
        visits.push({ pt: p, tArrive: tt, tDone: tt + DROP, uncertain: s.name === "B" && j === 4 });
        tt += DROP;
      });
      this.plans.push({ sector: s, pts, visits });
    });
  }

  private state(v: Visit, t: number): State {
    if (t < v.tArrive) return "PLANNED";
    if (t < v.tDone) return "INTENT";
    return v.uncertain ? "UNCERTAIN" : "RELEASED";
  }

  render(t: number) {
    const c = this.begin();
    c.fillStyle = this.dark ? "#16212b" : "#eef3ee"; c.fillRect(40, 60, 800, 440);
    for (const p of this.plans) {
      const s = p.sector;
      c.fillStyle = s.colour + "18"; c.fillRect(s.x0, 70, s.x1 - s.x0, 420);
      c.strokeStyle = s.colour; c.lineWidth = 2; c.setLineDash([7, 5]); c.strokeRect(s.x0, 70, s.x1 - s.x0, 420); c.setLineDash([]);
      this.text(`Sector ${s.name}`, s.x0 + 10, 86, 14, s.colour, "left", "700");
      for (const v of p.visits) {
        const st = this.state(v, t), { x, y } = v.pt;
        c.beginPath(); c.arc(x, y, 9, 0, 7);
        if (st === "RELEASED") { c.fillStyle = s.colour; c.fill(); }
        else if (st === "UNCERTAIN") { c.fillStyle = "#b03a2e"; c.fill(); }
        else { c.fillStyle = this.panel; c.fill(); c.strokeStyle = st === "INTENT" ? "#d39b2a" : this.line; c.lineWidth = st === "INTENT" ? 4 : 2; c.stroke(); }
        if (st === "UNCERTAIN") this.text("?", x, y + 1, 13, "#fff", "center", "700");
        this.text(v.pt.id, x, y + 20, 10.5, this.muted, "center");
      }
      // aircraft position
      let x = (s.x0 + s.x1) / 2, y = 530, prevX = x, prevY = y;
      for (const v of p.visits) {
        const tStart = v.tArrive - HOP;
        if (t >= tStart && t < v.tArrive) { const u = (t - tStart) / HOP; x = lerp(prevX, v.pt.x, u); y = lerp(prevY, v.pt.y, u); break; }
        if (t >= v.tArrive) { x = v.pt.x; y = v.pt.y; }
        prevX = v.pt.x; prevY = v.pt.y;
      }
      const lastDone = p.visits[p.visits.length - 1].tDone;
      if (t > lastDone) { const u = Math.min(1, (t - lastDone) / 1.5); x = lerp(prevX, (s.x0 + s.x1) / 2, u); y = lerp(prevY, 530, u); }
      this.drone(x, y, s.colour, t);
    }
    // ledger panel
    c.fillStyle = this.panel; this.rrect(860, 60, 120, 440, 10); c.fill();
    this.text("Ledger", 920, 84, 14, this.ink, "center", "700");
    let yy = 116;
    for (const p of this.plans) {
      const counts = { PLANNED: 0, INTENT: 0, RELEASED: 0, UNCERTAIN: 0 } as Record<State, number>;
      for (const v of p.visits) counts[this.state(v, t)]++;
      this.text(`Sector ${p.sector.name}`, 872, yy, 13, p.sector.colour, "left", "700"); yy += 22;
      for (const k of ["PLANNED", "RELEASED", "UNCERTAIN"] as State[]) {
        this.text(`${k.toLowerCase()} ${counts[k] + (k === "PLANNED" ? counts.INTENT : 0)}`, 872, yy, 12, this.muted); yy += 19;
      }
      yy += 18;
    }
    this.text("base", 450, 545, 12, this.muted, "center");
  }

  private drone(x: number, y: number, col: string, t: number) {
    const c = this.ctx;
    c.strokeStyle = this.ink; c.lineWidth = 2;
    c.beginPath(); c.moveTo(x - 14, y - 14); c.lineTo(x + 14, y + 14); c.moveTo(x + 14, y - 14); c.lineTo(x - 14, y + 14); c.stroke();
    for (const [dx, dy] of [[-14, -14], [14, -14], [-14, 14], [14, 14]]) {
      c.beginPath(); c.ellipse(x + dx, y + dy, 8, 3 + Math.abs(Math.sin(t * 40 + dx)) * 2, 0, 0, 7); c.strokeStyle = this.muted; c.stroke();
    }
    c.fillStyle = col; c.beginPath(); c.arc(x, y, 6, 0, 7); c.fill();
  }
}
