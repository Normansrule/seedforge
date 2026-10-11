import numpy as np
import pytest

from seedforge.vision import Thresholds, inspect
from seedforge.vision.synth import CoilSpec, render, standard_set

EXPECT = {"good": "VISION_OK", "gap": "FAULT_GAP", "overlap": "FAULT_OVERLAP", "length": "FAULT_LENGTH",
          "deformed": "FAULT_LENGTH"}


@pytest.mark.parametrize("spec", standard_set(), ids=lambda s: f"{s.label}-{s.seed}")
def test_synthetic_set(spec):
    res = inspect(render(spec), Thresholds())
    assert res.event == EXPECT[spec.label], res.reasons


def test_good_measurements():
    res = inspect(render(CoilSpec(seed=3)), Thresholds())
    assert res.pitch_mm == pytest.approx(5.0, abs=0.1)
    assert res.turns == pytest.approx(7.0, abs=0.3)
    assert res.axis_sag_mm < 0.1


def test_camera_faults():
    assert inspect(np.full((200, 400), 255, np.uint8), Thresholds()).event == "FAULT_CAMERA"
    assert inspect(np.zeros((0, 0), np.uint8), Thresholds()).event == "FAULT_CAMERA"
