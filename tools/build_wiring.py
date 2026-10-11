#!/usr/bin/env python3
"""R3.1 wiring schedule: single source -> CSV tables, Markdown and a pin-map SVG.

Outputs:
  hardware/wiring/connection_table.csv   point-to-point schedule (development wiring)
  hardware/wiring/pin_map.csv            Uno / ESP32-C3 / PCA9685 allocation
  hardware/wiring/WIRING.md              readable tables
  docs/diagrams/D_arduino_pin_map.svg            Uno pin-map figure
  website/public/data/wiring.json
The R2 schedule in archive/seedforge-r3-package/wiring/ used a different pin map
(display on the Uno, HX711 on A0/A1); it is superseded and kept only for history.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PIN_MAP = [
    # board, pin, signal, connects to, electrical notes
    ("Uno", "D2", "ROT_STEP", "A4988 rotation STEP", "5 V output, PORTD2 (ISR)"),
    ("Uno", "D3", "ROT_DIR", "A4988 rotation DIR", "5 V output"),
    ("Uno", "D4", "LIN_STEP", "A4988 linear STEP", "5 V output, PORTD4 (ISR)"),
    ("Uno", "D5", "LIN_DIR", "A4988 linear DIR", "5 V output"),
    ("Uno", "D6", "A4988_ENABLE", "both A4988 ENABLE", "active LOW; 10 kOhm pull-up to 5 V keeps drivers off during reset"),
    ("Uno", "D7", "START", "pushbutton to GND", "INPUT_PULLUP; BOOT=home, READY=start, moving=stop, SAFE_STOP=reset"),
    ("Uno", "D8", "ESTOP_FB", "switched 12 V rail via 10 kOhm (top) / 4.7 kOhm (to GND) divider", "INPUT; about 3.8 V = rail present = safe; LOW = E-stop pressed, fuse blown or wire broken"),
    ("Uno", "D9", "HOME", "home microswitch NC to GND", "INPUT_PULLUP; HIGH = actuated or broken wire"),
    ("Uno", "D10", "END", "end microswitch NC to GND", "INPUT_PULLUP; HIGH = actuated or broken wire"),
    ("Uno", "D11", "HX711_DOUT", "HX711 DOUT", "check the breakout's VDD/VCC: run HX711 logic at 5 V"),
    ("Uno", "D12", "HX711_SCK", "HX711 SCK", "output"),
    ("Uno", "D13", "STATUS_LED", "on-board LED", "solid = SAFE_STOP; never the only safety indication"),
    ("Uno", "A0", "DANCER", "10 kOhm pot wiper (F11)", "0-5 V; pot ends to 5 V and GND"),
    ("Uno", "A1", "LINK_RX", "ESP32-C3 GPIO21 (D6) TX", "3.3 V into 5 V input is read as HIGH"),
    ("Uno", "A2", "LINK_TX", "1 kOhm -> ESP32-C3 GPIO20 (D7) RX; 2 kOhm to GND", "divider makes ~3.3 V; never drive the C3 with 5 V"),
    ("Uno", "A3", "GUARD", "cutter-guard NC switch to GND (optional)", "set GUARD_FITTED=true in the sketch when wired"),
    ("Uno", "A4", "I2C_SDA", "PCA9685 0x40, ICM-20948 0x69, MCP23017 0x20", "check module pull-up voltage; 3.3 V-only modules need a level shifter"),
    ("Uno", "A5", "I2C_SCL", "same bus", "400 kHz"),
    ("ESP32-C3", "GPIO21/D6", "LINK_TX", "Uno A1", "3.3 V; the ESP32-C3 bridge is optional"),
    ("ESP32-C3", "GPIO20/D7", "LINK_RX", "Uno A2 via divider", "3.3 V max"),
    ("ESP32-C3", "GPIO8/D8", "TFT_SCK", "ILI9341 SCK", ""),
    ("ESP32-C3", "GPIO9/D9", "TFT_MISO", "ILI9341 MISO", "strapping pin: leave the boot button alone at power-up"),
    ("ESP32-C3", "GPIO10/D10", "TFT_MOSI", "ILI9341 MOSI", ""),
    ("ESP32-C3", "GPIO3/D1", "TFT_CS", "ILI9341 CS", ""),
    ("ESP32-C3", "GPIO4/D2", "TFT_DC", "ILI9341 DC", ""),
    ("ESP32-C3", "GPIO5/D3", "TFT_RST", "ILI9341 RESET", ""),
    ("PCA9685", "CH0", "CLAMP", "M3 clamp servo", "5 V servo rail"),
    ("PCA9685", "CH1", "CUTTER", "M3 cutter servo", ""),
    ("PCA9685", "CH2", "TAIL_SWEEP", "M4 sweep servo", ""),
    ("PCA9685", "CH3", "TAIL_CLAMP", "M4 clamp servo", ""),
    ("PCA9685", "CH4", "TRANSFER_GRIP", "M9 gripper", ""),
    ("PCA9685", "CH5", "TRANSFER_Z", "M9 Z lift", ""),
    ("PCA9685", "CH6", "DEMOLD_SUPPORT", "M3 split support (W07/W08)", "R3.1 addition"),
    ("MCP23017", "GPA0-3", "SEED_INDEX", "ULN2003 #1 IN1-IN4", "M6 seed indexer 28BYJ-48"),
    ("MCP23017", "GPB0-3", "SYRINGE", "ULN2003 #2 IN1-IN4", "M6 syringe 28BYJ-48"),
]

CONNECTIONS = [
    # subsystem, from, from_pin, to, to_pin, rail, notes
    ("Power", "12 V 3 A certified adapter", "barrel plug", "DC barrel jack", "5.5 x 2.1", "12V", "budget supply; check polarity (centre +) with a meter"),
    ("Power", "DC barrel jack", "+", "Fuse 3 A", "in", "12V", "fuse first, before anything else"),
    ("Power", "DC barrel jack", "-", "Star ground block", "GND", "GND", "single star point"),
    ("Power", "Fuse 3 A", "out", "E-stop contact (NC)", "COM", "12V", "E-stop physically breaks the actuator rail"),
    ("Power", "E-stop contact (NC)", "NC", "Fuse 2 A (motors)", "in", "12V_SW", ""),
    ("Power", "Fuse 2 A (motors)", "out", "A4988 rotation / linear", "VMOT", "12V_SW", "100 uF at each VMOT; set Vref before connecting motors"),
    ("Power", "E-stop contact (NC)", "NC", "Buck 12->5 V (LM2596)", "VIN+", "12V_SW", "servos lose power with the E-stop as well; set 5.0 V before connecting"),
    ("Power", "Buck 12->5 V (LM2596)", "VOUT+", "PCA9685", "V+ (screw terminal)", "5V_SERVO", "never feed from the Uno 5 V pin"),
    ("Power", "Buck 12->5 V (LM2596)", "VOUT+", "ULN2003 boards, LED back-light strip", "VCC", "5V_SERVO", "back-light could also run from USB"),
    ("Power", "all module grounds", "GND", "Star ground block", "GND", "GND", "Uno and ESP32 grounds join here once"),
    ("Logic power", "PC / powered hub", "USB", "Arduino Uno", "USB-B", "5V_USB", "development power"),
    ("Logic power", "PC / powered hub", "USB", "ESP32-C3 (optional)", "USB-C", "5V_USB", "do not also back-feed its 5 V pin"),
    ("Safety", "12V_SW motor rail (VMOT node, after the E-stop and the 2 A fuse)", "+", "10 kOhm -> Uno D8; 4.7 kOhm D8 -> GND", "D8", "sense", "Uno sees about 3.8 V while the rail is live; ESTOP_SENSE_RAIL=true in sf_config.h"),
    ("Winder", "Uno", "D2", "A4988 rotation", "STEP", "5V_LOGIC", ""),
    ("Winder", "Uno", "D3", "A4988 rotation", "DIR", "5V_LOGIC", ""),
    ("Winder", "Uno", "D4", "A4988 linear", "STEP", "5V_LOGIC", ""),
    ("Winder", "Uno", "D5", "A4988 linear", "DIR", "5V_LOGIC", ""),
    ("Winder", "Uno", "D6", "A4988 rotation + linear", "ENABLE", "5V_LOGIC", "shared, active LOW, 10 k pull-up to 5 V"),
    ("Winder", "Uno", "5V / GND", "A4988 rotation + linear", "VDD / GND", "5V_LOGIC", "RESET tied to SLEEP on each board"),
    ("Winder", "A4988 (both)", "MS1/MS2/MS3", "5 V", "HIGH", "5V_LOGIC", "1/16 microstepping; firmware assumes 3200 usteps/rev"),
    ("Winder", "A4988 rotation", "1A/1B/2A/2B", "NEMA17 rotation", "coil A / coil B", "12V_SW", "keyed 4-pin connector; never unplug while powered"),
    ("Winder", "A4988 linear", "1A/1B/2A/2B", "NEMA17 linear", "coil A / coil B", "12V_SW", ""),
    ("Winder", "Home microswitch (W14)", "C / NC", "Uno", "D9 / GND", "5V_LOGIC", "NC: a broken wire reads as 'actuated'"),
    ("Winder", "End microswitch (W14)", "C / NC", "Uno", "D10 / GND", "5V_LOGIC", ""),
    ("Winder", "START pushbutton", "NO", "Uno", "D7 / GND", "5V_LOGIC", ""),
    ("Tension", "Load cell", "E+/E-/A+/A-", "HX711", "E+/E-/A+/A-", "analog", "short twisted leads"),
    ("Tension", "HX711", "VCC / GND", "Uno", "5V / GND", "5V_LOGIC", ""),
    ("Tension", "HX711", "DOUT / SCK", "Uno", "D11 / D12", "5V_LOGIC", ""),
    ("Tension", "Dancer pot (F11)", "ends / wiper", "Uno", "5V,GND / A0", "5V_LOGIC", ""),
    ("I2C", "Uno", "A4 / A5", "PCA9685, ICM-20948, MCP23017", "SDA / SCL", "5V_LOGIC", "check each breakout's logic voltage"),
    ("I2C", "Uno", "5V / GND", "PCA9685", "VCC / GND", "5V_LOGIC", "logic only; servo power on V+"),
    ("Servos", "PCA9685", "CH0 / CH1 / CH6", "clamp / cutter / demold-support servos", "signal", "PWM", "M3"),
    ("Link", "ESP32-C3", "GPIO21 TX", "Uno", "A1", "3.3V", "38400 baud"),
    ("Link", "Uno", "A2", "1 kOhm -> ESP32-C3 GPIO20 RX (2 kOhm to GND)", "", "divided", ""),
    ("Link", "ESP32-C3", "GND", "Uno", "GND", "GND", ""),
    ("UI", "ESP32-C3", "GPIO8/9/10/3/4/5", "ILI9341", "SCK/MISO/MOSI/CS/DC/RST", "3.3V", "VCC and LED to 3V3"),
    ("Vision", "Host PC", "USB", "Camera", "USB", "data", "frames stay on the host; only events go to the controller"),
]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def pin_svg(path):
    uno = [r for r in PIN_MAP if r[0] == "Uno"]
    W, row_h, top = 1200, 34, 120
    H = top + row_h * len(uno) + 60
    navy, green, grey, muted = "#14273a", "#2f6f4f", "#e9ecef", "#5b6b7a"
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Inter, Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="40" y="52" font-size="26" font-weight="700" fill="{navy}">Arduino Uno pin map (SeedForge R3.1 core controller)</text>',
         f'<text x="40" y="82" font-size="15" fill="{muted}">Source: tools/build_wiring.py. Inputs are NC-to-GND with INPUT_PULLUP: an open wire reads as unsafe.</text>',
         f'<rect x="40" y="{top - 20}" width="190" height="{row_h * len(uno) + 30}" rx="12" fill="{navy}"/>',
         f'<text x="135" y="{top + row_h * len(uno) + 30}" text-anchor="middle" font-size="14" fill="#fff">ATmega328P</text>']
    for i, (_, pin, sig, to, note) in enumerate(uno):
        y = top + i * row_h
        colour = green if sig in ("ESTOP_FB", "HOME", "END", "GUARD", "A4988_ENABLE") else navy
        g += [f'<rect x="200" y="{y - 12}" width="60" height="24" rx="4" fill="#ffffff" stroke="{colour}" stroke-width="2"/>',
              f'<text x="230" y="{y + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="{colour}">{pin}</text>',
              f'<line x1="260" y1="{y}" x2="300" y2="{y}" stroke="{colour}" stroke-width="2"/>',
              f'<rect x="300" y="{y - 13}" width="170" height="26" rx="4" fill="{grey}"/>',
              f'<text x="310" y="{y + 5}" font-size="14" font-weight="600" fill="{navy}">{sig}</text>',
              f'<text x="485" y="{y + 5}" font-size="14" fill="{navy}">{to}</text>',
              f'<text x="485" y="{y + 19}" font-size="11" fill="{muted}">{note}</text>']
    g += [f'<rect x="40" y="{H - 38}" width="14" height="14" fill="{green}"/>',
          f'<text x="62" y="{H - 26}" font-size="13" fill="{muted}">safety-related input/output (software supplement only - the E-stop contact breaks actuator power)</text>',
          "</svg>"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(g))


def main():
    w = ROOT / "hardware" / "wiring"
    write_csv(w / "pin_map.csv", ["board", "pin", "signal", "connects_to", "notes"], PIN_MAP)
    write_csv(w / "connection_table.csv", ["subsystem", "from", "from_pin", "to", "to_pin", "rail", "notes"], CONNECTIONS)
    md = ["# Wiring (R3.1 development wiring)", "", "Generated by `python tools/build_wiring.py`. Research-prototype wiring, not certified machinery safety.",
          "The R2 schedule archived in `archive/seedforge-r3-package/wiring/` used a different pin map and is superseded.", "",
          "## Pin map", "", "| board | pin | signal | connects to | notes |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in PIN_MAP]
    md += ["", "## Point-to-point", "", "| subsystem | from | pin | to | pin | rail | notes |", "|---|---|---|---|---|---|---|"]
    md += ["| " + " | ".join(r) + " |" for r in CONNECTIONS]
    (w / "WIRING.md").write_text("\n".join(md) + "\n")
    pin_svg(ROOT / "docs" / "diagrams" / "D_arduino_pin_map.svg")
    site = ROOT / "website" / "public" / "data"
    site.mkdir(parents=True, exist_ok=True)
    (site / "wiring.json").write_text(json.dumps({"pins": [dict(zip(["board", "pin", "signal", "to", "notes"], r)) for r in PIN_MAP],
                                                  "connections": [dict(zip(["subsystem", "from", "from_pin", "to", "to_pin", "rail", "notes"], r)) for r in CONNECTIONS]}, indent=1))
    print(f"wiring: {len(PIN_MAP)} pins, {len(CONNECTIONS)} connections")


if __name__ == "__main__":
    main()
