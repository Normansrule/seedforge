import pytest

from seedforge.deploy.ledger import Ledger, LedgerError, PointState


def make(tmp_path):
    led = Ledger(tmp_path / "ledger.json")
    led.assign_sector("A", "drone-A")
    led.assign_sector("B", "drone-B")
    for i in range(3):
        led.add_point(f"A-{i}", "A", 0.0, i)
        led.add_point(f"B-{i}", "B", 1.0, i)
    return led


def test_sector_ownership(tmp_path):
    led = make(tmp_path)
    with pytest.raises(LedgerError):
        led.assign_sector("A", "drone-B")
    with pytest.raises(LedgerError):
        led.record_intent("B-0", "drone-A", 0)
    with pytest.raises(LedgerError):
        led.add_point("A-0", "A", 0, 0)


def test_uncertain_is_not_retried(tmp_path):
    led = make(tmp_path)
    p = led.next_point("drone-A")
    led.record_intent(p.point_id, "drone-A", 1)
    led.confirm(p.point_id, "drone-A", None)
    assert led.points[p.point_id].state == PointState.UNCERTAIN
    assert led.next_point("drone-A").point_id != p.point_id
    with pytest.raises(LedgerError):
        led.record_intent(p.point_id, "drone-A", 2)


def test_intent_survives_restart(tmp_path):
    led = make(tmp_path)
    led.record_intent("A-1", "drone-A", 0)
    led2 = Ledger(tmp_path / "ledger.json")       # power loss after intent, before confirmation
    led2.recover_after_restart()
    assert led2.points["A-1"].state == PointState.UNCERTAIN
    assert led2.summary()["UNCERTAIN"] == 1
