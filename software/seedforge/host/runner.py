"""Host-side job runner: recipe -> controller, heartbeat, vision, logging.

Transports
  serial  /dev/ttyACM0, COM5 ...   (Uno USB at 115200, or the ESP32-C3 USB-CDC bridge)
  tcp     host:3333                (ESP32-C3 Wi-Fi bridge, if enabled)
  sim                               in-process simulator (no hardware)

Safety notes
  * The runner sends HEARTBEAT every 500 ms from a dedicated thread; if this
    process stalls or dies, the controller stops itself (HEARTBEAT_TIMEOUT).
  * The runner never sends RESET automatically after a SAFE_STOP.
"""
from __future__ import annotations

import queue
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..protocol import cmd, parse_message
from ..recipe import Recipe
from ..runlog import CARRIER_FIELDS, TRACE_FIELDS, CsvLog, new_id, now_iso


class Transport:
    def write_line(self, line: str) -> None: ...
    def read_line(self, timeout: float) -> str | None: ...
    def close(self) -> None: ...


class SerialTransport(Transport):
    def __init__(self, port: str, baud: int = 115200):
        import serial  # pyserial
        self.s = serial.Serial(port, baud, timeout=0.05)
        self._buf = b""
        self._lock = threading.Lock()
        time.sleep(2.0)            # the Uno resets when the port opens

    def write_line(self, line):
        with self._lock:
            self.s.write((line + "\n").encode())

    def read_line(self, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                return line.decode(errors="replace").strip()
            self._buf += self.s.read(256)
        return None

    def close(self):
        self.s.close()


class TcpTransport(Transport):
    def __init__(self, host: str, port: int = 3333):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(0.05)
        self._buf = b""
        self._lock = threading.Lock()

    def write_line(self, line):
        with self._lock:
            self.sock.sendall((line + "\n").encode())

    def read_line(self, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                return line.decode(errors="replace").strip()
            try:
                chunk = self.sock.recv(256)
                if not chunk:
                    return None
                self._buf += chunk
            except socket.timeout:
                pass
        return None

    def close(self):
        self.sock.close()


class SimTransport(Transport):
    """Runs the simulator in a background thread at (scaled) real time."""

    def __init__(self, speed: float = 20.0, plant_kwargs: dict | None = None):
        from ..simulator.plant import Plant
        self.out: queue.Queue[str] = queue.Queue()
        self.inbox: queue.Queue[str] = queue.Queue()
        self.plant = Plant(**(plant_kwargs or {}))
        self.plant.hal.on_emit = lambda line: (self.plant.trace.append((self.plant.now_ms, line)), self.out.put(line))
        self.speed = speed
        self._stop = threading.Event()
        self.plant.begin()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        t0 = time.monotonic()
        while not self._stop.is_set():
            while not self.inbox.empty():
                self.plant.send(self.inbox.get())
            target_ms = int((time.monotonic() - t0) * 1000 * self.speed)
            n = min(200, target_ms - self.plant.now_ms)
            if n > 0:
                self.plant.step_ms(n)
            else:
                time.sleep(0.001)

    def write_line(self, line):
        self.inbox.put(line)

    def read_line(self, timeout):
        try:
            return self.out.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self._stop.set()


def open_transport(spec: str, speed: float = 20.0) -> Transport:
    if spec == "sim":
        return SimTransport(speed=speed)
    if spec.startswith("tcp:"):
        host, _, port = spec[4:].partition(":")
        return TcpTransport(host, int(port or 3333))
    return SerialTransport(spec)


@dataclass
class CycleResult:
    run_id: str
    carrier_id: str
    final_state: str
    fault: str
    vision: dict | None = None
    lines: list = field(default_factory=list)


class Runner:
    def __init__(self, transport: Transport, recipe: Recipe, log_dir: str | Path | None = None,
                 vision: Callable[[Recipe], dict] | None = None, echo: Callable[[str], None] | None = print,
                 hb_period_s: float = 0.5):
        self.t = transport
        self.recipe = recipe
        self.vision = vision
        self.echo = echo or (lambda s: None)
        self.log_dir = Path(log_dir) if log_dir else None
        self.state = "UNKNOWN"
        self.fault = "NONE"
        self.hb_period_s = hb_period_s
        self._hb_stop = threading.Event()

    # ---------------------------------------------------------------- plumbing
    def _heartbeat(self):
        period = self.hb_period_s / getattr(self.t, "speed", 1.0)   # simulator runs faster than real time
        while not self._hb_stop.wait(period):
            self.t.write_line("HEARTBEAT")

    def send(self, line: str):
        self.echo(f">> {line}")
        self.t.write_line(line)

    def _wait(self, predicate, timeout_s: float, on_line=None):
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            line = self.t.read_line(0.2)
            if not line:
                continue
            m = parse_message(line)
            if not line.startswith("STATUS"):
                self.echo(f"<< {line}")
            if m.kind == "STATE":
                self.state = m.value
            elif m.kind == "FAULT":
                self.fault = m.value
            elif m.kind == "STATUS":
                self.state = m.fields.get("state", self.state)
            if on_line:
                on_line(line, m)
            if predicate(m):
                return m
        return None

    # ---------------------------------------------------------------- job
    def prepare(self, timeout_s: float = 120.0) -> bool:
        errors, warnings = self.recipe.validate()
        for w in warnings:
            self.echo(f"WARNING: {w}")
        if errors:
            for e in errors:
                self.echo(f"RECIPE ERROR: {e}")
            return False
        self.send("STATUS")
        self._wait(lambda m: m.kind == "STATUS", 5.0)
        if self.state == "SAFE_STOP":
            self.echo("controller is in SAFE_STOP: inspect the cause, then send RESET yourself")
            return False
        for line in self.recipe.to_commands():
            self.send(line)
            if not self._wait(lambda m: m.kind in ("OK", "ERROR"), 5.0) or self.fault != "NONE":
                return False
        if self.state in ("BOOT", "UNKNOWN"):
            self.send("HOME")
            if not self._wait(lambda m: m.kind == "STATE" and m.value in ("READY", "SAFE_STOP"), timeout_s):
                return False
        return self.state in ("READY", "COMPLETE")

    def cycle(self, timeout_s: float = 600.0) -> CycleResult:
        run_id = new_id("RUN")
        carrier_id = new_id("SFC")
        lines: list[str] = []
        trace = CsvLog(self.log_dir / "trace.csv", TRACE_FIELDS) if self.log_dir else None
        vres: dict | None = None
        last = {"turn": 0, "tension": None}
        tensions: list[float] = []

        def on_line(line, m):
            lines.append(line)
            if m.kind == "TURN":
                last["turn"] = int(m.value)
            if m.kind == "TENSION":
                last["tension"] = float(m.value)
                tensions.append(last["tension"])
            if trace and m.kind in ("STATE", "FAULT", "TURN", "TENSION", "EVENT", "COMPLETE", "HOME_ERROR_MM", "POSITION", "ERROR"):
                trace.write({"timestamp": now_iso(), "run_id": run_id, "state": self.state,
                             "rot_steps": last["turn"] * 3200, "tension_N": last["tension"],
                             "vision_event": m.value if m.kind == "EVENT" else None,
                             "result": m.value if m.kind == "FAULT" else None, "notes": line})

        self._hb_stop.clear()
        hb = threading.Thread(target=self._heartbeat, daemon=True)
        hb.start()
        try:
            self.fault = "NONE"
            self.send("START")
            m = self._wait(lambda m: m.kind == "STATE" and m.value in ("VERIFY", "SAFE_STOP", "COMPLETE"), timeout_s, on_line)
            if m and m.value == "VERIFY" and self.recipe.require_vision:
                vres = self.vision(self.recipe) if self.vision else {"event": "FAULT_CAMERA", "reason": "no vision configured"}
                if vres.get("length_mm"):
                    self.send(cmd("LENGTH_MM", vres["length_mm"]))
                self.send(vres["event"])
            self._wait(lambda m: m.kind == "STATE" and m.value in ("COMPLETE", "SAFE_STOP"), timeout_s, on_line)
            self._wait(lambda m: m.kind == "COMPLETE" or self.state == "SAFE_STOP", 3.0, on_line)
        finally:
            self._hb_stop.set()
            hb.join(1.0)
            if trace:
                trace.close()
        if self.log_dir:
            comp = next((parse_message(l) for l in reversed(lines) if l.startswith("COMPLETE ")), None)
            with CsvLog(self.log_dir / "carriers.csv", CARRIER_FIELDS) as cl:
                r = self.recipe
                cl.write({"timestamp": now_iso(), "carrier_id": carrier_id, "run_id": run_id,
                          "data_source": "machine" if not isinstance(self.t, SimTransport) else "SIMULATION",
                          "material_lot": r.material_lot, "width_mm": r.strip_width_mm, "thickness_mm": r.strip_thickness_mm,
                          "mandrel_diameter_mm": r.mandrel_diameter_mm,
                          "guide_angle_deg": r.guide_angle_deg if r.guide_angle_deg is not None else round(r.derived_guide_angle, 2),
                          "pitch_mm": r.pitch_mm, "active_turns": r.active_turns, "sacrificial_turns": r.sacrificial_turns,
                          "tension_target_N": r.tension_setpoint_N,
                          "tension_mean_N": round(sum(tensions) / len(tensions), 3) if tensions else None,
                          "tension_max_N": max(tensions) if tensions else None,
                          "winding_rate_rpm": r.rate_rpm, "turn_count": comp.fields.get("turns") if comp else None,
                          "lin_steps": comp.fields.get("lin_steps") if comp else None,
                          "camera_result": vres.get("event") if vres else None,
                          "measured_length_mm": vres.get("length_mm") if vres else None,
                          "final_result": self.state, "fault": self.fault, "notes": r.name})
        return CycleResult(run_id, carrier_id, self.state, self.fault, vres, lines)
