#!/usr/bin/env bash
# Render docs/diagrams/src/*.mmd to SVG and PNG (needs @mermaid-js/mermaid-cli: npm i -g @mermaid-js/mermaid-cli).
set -euo pipefail
cd "$(dirname "$0")/../docs/diagrams"
for f in src/*.mmd; do
  n=$(basename "$f" .mmd)
  mmdc -i "$f" -o "$n.svg" -c src/mermaid.config.json -b white
  mmdc -i "$f" -o "$n.png" -c src/mermaid.config.json -b white -s 2
done
python3 ../../tools/build_wiring.py
python3 ../../tools/build_schematic.py
python3 ../../tools/svg_to_png.py D_arduino_pin_map.svg ../../hardware/electronics/seedforge_core_schematic.svg
