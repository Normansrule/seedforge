import "./style.css";
import { Viewer } from "./viewer";
import { Player, type Anim } from "./anim/player";
import { WindingAnim } from "./anim/winding";
import { DemoldAnim } from "./anim/demold";
import { TailAnim } from "./anim/tail";
import { AssemblyAnim } from "./anim/assembly";
import { FlowAnim } from "./anim/flow";
import { SelfBuryAnim } from "./anim/selfbury";
import { DroneAnim } from "./anim/drone";

const REPO = "https://github.com/Normansrule/seedforge";
const RELEASE = `${REPO}/releases/latest`;
const $ = <T extends HTMLElement = HTMLElement>(sel: string) => document.querySelector(sel) as T;
const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
const data = (name: string) => fetch(`data/${name}.json`).then((r) => r.json());

// ---------------------------------------------------------------- theme
const themeBtn = $("#theme");
const saved = (() => { try { return localStorage.getItem("sf-theme"); } catch { return null; } })();
if (saved) document.documentElement.dataset.theme = saved;
themeBtn.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = dark ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("sf-theme", next); } catch { /* private mode */ }
});

// repository links
document.querySelectorAll<HTMLAnchorElement>("[data-repo]").forEach((a) => {
  a.href = a.dataset.repo ? `${REPO}/${a.dataset.repo}` : REPO;
  a.rel = "noopener";
});

// ---------------------------------------------------------------- tabs helper
function tabs(host: HTMLElement, items: { id: string; label: string }[], onSelect: (id: string) => void, initial?: string) {
  host.innerHTML = "";
  const btns: HTMLButtonElement[] = [];
  for (const it of items) {
    const b = document.createElement("button");
    b.role = "tab";
    b.textContent = it.label;
    b.addEventListener("click", () => select(it.id));
    btns.push(b);
    host.appendChild(b);
  }
  function select(id: string) {
    items.forEach((it, i) => btns[i].setAttribute("aria-selected", String(it.id === id)));
    onSelect(id);
  }
  select(initial ?? items[0].id);
}

// ---------------------------------------------------------------- animations
const CONCEPT_BURY = "Conceptual visualization — not a validated physics simulation";
const CONCEPT_DRONE = "Conceptual deployment architecture";
new Player($("#anim-selfbury"), new SelfBuryAnim(), { title: "Self-burying concept", label: CONCEPT_BURY, aspect: 1000 / 560 });
new Player($("#anim-flow"), new FlowAnim(), { title: "Manufacturing flow", aspect: 1000 / 560 });
new Player($("#anim-drone"), new DroneAnim(), { title: "Sectors, unique points, no automatic retries", label: CONCEPT_DRONE, aspect: 1000 / 560 });

const procHost = $("#anim-process");
const procAnims: Record<string, { make: () => Anim; title: string; desc: string; label?: string }> = {
  winding: { make: () => new WindingAnim(), title: "M2 synchronized winding", desc: "Status: firmware unit-tested; hardware testing pending." },
  demold: { make: () => new DemoldAnim(), title: "M3 clamp, cut and demold", desc: "Sequence as coded in the firmware; mounting design still open (Phase 2)." },
  tail: { make: () => new TailAnim(), title: "M4 tail forming", desc: "Experimental. Tail shape is a RECONSTRUCTED reference.", label: "Experimental module - illustrative sequence" },
  assembly: { make: () => new AssemblyAnim(), title: "M6 seed, tip and three-tail assembly", desc: "Experimental development tooling.", label: "Experimental module - illustrative sequence" },
};
const procCache: Record<string, Player> = {};
tabs($("#anim-tabs"), [
  { id: "winding", label: "Winding" }, { id: "demold", label: "Clamp / cut / demold" },
  { id: "tail", label: "Tail forming" }, { id: "assembly", label: "Assembly" },
], (id) => {
  for (const p of Object.values(procCache)) p.root.hidden = true;
  if (!procCache[id]) {
    const a = procAnims[id];
    procCache[id] = new Player(procHost, a.make(), { title: a.title, description: a.desc, label: a.label });
  }
  procCache[id].root.hidden = false;
});

