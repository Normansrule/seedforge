"""Deterministic coil inspection (no machine learning).

Pipeline (docs/computer-vision.md):
  image -> optional undistortion -> back-lit segmentation (Otsu) -> largest
  body -> principal axis (PCA) and rotation to horizontal -> silhouette
  envelope and centre-line -> axial periodicity (FFT + peak picking) ->
  see-through gap measurement -> overlap estimate -> decision.

Assumptions (must hold on the real station, see the M7 module doc):
  * fixed camera, fixed focus, fixed back-light, view perpendicular to the
    mandrel axis (R3.1: overhead camera, back-light panel under the mandrel);
  * calibrated scale (px_per_mm) from a reference target in the same plane;
  * one body in view.

What a silhouette can and cannot see:
  * gaps between turns are seen directly as background through the coil;
  * overlap is NOT directly visible in a silhouette; it is ESTIMATED from the
    measured pitch and the recipe strip width, and flagged as an estimate.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np


@dataclass
class Thresholds:
    px_per_mm: float = 40.0
    strip_w_mm: float = 2.5
    strip_t_mm: float = 0.5
    mandrel_d_mm: float = 0.8
    expected_pitch_mm: float = 5.0
    expected_turns: float = 7.0
    pitch_tol_frac: float = 0.15          # allowed |measured/expected - 1|
    turns_tol: float = 0.5
    max_gap_mm: float = 1.6               # largest see-through gap allowed (recipe-specific)
    max_overlap_mm: float = 0.4           # estimated
    max_axis_sag_mm: float = 0.5          # gross deformation
    min_body_area_px: int = 2000


@dataclass
class Result:
    ok: bool
    event: str                             # VISION_OK, FAULT_GAP, FAULT_OVERLAP, FAULT_LENGTH, FAULT_CAMERA
    reasons: list[str] = field(default_factory=list)
    length_mm: float | None = None
    pitch_mm: float | None = None
    turns: float | None = None
    max_gap_mm: float | None = None
    overlap_est_mm: float | None = None
    axis_sag_mm: float | None = None
    debug: dict = field(default_factory=dict, repr=False)

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("debug", None)
        return d


def segment(gray: np.ndarray) -> np.ndarray:
    """Dark object on a bright back-light -> binary mask (uint8 0/1)."""
    g = cv2.GaussianBlur(gray, (5, 5), 0)
    _, m = cv2.threshold(g, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m


def largest_component(mask: np.ndarray) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return np.zeros_like(mask)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == k).astype(np.uint8)


def align_horizontal(gray: np.ndarray, mask: np.ndarray):
    """Rotate so the body's principal axis is horizontal."""
    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xs, ys]).astype(np.float64)
    mean = pts.mean(0)
    cov = np.cov((pts - mean).T)
    evals, evecs = np.linalg.eigh(cov)
    v = evecs[:, np.argmax(evals)]
    angle = math.degrees(math.atan2(v[1], v[0]))
    M = cv2.getRotationMatrix2D((float(mean[0]), float(mean[1])), angle, 1.0)
    h, w = mask.shape
    g2 = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)
    m2 = cv2.warpAffine(mask, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    return g2, m2, angle


def dominant_period(profile: np.ndarray, min_p: float, max_p: float) -> float | None:
    """Dominant spatial period (px) of a 1-D profile via a zero-padded FFT,
    refined by parabolic interpolation."""
    x = profile - profile.mean()
    if np.allclose(x, 0):
        return None
    x = x * np.hanning(len(x))
    n = 1 << int(math.ceil(math.log2(len(x) * 8)))
    spec = np.abs(np.fft.rfft(x, n))
    freqs = np.fft.rfftfreq(n)
    band = (freqs >= 1.0 / max_p) & (freqs <= 1.0 / min_p)
    if not band.any():
        return None
    idx = np.where(band)[0]
    k = idx[np.argmax(spec[idx])]
    if 0 < k < len(spec) - 1:
        a, b, c = spec[k - 1], spec[k], spec[k + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0.0
    else:
        off = 0.0
    f = (k + off) * (freqs[1] - freqs[0])
    return 1.0 / f if f > 0 else None


def inspect(image: np.ndarray, th: Thresholds) -> Result:
    if image is None or image.size == 0:
        return Result(False, "FAULT_CAMERA", ["no image"])
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.std() < 3:
        return Result(False, "FAULT_CAMERA", ["image has no contrast (lighting/exposure?)"])
    mask = largest_component(segment(gray))
    if mask.sum() < th.min_body_area_px:
        return Result(False, "FAULT_CAMERA", ["no body found"])

    g, m, angle = align_horizontal(gray, mask)
    cols = np.where(m.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    top = np.array([np.argmax(m[:, x]) if m[:, x].any() else -1 for x in range(x0, x1 + 1)], float)
    bot = np.array([len(m[:, x]) - 1 - np.argmax(m[::-1, x]) if m[:, x].any() else -1 for x in range(x0, x1 + 1)], float)
    valid = top >= 0
    centre = np.where(valid, (top + bot) / 2.0, np.nan)
    height = np.where(valid, bot - top, 0.0)
    ppm = th.px_per_mm

    # The coil is where the silhouette is clearly taller than the bare mandrel.
    coil_h_px = (th.mandrel_d_mm + 1.2 * th.strip_t_mm) * ppm
    is_coil = height > coil_h_px
    if is_coil.sum() < 10:
        return Result(False, "FAULT_LENGTH", ["no coil found on the body"], debug={"mask": m})
    cidx = np.where(is_coil)[0]
    c0, c1 = int(cidx.min()), int(cidx.max())
    length_mm = (c1 - c0 + 1) / ppm

    # Centre-line: quadratic fit tolerates a bent body; sag = deviation from a straight line.
    xs = np.arange(c0, c1 + 1)
    cy = centre[c0:c1 + 1]
    good = ~np.isnan(cy)
    quad = np.polyfit(xs[good], cy[good], 2)
    axis_y = np.polyval(quad, xs)
    chord = axis_y[0] + (axis_y[-1] - axis_y[0]) * (xs - xs[0]) / max(1, xs[-1] - xs[0])
    sag_mm = float(np.max(np.abs(axis_y - chord)) / ppm)

    # Edge radii.  In a back-lit silhouette the front and back halves of each
    # turn cross, so gaps rarely show as see-through holes; instead every turn
    # leaves a notch in the top edge and (half a pitch later) in the bottom
    # edge.  Notch spacing along ONE edge is the local pitch.
    r_top = axis_y - top[c0:c1 + 1]
    r_bot = bot[c0:c1 + 1] - axis_y
    exp_p = th.expected_pitch_mm * ppm
    r_out = (th.mandrel_d_mm / 2 + th.strip_t_mm) * ppm
    r_in = th.mandrel_d_mm / 2 * ppm
    sig = max(1.0, 0.04 * exp_p)

    def notches(r):
        sm = cv2.GaussianBlur(r.reshape(1, -1).astype(np.float64), (0, 0), sig).ravel()
        prom_min = 0.12 * (r_out - r_in)
        out = []
        w = int(max(3, 0.25 * exp_p))
        for i in range(w, len(sm) - w):
            seg = sm[i - w:i + w + 1]
            if sm[i] == seg.min() and seg.max() - sm[i] > prom_min:
                if not out or i - out[-1] > w:
                    out.append(i)
        return out, sm

    n_top, sm_top = notches(r_top)
    n_bot, sm_bot = notches(r_bot)
    local = [d / ppm for n in (n_top, n_bot) for d in np.diff(n)]
    profile = sm_top
    period_px = dominant_period(sm_top - sm_top.mean(), 0.4 * exp_p, 2.5 * exp_p)
    if local:
        pitch_mm = float(np.median(local))
    else:
        pitch_mm = period_px / ppm if period_px else None
    peaks = n_top

    # Direct evidence: columns where light passes the coil envelope away from
    # the mandrel shadow (large open gaps do show through).
    mand_half = r_in
    env_top = int(np.min(top[c0:c1 + 1][top[c0:c1 + 1] >= 0]))
    env_bot = int(np.max(bot[c0:c1 + 1]))
    open_cols = np.zeros(c1 - c0 + 1, bool)
    for j, x in enumerate(range(x0 + c0, x0 + c1 + 1)):
        yc = axis_y[j]
        col = m[:, x]
        upper = col[int(max(0, yc - r_out + 1)):int(yc - mand_half - 1)]
        lower = col[int(yc + mand_half + 2):int(yc + r_out)]
        if len(upper) and len(lower):
            open_cols[j] = (upper == 0).mean() > 0.6 and (lower == 0).mean() > 0.6
    runs, run = [], 0
    for v in open_cols:
        if v:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    see_through_mm = (max(runs) / ppm) if runs else 0.0

    # Gap / overlap.  Each span between successive notches on one edge is a
    # local pitch.  A long span is either a gap (thin shell, no bulge) or an
    # overlap that hid the notch (double layer: the edge bulges by ~1 strip
    # thickness).  The bulge separates the two.  First-order helix model with
    # the recipe strip width; see docs/computer-vision.md for limits.
    phi = math.atan2(math.pi * (th.mandrel_d_mm + th.strip_t_mm), th.expected_pitch_mm)
    axial_w = th.strip_w_mm / math.sin(phi)
    r_ref = float(np.median(np.r_[sm_top, sm_bot]))
    t_px = th.strip_t_mm * ppm
    gap_spans, ovl_spans, all_spans = [], [], []
    bulge_mm = 0.0
    for n, sm in ((n_top, sm_top), (n_bot, sm_bot)):
        for a_, b_ in zip(n, n[1:]):
            span = (b_ - a_) / ppm
            bulge = (sm[a_:b_ + 1].max() - r_ref) / ppm
            bulge_mm = max(bulge_mm, bulge)
            all_spans.append(span)
            if bulge * ppm > 0.45 * t_px:
                ovl_spans.append(span)
            else:
                gap_spans.append(span)
    p_max = max(gap_spans) if gap_spans else (pitch_mm or th.expected_pitch_mm)
    p_min = min(all_spans) if all_spans else (pitch_mm or th.expected_pitch_mm)
    max_gap_mm = max(see_through_mm, p_max - axial_w, 0.0)
    overlap_est = max(0.0, axial_w - p_min, bulge_mm if ovl_spans else 0.0)
    local_min_pitch = p_min

    # Turn count from body length and the measured (median local) pitch.
    # In silhouette the tapered ends drop out, so visible length ~= turns x pitch
    # (verified on the synthetic set; re-check with real images).
    turns = length_mm / pitch_mm if pitch_mm else None
    reasons = []
    event = "VISION_OK"
    if max_gap_mm > th.max_gap_mm:
        event = "FAULT_GAP"
        reasons.append(f"gap {max_gap_mm:.2f} mm > {th.max_gap_mm:.2f} mm (max local pitch {p_max:.2f} mm, see-through {see_through_mm:.2f} mm)")
    if overlap_est > th.max_overlap_mm and event == "VISION_OK":
        event = "FAULT_OVERLAP"
        reasons.append(f"estimated overlap {overlap_est:.2f} mm > {th.max_overlap_mm:.2f} mm "
                       f"(min local pitch {local_min_pitch:.2f} mm, edge bulge {bulge_mm:.2f} mm)")
    if pitch_mm is None or abs(pitch_mm / th.expected_pitch_mm - 1) > th.pitch_tol_frac:
        if event == "VISION_OK":
            event = "FAULT_LENGTH"
        reasons.append(f"pitch {pitch_mm if pitch_mm is None else round(pitch_mm, 3)} mm vs expected {th.expected_pitch_mm} mm")
    if turns is None or abs(turns - th.expected_turns) > th.turns_tol:
        if event == "VISION_OK":
            event = "FAULT_LENGTH"
        reasons.append(f"turn count {turns if turns is None else round(turns, 2)} vs expected {th.expected_turns}")
    if sag_mm > th.max_axis_sag_mm:
        if event == "VISION_OK":
            event = "FAULT_LENGTH"       # protocol has no separate deformation fault; reported in reasons
        reasons.append(f"gross deformation: axis sag {sag_mm:.2f} mm > {th.max_axis_sag_mm} mm")
    dbg = {"mask": m, "gray": g, "x0": x0, "c0": c0, "c1": c1, "centre": centre, "env": (env_top, env_bot),
           "profile": profile, "peaks": peaks, "peaks_bot": n_bot, "open_cols": open_cols, "angle_deg": angle,
           "local_pitch_mm": local}
    return Result(event == "VISION_OK", event, reasons, length_mm, pitch_mm, turns, max_gap_mm, overlap_est, sag_mm, dbg)


def overlay(image: np.ndarray, res: Result) -> np.ndarray:
    """Annotated BGR image: detected region, centre-line, pitch marks, gaps, verdict."""
    d = res.debug
    g = d.get("gray", image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    out = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    if "mask" in d:
        tint = out.copy()
        tint[d["mask"] > 0] = (0.55 * tint[d["mask"] > 0] + 0.45 * np.array([79, 111, 47])).astype(np.uint8)
        out = tint
    if "c0" in d:
        x0, c0, c1 = d["x0"], d["c0"], d["c1"]
        et, eb = d["env"]
        cv2.rectangle(out, (x0 + c0, et), (x0 + c1, eb), (60, 40, 20), 1)
        cl = d["centre"]
        pts = [(x0 + i, int(cl[i])) for i in range(len(cl)) if not np.isnan(cl[i])]
        for a, b in zip(pts[::4], pts[4::4]):
            cv2.line(out, a, b, (40, 120, 230), 1)
        for p in d["peaks"]:
            cv2.line(out, (x0 + c0 + p, et - 16), (x0 + c0 + p, et - 4), (30, 30, 30), 2)
        for p in d.get("peaks_bot", []):
            cv2.line(out, (x0 + c0 + p, eb + 4), (x0 + c0 + p, eb + 16), (30, 30, 30), 2)
        for i, v in enumerate(d["open_cols"]):
            if v:
                cv2.line(out, (x0 + c0 + i, eb + 20), (x0 + c0 + i, eb + 28), (40, 40, 200), 1)
    colour = (47, 111, 47) if res.ok else (40, 40, 190)
    lines = [f"{res.event}",
             f"length {res.length_mm:.2f} mm" if res.length_mm else "length -",
             f"pitch {res.pitch_mm:.3f} mm" if res.pitch_mm else "pitch -",
             f"turns {res.turns:.2f}" if res.turns else "turns -",
             f"max gap {res.max_gap_mm:.2f} mm   overlap(est) {res.overlap_est_mm:.2f} mm" if res.max_gap_mm is not None else "",
             f"axis sag {res.axis_sag_mm:.2f} mm" if res.axis_sag_mm is not None else ""]
    pad = np.full((22 * len(lines) + 12, out.shape[1], 3), 255, np.uint8)
    for k, t in enumerate(lines):
        cv2.putText(pad, t, (8, 24 + 22 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour if k == 0 else (40, 30, 20), 1, cv2.LINE_AA)
    return np.vstack([out, pad])
