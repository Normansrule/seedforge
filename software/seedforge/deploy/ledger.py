"""Drop-point ledger for the OPTIONAL downstream deployment concept (M10).

CONCEPT CODE - not flight software and not flight-validated.

Rules it enforces (docs/drone-concept.md):
  * every planting point has a unique ID inside exactly one pre-assigned,
    non-overlapping sector;
  * a drone may only claim points in its own sector;
  * release INTENT is persisted before a gate is commanded;
  * a point whose outcome is uncertain is marked UNCERTAIN and is never
    retried automatically (avoids duplicate planting); a human resolves it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class PointState(str, Enum):
    PLANNED = "PLANNED"
    INTENT = "INTENT"            # persisted before the gate opens
    RELEASED = "RELEASED"        # release confirmed (e.g. cell sensor + gate feedback)
    UNCERTAIN = "UNCERTAIN"      # gate commanded but confirmation missing
    SKIPPED = "SKIPPED"          # rejected site (terrain / permission / safety)


@dataclass
class Point:
    point_id: str
    sector: str
    lat: float
    lon: float
    state: PointState = PointState.PLANNED
    drone: str | None = None
    cell: int | None = None
    history: list = field(default_factory=list)


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.points: dict[str, Point] = {}
        self.sector_owner: dict[str, str] = {}
        if self.path and self.path.exists():
            self._load()

    # persistence: write-then-rename so an interrupted write cannot corrupt the ledger
    def _save(self):
        if not self.path:
            return
        tmp = self.path.with_suffix(".tmp")
        data = {"sector_owner": self.sector_owner,
                "points": [{**asdict(p), "state": p.state.value} for p in self.points.values()]}
        tmp.write_text(json.dumps(data, indent=1))
        tmp.replace(self.path)

    def _load(self):
        data = json.loads(self.path.read_text())
        self.sector_owner = data["sector_owner"]
        for d in data["points"]:
            d["state"] = PointState(d["state"])
            self.points[d["point_id"]] = Point(**d)

    def assign_sector(self, sector: str, drone: str):
        owner = self.sector_owner.get(sector)
        if owner and owner != drone:
            raise LedgerError(f"sector {sector} already assigned to {owner}")
        self.sector_owner[sector] = drone
        self._save()

    def add_point(self, point_id: str, sector: str, lat: float, lon: float):
        if point_id in self.points:
            raise LedgerError(f"duplicate point id {point_id}")
        self.points[point_id] = Point(point_id, sector, lat, lon)
        self._save()

    def _get(self, point_id: str, drone: str) -> Point:
        p = self.points.get(point_id)
        if p is None:
            raise LedgerError(f"unknown point {point_id}")
        if self.sector_owner.get(p.sector) != drone:
            raise LedgerError(f"{drone} does not own sector {p.sector}")
        return p

    def next_point(self, drone: str) -> Point | None:
        for p in self.points.values():
            if p.state == PointState.PLANNED and self.sector_owner.get(p.sector) == drone:
                return p
        return None

    def record_intent(self, point_id: str, drone: str, cell: int):
        p = self._get(point_id, drone)
        if p.state != PointState.PLANNED:
            raise LedgerError(f"point {point_id} is {p.state.value}; refusing a second release")
        p.state, p.drone, p.cell = PointState.INTENT, drone, cell
        p.history.append("INTENT")
        self._save()           # persisted BEFORE the payload controller opens the gate

    def confirm(self, point_id: str, drone: str, released: bool | None):
        """released=True confirmed, False confirmed not released, None = unknown."""
        p = self._get(point_id, drone)
        if p.state != PointState.INTENT:
            raise LedgerError(f"point {point_id} has no open intent")
        if released is True:
            p.state = PointState.RELEASED
        elif released is False:
            p.state = PointState.PLANNED       # gate never opened: safe to try again later
        else:
            p.state = PointState.UNCERTAIN     # never auto-retried
        p.history.append(p.state.value)
        self._save()

    def skip(self, point_id: str, drone: str, reason: str):
        p = self._get(point_id, drone)
        p.state = PointState.SKIPPED
        p.history.append(f"SKIPPED:{reason}")
        self._save()

    def recover_after_restart(self):
        """Any intent without a confirmation after a crash/power loss becomes UNCERTAIN."""
        for p in self.points.values():
            if p.state == PointState.INTENT:
                p.state = PointState.UNCERTAIN
                p.history.append("UNCERTAIN:restart")
        self._save()

    def summary(self) -> dict:
        out: dict[str, int] = {}
        for p in self.points.values():
            out[p.state.value] = out.get(p.state.value, 0) + 1
        return out