// ---------------------------------------------------------------- viewers
const pretty = (n: string) => n.replace(/^([A-Z]\d\d)_/, "$1 ").replace(/_/g, " ");
new Viewer($("#viewer-machine"), { src: "models/phase1_core_cell.glb", title: "Phase-1 core cell", prettyName: pretty, azimuth: -40, elevation: 28,
  note: "CAD layout reference - not physically validated" });
new Viewer($("#viewer-carrier"), { src: "models/finished_carrier.glb", title: "Finished carrier", azimuth: 30, elevation: 15,
  note: "Reconstructed reference geometry" });
new Viewer($("#viewer-exploded"), { src: "models/exploded_carrier.glb", title: "Exploded carrier", azimuth: 30, elevation: 20,
  note: "Body, three tails, tip, seed envelope" });

// ---------------------------------------------------------------- site / windows
data("site").then((s) => {
  $("#interf").textContent = String(s.static_interference);
  const rows = Object.entries(s.windows as Record<string, [number, number] | null>)
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([a, w]) => `<tr><td>${Number(a) > 0 ? "+" : ""}${Number(a)} deg</td><td>${w ? `${w[0]} - ${w[1]} mm` : "none"}</td></tr>`).join("");
  $("#windows").innerHTML = `<caption>Collision-free carriage window (CAD sweep, 5 mm steps; home trips at 45 mm)</caption>
    <thead><tr><th>guide angle</th><th>carriage x</th></tr></thead><tbody>${rows}</tbody>`;
});

