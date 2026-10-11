"""Helical winding geometry, step ratios and mandrel deflection.

First-order models used to choose *starting* recipe values.  Real wet veneer
compresses, swells, slips and changes its effective radius, so every value
derived here is an ENGINEERING ASSUMPTION until measured (docs/calibration.md).

Conventions
-----------
d   mandrel diameter (mm)
t   strip thickness (mm)
w   strip width (mm)
D   = d + t, diameter of the strip centre-line (single layer)
C   = pi * D, centre-line circumference per turn
p   axial pitch per mandrel revolution (mm/rev)
phi strip angle measured from the mandrel AXIS:  tan(phi) = C / p
guide angle (machine W12 scale) = 90 deg - phi, i.e. 0 = strip square to the axis

Axial edge-to-edge gap between neighbouring turns, measured perpendicular
to the strip (positive = gap, negative = overlap):

    gap_n = p * sin(phi) - w = C * cos(phi) - w

A butt joint (no gap, no overlap) therefore needs cos(phi) = w / C, which is
only possible when w <= C.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

FULL_STEPS = 200
MICROSTEPS = 16
LEAD_MM = 8.0
ROT_USTEPS_PER_REV = FULL_STEPS * MICROSTEPS              # 3200
LIN_USTEPS_PER_MM = FULL_STEPS * MICROSTEPS / LEAD_MM     # 400.0

STEEL_E_MPA = 200_000.0


def centreline_circumference(d: float, t: float) -> float:
    return math.pi * (d + t)


def pitch_from_strip_angle(d: float, t: float, phi_deg: float) -> float:
    """Pitch for a strip angle phi measured from the mandrel axis."""
    if not 0 < phi_deg < 90:
        raise ValueError("phi must be between 0 and 90 degrees")
    return centreline_circumference(d, t) / math.tan(math.radians(phi_deg))


def strip_angle_from_pitch(d: float, t: float, p: float) -> float:
    if p <= 0:
        raise ValueError("pitch must be positive")
    return math.degrees(math.atan2(centreline_circumference(d, t), p))


def guide_angle_from_pitch(d: float, t: float, p: float) -> float:
    """Machine guide-scale angle (0 = strip square to the mandrel axis)."""
    return 90.0 - strip_angle_from_pitch(d, t, p)


def normal_gap(d: float, t: float, w: float, p: float) -> float:
    """Edge-to-edge gap between turns, perpendicular to the strip (mm).
    Negative values are overlap."""
    phi = math.radians(strip_angle_from_pitch(d, t, p))
    return p * math.sin(phi) - w


def axial_gap(d: float, t: float, w: float, p: float) -> float:
    """Gap measured along the mandrel axis (what a side camera sees)."""
    phi = math.radians(strip_angle_from_pitch(d, t, p))
    return p - w / math.sin(phi)


def butt_joint_pitch(d: float, t: float, w: float) -> float | None:
    """Pitch giving zero gap and zero overlap, or None if impossible (w > C)."""
    C = centreline_circumference(d, t)
    if w >= C:
        return None
    return w * C / math.sqrt(C * C - w * w)


def body_length(turns: float, p: float, d: float, t: float, w: float) -> float:
    """Approximate axial length of a wound body of `turns` turns."""
    phi = math.radians(strip_angle_from_pitch(d, t, p))
    return turns * p + w / math.sin(phi)


def strip_length(turns: float, p: float, d: float, t: float) -> float:
    """Centre-line strip length consumed by `turns` turns."""
    C = centreline_circumference(d, t)
    return turns * math.hypot(C, p)


# --------------------------------------------------------------------------- machine
def linear_usteps_per_rev(p: float) -> float:
    return LIN_USTEPS_PER_MM * p


def lin_total_steps(p: float, turns: int) -> int:
    """Exactly what the firmware computes: round(pitch_um * 400 * turns / 1000)."""
    pitch_um = int(round(p * 1000))
    return (pitch_um * int(LIN_USTEPS_PER_MM) * turns + 500) // 1000


def realised_pitch(p: float, turns: int) -> float:
    """Pitch actually produced after integer step rounding."""
    return lin_total_steps(p, turns) / LIN_USTEPS_PER_MM / turns


def master_rate_hz(rpm: float, p: float) -> float:
    rot_hz = rpm * ROT_USTEPS_PER_REV / 60.0
    ratio = linear_usteps_per_rev(p) / ROT_USTEPS_PER_REV
    return rot_hz * max(1.0, ratio)


# --------------------------------------------------------------------------- mandrel
def mandrel_second_moment(d: float) -> float:
    return math.pi * d ** 4 / 64.0


def mandrel_deflection(force_n: float, span_mm: float, d: float = 0.8,
                       support: str = "pinned-pinned", e_mpa: float = STEEL_E_MPA) -> float:
    """Maximum lateral deflection (mm) for a point load at mid-span.

    pinned-pinned  F L^3 / (48 E I)     (chuck treated as a pin: conservative)
    fixed-pinned   F L^3 / (107.3 E I)  (stiff chuck, end support W05)
    cantilever     F L^3 / (3 E I)      (no end support, load at the tip)
    """
    k = {"pinned-pinned": 48.0, "fixed-pinned": 107.3, "cantilever": 3.0}[support]
    return force_n * span_mm ** 3 / (k * e_mpa * mandrel_second_moment(d))


def mandrel_bending_stress(force_n: float, span_mm: float, d: float = 0.8, support: str = "pinned-pinned") -> float:
    """Peak bending stress (MPa) for the same load cases."""
    m = {"pinned-pinned": force_n * span_mm / 4.0, "fixed-pinned": 3.0 * force_n * span_mm / 16.0,
         "cantilever": force_n * span_mm}[support]
    return m * (d / 2.0) / mandrel_second_moment(d)


@dataclass
class GeometryReport:
    name: str
    d: float
    t: float
    w: float
    p: float
    turns: int
    C: float
    strip_angle_deg: float
    guide_angle_deg: float
    normal_gap_mm: float
    axial_gap_mm: float
    butt_joint_pitch_mm: float | None
    body_length_mm: float
    strip_length_mm: float
    lin_usteps_per_rev: float
    realised_pitch_mm: float

    def as_dict(self):
        return asdict(self)


def report(name: str, d: float, t: float, w: float, p: float, turns: int) -> GeometryReport:
    C = centreline_circumference(d, t)
    return GeometryReport(
        name=name, d=d, t=t, w=w, p=p, turns=turns, C=C,
        strip_angle_deg=strip_angle_from_pitch(d, t, p),
        guide_angle_deg=guide_angle_from_pitch(d, t, p),
        normal_gap_mm=normal_gap(d, t, w, p),
        axial_gap_mm=axial_gap(d, t, w, p),
        butt_joint_pitch_mm=butt_joint_pitch(d, t, w),
        body_length_mm=body_length(turns, p, d, t, w),
        strip_length_mm=strip_length(turns, p, d, t),
        lin_usteps_per_rev=linear_usteps_per_rev(p),
        realised_pitch_mm=realised_pitch(p, turns),
    )


def reference_cases() -> list[GeometryReport]:
    """The two geometries the project must not conflate, plus derived options."""
    out = [
        # Course/experimental target as stated: 4.0 x 0.5 mm strip, 0.8 mm mandrel, 45 deg.
        report("course target as stated (4.0 mm strip, 45 deg)", 0.8, 0.5, 4.0, pitch_from_strip_angle(0.8, 0.5, 45.0), 7),
        # Paper-inspired reference body: 7 turns over 35 mm, 2.5 x 0.5 mm.
        report("paper reference body (2.5 mm, 7 turns / 35 mm)", 0.8, 0.5, 2.5, 35.0 / 7.0, 7),
    ]
    p_butt_25 = butt_joint_pitch(0.8, 0.5, 2.5)
    out.append(report("2.5 mm strip, butt joint", 0.8, 0.5, 2.5, p_butt_25, 7))
    p_butt_4 = butt_joint_pitch(0.8, 0.5, 4.0)
    if p_butt_4:
        out.append(report("4.0 mm strip, butt joint (nearly axial)", 0.8, 0.5, 4.0, p_butt_4, 7))
    return out


def main(argv=None) -> int:
    """python -m seedforge.geometry [--pitch P | --angle GUIDE_DEG] [--width W --thickness T --mandrel D --turns N]"""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m seedforge.geometry",
                                 description="First-order helix model. No arguments: print the reference table.")
    ap.add_argument("--pitch", type=float, help="axial pitch, mm per mandrel revolution")
    ap.add_argument("--angle", type=float, help="W12 guide-scale angle in degrees (0 = strip square to the mandrel)")
    ap.add_argument("--width", type=float, default=2.5, help="strip width, mm (default 2.5)")
    ap.add_argument("--thickness", type=float, default=0.5, help="strip thickness, mm (default 0.5)")
    ap.add_argument("--mandrel", type=float, default=0.8, help="mandrel diameter, mm (default 0.8)")
    ap.add_argument("--turns", type=int, default=7, help="active turns (default 7)")
    a = ap.parse_args(argv)
    if a.pitch is None and a.angle is None:
        cases = reference_cases()
    else:
        p = a.pitch if a.pitch is not None else pitch_from_strip_angle(a.mandrel, a.thickness, 90.0 - a.angle)
        cases = [report("custom", a.mandrel, a.thickness, a.width, p, a.turns)]
    for r in cases:
        bj = "none (strip wider than circumference)" if r.butt_joint_pitch_mm is None else f"{r.butt_joint_pitch_mm:.3f} mm"
        print(f"{r.name}\n  pitch {r.p:.3f} mm/rev  strip angle {r.strip_angle_deg:.1f} deg from axis  "
              f"guide {r.guide_angle_deg:.1f} deg  normal gap {r.normal_gap_mm:+.3f} mm  "
              f"butt-joint pitch {bj}  body {r.body_length_mm:.1f} mm  linear usteps/rev {r.lin_usteps_per_rev:.1f}")
    if a.pitch is None and a.angle is None:
        for F in (0.1, 0.25, 0.5, 1.0):
            print(f"mandrel 0.8 mm, 90 mm span, {F} N: pinned {mandrel_deflection(F, 90):.2f} mm, "
                  f"fixed-pinned {mandrel_deflection(F, 90, support='fixed-pinned'):.2f} mm, "
                  f"stress {mandrel_bending_stress(F, 90):.0f} MPa")
    print("First-order model only: wet wood compresses, slips and swells. Measure real coils.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
