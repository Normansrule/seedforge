"""SeedForge line protocol: Python side.

Mirrors firmware/arduino/seedforge_core/src/sf_protocol.cpp (same keywords,
same fixed-point scales, same validation) so host tools, the simulator and the
firmware agree.  Specification: docs/protocol.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# keyword -> (needs_value, decimal scale)
COMMANDS: dict[str, tuple[bool, int]] = {
    "START": (False, 0), "STOP": (False, 0), "EMERGENCY_STOP": (False, 0), "RESET": (False, 0),
    "HOME": (False, 0), "STATUS": (False, 0), "GET_RECIPE": (False, 0), "TARE": (False, 0),
    "CAL_TENSION": (True, 3),
    "HEARTBEAT": (False, 0), "VISION_OK": (False, 0), "FAULT_GAP": (False, 0), "FAULT_OVERLAP": (False, 0),
    "FAULT_LENGTH": (False, 0), "FAULT_TAIL": (False, 0), "FAULT_CAMERA": (False, 0), "LENGTH_MM": (True, 2),
    "SET_PITCH": (True, 3), "PITCH": (True, 3), "SET_TURNS": (True, 0), "SET_SACRIFICIAL": (True, 0),
    "SET_RATE": (True, 1), "SET_ACCEL": (True, 1), "SET_START": (True, 2), "SET_TENSION": (True, 3),
    "SET_TENSION_MAX": (True, 3), "SET_TENSION_MIN": (True, 3), "SET_REQUIRE_TENSION": (True, 0),
    "SET_REQUIRE_VISION": (True, 0), "SET_M3": (True, 0), "SET_DEMOLD": (True, 2), "SET_HEARTBEAT_MS": (True, 0),
    "SET_DIR": (True, 0), "JOG": (True, 2),
}
ALIASES = {"EMERGENCY_STOP": "STOP", "PITCH": "SET_PITCH"}

STATES = ["BOOT", "HOME", "READY", "PRETENSION", "WIND", "VERIFY", "CLAMP", "CUT", "DEMOLD", "COMPLETE", "SAFE_STOP"]
FAULTS = ["NONE", "ESTOP_OPEN", "END_LIMIT", "HOME_LIMIT", "LIMIT_WIRING", "SOFT_LIMIT", "TENSION_HIGH", "LOADCELL",
          "PRETENSION_TIMEOUT", "HOME_TIMEOUT", "SKIPPED_STEPS", "HEARTBEAT_TIMEOUT", "VISION_TIMEOUT", "VISION_GAP",
          "VISION_OVERLAP", "VISION_LENGTH", "VISION_TAIL", "VISION_CAMERA", "COMM_ERRORS", "GUARD_OPEN", "VIBRATION",
          "REMOTE_STOP", "LOCAL_STOP"]

_FIXED = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


class ProtocolError(ValueError):
    pass


def parse_fixed(text: str, scale: int) -> int:
    """Decimal string -> fixed point int with `scale` decimals (extra decimals truncated)."""
    s = text.strip()
    if not _FIXED.match(s):
        raise ProtocolError(f"not a decimal number: {text!r}")
    neg = s.startswith("-")
    whole, _, frac = s.lstrip("+-").partition(".")
    frac = frac[:scale]
    if len(whole + frac) > 12:
        raise ProtocolError("too many digits")
    v = int(whole or "0") * 10 ** scale + (int(frac.ljust(scale, "0")) if scale else 0)
    if v > 2_000_000_000:
        raise ProtocolError("value out of range")
    return -v if neg else v


def format_fixed(value: int, scale: int) -> str:
    if scale == 0:
        return str(value)
    neg = value < 0
    v = abs(value)
    s = f"{v // 10 ** scale}.{v % 10 ** scale:0{scale}d}"
    return "-" + s if neg else s


@dataclass(frozen=True)
class Command:
    name: str               # canonical keyword
    value: int | None = None  # fixed point (scale = COMMANDS[name][1])

    @property
    def scale(self) -> int:
        return COMMANDS[self.name][1]

    @property
    def number(self) -> float | None:
        return None if self.value is None else self.value / 10 ** self.scale

    def encode(self) -> str:
        if self.value is None:
            return self.name
        return f"{self.name}={format_fixed(self.value, self.scale)}"


def parse_command(line: str) -> Command:
    """Parse one host->controller line exactly like the firmware does."""
    s = line.strip()
    if not s:
        raise ProtocolError("empty line")
    key, eq, value = s.partition("=")
    key = key.strip().upper()
    value = value.strip()
    if key == "STEP_US" and eq:              # R3 legacy: master interval in microseconds
        us = parse_fixed(value, 0)
        if us <= 0:
            raise ProtocolError("STEP_US must be positive")
        return Command("SET_RATE", (6_000_000_000 // (us * 3200) + 5) // 10)
    if key not in COMMANDS:
        raise ProtocolError(f"unknown command {key!r}")
    needs, scale = COMMANDS[key]
    if needs and not eq:
        raise ProtocolError(f"{key} needs a value")
    if not needs and eq:
        raise ProtocolError(f"{key} takes no value")
    canon = ALIASES.get(key, key)
    return Command(canon, parse_fixed(value, scale) if needs else None)


def cmd(name: str, number: float | int | None = None) -> str:
    """Build a command line from a float, e.g. cmd('SET_PITCH', 4.084) -> 'SET_PITCH=4.084'."""
    name = name.upper()
    needs, scale = COMMANDS[name]
    if needs:
        if number is None:
            raise ProtocolError(f"{name} needs a value")
        v = int(round(float(number) * 10 ** scale))
        return Command(name, v).encode()
    return name


@dataclass
class Message:
    """A controller->host line, decoded."""
    raw: str
    kind: str                     # STATE, FAULT, TURN, TENSION, POSITION, ERROR, OK, EVENT, COMPLETE, STATUS, RECIPE, BANNER, OTHER
    value: str | None = None
    fields: dict[str, str] = field(default_factory=dict)


_KV_KINDS = {"STATE", "FAULT", "TURN", "TENSION", "POSITION", "ERROR", "OK", "EVENT", "LENGTH_MM", "HOME_ERROR_MM"}


def parse_message(line: str) -> Message:
    s = line.strip()
    head, _, rest = s.partition(" ")
    if head in ("STATUS", "RECIPE", "COMPLETE", "BRIDGE"):
        fields = dict(tok.split("=", 1) for tok in rest.split() if "=" in tok)
        return Message(s, head, None, fields)
    if head.startswith("SEEDFORGE_CORE"):
        return Message(s, "BANNER", None, dict(tok.split("=", 1) for tok in rest.split() if "=" in tok))
    k, eq, v = s.partition("=")
    if eq and k in _KV_KINDS:
        return Message(s, k, v)
    return Message(s, "OTHER", s)