// ---------------------------------------------------------------- modules
const STATUS_CLASS = (s: string) => /core/.test(s) ? "core" : /concept|upcoming/.test(s) ? "concept" : "exp";
Promise.all([data("modules"), data("parts")]).then(([mods, parts]) => {
  const body = $("#module-body");
  const viewers: Record<string, HTMLElement> = {};
  tabs($("#module-tabs"), mods.map((m: any) => ({ id: m.id, label: m.id })), (id) => {
    const m = mods.find((x: any) => x.id === id);
    const prefixParts = parts.filter((p: any) => p.family === "machine" && String(p.module).split("/").includes(m.id));
    const list = (xs: string[]) => `<ul>${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
    body.innerHTML = `
      <div class="module-head"><h3>${esc(m.id)} &middot; ${esc(m.name)}</h3>
        <span class="tag ${STATUS_CLASS(m.status)}">${esc(m.status)}</span><span class="tag">build phase ${esc(m.phase)}</span></div>
      <p class="lede-sm">${esc(m.purpose)}</p>
      <div class="cols3">
        <div><h4>Inputs</h4>${list(m.inputs)}<h4>Outputs</h4>${list(m.outputs)}</div>
        <div><h4>Electronics</h4>${list(m.electronics)}<h4>Software</h4>${list(m.software)}</div>
        <div><h4>Acceptance</h4>${list(m.acceptance)}<h4>Known risks</h4>${list(m.risks)}</div>
      </div>
      <div class="split">
        <div>
          <h4>Printed parts</h4>
          <div class="table-wrap"><table class="compact"><thead><tr><th>part</th><th>status</th><th>qty</th><th>size (mm)</th><th></th></tr></thead><tbody>
          ${prefixParts.map((p: any) => `<tr><td>${esc(p.file_stem)}</td><td><span class="tag ${STATUS_CLASS(p.status)}">${esc(p.status)}</span></td><td>${esc(p.qty)}</td>
            <td class="nw">${Number(p.bbox_x_mm).toFixed(0)} x ${Number(p.bbox_y_mm).toFixed(0)} x ${Number(p.bbox_z_mm).toFixed(0)}</td>
            <td><button class="mini" data-part="${esc(p.part_id)}">3D</button></td></tr>`).join("") || `<tr><td colspan="5">no printed parts in this module</td></tr>`}
          </tbody></table></div>
          <p><a href="${REPO}/blob/main/docs/modules/${esc(m.slug)}.md">Full module documentation</a></p>
        </div>
        <div>
          <figure><img src="img/${esc(String(m.figure).replace("images/", ""))}" alt="${esc(m.name)} CAD render" loading="lazy"><figcaption>CAD render - not evidence that the module works.</figcaption></figure>
          <div class="part-viewer"></div>
        </div>
      </div>`;
    const pv = body.querySelector(".part-viewer") as HTMLElement;
    body.querySelectorAll<HTMLButtonElement>("[data-part]").forEach((b) => b.addEventListener("click", () => {
      pv.innerHTML = "";
      const id = b.dataset.part!;
      viewers[id] = pv;
      new Viewer(pv, { src: `models/parts/${id}.glb`, title: id, explode: false, parts: false, labels: false, note: `${id} - CAD-validated mesh` });
    }));
  });
});

// ---------------------------------------------------------------- geometry table
data("geometry").then((rows) => {
  $("#geometry").innerHTML = `<thead><tr><th>case</th><th>pitch mm/rev</th><th>guide angle</th><th>predicted gap</th><th>butt-joint pitch</th></tr></thead><tbody>${
    rows.map((r: any) => `<tr><td>${esc(r.name)}</td><td>${r.pitch_mm.toFixed(3)}</td><td>${r.guide_angle_deg.toFixed(1)} deg</td>
      <td class="${r.normal_gap_mm < -0.01 ? "bad" : ""}">${r.normal_gap_mm >= 0 ? "+" : ""}${r.normal_gap_mm.toFixed(2)} mm${r.normal_gap_mm < -0.01 ? " (overlap)" : ""}</td>
      <td>${r.butt_joint_pitch_mm == null ? "-" : r.butt_joint_pitch_mm.toFixed(2) + " mm"}</td></tr>`).join("")}</tbody>`;
});

// ---------------------------------------------------------------- pins
data("wiring").then((w) => {
  $("#pins").innerHTML = `<thead><tr><th>board</th><th>pin</th><th>signal</th><th>connects to</th><th>notes</th></tr></thead><tbody>${
    w.pins.map((p: any) => `<tr><td>${esc(p.board)}</td><td>${esc(p.pin)}</td><td><code>${esc(p.signal)}</code></td><td>${esc(p.to)}</td><td>${esc(p.notes)}</td></tr>`).join("")}</tbody>`;
});

// ---------------------------------------------------------------- simulator replay
data("sim_traces").then((traces) => {
  const STATES = ["BOOT", "HOME", "READY", "PRETENSION", "WIND", "VERIFY", "CLAMP", "CUT", "DEMOLD", "COMPLETE", "SAFE_STOP"];
  const bar = $("#statebar");
  bar.innerHTML = STATES.map((s) => `<span data-s="${s}">${s}</span>`).join("");
  const pre = $("#trace");
  let timer = 0;
  const names: Record<string, string> = { normal_cycle: "normal", estop: "E-stop", tension_high: "tension high", vision_gap: "vision gap",
    heartbeat_timeout: "heartbeat timeout", home_switch_fault: "home switch fault", m3_cycle: "M3 cycle" };
  tabs($("#sim-tabs"), Object.keys(traces).map((k) => ({ id: k, label: names[k] ?? k })), (id) => {
    window.clearInterval(timer);
    const tr = traces[id];
    let i = 0;
    pre.textContent = `# ${tr.description}\n`;
    const setState = (s: string) => bar.querySelectorAll("span").forEach((e) => e.classList.toggle("on", (e as HTMLElement).dataset.s === s));
    setState("BOOT");
    timer = window.setInterval(() => {
      if (i >= tr.trace.length) {
        pre.textContent += `\nfinal state ${tr.final_state}, fault ${tr.fault}`;
        window.clearInterval(timer);
        return;
      }
      const [ms, line] = tr.trace[i++];
      pre.textContent += `${(ms / 1000).toFixed(3).padStart(8)} s  ${line}\n`;
      pre.scrollTop = pre.scrollHeight;
      const m = /^STATE=(\w+)/.exec(line);
      if (m) setState(m[1]);
    }, 260);
  });
});

