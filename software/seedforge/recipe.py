"""Winding recipes (JSON) and their validation.

A recipe is a set of ENGINEERING ASSUMPTIONS until the calibration worksheet
(validation/CALIBRATION_WORKSHEET.csv) records measured values for it.  The
`provenance` field must say which.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path

from . import geometry as g
from .protocol import cmd

# Collision-free carriage windows from hardware/cad/source/core_cell_layout.json,
# converted to firmware position (mm from the home trip point at carriage x = 45 mm).
HOME_TRIP_X = 45.0
SOFT_LIMIT_MM = 100.0
MANDREL_FREE_SPAN_X = (24.0, 93.0)   # chuck jaws + clearance .. W05 guide tube - clearance


@dataclass
class Recipe:
    name: str
    provenance: str = "ENGINEERING ASSUMPTION - not yet measured"
    material_lot: str = ""
    strip_width_mm: float = 2.5
    strip_thickness_mm: float = 0.5
    mandrel_diameter_mm: float = 0.8
    pitch_mm: float = 5.0
    guide_angle_deg: float | None = None     # None -> derived from pitch
    active_turns: int = 7
    sacrificial_turns: int = 1
    rate_rpm: float = 30.0
    accel_rpm_s: float = 30.0
    start_mm: float = 5.0
    tension_setpoint_N: float | None = None
    tension_min_N: float | None = None
    tension_max_N: float | None = None
    require_tension: bool = False
    require_vision: bool = True
    m3_enabled: bool = False
    demold_mm: float = 20.0
    heartbeat_ms: int = 3000
    vision: dict = field(default_factory=lambda: {"px_per_mm": 40.0, "max_gap_mm": 1.6, "max_overlap_mm": 0.4,
                                                  "pitch_tol_frac": 0.15, "turns_tol": 0.5, "max_axis_sag_mm": 0.5})
    notes: str = ""

    @property
    def derived_guide_angle(self) -> float:
        return g.guide_angle_from_pitch(self.mandrel_diameter_mm, self.strip_thickness_mm, self.pitch_mm)

    def to_commands(self) -> list[str]:
        out = [cmd("SET_PITCH", self.pitch_mm), cmd("SET_TURNS", self.active_turns),
               cmd("SET_SACRIFICIAL", self.sacrificial_turns), cmd("SET_RATE", self.rate_rpm),
               cmd("SET_ACCEL", self.accel_rpm_s), cmd("SET_START", self.start_mm),
               cmd("SET_REQUIRE_TENSION", int(self.require_tension)), cmd("SET_REQUIRE_VISION", int(self.require_vision)),
               cmd("SET_M3", int(self.m3_enabled)), cmd("SET_DEMOLD", self.demold_mm),
               cmd("SET_HEARTBEAT_MS", self.heartbeat_ms)]
        for key, val in (("SET_TENSION", self.tension_setpoint_N), ("SET_TENSION_MIN", self.tension_min_N),
                         ("SET_TENSION_MAX", self.tension_max_N)):
            if val is not None:
                out.append(cmd(key, val))
        return out

    def validate(self) -> tuple[list[str], list[str]]:
        """Return (errors, warnings).  Errors block a run; warnings must be read."""
        errors, warnings = [], []
        d, t, w, p = self.mandrel_diameter_mm, self.strip_thickness_mm, self.strip_width_mm, self.pitch_mm
        turns = self.active_turns + self.sacrificial_turns
        if not 0.2 <= p <= 30:
            errors.append("pitch must be 0.2-30 mm/rev (firmware range)")
        if self.tension_max_N is None and self.require_tension:
            errors.append("require_tension needs tension_max_N from the measured damage/break test")
        if self.tension_max_N is not None and self.tension_min_N is not None and self.tension_min_N >= self.tension_max_N:
            errors.append("tension_min_N must be below tension_max_N")
        end = self.start_mm + p * turns
        if end > SOFT_LIMIT_MM:
            errors.append(f"wind ends at {end:.1f} mm, beyond the {SOFT_LIMIT_MM} mm soft limit")
        if self.m3_enabled and not 0 <= end + self.demold_mm <= SOFT_LIMIT_MM:
            errors.append("demold retraction leaves the soft travel range")
        # contact point must stay on the free mandrel span
        x_start, x_end = HOME_TRIP_X + self.start_mm, HOME_TRIP_X + end
        lo, hi = MANDREL_FREE_SPAN_X
        if x_start < lo or x_end > hi:
            errors.append(f"contact point travels x={x_start:.0f}..{x_end:.0f} mm; the free mandrel span is x={lo:.0f}..{hi:.0f} mm")
        ga = self.guide_angle_deg if self.guide_angle_deg is not None else self.derived_guide_angle
        if abs(ga) > 60:
            errors.append(f"guide angle {ga:.1f} deg is outside the W12 range (+/-60 deg)")
        windows = core_cell_windows()
        if windows:
            key = min(windows, key=lambda a: abs(float(a) - ga) if windows[a] else 1e9)
            win = windows.get(key)
            if win:
                wx0, wx1 = win
                if x_start < wx0 or x_end > wx1:
                    warnings.append(f"carriage x {x_start:.0f}..{x_end:.0f} mm vs CAD collision-free window "
                                    f"{wx0}..{wx1} mm at guide angle {key} deg: check clearance by hand jogging first")
        gap = g.normal_gap(d, t, w, p)
        if gap < -0.05 * w:
            warnings.append(f"first-order model predicts OVERLAP of {-gap:.2f} mm between turns "
                            f"(butt-joint pitch would be {g.butt_joint_pitch(d, t, w) or float('nan'):.3f} mm)")
        elif gap > 0.05 * w:
            warnings.append(f"first-order model predicts a gap of {gap:.2f} mm between turns")
        if w >= g.centreline_circumference(d, t):
            warnings.append("strip is wider than the centre-line circumference; it cannot lie flat on this mandrel")
        hz = g.master_rate_hz(self.rate_rpm, p)
        if hz > 8000:
            warnings.append(f"master step rate {hz:.0f} Hz exceeds the 8 kHz firmware ceiling and will be clamped")
        if "not yet measured" in self.provenance.lower() or "assumption" in self.provenance.lower():
            warnings.append("recipe values are unmeasured engineering assumptions")
        return errors, warnings

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"


def load(path: str | Path) -> Recipe:
    data = json.loads(Path(path).read_text())
    return Recipe(**data)


def builtin(name: str) -> Recipe:
    ref = resources.files("seedforge") / "recipes" / f"{name}.json"
    return Recipe(**json.loads(ref.read_text()))


def core_cell_windows() -> dict:
    """CAD-derived collision-free carriage windows (carriage x, mm) per guide angle."""
    try:
        ref = resources.files("seedforge") / "data" / "core_cell_limits.json"
        return json.loads(ref.read_text()).get("collision_free_carriage_window_mm", {})
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError):
        return {}
