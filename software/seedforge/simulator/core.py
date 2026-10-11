"""Pure-Python port of the Uno controller core (sf_motion / sf_controller).

Kept line-for-line close to firmware/arduino/seedforge_core/src so that
tests/host/test_sim_parity.py can compare it event-by-event with the compiled
C++ core.  If you change the firmware state machine, change this file too and
run `make -C tests/firmware && pytest tests/host`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..protocol import Command, ProtocolError, format_fixed, parse_command

ROT_USTEPS_PER_REV = 3200
LIN_USTEPS_PER_MM = 400
MAX_MASTER_HZ = 8000
MIN_MASTER_HZ = 40
HOMING_HZ = 1600
MAX_TRAVEL_UM = 100000

CH_CLAMP, CH_CUTTER, CH_DEMOLD_SUPPORT = 0, 1, 6
SERVO_CLAMP_OPEN, SERVO_CLAMP_CLOSED = 1100, 1600
SERVO_CUT_REST, SERVO_CUT_STROKE = 1000, 1800
SERVO_SUPPORT_OPEN, SERVO_SUPPORT_CLOSED = 1100, 1500
SERVO_DWELL_MS = 700
VISION_VERIFY_TIMEOUT_MS = 15000
PRETENSION_TIMEOUT_MS = 15000
PRETENSION_HOLD_MS = 300
LOADCELL_STALE_MS = 500
HOME_BACKOFF_UM = 2000
HOME_CLEAR_UM = 3000
SKIP_TOLERANCE_UM = 300
SKIP_FAULT_COUNT = 2
COMM_ERROR_LIMIT = 5
COMM_WINDOW_MS = 2000
POSITION_HZ = 2400
POSITION_ACCEL = 8000
DEMOLD_HZ = 800
FW_VERSION = "0.3.0-alpha"

STEP_ROT, STEP_LIN = 1, 2
U32 = 0xFFFFFFFF


def um_to_steps(um: int) -> int:
    n = um * LIN_USTEPS_PER_MM + (500 if um >= 0 else -500)
    return int(n / 1000)          # C++ integer division truncates toward zero


def steps_to_um(st: int) -> int:
    return int(st * 1000 / LIN_USTEPS_PER_MM)


def cdiv(a: int, b: int) -> int:
    """C-style integer division (truncate toward zero)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