// ---------------------------------------------------------------- vision
data("vision").then((v) => {
  $("#confusion").innerHTML = `<caption>Synthetic set (${v.n} images)</caption>
    <thead><tr><th></th><th>predicted accept</th><th>predicted reject</th></tr></thead>
    <tbody><tr><th>labelled good</th><td class="good">${v.true_accept} true accept</td><td>${v.false_reject} false reject</td></tr>
    <tr><th>labelled defective</th><td>${v.false_accept} false accept</td><td class="good">${v.true_reject} true reject</td></tr></tbody>`;
});

// ---------------------------------------------------------------- BOM
data("bom").then((b) => {
  const views: Record<string, any[]> = {
    A: b.items.filter((i: any) => i.view === "A"),
    AB: b.items.filter((i: any) => i.view === "A" || i.view === "B"),
    C: b.items.filter((i: any) => i.view === "C"),
  };
  const totals: Record<string, number> = { A: b.totals.A, AB: b.totals.A_plus_B, C: b.totals.C };
  const allIn: Record<string, number> = { A: b.totals.A_all, AB: b.totals.A_plus_B_all, C: b.totals.C_all };
  const desc: Record<string, string> = {
    A: "Minimum demonstrator: the Phase-1 core cell plus M3 clamp/cut/demold and the fixed camera. Every fastener is M2.",
    AB: "Complete manufacturing bench: adds tails, drying, seed handling, tip forming, final QA and XY transfer (donor printer gantry).",
    C: `Optional deployment: payload kit (about $${Math.round(b.totals.C_payload)} on its own) plus a budget ArduPilot quad. Not needed for manufacturing; not flight-validated.`,
  };
  tabs($("#bom-tabs"), [{ id: "A", label: "A - minimum demonstrator" }, { id: "AB", label: "A + B - manufacturing bench" }, { id: "C", label: "C - optional deployment" }], (id) => {
    const items = views[id];
    $("#bom-kpis").innerHTML = `<div><b>$${Math.round(totals[id])}</b><span>to buy if Uno/motors/drivers (or charger/radio) are owned</span></div>
      <div><b>$${Math.round(allIn[id])}</b><span>buying everything</span></div>
      <div><b>${items.length}</b><span>line items</span></div>
      <div><b>M2</b><span>the only fastener size</span></div>
      <p>${desc[id]}</p>`;
    $("#bom-table").innerHTML = `<thead><tr><th>id</th><th>qty</th><th>item</th><th>key spec</th><th>example</th><th>est. USD</th><th>status</th></tr></thead><tbody>${
      items.map((i: any) => `<tr><td>${esc(i.item_id)}</td><td>${esc(i.qty)}</td><td>${esc(i.description)}</td><td>${esc(i.key_spec)}</td>
      <td>${i.verified_url ? `<a href="${esc(i.verified_url)}" rel="noopener">${esc(i.example_part)}</a>` : esc(i.example_part)}</td>
      <td class="usd">${Number(i.est_total_usd).toFixed(2)}</td><td>${esc(i.ownership)}</td></tr>`).join("")}</tbody>`;
  });
});

