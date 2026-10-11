import pytest

from seedforge.protocol import (Command, ProtocolError, cmd, format_fixed, parse_command, parse_fixed,
                                parse_message)


@pytest.mark.parametrize("line,name,value", [
    ("  start ", "START", None), ("SET_PITCH=4.084", "SET_PITCH", 4084), ("set_pitch = 19.85", "SET_PITCH", 19850),
    ("PITCH=5", "SET_PITCH", 5000), ("STEP_US=1500", "SET_RATE", 125), ("LENGTH_MM=35.25", "LENGTH_MM", 3525),
    ("SET_DEMOLD=-40", "SET_DEMOLD", -4000), ("EMERGENCY_STOP", "STOP", None), ("SET_PITCH=4.08449", "SET_PITCH", 4084),
])
def test_parse_ok(line, name, value):
    c = parse_command(line)
    assert (c.name, c.value) == (name, value)


@pytest.mark.parametrize("line", ["START=1", "SET_PITCH", "SET_PITCH=4.0.1", "SET_PITCH=abc", "WIBBLE", "",
                                  "SET_PITCH=99999999999"])
def test_parse_rejects(line):
    with pytest.raises(ProtocolError):
        parse_command(line)


def test_fixed_roundtrip():
    for v in (0, 1, -1, 999, 1000, 123456, -98765):
        assert parse_fixed(format_fixed(v, 3), 3) == v
    assert format_fixed(-50, 2) == "-0.50"
    assert format_fixed(5, 3) == "0.005"


def test_cmd_builder():
    assert cmd("SET_PITCH", 19.816) == "SET_PITCH=19.816"
    assert cmd("start") == "START"
    assert Command("SET_RATE", 125).number == 12.5


def test_parse_messages():
    m = parse_message("STATUS state=READY fault=NONE homed=1 pos_mm=2.00")
    assert m.kind == "STATUS" and m.fields["state"] == "READY"
    assert parse_message("STATE=WIND").value == "WIND"
    assert parse_message("COMPLETE turns=8 lin_steps=13069 pitch_mm=4.084 length_mm=nan").fields["turns"] == "8"
    assert parse_message("SEEDFORGE_CORE fw=0.3.0-alpha").kind == "BANNER"
