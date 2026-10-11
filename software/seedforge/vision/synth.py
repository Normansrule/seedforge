"""Synthetic side-view images of a wound coil, with known ground truth.

Used to develop and regression-test the deterministic QA pipeline without
hardware.  Images are clearly SYNTHETIC: they model an ideal flat ribbon on
a straight mandrel, back-lit, viewed orthographically from the side.  They do
not model real wood texture, delamination, splinters or wet sheen.  A labelled
set of REAL images is still required for Phase 6 validation
(docs/validation.md).
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class CoilSpec:
    mandrel_d: float = 0.8
    strip_w: float = 2.5
    strip_t: float = 0.5
    pitch: float = 5.0
    turns: float = 7.0
    px_per_mm: float = 40.0
    # defects
    pitch_jump_at_turn: float | None = None   # a local pitch error starting at this turn
    pitch_jump_factor: float = 1.0            # >1 opens a gap, <1 makes an overlap
    pitch_jump_turns: float = 1.0
    bend_mm: float = 0.0                      # gross deformation: peak axis sag
    noise: float = 0.02
    blur_px: float = 1.0
    seed: int = 0
    label: str = "good"
    notes: list = field(default_factory=list)


def _axial_position(theta_turns: np.ndarray, s: CoilSpec) -> np.ndarray:
    """Axial position of the helix centre-line as a function of turn number."""
    z = theta_turns * s.pitch
    if s.pitch_jump_at_turn is not None and s.pitch_jump_factor != 1.0:
        a = s.pitch_jump_at_turn
        b = a + s.pitch_jump_turns
        extra = (s.pitch_jump_factor - 1.0) * s.pitch
        z = z + extra * np.clip(theta_turns - a, 0.0, b - a)
    return z


def render(s: CoilSpec) -> np.ndarray:
    """Return an 8-bit grayscale image: bright backlight, dark coil and mandrel."""
    rng = np.random.default_rng(s.seed)
    r_mid = s.mandrel_d / 2 + s.strip_t / 2
    total_len = _axial_position(np.array([s.turns]), s)[0] + s.strip_w * 2
    margin_mm = 4.0
    W = int((total_len + 2 * margin_mm) * s.px_per_mm)
    H = int((2 * r_mid + s.strip_t + 2 * margin_mm + 2 * abs(s.bend_mm)) * s.px_per_mm)
    img = np.ones((H, W), np.float32)
    cy = H / 2.0
    x0 = margin_mm * s.px_per_mm

    # mandrel (only visible through gaps and at the ends)
    rr = s.mandrel_d / 2 * s.px_per_mm
    xs = np.arange(W)
    sag = lambda xmm: s.bend_mm * np.sin(np.pi * np.clip(xmm / max(total_len, 1e-6), 0, 1))  # noqa: E731
    for x in xs:
        yc = cy + sag((x - x0) / s.px_per_mm) * s.px_per_mm
        y0, y1 = int(max(0, yc - rr)), int(min(H, yc + rr + 1))
        img[y0:y1, x] = 0.45

    # ribbon: sample (turn, across-width) points, project to the x-z plane
    n_turn = int(s.turns * 900)
    th = np.linspace(0.0, s.turns, n_turn)
    across = np.linspace(-0.5, 0.5, max(8, int(s.strip_w * s.px_per_mm / 2)))
    T, A = np.meshgrid(th, across, indexing="ij")
    ang = 2 * np.pi * T
    zc = _axial_position(T, s)
    C = 2 * np.pi * r_mid
    # strip width direction is perpendicular to the helix tangent on the cylinder
    phi = math.atan2(C, s.pitch)        # strip angle from the axis
    z = zc + A * s.strip_w * math.sin(phi)
    ang = ang - A * s.strip_w * math.cos(phi) / r_mid
    # Where turns overlap, real strip must ride on the previous turn: lift the
    # radius by up to one strip thickness (first-order approximation of stacking).
    dz_dt = np.gradient(zc[:, 0], T[:, 0]) if zc.shape[0] > 1 else np.full(zc.shape[0], s.pitch)
    axial_w = s.strip_w / math.sin(phi)
    lift = s.strip_t * np.clip((axial_w - dz_dt) / (0.5 * axial_w), 0.0, 1.0)
    lift = np.convolve(lift, np.ones(301) / 301, mode="same")[:, None] * np.ones_like(A)
    for dr in (-s.strip_t / 2, 0.0, s.strip_t / 2):
        r = r_mid + dr + lift
        yv = r * np.cos(ang)
        depth = np.sin(ang)               # >0 faces the camera
        px = (x0 + z * s.px_per_mm).astype(int)
        py = (cy + (yv + sag(z)) * s.px_per_mm).astype(int)
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        shade = np.where(depth > 0, 0.18 + 0.12 * depth, 0.26)
        img[py[ok], px[ok]] = np.minimum(img[py[ok], px[ok]], shade[ok])

    # close sampling holes, blur, noise
    import cv2
    dark = (img < 0.6).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    img = np.where(dark > 0, np.minimum(img, 0.3), img)
    if s.blur_px > 0:
        img = cv2.GaussianBlur(img, (0, 0), s.blur_px)
    img = img * (0.92 + 0.08 * np.linspace(0, 1, W)[None, :])   # mild illumination gradient
    img = img + rng.normal(0, s.noise, img.shape)
    return np.clip(img * 255, 0, 255).astype(np.uint8)


def truth(s: CoilSpec) -> dict:
    """Ground-truth geometry for the spec (first-order helix model)."""
    from ..geometry import axial_gap
    t = asdict(s)
    nominal_gap = axial_gap(s.mandrel_d, s.strip_t, s.strip_w, s.pitch)
    local = s.pitch * s.pitch_jump_factor if s.pitch_jump_at_turn is not None else s.pitch
    t["truth"] = {
        "nominal_axial_gap_mm": nominal_gap,
        "worst_axial_gap_mm": min(nominal_gap, axial_gap(s.mandrel_d, s.strip_t, s.strip_w, local))
        if local < s.pitch else max(nominal_gap, axial_gap(s.mandrel_d, s.strip_t, s.strip_w, local)),
        "turns": s.turns,
        "body_length_mm": float(_axial_position(np.array([s.turns]), s)[0] + s.strip_w / math.sin(math.atan2(2 * math.pi * (s.mandrel_d / 2 + s.strip_t / 2), s.pitch))),
    }
    return t


def standard_set(px_per_mm: float = 40.0) -> list[CoilSpec]:
    """A small labelled synthetic set around the paper-reference geometry."""
    base = dict(mandrel_d=0.8, strip_w=2.5, strip_t=0.5, pitch=5.0, turns=7.0, px_per_mm=px_per_mm)
    specs = []
    for i in range(6):
        specs.append(CoilSpec(**base, seed=i, noise=0.015 + 0.005 * i, label="good"))
    for i, f in enumerate((1.6, 1.8, 2.0)):
        specs.append(CoilSpec(**base, seed=10 + i, pitch_jump_at_turn=3.0, pitch_jump_factor=f, label="gap",
                              notes=[f"local pitch x{f} over one turn"]))
    for i, f in enumerate((0.35, 0.3, 0.25)):
        specs.append(CoilSpec(**base, seed=20 + i, pitch_jump_at_turn=2.5, pitch_jump_factor=f, pitch_jump_turns=1.5,
                              label="overlap", notes=[f"local pitch x{f} over 1.5 turns"]))
    for i, n in enumerate((5.0, 5.5)):
        b = dict(base, turns=n)
        specs.append(CoilSpec(**b, seed=30 + i, label="length", notes=[f"{n} turns instead of 7"]))
    for i, bend in enumerate((0.9, 1.2)):
        specs.append(CoilSpec(**base, seed=40 + i, bend_mm=bend, label="deformed", notes=[f"axis sag {bend} mm"]))
    return specs


def write_set(out_dir: str | Path, specs: list[CoilSpec] | None = None) -> list[Path]:
    import cv2
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for k, s in enumerate(specs or standard_set()):
        stem = f"synthetic_{k:02d}_{s.label}"
        cv2.imwrite(str(out / f"{stem}.png"), render(s))
        (out / f"{stem}.json").write_text(json.dumps(truth(s), indent=2))
        paths.append(out / f"{stem}.png")
    return paths