// ---------------------------------------------------------------- roadmap + status
const GATES: Record<number, string> = {
  0: "wet/dry dimensions, damage and break tension -> tension band",
  1: ">= 20 consecutive cycles, exact turns, no skipped steps, tension in band, vision stops a fault",
  2: "20/20 cut + release without dragging or delamination",
  3: "repeatable dried tail shape that seats in the nest",
  4: "environment and geometry logged; no fixture deformation",
  5: "one seed, three tails, no adhesive on active coils, intact tip, viability",
  6: "labelled real-image confusion matrix",
  7: ">= 50 transfers without drop or collision",
  8: "bench release tests, mass/CG/thrust margin, permissions",
};
const LEVELS = ["SOURCE-SUPPORTED", "ENGINEERING ASSUMPTION", "RECONSTRUCTED REFERENCE", "CAD-VALIDATED", "SOFTWARE-TESTED", "PHYSICALLY TESTED", "BIOLOGICALLY VALIDATED", "FLIGHT-VALIDATED"];
data("status").then((s) => {
  $("#ladder").innerHTML = s.phases.map((p: any) => `<li class="${p.phase <= 1 ? "first" : p.phase === 8 ? "last" : ""}">
    <span class="ph">Phase ${p.phase}</span><strong>${esc(p.name)}</strong><span class="gate">${esc(GATES[p.phase])}</span>
    <span class="tag concept">${esc(p.status)}</span></li>`).join("");
  $("#levels").innerHTML = LEVELS.map((l) => `<span class="lvl" data-l="${l}">${l}</span>`).join("");
  $("#status-table").innerHTML = `<thead><tr><th>item</th><th>evidence level</th><th>detail</th><th>evidence</th></tr></thead><tbody>${
    s.items.map((i: any) => `<tr><td>${esc(i.name)}</td><td><span class="lvl" data-l="${esc(i.level)}">${esc(i.level)}</span></td><td>${esc(i.detail)}</td>
    <td>${(i.evidence as string[]).map((e) => `<a href="${REPO}/blob/main/${esc(e)}">${esc(e.split("/").pop())}</a>`).join(", ")}</td></tr>`).join("")}</tbody>`;
});

// ---------------------------------------------------------------- downloads
const V = "v0.3.0-alpha";
$("#release-links").innerHTML = [
  [`SeedForge_${V}_COMPLETE.zip`, "everything in the repository at the release tag"],
  [`SeedForge_${V}_PHASE1_PRINTS.zip`, "3MF/STL/STEP for the core cell, the fit coupon and M3"],
  [`SeedForge_${V}_SEED_REFERENCE_CAD.zip`, "MR/PR reference carrier models"],
  [`SeedForge_${V}_DOCUMENTATION.zip`, "docs, renders, diagrams and this site"],
].map(([f, d]) => `<li><a href="${REPO}/releases/download/${V}/${f}">${f}</a><span>${d}</span></li>`).join("") +
  `<li><a href="${RELEASE}">All releases</a><span>checksums in SHA256SUMS.txt</span></li>`;
$("#folder-links").innerHTML = [
  ["hardware/cad/3mf/machine", "3MF print files"], ["hardware/cad/stl/machine", "STL print files"], ["hardware/cad/step", "STEP (editable)"],
  ["hardware/cad/source", "CadQuery generators"], ["hardware/bom", "BOM CSV"], ["hardware/wiring", "pin map and wiring table"],
  ["hardware/drawings", "plywood drilling template (1:1 SVG)"], ["firmware", "Uno and ESP32-C3 firmware"], ["software", "Python package"],
  ["validation", "worksheets and templates"],
].map(([p, d]) => `<li><a href="${REPO}/tree/main/${p}">${p}</a><span>${d}</span></li>`).join("");
data("parts").then((parts) => {
  const core = parts.filter((p: any) => p.family === "machine" && p.status === "core");
  $("#parts-table").innerHTML = `<thead><tr><th>part</th><th>module</th><th>qty</th><th>material</th><th>A1 Mini</th><th>files</th></tr></thead><tbody>${
    core.map((p: any) => `<tr><td>${esc(p.file_stem)}</td><td>${esc(p.module)}</td><td>${esc(p.qty)}</td><td>${esc(p.material)}</td>
      <td>${p.fits_a1_mini === "True" ? "fits" : "check"}</td>
      <td><a href="${REPO}/raw/main/hardware/cad/3mf/machine/${esc(p.file_stem)}.3mf">3MF</a> &middot;
      <a href="${REPO}/raw/main/hardware/cad/stl/machine/${esc(p.file_stem)}.stl">STL</a> &middot;
      <a href="${REPO}/raw/main/hardware/cad/step/machine/${esc(p.file_stem)}.step">STEP</a></td></tr>`).join("")}</tbody>`;
});
