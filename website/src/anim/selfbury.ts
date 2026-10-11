// Conceptual visualization of the self-burying idea (after Luo et al. 2023, described in words,
// not copied). Not a validated physics simulation: motion, depth and timing are illustrative.
import type { Anim } from "./player";
import { CanvasBase, ease } from "./canvas-base";

const CYCLE = 6;           // one wet + dry cycle (illustrative seconds)
const CYCLES = 3;

export class SelfBuryAnim extends CanvasBase implements Anim {
  duration = CYCLE * CYCLES + 3;
  phases = [
    { t: 0, text: "Carrier lands on the soil; the tails rest on the ground and act as anchors." },
    { t: 1, text: "Humidity rises: the wooden coil unwinds and the body turns; the tails brace it so the tip turns into the soil." },
    { t: 4, text: "Drying: the coil winds back; ratcheting against the tails keeps the depth gained." },
    { t: CYCLE * CYCLES, text: "After repeated wet/dry cycles the seed-bearing tip sits below the surface (illustrative)." },
  ];

  render(t: number) {
    const c = this.begin();
    const cyc = Math.min(CYCLES, Math.floor(t / CYCLE));
    const u = (t % CYCLE) / CYCLE;
    const inCycles = t < CYCLE * CYCLES;
    const wet = inCycles ? Math.sin(Math.PI * Math.min(1, u * 1.6)) * (u < 0.62 ? 1 : 1 - (u - 0.62) / 0.38) : 0;
    const progress = inCycles ? cyc + ease(u / 0.62) : CYCLES;     // depth only advances while wetting
    const depth = 16 * Math.min(progress, CYCLES);                 // px, illustrative
    const twist = inCycles ? (cyc + ease(u / 0.62)) * Math.PI * 2 : CYCLES * Math.PI * 2;
    // sky + soil
    const surf = 320;
    c.fillStyle = this.dark ? "#14202b" : "#eef4f8"; c.fillRect(0, 0, 1000, surf);
    const g = c.createLinearGradient(0, surf, 0, 560);
    g.addColorStop(0, this.dark ? "#4a3a2a" : "#8b6b4a"); g.addColorStop(1, this.dark ? "#2b2118" : "#5e4630");
    c.fillStyle = g; c.fillRect(0, surf, 1000, 240);
    c.fillStyle = this.dark ? "#5b4a39" : "#a07e59";
    for (let i = 0; i < 60; i++) { const x = (i * 157) % 1000, y = surf + 20 + ((i * 89) % 210); c.beginPath(); c.ellipse(x, y, 4 + (i % 4), 3, 0, 0, 7); c.fill(); }
    // rain / humidity
    if (wet > 0.05) {
      c.strokeStyle = `rgba(80,140,200,${0.5 * wet})`; c.lineWidth = 2;
      for (let i = 0; i < 40; i++) { const x = (i * 97 + t * 160) % 1000, y = (i * 53 + t * 380) % surf; c.beginPath(); c.moveTo(x, y); c.lineTo(x - 4, y + 14); c.stroke(); }
    }
    // humidity gauge
    c.fillStyle = this.panel; this.rrect(740, 30, 230, 100, 10); c.fill();
    this.text("humidity", 760, 54, 20, this.muted);
    c.fillStyle = this.line; c.fillRect(760, 72, 190, 16);
    c.fillStyle = "#4f8fc0"; c.fillRect(760, 72, 190 * (0.2 + 0.8 * wet), 16);
    this.text(wet > 0.5 ? "wet: coil unwinds" : "dry: coil rewinds", 760, 110, 19, this.ink, "left", "600");
    // carrier: tip at (cx, surf + depth), body inclined, tails at top end on the ground
    const cx = 430, tipY = surf + depth;
    const ang = (-62 * Math.PI) / 180;     // body inclination
    const L = 230;
    const topX = cx + Math.cos(ang) * L * 0.55, topY = tipY + Math.sin(ang) * L;
    const ux = (topX - cx) / L, uy = (topY - tipY) / L;
    // body (side view of a helix: phase shifts with twist)
    c.lineWidth = 5; c.strokeStyle = "#b08850";
    c.beginPath();
    for (let i = 0; i <= 120; i++) {
      const s = i / 120;
      const amp = 10 + 3 * wet;
      const off = Math.sin(s * Math.PI * 2 * 7 - twist) * amp;
      const px = cx + ux * L * s - uy * off, py = tipY + uy * L * s + ux * off;
      if (i) c.lineTo(px, py); else c.moveTo(px, py);
    }
    c.stroke();
    // tip + seed
    c.fillStyle = "#8a9a5b";
    c.beginPath(); c.moveTo(cx - uy * 9, tipY + ux * 9); c.lineTo(cx - ux * 26, tipY - uy * 26); c.lineTo(cx + uy * 9, tipY - ux * 9); c.closePath(); c.fill();
    c.fillStyle = "#6b4a2b"; c.beginPath(); c.ellipse(cx - ux * 10, tipY - uy * 10, 5, 3.5, Math.atan2(uy, ux), 0, 7); c.fill();
    // tails resting on the soil, rotating about the body end
    c.strokeStyle = "#b08850"; c.lineWidth = 3;
    for (let k = 0; k < 3; k++) {
      const a = twist * 0.5 + (k * 2 * Math.PI) / 3;
      const len = [120, 132, 144][k];
      const ex = topX + Math.cos(a) * len, ey = Math.min(surf - 2, topY + 26 + Math.sin(a) * 12);
      c.beginPath(); c.moveTo(topX, topY); c.quadraticCurveTo((topX + ex) / 2, topY - 10, ex, ey); c.stroke();
    }
    // cut-away: soil drawn translucent over the buried part
    c.fillStyle = this.dark ? "rgba(43,33,24,0.35)" : "rgba(94,70,48,0.3)";
    c.fillRect(0, surf, 1000, 240);
    this.text("cut-away view", 970, surf + 26, 19, "#f3efe8", "right");
    // depth marker
    c.strokeStyle = this.muted; c.setLineDash([5, 5]); c.lineWidth = 1.5;
    c.beginPath(); c.moveTo(cx - 140, surf); c.lineTo(cx - 140, tipY); c.stroke(); c.setLineDash([]);
    this.text("depth (illustrative)", cx - 150, surf + 24 + depth / 2, 19, "#fff", "right");
    this.text(`wet/dry cycle ${Math.min(CYCLES, cyc + (inCycles ? 1 : 0))} of ${CYCLES}`, 40, 80, 22, this.ink, "left", "700");
  }
}
