"""Master purchased-parts list (source of truth for hardware/bom/*.csv).

Edit here, then run `python tools/build_bom.py`.

view: A = minimum demonstrator (feed, tension, winding, stopping, clamp, cut, demold, vision)
      B = adds the complete manufacturing bench (tails, drying, seed, tip, final QA, XY transfer)
      C = optional deployment system (cassette, payload controller, aircraft)
Prices are BUDGET planning estimates: typical marketplace prices for generic parts (USD,
October 2026, before tax/shipping; multi-packs divided per piece). They are NOT quotations.
Every fastener is M2 (one kit); see hardware/cad/README.md#fasteners.
ownership: buy | owned (price shown, counted only in the "buying everything" total) |
           optional (not needed for the view; not counted).
verified_url is filled only where the product page/ID was confirmed by web search on
2026-10-11; everything else names a part type and suppliers without a link.
"""

COLUMNS = ["item_id", "view", "module", "qty", "description", "key_spec", "example_part", "preferred_supplier",
           "alternative_supplier", "est_unit_usd", "ownership", "cad_model", "verified_url", "notes", "change_vs_r3"]

ROWS = [
    # ---------------------------------------------------------------- A: control
    ["A01", "A", "Control", 1, "Arduino Uno R3 (or clone)", "ATmega328P, 5 V logic", "Uno R3 compatible (CH340 USB)", "AliExpress / Amazon", "Arduino store", 6, "owned", "vendor download", "", "Core FSM + step generation. A clone works.", ""],
    ["A02", "A", "Control", 1, "ESP32-C3 USB-C board", "XIAO pin-out assumed by firmware", "Seeed XIAO ESP32C3 (SKU 113991054)", "Seeed Studio", "Digi-Key / Mouser", 5, "optional", "vendor download", "", "BLE/Wi-Fi bridge + display. Not needed: the Uno's USB port speaks the same protocol.", "optional for the budget build"],
    ["A03", "A", "Motion", 2, "A4988 stepper driver module", "set current limit per board Rsense", "generic A4988 (or Pololu #1182)", "AliExpress / Amazon", "Pololu", 1.5, "owned", "vendor download", "https://www.pololu.com/product/1182", "MS1-3 high (1/16). Small heatsink.", ""],
    ["A04", "A", "Motion", 2, "Electrolytic capacitor", ">=100 uF, >=25 V", "generic", "assortment", "Digi-Key", 0.1, "buy", "n/a", "", "One at each A4988 VMOT, close to the pins.", ""],
    ["A05", "A", "Motion", 2, "NEMA17 stepper motor", "200 step/rev, 40 mm body, 5 mm shaft", "17HS4401-class", "AliExpress / Amazon", "StepperOnline", 8, "owned", "generic STEP widely available", "", "Held by W15/W16 body clamps (face holes are M3 and unused).", ""],
    ["A06", "A", "M2", 1, "T8x8 lead screw + brass flange nut", "8 mm lead, 250 mm", "generic T8 x 8 kit", "AliExpress / Amazon", "StepperOnline", 7, "buy", "generic", "", "Nut flange bolts to W11 with 4 x M2 (holes 3.5 mm, 16 mm PCD: measure).", "250 mm (R3: 300 mm)"],
    ["A07", "A", "M2", 2, "Smooth rod", "8 mm, 250 mm", "generic linear rod (or salvaged printer rods)", "AliExpress / Amazon", "Misumi", 4, "buy", "n/a", "", "Traverse guides; W09/W10 sockets with M2 set screws.", "250 mm (R3: 300 mm)"],
    ["A08", "A", "M2", 2, "LM8UU linear bearing", "8 x 15 x 24 mm", "generic LM8UU", "AliExpress / Amazon", "igus (polymer alternative)", 1, "buy", "generic", "", "One per rod in W11.", "2 (R3 listed 4)"],
    ["A09", "A", "M2", 1, "Flexible shaft coupler", "5 mm to 8 mm", "generic jaw/helical coupler", "AliExpress / Amazon", "-", 2, "buy", "generic", "", "Linear motor to T8 screw (its own grub screws).", ""],
    ["A10", "A", "M2/M1", 3, "608ZZ ball bearing", "8 x 22 x 7 mm", "generic 608ZZ (skateboard bearing)", "AliExpress / Amazon", "local", 0.5, "buy", "generic", "", "W10 screw end (1) + spool stands F09/F02 (2).", ""],
    ["A11", "A", "M2", 1, "Mini drill chuck on 5 mm shaft", "grips 0.3-4 mm incl. 0.8 mm", "JT0-type mini chuck with 5 mm arbor", "AliExpress / Amazon", "-", 5, "buy", "measure", "", "Mounts on the rotation motor shaft (its own grub screws). MEASURE length and runout.", "replaces printed collet as baseline"],
    ["A12", "A", "M2", 1, "Forming mandrel wire", "0.8 mm straight music/spring wire, cut to 100 mm", "0.8 mm music wire (pack of straight lengths)", "hobby shop / Amazon", "K&S", 4, "buy", "MR01 reference", "", "Never print the working mandrel. Check straightness by rolling on glass.", ""],
    ["A13", "A", "M2", 1, "PTFE tube", "1 mm ID, 2 mm OD, 1 m", "PTFE capillary tube", "AliExpress / Amazon", "-", 2, "buy", "n/a", "", "Bushing in W05 for the free mandrel end.", ""],
    ["A14", "A", "M2", 2, "Lever microswitch", "KW12-type, NC used, 2 x M2 holes", "KW12 generic", "AliExpress / Amazon", "Omron SS-5GL", 0.3, "buy", "generic", "", "Home and end limits on W14 clamps (M2 screws), wired NC to GND.", ""],
    # ---------------------------------------------------------------- A: feed + tension
    ["A15", "A", "M1", 1, "Bar load cell + HX711 kit", "1 kg bar 80 x 12.7 x 12.7 mm; 24-bit ADC", "generic 1 kg cell + HX711 board kit (or SparkFun HX711 SEN-13879)", "AliExpress / Amazon", "SparkFun", 4, "buy", "measure", "https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html", "Clamped in F08/F13 (its own M4/M5 threads are not used). Calibrate in place with hanging masses.", ""],
    ["A16", "A", "M1", 2, "MR62ZZ miniature bearing", "2 x 6 x 2.5 mm", "generic MR62ZZ", "AliExpress / Amazon", "-", 0.4, "buy", "generic", "", "Sensing roller on an M2 x 16 axle in F12.", "replaces 3 x 623ZZ on M3"],
    ["A17", "A", "M1", 1, "Rotary potentiometer", "10 kOhm, 6 mm shaft, M7 bushing", "generic 16 mm pot", "AliExpress / Amazon", "Digi-Key", 0.3, "buy", "measure", "", "Dancer pivot on F11 (its own bushing nut); A0 input.", ""],
    ["A18", "A", "M1", 1, "Spool axle", "8 mm x 160 mm steel rod or hardwood dowel", "offcut / dowel", "hardware store", "-", 1, "buy", "n/a", "", "Runs in 608ZZ in F09/F02 with F10 hubs.", "8 mm (R3 specified 5 mm with 608 bearings - incompatible)"],
    ["A19", "A", "M1/M3", 1, "Contact consumables", "felt pads, 1 mm silicone or rubber sheet, PTFE tape, rubber band / light spring", "household + assortments", "hardware store", "Amazon", 4, "buy", "n/a", "", "Drag tensioner, soft jaws, low-friction guide lining.", ""],
    # ---------------------------------------------------------------- A: power + safety
    ["A20", "A", "Power", 1, "12 V DC power adapter", "12 V, 3 A, certified, 5.5 x 2.1 mm barrel", "generic certified 12 V 3 A adapter", "electronics retailer", "Amazon", 8, "buy", "n/a", "", "Replaces the 65 W USB-C PD supply + PD trigger + 20-12 V buck of R3.1.", "budget power path"],
    ["A21", "A", "Power", 1, "DC barrel jack", "5.5 x 2.1 mm panel or pigtail", "generic", "assortment", "-", 0.5, "buy", "n/a", "", "Into the C03 electronics box.", "budget power path"],
    ["A23", "A", "Power", 1, "Buck converter 12 V -> 5 V", "3 A, adjustable (LM2596 class)", "generic LM2596 module", "AliExpress / Amazon", "Pololu D36V28F5", 1.5, "buy", "n/a", "", "Servo/aux rail after the E-stop. Set to 5.0 V with a meter BEFORE connecting servos. Never back-feed the Uno 5 V pin.", ""],
    ["A24", "A", "Safety", 1, "Latching mushroom E-stop", "22 mm, 1 NC contact rated for the DC load (>= 12 V DC, 3 A)", "generic 22 mm E-stop with NC block", "AliExpress / Amazon", "AutomationDirect", 5, "buy", "n/a", "", "Physically breaks the 12 V actuator rail. The Uno senses the switched rail through a divider (no auxiliary contact needed). Check the DC rating.", "rail sensing replaces the auxiliary contact"],
    ["A25", "A", "Safety", 1, "Fuses and holders", "3 A main + 2 A motor branch, inline blade (ATO/mini)", "inline blade fuse holders + fuses", "auto parts store", "Amazon", 2, "buy", "n/a", "", "Fuse directly after the barrel jack.", ""],
    ["A26", "A", "Electrical", 1, "Wire + connectors", "20-22 AWG hook-up wire, 5 lever connectors, heat-shrink", "assortments", "AliExpress / Amazon", "hardware store", 5, "buy", "n/a", "", "One lever connector is the star ground.", ""],
    ["A27", "A", "Electrical", 1, "Keyed motor connectors", "4-pin JST-XH pairs (kit)", "JST-XH kit with crimps", "AliExpress / Amazon", "Digi-Key", 3, "buy", "n/a", "", "Never USB-C for motor phases.", ""],
    ["A28", "A", "Electrical", 1, "Small parts", "START pushbutton; 10 k + 4.7 k (E-stop sense), 1 k + 2 k (link), 10 k pull-up; LED", "assortment", "assortment", "-", 1, "buy", "n/a", "", "Resistor assortment covers all of these.", ""],
    # ---------------------------------------------------------------- A: vision + M3
    ["A29", "A", "M7", 1, "USB board camera", "38 x 38 mm board, UVC, 1080p, manual-focus M12 lens ~6 mm, M2 holes", "generic 38 x 38 USB camera board", "AliExpress / Amazon", "Arducam / ELP", 15, "buy", "W18 mount", "", ">= 40 px/mm over the coil needs a narrow field: ~6 mm M12 lens at ~50 mm. Must not move between calibration and use.", "replaces RealSense + 2020 mast"],
    ["A30", "A", "M7", 1, "Back-light", "5 V white LED strip, 10-15 cm + 1 mm white printed or paper diffuser", "generic 5 V LED strip (USB or 5 V rail)", "AliExpress / Amazon", "-", 1.5, "buy", "n/a", "", "Under the mandrel on the standoffs; overhead camera sees the coil silhouette.", "added (R3 had only an LED ring)"],
    ["A31", "A", "M3", 3, "Micro servo", "SG90 (clamp, support); MG90S recommended for the cutter", "SG90 / MG90S", "AliExpress / Amazon", "-", 2, "buy", "generic", "", "PCA9685 CH0 clamp, CH1 cutter, CH6 demold support. Servo horns use their own M2 screws.", ""],
    ["A32", "A", "M3", 1, "PCA9685 servo driver", "16-ch, I2C 0x40", "PCA9685 clone board", "AliExpress / Amazon", "Adafruit 815", 2.5, "buy", "vendor", "", "Separate 5 V servo rail on V+.", ""],
    ["A33", "A", "M3", 1, "Flush cutter (spring return)", "small electronics flush cutter, guardable", "generic 5 in flush cutter", "AliExpress / hardware store", "-", 3, "buy", "measure", "", "Do not print a blade. Mount in X03 with X04 guard.", ""],
    ["A34", "A", "Sensors", 1, "9DoF IMU (vibration supervisor)", "ICM-20948, I2C 0x69", "SparkFun SEN-15335", "SparkFun", "-", 17, "optional", "vendor", "https://www.sparkfun.com/sparkfun-9dof-imu-breakout-icm-20948-qwiic.html", "Machine-health only; not needed to wind. Check 5 V-safe I2C.", "optional for the budget build"],
    ["A35", "A", "UI", 1, "2.2 in ILI9341 SPI display", "3.3 V logic", "generic module", "AliExpress", "Adafruit", 6, "optional", "C05 bezel", "", "Driven by the optional ESP32-C3.", "optional for the budget build"],
    ["A36", "A", "Frame", 1, "Plywood base", "18 mm, about 400 x 520 mm; offcut gives the 30 x 18 x 175 mm camera mast", "birch or construction plywood", "lumber yard", "hardware store", 10, "buy", "drilling template", "", "Drill from hardware/drawings/core_cell_drilling_template.svg.", "core cell is 380 x 507 mm"],
    ["A37", "A", "Fasteners", 1, "M2 fastener kit (the only fasteners)", "M2 x 4-20 mm screws, M2 nuts, M2 washers, M2 thread-forming (self-tapping) 2 x 8-12, M2.2 wood screws x 13-16 mm", "M2 assortment box + wood-screw pack", "AliExpress / Amazon", "McMaster-Carr", 7, "buy", "n/a", "", "One kit covers the whole machine.", "M2-only standard (R3.1 used M2-M5)"],
    ["A38", "A", "Printing", 1, "PETG filament", "1.75 mm, 1 kg", "any brand", "any", "-", 15, "buy", "n/a", "", "Core parts use about 0.6-0.7 kg at 3-4 walls / 25-40 % infill. PLA for fit tests only.", ""],
    # ---------------------------------------------------------------- B: complete bench
    ["B01", "B", "M4", 2, "Micro servo", "SG90", "SG90", "AliExpress / Amazon", "-", 1.5, "buy", "generic", "", "Tail sweep (CH2) + tail clamp (CH3).", ""],
    ["B02", "B", "M5", 1, "120 mm 5 V USB fan", "low noise", "generic", "AliExpress / Amazon", "-", 5, "buy", "n/a", "", "Mounted to Q02 with M2 screws + washers. Room-temperature airflow only; no heater.", ""],
    ["B03", "B", "M5", 1, "PTFE baking mesh", "low adhesion", "PTFE baking mesh sheet", "kitchen supplier", "Amazon", 4, "buy", "n/a", "", "Validate that wet wood does not stick.", ""],
    ["B04", "B", "M5", 1, "Temperature/RH sensor", "I2C, +-3 %RH", "AHT20 or SHT31 breakout", "AliExpress", "Adafruit", 1.5, "buy", "vendor", "", "Logged with every drying tray.", "added"],
    ["B05", "B", "M6", 2, "28BYJ-48 + ULN2003 kit", "5 V geared stepper", "generic kit", "AliExpress / Amazon", "-", 2, "buy", "generic", "", "Seed indexing + syringe. Not for winding.", ""],
    ["B06", "B", "M6", 1, "MCP23017 I/O expander", "I2C 0x20, 16 GPIO", "MCP23017 breakout", "AliExpress", "Adafruit", 1.5, "buy", "vendor", "", "Drives both ULN2003 boards.", ""],
    ["B07", "B", "M6", 4, "10 mL Luer-lock syringe", "20-21 mm barrel (measure)", "generic + blunt needles", "lab supplier", "Amazon", 0.5, "buy", "S05 mount", "", "", ""],
    ["B08", "B", "M6", 1, "Moulding silicone", "platinum-cure, small kit", "Mold Star class or generic platinum silicone", "art supplier", "Smooth-On distributor", 20, "buy", "S07/S08 masters", "", "Working tip-mould inserts cast from the printed masters.", ""],
    ["B09", "B", "M6", 1, "M5 threaded rod + 2 nuts", "100 mm", "generic", "hardware store", "-", 1, "buy", "n/a", "", "Syringe plunger DRIVE screw (motion part, not a fastener).", ""],
    ["B10", "B", "M9", 1, "XY transfer gantry", "donor 3D-printer XY (second-hand) incl. 2 x NEMA17 + belts", "Ender-style donor", "second-hand", "-", 40, "buy", "R01-R08", "", "Keeps its own hardware; R parts attach with M2. Start with manual transfer.", ""],
    ["B11", "B", "M9", 2, "Micro servo", "SG90", "SG90", "AliExpress / Amazon", "-", 1.5, "buy", "generic", "", "Gripper (CH4) + Z lift (CH5).", ""],
    ["B12", "B", "Frame", 1, "Bench base", "18 mm plywood 800 x 350 mm", "plywood", "lumber yard", "hardware store", 12, "buy", "C01 template", "", "For stations beyond the core cell.", ""],
    # ---------------------------------------------------------------- C: optional deployment (budget)
    # Payload kit first: this is all that is needed if an ArduPilot aircraft is already available.
    ["C01", "C", "M10 payload", 1, "Payload controller", "RP2040 board (Raspberry Pi Pico or RP2040-Zero)", "Raspberry Pi Pico / RP2040-Zero", "authorised reseller", "AliExpress", 4, "buy", "vendor", "", "Gate state machine; logs INTENT to flash before a door opens; fails closed.", ""],
    ["C02", "C", "M10 payload", 4, "Gate servo", "SG90", "SG90", "AliExpress / Amazon", "-", 1.5, "buy", "D03 mounts", "", "One per cassette cell; mounts with the servo's own M2 screws.", ""],
    ["C03", "C", "M10 payload", 4, "Cell occupancy sensor", "TCRT5000 reflective IR module", "TCRT5000 module", "AliExpress / Amazon", "-", 0.4, "buy", "n/a", "", "Confirms each release (cell empty after the door opens).", "added: release confirmation"],
    ["C04", "C", "M10 payload", 1, "Payload wiring", "servo extension leads, JST-GH/XH to the FC, heat-shrink", "assortment", "AliExpress", "-", 3, "buy", "n/a", "", "Servos powered from a separate 5 V BEC, not from the Pico.", ""],
    ["C05", "C", "M10 payload", 1, "5 V BEC for servos", "3 A", "generic UBEC", "hobby retailer", "AliExpress", 3, "buy", "n/a", "", "", ""],
    # Aircraft (skip if one is owned or borrowed). Cheapest ArduPilot-capable quad that can lift the cassette.
    ["C06", "C", "M10 aircraft", 1, "Flight controller + 4-in-1 ESC stack", "F405 FC supported by ArduPilot + 30-40 A 4-in-1 ESC", "ArduPilot-supported F405 stack (check the ArduPilot firmware list)", "hobby retailer", "AliExpress", 55, "buy", "vendor", "", "Flight control stays on the autopilot. Verify the exact board is supported by ArduPilot before buying.", "replaces Pixhawk-class FC + 4 ESCs"],
    ["C07", "C", "M10 aircraft", 1, "450-class quad frame", "F450-type, purchased", "F450 clone", "hobby retailer", "AliExpress", 15, "buy", "vendor", "", "Never print arms or motor mounts.", ""],
    ["C08", "C", "M10 aircraft", 4, "Brushless motor", "2212 920-1000 KV", "A2212 class", "hobby retailer", "AliExpress", 7, "buy", "vendor", "", "Motor/prop/battery validated as a set.", ""],
    ["C09", "C", "M10 aircraft", 2, "Propeller pairs", "1045", "generic", "hobby retailer", "-", 2.5, "buy", "vendor", "", "Balance; spares.", ""],
    ["C10", "C", "M10 aircraft", 1, "GNSS + compass", "M10-class GPS with compass", "generic M10 GPS module", "hobby retailer", "AliExpress", 15, "buy", "vendor", "", "Geofence and sector discipline.", ""],
    ["C11", "C", "M10 aircraft", 1, "3S LiPo", "2200 mAh", "generic", "hobby retailer", "-", 18, "buy", "n/a", "", "LiPo safety: docs/safety.md.", "smaller than R3.1's 4S 5000 mAh"],
    ["C12", "C", "M10 aircraft", 1, "Balance charger", "2-4S, with certified supply", "basic balance charger", "hobby retailer", "-", 15, "owned", "n/a", "", "Do not improvise charging.", ""],
    ["C13", "C", "M10 aircraft", 1, "RC link", "ELRS receiver + transmitter", "budget ELRS transmitter + receiver", "hobby retailer", "-", 55, "owned", "n/a", "", "ELRS can also carry MAVLink telemetry (no separate telemetry radio).", "telemetry radio removed"],
    ["C14", "C", "M10 option", 1, "Companion computer", "Raspberry Pi Zero 2 W", "Raspberry Pi Zero 2 W", "authorised reseller", "-", 15, "optional", "D05 plate", "", "Only for terrain classification; pre-planned points do not need it.", "optional for the budget build"],
    ["C15", "C", "M10 option", 1, "Downward camera", "Pi camera module (clone)", "OV5647 module", "AliExpress", "-", 6, "optional", "D06 mount", "", "With C14 only.", "optional for the budget build"],
]
