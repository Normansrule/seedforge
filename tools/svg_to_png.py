#!/usr/bin/env python3
"""Rasterise generated SVG figures to PNG with headless Chromium (Playwright).

    python tools/svg_to_png.py docs/diagrams/D_arduino_pin_map.svg [more.svg ...]

Writes NAME.png next to each SVG at 2x scale. Used by tools/build_diagrams.sh.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def size(svg: str) -> tuple[float, float]:
    m = re.search(r'viewBox="\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)"', svg)
    return (float(m.group(1)), float(m.group(2))) if m else (1600.0, 1000.0)


def main(paths: list[str]) -> int:
    with sync_playwright() as p:
        b = p.chromium.launch()
        for s in paths:
            src = Path(s).resolve()
            w, h = size(src.read_text())
            pg = b.new_page(viewport={"width": int(w), "height": int(h)}, device_scale_factor=2)
            pg.set_content(f'<html><body style="margin:0;background:#fff">{src.read_text()}</body></html>')
            pg.locator("svg").first.screenshot(path=str(src.with_suffix(".png")))
            pg.close()
            print(f"png: {src.with_suffix('.png').name}")
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
