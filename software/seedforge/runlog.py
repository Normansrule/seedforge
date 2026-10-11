"""CSV run logging for traceability (docs/validation.md, brief section 36).

Two files per session:
  * carriers.csv - one row per manufactured carrier (CARRIER_FIELDS)
  * trace.csv    - time series while a cycle runs (TRACE_FIELDS; same columns as
                   validation/RUN_LOG_TEMPLATE.csv)

CSV first; SQLite can be added later without changing the field names.
"""
from __future__ import annotations

import csv
import datetime as _dt
import uuid
from pathlib import Path

CARRIER_FIELDS = [
    "timestamp", "carrier_id", "run_id", "data_source", "material_lot", "width_mm", "thickness_mm",
    "mandrel_diameter_mm", "guide_angle_deg", "pitch_mm", "active_turns", "sacrificial_turns",
    "tension_target_N", "tension_mean_N", "tension_max_N", "vibration_rms_mg", "winding_rate_rpm",
    "turn_count", "lin_steps", "camera_result", "measured_length_mm", "demold_result", "tail_form_recipe",
    "drying_duration_h", "final_result", "fault", "notes",
]

TRACE_FIELDS = ["timestamp", "run_id", "state", "rot_steps", "lin_steps", "tension_N", "dancer_raw",
                "vibration_rms", "vision_event", "limit_home", "limit_end", "estop_ok", "result", "notes"]


def new_id(prefix: str) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class CsvLog:
    def __init__(self, path: str | Path, fields: list[str]):
        self.path = Path(path)
        self.fields = fields
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists() or self.path.stat().st_size == 0
        self._f = self.path.open("a", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        if new:
            self._w.writeheader()

    def write(self, row: dict) -> None:
        unknown = set(row) - set(self.fields)
        if unknown:
            raise KeyError(f"unknown log fields: {sorted(unknown)}")
        self._w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in self.fields})
        self._f.flush()

    def close(self) -> None:
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def read_rows(path: str | Path) -> list[dict]:
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))
