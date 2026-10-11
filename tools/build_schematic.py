#!/usr/bin/env python3
"""Block-level system schematic for the Phase-1/2 core cell.

    python tools/build_schematic.py

Draws every module as a block with its pins; pins carry **net labels**
(same label = same conductor, the usual schematic convention). The main power
path is drawn as wires. Generated from the same tables as the wiring schedule
(tools/build_wiring.py), so pin assignments stay in one place.

Output: hardware/electronics/seedforge_core_schematic.svg
Research-prototype wiring; not certified machinery safety.
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware" / "electronics" / "seedforge_core_schematic.svg"

NAVY, GREEN, MUTED, RED, AMBER = "#14273a", "#2f6f4f", "#5b6b7a", "#b03a2e", "#a6761d"
NET_COLOUR = {"12V_SW": RED, "12V_SW (pre-fuse)": RED, "12V": RED, "20V": RED, "5V_SERVO": AMBER, "GND": NAVY}

# block: (title, subtitle, x, y, w, left pins, right pins); pin = (pin name, net)
BLOCKS = [
    ("Arduino Uno", "core controller (ATmega328P, 5 V)", 990, 300, 230,
     [("D2", "ROT_STEP"), ("D3", "ROT_DIR"), ("D4", "LIN_STEP"), ("D5", "LIN_DIR"), ("D6", "DRV_EN"),
      ("5V", "5V_LOGIC"), ("GND", "GND")],
     [("D7", "START"), ("D8", "ESTOP_FB"), ("D9", "HOME_SW"), ("D10", "END_SW"), ("D11", "HX_DOUT"), ("D12", "HX_SCK"),
      ("A0", "DANCER"), ("A1", "LINK_C3_TX"), ("A2", "LINK_UNO_TX"), ("A3", "GUARD_SW"), ("A4", "SDA"), ("A5", "SCL"),
      ("USB", "PC USB (115200)")]),
    ("A4988 rotation", "MS1-3 = 5 V (1/16)", 500, 300, 190,
     [("VMOT", "12V_SW"), ("GND", "GND"), ("1A/1B", "ROT_COIL_A"), ("2A/2B", "ROT_COIL_B")],
     [("STEP", "ROT_STEP"), ("DIR", "ROT_DIR"), ("EN", "DRV_EN"), ("VDD", "5V_LOGIC"), ("RST=SLP", "-")]),
    ("A4988 linear", "MS1-3 = 5 V (1/16)", 500, 500, 190,
     [("VMOT", "12V_SW"), ("GND", "GND"), ("1A/1B", "LIN_COIL_A"), ("2A/2B", "LIN_COIL_B")],
     [("STEP", "LIN_STEP"), ("DIR", "LIN_DIR"), ("EN", "DRV_EN"), ("VDD", "5V_LOGIC"), ("RST=SLP", "-")]),
    ("NEMA17 rotation", "keyed JST-XH, never USB-C", 60, 320, 170,
     [], [("coil A", "ROT_COIL_A"), ("coil B", "ROT_COIL_B")]),
    ("NEMA17 linear", "keyed JST-XH, never USB-C", 60, 520, 170,
     [], [("coil A", "LIN_COIL_A"), ("coil B", "LIN_COIL_B")]),
    ("100 uF x2", "at each VMOT", 60, 680, 170, [], [("+", "12V_SW"), ("-", "GND")]),
    ("Buck 12 -> 5 V", "LM2596, after the E-stop contact", 60, 820, 170, [],
     [("VIN+", "12V_SW (pre-fuse)"), ("VOUT+", "5V_SERVO"), ("GND", "GND")]),
    ("XIAO ESP32-C3 (optional)", "bridge + display, 3.3 V, not safety", 1510, 300, 220,
     [("D6/GPIO21 TX", "LINK_C3_TX"), ("D7/GPIO20 RX", "LINK_C3_RX"), ("GND", "GND")],
     [("D8/GPIO8", "TFT_SCK"), ("D9/GPIO9", "TFT_MISO"), ("D10/GPIO10", "TFT_MOSI"), ("D1/GPIO3", "TFT_CS"),
      ("D2/GPIO4", "TFT_DC"), ("D3/GPIO5", "TFT_RST"), ("3V3", "3V3"), ("USB-C", "PC USB / BLE / Wi-Fi")]),
    ("Link divider", "5 V -> 3.3 V", 1510, 560, 220,
     [("in (1 k series)", "LINK_UNO_TX"), ("2 k to GND", "GND")], [("out", "LINK_C3_RX")]),
    ("ILI9341 2.2 in (optional)", "SPI display", 2020, 300, 180,
     [("SCK", "TFT_SCK"), ("MISO", "TFT_MISO"), ("MOSI", "TFT_MOSI"), ("CS", "TFT_CS"), ("DC", "TFT_DC"),
      ("RST", "TFT_RST"), ("VCC, LED", "3V3")], []),
    ("HX711", "24-bit ADC, logic 5 V", 1510, 690, 220,
     [("DOUT", "HX_DOUT"), ("SCK", "HX_SCK"), ("VCC", "5V_LOGIC"), ("GND", "GND")],
     [("E+/E-/A+/A-", "LOAD_CELL")]),
    ("1 kg bar load cell", "clamped in F08 + F13", 2020, 700, 180, [("4 wires", "LOAD_CELL")], []),
    ("Inputs", "switches to GND (INPUT_PULLUP); D8 divider (INPUT)", 990, 690, 230,
     [], [("START (NO)", "START"), ("12V_SW sense divider", "ESTOP_FB"), ("home sw (NC)", "HOME_SW"), ("end sw (NC)", "END_SW"),
          ("guard sw (NC, opt.)", "GUARD_SW"), ("dancer pot wiper", "DANCER")]),
    ("PCA9685", "0x40, servo power on V+", 1510, 850, 220,
     [("SDA", "SDA"), ("SCL", "SCL"), ("VCC", "5V_LOGIC"), ("V+", "5V_SERVO"), ("GND", "GND")],
     [("CH0", "clamp servo"), ("CH1", "cutter servo"), ("CH6", "demold support servo")]),
    ("ICM-20948 (opt.)", "0x69, check 5 V-safe I2C", 2020, 870, 180, [("SDA", "SDA"), ("SCL", "SCL"), ("GND", "GND")], []),
]

POWER_CHAIN = [("12 V 3 A adapter", "certified; barrel jack"), ("Fuse 3 A", "first after the jack"),
               ("E-STOP contact", "NC, DC-rated, latching"), ("Fuse 2 A", "motor branch"),
               ("VMOT node", "100 uF at each A4988"), ("Sense divider", "10 k / 4.7 k -> Uno D8")]

ROW = 19


def text(x, y, s, size=12, fill=NAVY, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


def block(title, sub, x, y, w, left, right):
    n = max(len(left), len(right), 1)
    h = 46 + n * ROW + 8
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#f6f8f9" stroke="{NAVY}" stroke-width="1.4"/>',
           text(x + 10, y + 19, title, 14, NAVY, "bold"), text(x + 10, y + 35, sub, 10.5, MUTED)]
    for i, (pin, net) in enumerate(left):
        yy = y + 58 + i * ROW
        col = NET_COLOUR.get(net, GREEN)
        out += [f'<line x1="{x - 26}" y1="{yy - 4}" x2="{x}" y2="{yy - 4}" stroke="{col}" stroke-width="1.6"/>',
                text(x + 8, yy, pin, 11), text(x - 30, yy, net, 10.5, col, "bold", "end")]
    for i, (pin, net) in enumerate(right):
        yy = y + 58 + i * ROW
        col = NET_COLOUR.get(net, GREEN)
        out += [f'<line x1="{x + w}" y1="{yy - 4}" x2="{x + w + 26}" y2="{yy - 4}" stroke="{col}" stroke-width="1.6"/>',
                text(x + w - 8, yy, pin, 11, NAVY, "normal", "end"), text(x + w + 30, yy, net, 10.5, col, "bold")]
    return out


def main():
    W, H = 2260, 1110
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Inter, Helvetica, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="#fff"/>',
         text(40, 40, "SeedForge R3.1 core cell - system schematic (block level, budget power path)", 22, NAVY, "bold"),
         text(40, 62, "Same net label = same conductor. Research-prototype wiring, not certified machinery safety. "
                      "Generated by tools/build_schematic.py; pin map: hardware/wiring/WIRING.md.", 12, MUTED)]
    # power chain across the top
    x, y = 40, 100
    bw, gap = 270, 70
    for i, (t, s) in enumerate(POWER_CHAIN):
        bx = x + i * (bw + gap)
        safety = "E-STOP" in t or "Fuse" in t
        g.append(f'<rect x="{bx}" y="{y}" width="{bw}" height="54" rx="6" fill="{"#e7f0ea" if safety else "#fff8e6"}" '
                 f'stroke="{GREEN if safety else AMBER}" stroke-width="{2 if safety else 1.4}"/>')
        g += [text(bx + 10, y + 22, t, 13, NAVY, "bold"), text(bx + 10, y + 40, s, 10.5, MUTED)]
        if i:
            g.append(f'<line x1="{bx - gap}" y1="{y + 27}" x2="{bx - 6}" y2="{y + 27}" stroke="{RED}" stroke-width="2.2" '
                     f'marker-end="url(#arr)"/>')
    end_x = x + len(POWER_CHAIN) * (bw + gap) - gap
    g.append(f'<line x1="{end_x}" y1="{y + 27}" x2="{end_x + 40}" y2="{y + 27}" stroke="{RED}" stroke-width="2.2"/>')
    g.append(text(end_x + 44, y + 23, "12V_SW", 12, RED, "bold"))
    g.append(text(end_x + 44, y + 38, "-> A4988 VMOT x2", 10.5, RED))
    g.append(text(40, y + 80, "The E-stop-switched rail (before the motor fuse) also feeds the Buck 12 -> 5 V = 5V_SERVO "
                              "(PCA9685 V+). Pressing the E-stop de-energises motors and servos; the Uno senses the VMOT node "
                              "through the divider on D8 (ESTOP_FB): no auxiliary contact needed.", 11.5, MUTED))
    g.append(text(40, y + 97, "Star ground: jack -, buck, Uno GND (and the optional XIAO GND) join one lever connector once "
                              "(net GND). Uno powered from PC USB. All mounting hardware is M2.", 11.5, MUTED))
    for b in BLOCKS:
        g += block(*b)
    g.insert(2, f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>')
    g.append(text(40, H - 20, "Legend: red = actuator power, amber = servo rail, navy = ground, green = signal. "
                              "Pin details and connector types: docs/electronics.md.", 11.5, MUTED))
    g.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(g) + "\n")
    print(f"schematic: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
