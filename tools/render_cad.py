#!/usr/bin/env python3
"""Render the documentation images from the CAD GLBs (headless Chromium + Three.js).

    python tools/render_cad.py            # all renders -> docs/images/
    python tools/render_cad.py hero_machine mandrel_closeup

Needs: `npm ci` in website/ (for three.js), `pip install playwright pillow`
and a Playwright Chromium.  Every image is labelled as a CAD render; none of
them is a photograph or evidence that hardware works.
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import json
import shutil
import sys
import threading
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
NAVY, GREEN, MUTED, RULE = (20, 39, 58), (47, 111, 79), (91, 107, 122), (201, 209, 217)
GLB = "hardware/cad/glb"


def font(size, bold=False):
    names = (["Inter-SemiBold.otf", "Inter-Bold.otf"] if bold else ["Inter-Regular.otf"]) + \
            (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"])
    for base in ("/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"):
        for n in names:
            p = Path(base) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


# name -> (glb, camera params, title, subtitle, labels {node prefix: text}, extra)
CORE_LABELS = {
    "W01_nema17_rotation_mount": "W01 rotation motor mount (R3)",
    "mini_drill_chuck": "mini chuck on motor shaft",
    "mandrel_0p8mm_steel": "0.8 mm steel mandrel (bought, not printed)",
    "W05_mandrel_end_guide": "W05 end guide + W13 riser",
    "W12_angle_adjustable_guide_arm": "W12 guide arm, +/-60 deg scale",
    "F06_veneer_guide_lower": "F06/F07 veneer guide",
    "W11_lm8uu_traverse_carriage": "W11 LM8UU carriage + T8 nut",
    "W09_linear_motor_end_block": "W09 linear motor end",
    "W10_linear_idler_end_block": "W10 idler end + 608",
    "F08_load_cell_mount": "F08 load cell (tension sensor)",
    "F11_dancer_pivot_post": "F11 dancer pivot (pot)",
    "veneer_spool": "veneer reel on F09/F02 stands",
    "camera_proxy": "USB board camera on W18 arm",
    "W15_nema17_body_clamp_rotation": "W15 motor body clamp (M2)",
}
JOBS = {
    "hero_machine": (f"{GLB}/phase1_core_cell.glb", dict(az=-58, el=30, zoom=1.35, edges=1, w=1800, h=1050),
                     "SeedForge core winding cell (M1 + M2 + fixed QA camera)",
                     "R3.1 CAD layout render - interference-checked in CAD, not yet physically validated", {}),
    "winder_isometric": (f"{GLB}/phase1_core_cell.glb", dict(az=-58, el=30, zoom=1.5, edges=1, w=1800, h=1100),
                         "Phase-1 core cell - isometric", "CAD render with nominal purchased-part proxies (measure real parts)",
                         CORE_LABELS),
    "winder_exploded": (f"{GLB}/phase1_core_cell.glb", dict(az=-58, el=32, zoom=1.25, edges=1, w=1800, h=1100,
                         hide="veneer_strip,base_plywood",
                         move=";".join([
                             "W12_angle_adjustable_guide_arm:0:0:45", "F06_veneer_guide_lower:0:0:70", "F07_veneer_guide_lid:0:0:90",
                             "W11_lm8uu_traverse_carriage:0:0:25", "lm8uu_1:0:0:25", "lm8uu_2:0:0:25", "t8_flange_nut:-25:0:25",
                             "W13_w05_axis_riser_11mm:0:0:-20", "W05_mandrel_end_guide:0:0:15", "guide_tube_ptfe:0:0:15",
                             "mini_drill_chuck:25:0:20", "chuck_adapter_5mm:25:0:20", "mandrel_0p8mm_steel:25:0:40",
                             "motor_rotation_NEMA17:-40:0:0", "motor_linear_NEMA17:-40:0:0", "W15_nema17_body_clamp_rotation:-40:0:30", "W16_nema17_body_clamp_linear:-40:0:30", "coupler_5x8:-20:0:0",
                             "W14_limit_switch_clamp_home:0:-30:0", "microswitch_home:0:-30:0", "microswitch_lever_home:0:-30:0",
                             "W14_limit_switch_clamp_end:0:-30:0", "microswitch_end:0:-30:0", "microswitch_lever_end:0:-30:0"])),
                        "Phase-1 core cell - exploded", "Green parts are new in R3.1; grey parts are retained from R3; every fastener is M2",
                        {k: v for k, v in CORE_LABELS.items() if k in ("W12_angle_adjustable_guide_arm", "W11_lm8uu_traverse_carriage",
                                                                       "W09_linear_motor_end_block", "W10_linear_idler_end_block",
                                                                       "W05_mandrel_end_guide", "mandrel_0p8mm_steel", "F06_veneer_guide_lower")}),
    "mandrel_closeup": (f"{GLB}/rotation_train.glb", dict(az=-75, el=18, zoom=1.15, edges=1, w=1800, h=900),
                        "Rotation train: NEMA17 -> mini chuck -> 0.8 mm mandrel -> W05 support",
                        "Paper-reference 2.5 x 0.5 mm coil shown on the mandrel; axis height 37.0 mm everywhere",
                        {"mini_drill_chuck": "mini drill chuck (5 mm arbor)", "mandrel_0p8mm_steel": "0.8 mm x 100 mm steel mandrel",
                         "veneer_coil_wound": "wound body (reference geometry)", "W13_w05_axis_riser_11mm": "W13 riser (11.0 mm)",
                         "W05_mandrel_end_guide": "W05 end guide (R3)", "guide_tube_ptfe": "PTFE bushing"}),
    "feed_tension_path": (f"{GLB}/phase1_core_cell.glb", dict(az=-135, el=26, zoom=1.25, edges=1, w=1800, h=1050,
                          only="F09,F02,F10,veneer,axle,F11,pot_10k,F04,F05,F08,F12,F13,load_cell,sensing_roller,W11,W12,F06,F07,W09,W10,rod,lead,lm8,t8,coupler,motor_linear"),
                          "M1 feed and tension path", "reel -> drag -> dancer (pot) -> load-cell roller -> angle-adjustable guide -> mandrel",
                          {"veneer_spool": "reel + felt drag (F10 hubs)", "F05_dancer_roller": "dancer roller (F04 arm)",
                           "F11_dancer_pivot_post": "F11 pivot post + 10k pot", "F12_sensing_roller_yoke": "F12 roller yoke (2 x MR62ZZ on M2)",
                           "F08_load_cell_mount": "F08 cradle + F13 cap clamp the 1 kg cell", "F06_veneer_guide_lower": "guide on W12 arm"}),
    "clamp_cut_demold": (f"{GLB}/m3_clamp_cut_demold.glb", dict(az=-50, el=30, zoom=1.2, edges=1, w=1600, h=900),
                         "M3 clamp, cut and demold tooling (R3 parts)", "Layout of R3 parts; Phase-2 mounting to the core cell is still open",
                         {"X01_sg90_clamp_mount": "X01 servo clamp mount", "X02_soft_clamp_jaw_a": "X02 silicone-lined jaws",
                          "X04_cutter_guard": "X04 guard over purchased shear", "W07_split_support_lower": "W07/W08 split demold support"}),
    "tail_former": (f"{GLB}/tail_former.glb", dict(az=-40, el=42, zoom=1.15, edges=1, w=1600, h=1000),
                    "M4 split tail former", "The split former opens to release the wet tail - no sliding over an undercut",
                    {"T01_tail_former_left": "T01 left half", "T02_tail_former_right": "T02 right half (opens)",
                     "T03_tail_sweep_shoe": "T03 servo sweep shoe", "T04_tail_blank_clamp": "T04 blank clamp", "tail_blank_wet": "wet tail blank"}),
    "drying_station": (f"{GLB}/drying_station.glb", dict(az=-35, el=30, zoom=1.2, edges=1, w=1600, h=1000),
                       "M5 free-drying buffer", "Wet bodies rest unrestrained on PTFE/silicone mesh; room-temperature airflow, no heater",
                       {"Q01_free_dry_tray_2": "Q01 trays (stackable buffer)", "usb_fan_120mm": "120 mm USB fan on Q02"}),
    "assembly_station": (f"{GLB}/assembly_station.glb", dict(az=-60, el=40, zoom=1.15, edges=1, w=1800, h=1000),
                         "M6 seed, tip and three-tail assembly tooling (development)", "S07/S08 are mould MASTERS for compliant working inserts",
                         {"S04_three_tail_assembly_nest": "S04 three-tail nest (120 deg)", "S01_seed_hopper": "S01 hopper + S02 disk",
                          "S05_10ml_syringe_holder": "S05/S06 syringe dispenser", "S07_tip_mold_half_A": "S07/S08 tip mould masters"}),
    "vision_station": (f"{GLB}/phase1_core_cell.glb", dict(az=-150, el=24, zoom=1.3, edges=1, w=1600, h=1100,
                       only="camera_proxy,W17,W18,camera_mast,backlight,mandrel,veneer_coil,mini_drill,W05,W13,guide_tube,W01,motor_rotation"),
                       "M7 fixed vision QA station", "Overhead camera, fixed focus, back-light panel under the coil: deterministic silhouette QA",
                       {"camera_proxy": "38 mm USB board camera, M12 lens", "W18_camera_arm": "W18 arm on a plywood mast (M2 wood screws)",
                        "backlight_panel": "back-light panel under the coil", "veneer_coil_wound": "coil under inspection"}),
    "hero_seed_carrier": (f"{GLB}/finished_carrier.glb", dict(az=-35, el=15, zoom=1.05, edges=0, w=1400, h=1400),
                          "Three-tailed self-burying carrier - reference geometry",
                          "Inspired by Luo et al., Nature 614, 463-470 (2023). Reconstructed reference, not the authors' CAD.", {}),
    "seed_carrier_exploded": (f"{GLB}/exploded_carrier.glb", dict(az=-35, el=20, zoom=1.0, edges=0, w=1500, h=1300),
                              "Carrier reference - exploded", "Body (7 coils) + three tails + biodegradable tip + seed envelope",
                              {"body": "7-coil body, 2.5 x 0.5 mm", "tail1": "tail 27 mm", "tail2": "tail 29.5 mm", "tail3": "tail 32.5 mm",
                               "tip": "tip envelope", "seed": "seed envelope"}),
    "optional_drone_payload": (f"{GLB}/payload_cassette.glb", dict(az=-40, el=32, zoom=1.15, edges=1, w=1600, h=1000),
                               "OPTIONAL downstream concept: four-cell payload cassette",
                               "Concept only - not flight-validated. One carrier per isolated cell; fail-closed doors.",
                               {"D01_four_cell_payload_cassette": "D01 cassette", "D02_door_1": "D02 door (one per cell)",
                                "D03_servo_mount_1": "D03 gate servo mount"}),
    "seed_carrier_dimensioned": (f"{GLB}/finished_carrier.glb", dict(az=-90, el=0, zoom=0.9, edges=0, w=1400, h=1600, ortho=1),
                                 "Carrier reference - dimensions (mm)", "SOURCE-SUPPORTED values in bold; tail/tip free shape is RECONSTRUCTED", {}),
}
DIAGRAM_COPIES = {"electronics_architecture": "B_electronics_hierarchy", "power_architecture": "C_power_tree",
                  "controller_fsm": "E_state_machine"}


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path, port: int):
    handler = functools.partial(_Quiet, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def shoot(jobs, port):
    from playwright.async_api import async_playwright
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for name, (glb, params, *_rest) in jobs.items():
            q = urllib.parse.urlencode({"glb": "/" + glb, **params})
            page = await b.new_page(viewport={"width": params["w"], "height": params["h"]})
            await page.goto(f"http://127.0.0.1:{port}/tools/render/render.html?{q}")
            await page.wait_for_function("window.__done === true", timeout=240000)
            path = OUT / f"_{name}_raw.png"
            await page.screenshot(path=str(path))
            res[name] = (path, await page.evaluate("window.__anchors"))
            await page.close()
        await b.close()
    return res


def annotate(name, raw, anchors, title, subtitle, labels):
    img = Image.open(raw).convert("RGB")
    W, H = img.size
    band = 110
    canvas = Image.new("RGB", (W, H + band + 40), "white")
    canvas.paste(img, (0, band))
    d = ImageDraw.Draw(canvas)
    d.text((48, 28), title, font=font(34, True), fill=NAVY)
    d.text((48, 72), subtitle, font=font(20), fill=MUTED)
    d.line([(48, band - 6), (W - 48, band - 6)], fill=GREEN, width=3)
    d.text((48, H + band + 8), "SeedForge  |  CAD render generated by tools/render_cad.py  |  not a photograph",
           font=font(16), fill=MUTED)
    f = font(19, True)
    placed = []
    for key, text in labels.items():
        a = next((v for k, v in anchors.items() if k and k.startswith(key)), None)
        if not a:
            continue
        cx, cy = a["c"]
        cy += band
        left = cx < W / 2
        tx = 40 if left else W - 40 - d.textlength(text, font=f)
        ty = max(band + 20, min(H + band - 40, cy - 60 if cy > band + 120 else cy + 60))
        while any(abs(ty - p) < 34 and side == left for p, side in placed):
            ty += 36
        placed.append((ty, left))
        ex = tx + d.textlength(text, font=f) + 8 if left else tx - 8
        d.line([(ex, ty + 12), (cx, cy)], fill=NAVY, width=2)
        d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=GREEN)
        d.rectangle([tx - 6, ty - 4, tx + d.textlength(text, font=f) + 6, ty + 26], fill=(255, 255, 255))
        d.text((tx, ty), text, font=f, fill=NAVY)
    if name == "seed_carrier_dimensioned":
        dimension_carrier(d, anchors, band)
    canvas.save(OUT / f"{name}.png", optimize=True)
    raw.unlink()


def dimension_carrier(d, anchors, band):
    """Dimension lines from the projected (orthographic, side) bounding boxes."""
    body, tip = anchors.get("body"), anchors.get("tip")
    allbb = [v["bb"] for v in anchors.values()]
    x0, y0 = min(b[0] for b in allbb), min(b[1] for b in allbb)
    x1, y1 = max(b[2] for b in allbb), max(b[3] for b in allbb)
    wz = [v["world"] for v in anchors.values()]
    total_mm = max(w[4] for w in wz) - min(w[1] for w in wz)      # three.js y = CAD z (axial)
    f = font(20, True)

    def vdim(x, ya, yb, text):
        d.line([(x, ya + band), (x, yb + band)], fill=NAVY, width=2)
        for y in (ya, yb):
            d.line([(x - 10, y + band), (x + 10, y + band)], fill=NAVY, width=2)
        d.text((x + 14, (ya + yb) / 2 + band - 12), text, font=f, fill=NAVY)

    vdim(x1 + 60, y0, y1, f"overall {total_mm:.1f} (reference)")
    if body:
        bx0, by0, bx1, by1 = body["bb"]
        vdim(x0 - 220, by0, by1, "body 35.0, 7 coils")
        d.text((x0 - 206, (by0 + by1) / 2 + band + 18), "2.5 x 0.5 ribbon\non 0.8 mandrel", font=font(18), fill=MUTED)
    if tip:
        tx0, ty0, tx1, ty1 = tip["bb"]
        vdim(x0 - 220, ty0 + 6, ty1, "tip envelope 14")
    d.text((x1 + 60, y0 + band - 40), "tails: 27 / 29.5 / 32.5 path length", font=font(18), fill=MUTED)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(JOBS)
    jobs = {n: JOBS[n] for n in names if n in JOBS}
    port = 8799
    httpd = serve(ROOT, port)
    try:
        shots = asyncio.run(shoot(jobs, port))
    finally:
        httpd.shutdown()
    for n, (raw, anchors) in shots.items():
        _, _, title, subtitle, labels = jobs[n]
        annotate(n, raw, anchors, title, subtitle, labels)
        print("rendered", n)
    for dst, src in DIAGRAM_COPIES.items():
        p = ROOT / "docs" / "diagrams" / f"{src}.png"
        if p.exists() and (not sys.argv[1:] or dst in names):
            shutil.copy2(p, OUT / f"{dst}.png")
    if not sys.argv[1:] or "complete_process" in names:
        complete_process()


def complete_process():
    """Montage of module renders along the process line."""
    tiles = [("M1+M2", "winder_isometric"), ("M3", "clamp_cut_demold"), ("M4", "tail_former"), ("M5", "drying_station"),
             ("M6", "assembly_station"), ("M7", "vision_station"), ("M10*", "optional_drone_payload")]
    tw, th = 520, 330
    W = 60 + len(tiles) * (tw + 40)
    canvas = Image.new("RGB", (W, th + 230), "white")
    d = ImageDraw.Draw(canvas)
    d.text((60, 30), "SeedForge manufacturing process (CAD renders)", font=font(40, True), fill=NAVY)
    d.text((60, 82), "Green = core build target (v0.3); other stations are experimental/upcoming. *M10 is an optional downstream concept.",
           font=font(22), fill=MUTED)
    for i, (mod, src) in enumerate(tiles):
        p = OUT / f"{src}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        im = im.crop((0, 110, im.width, im.height - 40))
        im.thumbnail((tw, th))
        x = 60 + i * (tw + 40)
        canvas.paste(im, (x + (tw - im.width) // 2, 140))
        core = mod in ("M1+M2", "M3", "M7")
        d.rectangle([x, 136, x + tw, 140 + th], outline=GREEN if core else RULE, width=3)
        d.text((x + 8, 150 + th), mod, font=font(28, True), fill=GREEN if core else NAVY)
        if i < len(tiles) - 1:
            ax = x + tw + 6
            d.polygon([(ax, 140 + th // 2 - 10), (ax + 28, 140 + th // 2), (ax, 140 + th // 2 + 10)], fill=NAVY)
    canvas.save(OUT / "complete_process.png", optimize=True)
    print("rendered complete_process")


if __name__ == "__main__":
    main()
