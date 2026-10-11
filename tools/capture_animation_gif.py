#!/usr/bin/env python3
"""Capture the website's winding animation as docs/animations/winding.gif (README "What it does").

    cd website && npm run build && cd .. && python tools/capture_animation_gif.py website/dist docs/animations/winding.gif

Serves the built site, scrubs the animation timeline in headless Chromium (Playwright, software GL)
and writes a looping GIF. The GIF is a CAD-based visualization, not a recording of a machine.
"""
import sys, subprocess, time, io
from PIL import Image
from playwright.sync_api import sync_playwright
root, out = sys.argv[1], sys.argv[2]
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--directory", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
frames = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
        pg.goto("http://localhost:8765/index.html"); pg.wait_for_timeout(800)
        pg.locator("#winding").scroll_into_view_if_needed(); pg.wait_for_timeout(800)
        fig = pg.locator("#anim-process figure.anim")
        fig.locator(".anim-play").click()
        stage = fig.locator(".anim-stage")
        n = 64
        for i in range(n):
            fig.locator(".anim-scrub").fill(str(int(i * 1000 / n)))
            pg.wait_for_timeout(60)
            frames.append(Image.open(io.BytesIO(stage.screenshot())).convert("RGB"))
        b.close()
finally:
    srv.terminate()
w = 720
frames = [f.resize((w, int(f.height * w / f.width)), Image.LANCZOS) for f in frames]

q = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
q[0].save(out, save_all=True, append_images=q[1:], duration=250, loop=0, optimize=True)
print(out, len(q))