class Motion:
    def __init__(self):
        self.running = False
        self.finished = False
        self.rot_is_master = True
        self.lin_positive = True
        self.rot_total = self.lin_total = 0
        self.master_total = self.slave_total = 0
        self.master_done = self.rot_done = self.lin_done = 0
        self.acc = 0
        self.lin_pos = 0
        self.cruise_hz = self.base_cruise_hz = self.accel = 0
        self.rate_hz = 0
        self.rate_frac = 0
        self.interval_us = 1000

    def _begin(self, master_total, cruise_hz, accel):
        cruise_hz = max(MIN_MASTER_HZ, min(MAX_MASTER_HZ, cruise_hz))
        accel = accel or 1
        self.master_total = master_total
        self.master_done = self.rot_done = self.lin_done = 0
        self.acc = master_total // 2
        self.cruise_hz = self.base_cruise_hz = cruise_hz
        self.accel = accel
        self.rate_hz = MIN_MASTER_HZ
        self.rate_frac = 0
        self.interval_us = 1_000_000 // self.rate_hz
        self.finished = False
        self.running = master_total > 0
        if not self.running:
            self.finished = True

    def start_sync(self, rot_total, lin_total, lin_positive, cruise_hz, accel):
        self.running = False
        self.rot_total, self.lin_total, self.lin_positive = rot_total, lin_total, lin_positive
        self.rot_is_master = rot_total >= lin_total
        self.slave_total = lin_total if self.rot_is_master else rot_total
        self._begin(rot_total if self.rot_is_master else lin_total, cruise_hz, accel)

    def start_linear(self, lin_total, lin_positive, cruise_hz, accel):
        self.running = False
        self.rot_total, self.lin_total, self.lin_positive = 0, lin_total, lin_positive
        self.rot_is_master = False
        self.slave_total = 0
        self._begin(lin_total, cruise_hz, accel)

    def stop(self):
        self.running = False

    def tick(self) -> int:
        if not self.running:
            return 0
        bits = STEP_ROT if self.rot_is_master else STEP_LIN
        self.master_done += 1
        if self.slave_total:
            self.acc += self.slave_total
            if self.acc >= self.master_total:
                self.acc -= self.master_total
                bits |= STEP_LIN if self.rot_is_master else STEP_ROT
        if bits & STEP_ROT:
            self.rot_done += 1
        if bits & STEP_LIN:
            self.lin_done += 1
            self.lin_pos += 1 if self.lin_positive else -1
        if self.master_done >= self.master_total:
            self.running = False
            self.finished = True
        return bits

    def scale_cruise(self, permille):
        permille = max(200, min(1000, permille))
        self.cruise_hz = max(MIN_MASTER_HZ, self.base_cruise_hz * permille // 1000)

    def update(self, dt_us):
        if not self.running:
            return
        remaining = max(0, self.master_total - self.master_done)
        stop_steps = (self.rate_hz * self.rate_hz) // (2 * self.accel) + 1
        self.rate_frac += self.accel * dt_us
        dv = self.rate_frac // 1_000_000
        self.rate_frac %= 1_000_000
        if remaining <= stop_steps:
            self.rate_hz = self.rate_hz - dv if self.rate_hz > MIN_MASTER_HZ + dv else MIN_MASTER_HZ
        elif self.rate_hz < self.cruise_hz:
            self.rate_hz = min(self.cruise_hz, self.rate_hz + dv)
        elif self.rate_hz > self.cruise_hz:
            self.rate_hz = self.rate_hz - dv if self.rate_hz > self.cruise_hz + dv else self.cruise_hz
        self.interval_us = 1_000_000 // self.rate_hz


@dataclass
class Recipe:
    pitch_um: int = 4084
    active_turns: int = 7
    sacrificial_turns: int = 1
    rate_rpm_x10: int = 300
    accel_rpm_s_x10: int = 300
    start_um: int = 5000
    tension_set_mN: int = 0
    tension_max_mN: int = 0
    tension_min_mN: int = 0
    require_tension: int = 0
    require_vision: int = 1
    m3_enabled: int = 0
    demold_um: int = 20000
    heartbeat_ms: int = 3000
    dir_bits: int = 0


@dataclass
class Inputs:
    now_ms: int = 0
    estop_ok: bool = False
    home_active: bool = False
    end_active: bool = False
    start_pressed: bool = False
    guard_ok: bool = True
    tension_valid: bool = False
    tension_new: bool = False
    tension_mN: int = 0
    vibration_mg: int = 0
    dancer_raw: int = 0


@dataclass
class Hal:
    enabled: bool = False
    rot_level: bool = True
    lin_level: bool = True
    lines: list = field(default_factory=list)
    servos: list = field(default_factory=list)
    on_emit: Callable[[str], None] | None = None

    def enable_drivers(self, on):
        self.enabled = on

    def set_directions(self, r, l):
        self.rot_level, self.lin_level = r, l

    def servo(self, ch, us):
        self.servos.append((ch, us))

    def servos_off(self):
        self.servos.append((-1, 0))

    def emit(self, line):
        self.lines.append(line)
        if self.on_emit:
            self.on_emit(line)

    def tare(self):
        pass

    def calibrate(self, known_mN):
        return True


MOVING = {"HOME", "PRETENSION", "WIND", "VERIFY", "CLAMP", "CUT", "DEMOLD"}
SETTABLE = {"BOOT", "READY", "COMPLETE", "SAFE_STOP"}


class Controller:
    def __init__(self, hal: Hal):
        self.hal = hal
        self.motion = Motion()
        self.recipe = Recipe()
        self.state = "BOOT"
        self.fault = "NONE"
        self.phase = "NONE"
        self.homed = False
        self.cycle_pending = False
        self.home_check = False
        self.skip_strikes = 0
        self.t_enter = self.t_phase = self.t_hb = self.t_last = self.t_tension_ok = self.t_tension_seen = 0
        self.t_report = 0
        self.last_turn = 0
        self.wound_turns = 0
        self.wound_lin_steps = 0
        self.tension_strikes = 0
        self.comm_errors = 0
        self.t_comm_window = 0
        self.last_length_x100 = -1
        self.tension_mN = 0
        self.tension_valid = False
        self.last_in = Inputs()

    # ---------------------------------------------------------------- output helpers
    def emit_kv(self, key, v, scale):
        self.hal.emit(f"{key}={format_fixed(v, scale)}")

    def error(self, code):
        self.hal.emit(f"ERROR={code}")

    def begin(self, now_ms):
        self.hal.enable_drivers(False)
        self.t_last = self.t_hb = self.t_enter = self.t_report = now_ms
        self.hal.emit(f"SEEDFORGE_CORE fw={FW_VERSION}")
        self.enter("BOOT")

    def enter(self, s):
        self.state = s
        self.phase = "NONE"
        self.t_enter = self.t_phase = self.last_in.now_ms
        self.hal.emit(f"STATE={s}")

    def safe_stop(self, f):
        self.motion.stop()
        self.hal.enable_drivers(False)
        self.hal.servos_off()
        self.fault = f
        self.cycle_pending = False
        self.homed = False
        self.hal.emit(f"FAULT={f}")
        if self.state != "SAFE_STOP":
            self.enter("SAFE_STOP")

    def turns_done(self):
        return self.motion.rot_done // ROT_USTEPS_PER_REV

    def lin_target_steps(self):
        r = self.recipe
        turns = r.active_turns + r.sacrificial_turns
        return (r.pitch_um * LIN_USTEPS_PER_MM * turns + 500) // 1000

    def master_hz(self):
        r = self.recipe
        rot_total = (r.active_turns + r.sacrificial_turns) * ROT_USTEPS_PER_REV
        lin_total = self.lin_target_steps()
        rot_hz = r.rate_rpm_x10 * ROT_USTEPS_PER_REV // 600
        if lin_total > rot_total and rot_total:
            return rot_hz * lin_total // rot_total
        return rot_hz

    def emit_status(self):
        pos = format_fixed(cdiv(steps_to_um(self.motion.lin_pos), 10), 2)
        t = format_fixed(self.tension_mN, 3) if self.tension_valid else "nan"
        i = self.last_in
        self.hal.emit(f"STATUS state={self.state} fault={self.fault} homed={int(self.homed)} pos_mm={pos} "
                      f"turn={self.turns_done()} tension_N={t} estop={int(i.estop_ok)} home={int(i.home_active)} "
                      f"end={int(i.end_active)} dancer={i.dancer_raw} vib_mg={i.vibration_mg}")

    def settable(self):
        return self.state in SETTABLE

    def apply_setter(self, c: Command) -> bool:
        v = c.value
        r = self.recipe
        lim = MAX_TRAVEL_UM // 10
        rules = {
            "SET_PITCH": ("pitch_um", 200, 30000, 1), "SET_TURNS": ("active_turns", 1, 40, 1),
            "SET_SACRIFICIAL": ("sacrificial_turns", 0, 5, 1), "SET_RATE": ("rate_rpm_x10", 10, 3000, 1),
            "SET_ACCEL": ("accel_rpm_s_x10", 10, 30000, 1), "SET_START": ("start_um", 0, lim, 10),
            "SET_TENSION": ("tension_set_mN", 0, 9800, 1), "SET_TENSION_MAX": ("tension_max_mN", 0, 9800, 1),
            "SET_TENSION_MIN": ("tension_min_mN", 0, 9800, 1), "SET_REQUIRE_TENSION": ("require_tension", 0, 1, 1),
            "SET_REQUIRE_VISION": ("require_vision", 0, 1, 1), "SET_M3": ("m3_enabled", 0, 1, 1),
            "SET_DEMOLD": ("demold_um", -lim, lim, 10), "SET_HEARTBEAT_MS": ("heartbeat_ms", 200, 60000, 1),
            "SET_DIR": ("dir_bits", 0, 3, 1),
        }
        if c.name not in rules:
            return False
        attr, lo, hi, mult = rules[c.name]
        if not lo <= v <= hi:
            return False
        setattr(r, attr, v * mult)
        return True

    def begin_cycle(self):
        r = self.recipe
        end_um = r.start_um + r.pitch_um * (r.active_turns + r.sacrificial_turns)
        demold_end = end_um + (r.demold_um if r.m3_enabled else 0)
        if end_um > MAX_TRAVEL_UM or demold_end > MAX_TRAVEL_UM or demold_end < 0:
            self.error("RECIPE_TRAVEL")
            return
        if r.require_tension and (not self.tension_valid or r.tension_max_mN <= 0):
            self.error("TENSION_NOT_CONFIGURED")
            return
        self.fault = "NONE"
        self.cycle_pending = True
        self.home_check = self.homed
        self.hal.enable_drivers(True)
        self.enter("HOME")

    def start_position_move(self, target_um, hz):
        delta = um_to_steps(target_um) - self.motion.lin_pos
        pos = delta >= 0
        db = self.recipe.dir_bits
        self.hal.set_directions(not (db & 1), pos != bool(db & 2))
        self.motion.start_linear(abs(delta), pos, hz, POSITION_ACCEL)

    # ---------------------------------------------------------------- input
    def handle_line(self, line: str, now_ms: int):
        try:
            c = parse_command(line)
        except ProtocolError:
            if now_ms - self.t_comm_window > COMM_WINDOW_MS:
                self.t_comm_window = now_ms
                self.comm_errors = 0
            self.comm_errors += 1
            self.error("BAD_COMMAND")
            if self.state in MOVING and self.comm_errors >= COMM_ERROR_LIMIT:
                self.safe_stop("COMM_ERRORS")
            return
        self.handle(c, now_ms)

    def handle(self, c: Command, now_ms: int):
        self.last_in.now_ms = now_ms
        n = c.name
        faults = {"FAULT_GAP": "VISION_GAP", "FAULT_OVERLAP": "VISION_OVERLAP", "FAULT_LENGTH": "VISION_LENGTH",
                  "FAULT_TAIL": "VISION_TAIL", "FAULT_CAMERA": "VISION_CAMERA"}
        if n == "STOP":
            return self.safe_stop("REMOTE_STOP")
        if n in faults:
            return self.safe_stop(faults[n])
        if n == "HEARTBEAT":
            self.t_hb = now_ms
            return
        if n == "STATUS":
            return self.emit_status()
        if n == "LENGTH_MM":
            self.last_length_x100 = c.value
            return self.emit_kv("LENGTH_MM", c.value, 2)
        if n == "GET_RECIPE":
            r = self.recipe
            self.hal.emit(f"RECIPE pitch_mm={format_fixed(r.pitch_um, 3)} turns={r.active_turns} "
                          f"sacrificial={r.sacrificial_turns} rate_rpm={format_fixed(r.rate_rpm_x10, 1)} "
                          f"start_mm={format_fixed(r.start_um // 10, 2)} tension_max_N={format_fixed(r.tension_max_mN, 3)} "
                          f"m3={r.m3_enabled} vision={r.require_vision}")
            return
        if n == "RESET":
            if self.state not in ("SAFE_STOP", "COMPLETE", "BOOT"):
                return self.error("BUSY")
            if not self.last_in.estop_ok:
                return self.error("ESTOP_STILL_OPEN")
            r = self.recipe
            if r.tension_max_mN > 0 and self.tension_valid and self.tension_mN > r.tension_max_mN:
                return self.error("TENSION_STILL_HIGH")
            self.fault = "NONE"
            self.hal.enable_drivers(False)
            return self.enter("BOOT")
        if n == "HOME":
            if self.state not in ("BOOT", "READY", "COMPLETE"):
                return self.error("BUSY")
            if not self.last_in.estop_ok:
                return self.error("ESTOP_OPEN")
            self.cycle_pending = False
            self.home_check = False
            self.hal.enable_drivers(True)
            return self.enter("HOME")
        if n == "START":
            if self.state not in ("READY", "COMPLETE"):
                return self.error("BUSY" if self.homed else "NOT_HOMED")
            if not self.last_in.estop_ok:
                return self.error("ESTOP_OPEN")
            return self.begin_cycle()
        if n == "VISION_OK":
            if self.state != "VERIFY":
                return self.error("UNEXPECTED_VISION_OK")
            return self.enter("CLAMP" if self.recipe.m3_enabled else "COMPLETE")
        if n == "TARE":
            if not self.settable():
                return self.error("BUSY")
            self.hal.tare()
            return self.hal.emit("OK=TARE")
        if n == "CAL_TENSION":
            if not self.settable():
                return self.error("BUSY")
            if c.value <= 0 or not self.hal.calibrate(c.value):
                return self.error("CAL_FAILED")
            return self.hal.emit("OK=CAL_TENSION")
        if n == "JOG":
            if self.state != "READY" or self.motion.running:
                return self.error("NOT_READY")
            target = steps_to_um(self.motion.lin_pos) + c.value * 10
            if target < 0 or target > MAX_TRAVEL_UM:
                return self.error("JOG_RANGE")
            self.hal.enable_drivers(True)
            self.start_position_move(target, POSITION_HZ)
            self.phase = "RUN"
            return
        if not self.settable():
            return self.error("BUSY")
        if not self.apply_setter(c):
            return self.error("OUT_OF_RANGE")
        self.hal.emit(f"OK={n}")

    # ---------------------------------------------------------------- periodic
    def check_safety(self, i: Inputs):
        if self.state == "SAFE_STOP":
            return
        if not i.estop_ok:
            return self.safe_stop("ESTOP_OPEN")
        if i.home_active and i.end_active:
            return self.safe_stop("LIMIT_WIRING")
        m = self.motion
        if m.running:
            lin_moving = m.lin_total > 0
            if lin_moving and m.lin_positive and i.end_active:
                return self.safe_stop("END_LIMIT")
            if lin_moving and not m.lin_positive and i.home_active and self.state != "HOME":
                return self.safe_stop("HOME_LIMIT")
            if steps_to_um(m.lin_pos) > MAX_TRAVEL_UM and self.state != "HOME":
                return self.safe_stop("SOFT_LIMIT")
        r = self.recipe
        tension_state = self.state in ("PRETENSION", "WIND", "VERIFY", "CLAMP", "CUT", "DEMOLD")
        if r.tension_max_mN > 0 and i.tension_valid and i.tension_new:
            if i.tension_mN > r.tension_max_mN:
                self.tension_strikes += 1
                if self.tension_strikes >= 2 and tension_state:
                    return self.safe_stop("TENSION_HIGH")
            else:
                self.tension_strikes = 0
        if r.require_tension and self.state in ("PRETENSION", "WIND"):
            if not i.tension_valid or (i.now_ms - self.t_tension_seen) > LOADCELL_STALE_MS:
                return self.safe_stop("LOADCELL")
        if r.require_vision and self.state in ("WIND", "VERIFY") and (i.now_ms - self.t_hb) > r.heartbeat_ms:
            return self.safe_stop("HEARTBEAT_TIMEOUT")
        if self.state == "CUT" and not i.guard_ok:
            return self.safe_stop("GUARD_OPEN")

    def step(self, i: Inputs):
        dt_ms = i.now_ms - self.t_last
        self.t_last = i.now_ms
        self.last_in = i
        if i.tension_new:
            self.t_tension_seen = i.now_ms
            self.tension_mN = i.tension_mN
        self.tension_valid = i.tension_valid
        self.motion.update(dt_ms * 1000)
        if i.start_pressed:
            if self.state == "BOOT":
                self.handle(Command("HOME"), i.now_ms)
            elif self.state in ("READY", "COMPLETE"):
                self.handle(Command("START"), i.now_ms)
            elif self.state == "SAFE_STOP":
                self.handle(Command("RESET"), i.now_ms)
            else:
                self.safe_stop("LOCAL_STOP")
        self.check_safety(i)
        self.run_state(i)

    def run_state(self, i: Inputs):
        now = i.now_ms
        m = self.motion
        r = self.recipe
        s = self.state
        db = r.dir_bits
        if s in ("BOOT", "SAFE_STOP"):
            self.hal.enable_drivers(False)
            if now - self.t_report >= 1000:
                self.t_report = now
                self.emit_status()
        elif s == "READY":
            if self.phase == "RUN" and m.finished:
                m.finished = False
                self.phase = "NONE"
                self.hal.enable_drivers(False)
                self.emit_kv("POSITION", cdiv(steps_to_um(m.lin_pos), 10), 2)
            if now - self.t_report >= 1000 and not m.running:
                self.t_report = now
                self.emit_status()
        elif s == "HOME":
            max_steps = um_to_steps(MAX_TRAVEL_UM + 20000)
            if self.phase == "NONE":
                if i.home_active:
                    self.hal.set_directions(True, not (db & 2))
                    m.start_linear(um_to_steps(HOME_CLEAR_UM), True, HOMING_HZ // 2, POSITION_ACCEL)
                    self.phase = "CLEAR"
                else:
                    self.hal.set_directions(True, bool(db & 2))
                    m.start_linear(max_steps, False, HOMING_HZ, POSITION_ACCEL)
                    self.phase = "SEEK"
            elif self.phase == "CLEAR" and m.finished:
                m.finished = False
                if i.home_active:
                    return self.safe_stop("HOME_LIMIT")
                self.phase = "NONE"
            elif self.phase == "SEEK":
                if i.home_active:
                    m.stop()
                    err = steps_to_um(m.lin_pos)
                    if self.home_check:
                        self.emit_kv("HOME_ERROR_MM", cdiv(err, 10), 2)
                        if abs(err) > SKIP_TOLERANCE_UM:
                            self.skip_strikes += 1
                            if self.skip_strikes >= SKIP_FAULT_COUNT:
                                return self.safe_stop("SKIPPED_STEPS")
                            self.error("HOME_DRIFT")
                        else:
                            self.skip_strikes = 0
                    m.lin_pos = 0
                    self.hal.set_directions(True, not (db & 2))
                    m.start_linear(um_to_steps(HOME_BACKOFF_UM), True, HOMING_HZ // 2, POSITION_ACCEL)
                    self.phase = "BACKOFF"
                elif m.finished:
                    m.finished = False
                    self.safe_stop("HOME_TIMEOUT")
            elif self.phase == "BACKOFF" and m.finished:
                m.finished = False
                if i.home_active:
                    return self.safe_stop("HOME_LIMIT")
                self.homed = True
                self.emit_kv("POSITION", cdiv(steps_to_um(m.lin_pos), 10), 2)
                if self.cycle_pending:
                    self.enter("PRETENSION")
                else:
                    self.hal.enable_drivers(False)
                    self.enter("READY")
        elif s == "PRETENSION":
            if self.phase == "NONE":
                self.hal.enable_drivers(True)
                self.start_position_move(r.start_um, POSITION_HZ)
                self.phase = "POSITION"
            elif self.phase == "POSITION" and m.finished:
                m.finished = False
                self.emit_kv("POSITION", cdiv(steps_to_um(m.lin_pos), 10), 2)
                self.phase = "WAIT"
                self.t_phase = now
                self.t_tension_ok = 0
                if not r.require_tension:
                    self.hal.emit("EVENT=PRETENSION_SKIPPED")
            elif self.phase == "WAIT":
                ok = (not r.require_tension) or (self.tension_valid and self.tension_mN >= r.tension_min_mN)
                if ok:
                    if not self.t_tension_ok:
                        self.t_tension_ok = now if now else 1
                    if not r.require_tension or now - self.t_tension_ok >= PRETENSION_HOLD_MS:
                        self.enter("WIND")
                else:
                    self.t_tension_ok = 0
                    if now - self.t_phase > PRETENSION_TIMEOUT_MS:
                        self.safe_stop("PRETENSION_TIMEOUT")
        elif s == "WIND":
            if self.phase == "NONE":
                rot_total = (r.active_turns + r.sacrificial_turns) * ROT_USTEPS_PER_REV
                lin_total = self.lin_target_steps()
                hz = self.master_hz()
                rot_accel = r.accel_rpm_s_x10 * ROT_USTEPS_PER_REV // 600
                accel = rot_accel * lin_total // rot_total if lin_total > rot_total else rot_accel
                self.wound_turns = 0
                self.wound_lin_steps = 0
                if hz > MAX_MASTER_HZ:
                    self.error("RATE_CLAMPED")
                self.hal.set_directions(not (db & 1), not (db & 2))
                m.start_sync(rot_total, lin_total, True, hz, accel)
                self.last_turn = 0
                self.phase = "RUN"
            elif self.phase == "RUN":
                t = self.turns_done()
                if t != self.last_turn:
                    self.last_turn = t
                    self.emit_kv("TURN", t, 0)
                if r.require_tension and now - self.t_report >= 500:
                    self.t_report = now
                    self.emit_kv("TENSION", self.tension_mN, 3)
                if m.finished:
                    m.finished = False
                    self.wound_turns = self.turns_done()
                    self.wound_lin_steps = m.lin_done
                    self.emit_kv("POSITION", cdiv(steps_to_um(m.lin_pos), 10), 2)
                    self.hal.emit("EVENT=WIND_DONE")
                    self.enter("VERIFY")
                    if not r.require_vision:
                        self.hal.emit("EVENT=VISION_BYPASSED")
                        self.enter("CLAMP" if r.m3_enabled else "COMPLETE")
        elif s == "VERIFY":
            if now - self.t_enter > VISION_VERIFY_TIMEOUT_MS:
                self.safe_stop("VISION_TIMEOUT")
        elif s == "CLAMP":
            if self.phase == "NONE":
                self.hal.servo(CH_CLAMP, SERVO_CLAMP_CLOSED)
                self.phase, self.t_phase = "DWELL1", now
            elif now - self.t_phase >= SERVO_DWELL_MS:
                self.enter("CUT")
        elif s == "CUT":
            if self.phase == "NONE":
                self.hal.servo(CH_CUTTER, SERVO_CUT_STROKE)
                self.phase, self.t_phase = "DWELL1", now
            elif self.phase == "DWELL1" and now - self.t_phase >= SERVO_DWELL_MS:
                self.hal.servo(CH_CUTTER, SERVO_CUT_REST)
                self.phase, self.t_phase = "DWELL2", now
            elif self.phase == "DWELL2" and now - self.t_phase >= SERVO_DWELL_MS:
                self.enter("DEMOLD")
        elif s == "DEMOLD":
            if self.phase == "NONE":
                self.hal.servo(CH_DEMOLD_SUPPORT, SERVO_SUPPORT_CLOSED)
                self.phase, self.t_phase = "DWELL1", now
            elif self.phase == "DWELL1" and now - self.t_phase >= SERVO_DWELL_MS:
                self.start_position_move(steps_to_um(m.lin_pos) + r.demold_um, DEMOLD_HZ)
                self.phase = "RETRACT"
            elif self.phase == "RETRACT" and m.finished:
                m.finished = False
                self.hal.servo(CH_DEMOLD_SUPPORT, SERVO_SUPPORT_OPEN)
                self.phase, self.t_phase = "DWELL2", now
            elif self.phase == "DWELL2" and now - self.t_phase >= SERVO_DWELL_MS:
                self.hal.servo(CH_CLAMP, SERVO_CLAMP_OPEN)
                self.phase, self.t_phase = "DWELL3", now
            elif self.phase == "DWELL3" and now - self.t_phase >= SERVO_DWELL_MS:
                self.enter("COMPLETE")
        elif s == "COMPLETE":
            if self.phase == "NONE":
                self.hal.enable_drivers(False)
                length = format_fixed(self.last_length_x100, 2) if self.last_length_x100 >= 0 else "nan"
                self.hal.emit(f"COMPLETE turns={self.wound_turns} lin_steps={self.wound_lin_steps} "
                              f"pitch_mm={format_fixed(r.pitch_um, 3)} length_mm={length}")
                self.phase = "WAIT"
                self.last_length_x100 = -1
            if now - self.t_report >= 1000:
                self.t_report = now
                self.emit_status()
