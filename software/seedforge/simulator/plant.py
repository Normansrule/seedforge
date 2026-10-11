"""Virtual plant (Python twin of tests/firmware/plant.h) and scenario runner.

The plant simulates the Timer1 step interrupt, a lead-screw carriage with
normally-closed home/end switches, the E-stop loop, a load cell, and a host
vision process that sends HEARTBEAT and, optionally, VISION_OK.

This is a logic/timing simulation, NOT a physics simulation: veneer
mechanics, tension dynamics and coil quality are not modelled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .core import STEP_LIN, STEP_ROT, Controller, Hal, Inputs

LIN_USTEPS_PER_MM = 400


@dataclass
class Plant:
    estop_ok: bool = True
    home_stuck: bool = False
    home_dead: bool = False
    end_forced: bool = False
    guard_ok: bool = True
    tension_valid: bool = False
    tension_mN: int = 0
    hb_period_ms: int = 0
    auto_vision_ok: bool = False
    drift_per_cycle: int = 0
    phys_steps: int = 12000            # carriage starts 30 mm from the home trip point
    end_steps: int = LIN_USTEPS_PER_MM * 104
    now_ms: int = 0
    phys_rot: int = 0
    start_press: bool = False
    trace: list = field(default_factory=list)   # (ms, line)
    record: list = field(default_factory=list)  # periodic samples for logs/plots

    def __post_init__(self):
        self.hal = Hal(on_emit=lambda line: self.trace.append((self.now_ms, line)))
        self.ctrl = Controller(self.hal)
        self._isr_us = 0.0
        self._t_hb = 0

    def begin(self):
        self.ctrl.begin(self.now_ms)
        self.step_ms(1)

    def home_active(self):
        return self.home_stuck or (not self.home_dead and self.phys_steps <= 0)

    def end_active(self):
        return self.end_forced or self.phys_steps >= self.end_steps

    def send(self, line: str):
        self.ctrl.handle_line(line, self.now_ms)

    def step_ms(self, n: int = 1):
        c = self.ctrl
        for _ in range(n):
            m = c.motion
            self._isr_us += 1000.0
            while m.running and self._isr_us >= m.interval_us:
                self._isr_us -= m.interval_us
                bits = m.tick()
                if not self.hal.enabled:
                    continue
                lin_pos_dir = self.hal.lin_level == (not (c.recipe.dir_bits & 2))
                if bits & STEP_LIN:
                    self.phys_steps += 1 if lin_pos_dir else -1
                if bits & STEP_ROT:
                    self.phys_rot += 1
            if not m.running:
                self._isr_us = 0.0
            self.now_ms += 1
            if self.hb_period_ms and self.now_ms - self._t_hb >= self.hb_period_ms:
                self._t_hb = self.now_ms
                self.send("HEARTBEAT")
            i = Inputs(now_ms=self.now_ms, estop_ok=self.estop_ok, home_active=self.home_active(),
                       end_active=self.end_active(), guard_ok=self.guard_ok, tension_valid=self.tension_valid,
                       tension_new=self.tension_valid and self.now_ms % 12 == 0, tension_mN=self.tension_mN,
                       start_pressed=self.start_press)
            self.start_press = False
            before = c.state
            c.step(i)
            if before == "WIND" and c.state == "VERIFY" and self.auto_vision_ok:
                self.send("VISION_OK")
            if before != "COMPLETE" and c.state == "COMPLETE":
                self.phys_steps -= self.drift_per_cycle
            if self.now_ms % 50 == 0:
                self.record.append((self.now_ms, c.state, m.rot_done, m.lin_done, self.phys_steps / LIN_USTEPS_PER_MM,
                                    self.phys_rot / 3200.0, self.tension_mN if self.tension_valid else None,
                                    int(self.estop_ok), int(self.home_active()), int(self.end_active())))

    def run_until(self, state: str, timeout_ms: int) -> bool:
        for _ in range(timeout_ms):
            if self.ctrl.state == state:
                return True
            self.step_ms(1)
        return self.ctrl.state == state


SET_KEYS = {"estop": ("estop_ok", bool), "home_dead": ("home_dead", bool), "home_stuck": ("home_stuck", bool),
            "end_forced": ("end_forced", bool), "guard": ("guard_ok", bool), "tension_valid": ("tension_valid", bool),
            "tension_mN": ("tension_mN", int), "hb_period_ms": ("hb_period_ms", int),
            "auto_vision_ok": ("auto_vision_ok", bool), "drift_per_cycle": ("drift_per_cycle", int),
            "phys_steps": ("phys_steps", int)}


def run_script(text: str, plant: Plant | None = None) -> Plant:
    """Execute a scenario script (same format as tests/firmware/sim_core.cpp)."""
    p = plant or Plant()
    p.begin()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        op, _, rest = line.partition(" ")
        if op == "step":
            p.step_ms(int(rest))
        elif op == "until":
            st, ms = rest.split()
            for _ in range(int(ms)):
                if p.ctrl.state == st:
                    break
                p.step_ms(1)
        elif op == "send":
            p.send(rest.strip())
        elif op == "press":
            p.start_press = True
        elif op == "set":
            k, v = rest.split()
            attr, typ = SET_KEYS[k]
            setattr(p, attr, typ(int(v)))
        else:
            raise ValueError(f"unknown scenario op {op!r}")
    return p


def run_scenario_file(path: str | Path) -> Plant:
    return run_script(Path(path).read_text())
