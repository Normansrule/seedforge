from seedforge import recipe as r
from seedforge.protocol import parse_command


def test_builtin_recipes_valid_and_parseable():
    for name in ("paper_reference", "course_target_45deg", "butt_joint_2p5mm"):
        rec = r.builtin(name)
        errors, warnings = rec.validate()
        assert errors == []
        assert any("unmeasured" in w for w in warnings)
        for line in rec.to_commands():
            parse_command(line)


def test_course_target_warns_overlap():
    _, warnings = r.builtin("course_target_45deg").validate()
    assert any("OVERLAP" in w for w in warnings)


def test_travel_errors():
    rec = r.builtin("paper_reference")
    rec.pitch_mm = 12.0
    errors, _ = rec.validate()
    assert any("soft limit" in e or "free mandrel span" in e for e in errors)
    rec = r.builtin("paper_reference")
    rec.require_tension = True
    assert any("tension_max_N" in e for e in rec.validate()[0])


def test_runner_end_to_end_sim(tmp_path):
    from seedforge.host.__main__ import make_vision
    from seedforge.host.runner import Runner, SimTransport
    t = SimTransport(speed=20.0)   # vision must answer within the 15 s (simulated) VERIFY timeout
    try:
        run = Runner(t, r.builtin("paper_reference"), tmp_path, make_vision("synthetic"), echo=None)
        assert run.prepare()
        res = run.cycle()
    finally:
        t.close()
    assert res.final_state == "COMPLETE" and res.vision["event"] == "VISION_OK"
    rows = (tmp_path / "carriers.csv").read_text().splitlines()
    assert len(rows) == 2 and "SIMULATION" in rows[1]
