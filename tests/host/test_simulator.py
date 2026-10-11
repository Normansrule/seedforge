from importlib import resources

import pytest

from seedforge.simulator import Plant, run_script


def scenario(name):
    return (resources.files("seedforge.simulator") / "scenarios" / f"{name}.txt").read_text()


@pytest.mark.parametrize("name,state,fault", [
    ("normal_cycle", "COMPLETE", "NONE"), ("estop", "BOOT", "NONE"), ("tension_high", "SAFE_STOP", "TENSION_HIGH"),
    ("vision_gap", "SAFE_STOP", "VISION_GAP"), ("heartbeat_timeout", "SAFE_STOP", "HEARTBEAT_TIMEOUT"),
    ("home_switch_fault", "SAFE_STOP", "HOME_TIMEOUT"), ("m3_cycle", "COMPLETE", "NONE"),
])
def test_required_scenarios(name, state, fault):
    p = run_script(scenario(name), Plant())
    assert p.ctrl.state == state
    assert p.ctrl.fault == fault


def test_normal_cycle_exact_turns():
    p = run_script(scenario("normal_cycle"), Plant())
    assert p.phys_rot == 8 * 3200
    assert any(l.startswith("COMPLETE turns=8 lin_steps=13069") for _, l in p.trace)


def test_estop_sequence():
    p = run_script(scenario("estop"), Plant())
    lines = [l for _, l in p.trace if not l.startswith("STATUS")]
    assert "FAULT=ESTOP_OPEN" in lines
    assert lines.index("FAULT=ESTOP_OPEN") < lines.index("ERROR=ESTOP_STILL_OPEN")
    assert not p.hal.enabled


def test_motion_exact_totals_python():
    from seedforge.simulator.core import Motion
    import random
    rng = random.Random(149)
    for _ in range(50):
        rot, lin = rng.randrange(20000), rng.randrange(20000)
        m = Motion()
        m.start_sync(rot, lin, True, 4000, 20000)
        while m.running:
            m.tick()
        assert (m.rot_done, m.lin_done) == (rot, lin)
