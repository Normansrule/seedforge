import math

import pytest

from seedforge import geometry as g


def test_pitch_angle_roundtrip():
    for phi in (10, 30, 45, 60, 80):
        p = g.pitch_from_strip_angle(0.8, 0.5, phi)
        assert g.strip_angle_from_pitch(0.8, 0.5, p) == pytest.approx(phi)
        assert g.guide_angle_from_pitch(0.8, 0.5, p) == pytest.approx(90 - phi)


def test_course_target_is_overlapping():
    # 4.0 x 0.5 mm strip on a 0.8 mm mandrel at 45 deg: the stated "no gap / no overlap" is not achievable
    p = g.pitch_from_strip_angle(0.8, 0.5, 45.0)
    assert p == pytest.approx(math.pi * 1.3)          # 4.084 mm/rev (R3 development value)
    assert g.normal_gap(0.8, 0.5, 4.0, p) == pytest.approx(-1.112, abs=1e-3)
    assert g.butt_joint_pitch(0.8, 0.5, 4.0) == pytest.approx(19.816, abs=1e-3)


def test_paper_reference_gap():
    assert g.normal_gap(0.8, 0.5, 2.5, 5.0) == pytest.approx(0.663, abs=1e-3)
    assert g.guide_angle_from_pitch(0.8, 0.5, 5.0) == pytest.approx(50.76, abs=0.01)


def test_butt_joint_has_zero_gap():
    for w in (1.0, 2.0, 2.5, 3.5):
        p = g.butt_joint_pitch(0.8, 0.5, w)
        assert g.normal_gap(0.8, 0.5, w, p) == pytest.approx(0.0, abs=1e-9)
        assert g.axial_gap(0.8, 0.5, w, p) == pytest.approx(0.0, abs=1e-9)
    assert g.butt_joint_pitch(0.8, 0.5, 4.2) is None     # wider than the circumference


def test_step_math_matches_firmware():
    assert g.ROT_USTEPS_PER_REV == 3200 and g.LIN_USTEPS_PER_MM == 400
    assert g.lin_total_steps(4.084, 8) == 13069          # firmware COMPLETE line in tests/firmware
    assert g.lin_total_steps(5.0, 8) == 16000
    assert g.realised_pitch(4.084, 8) == pytest.approx(4.084, abs=0.001)
    assert g.master_rate_hz(30, 4.084) == pytest.approx(1600)
    assert g.master_rate_hz(30, 19.816) > 1600            # linear axis becomes the master


def test_mandrel_deflection_is_large():
    # 0.8 mm steel, 90 mm span, 0.5 N: of order a millimetre -> tension must stay low or the span short
    d = g.mandrel_deflection(0.5, 90.0)
    assert 1.5 < d < 2.5
    assert g.mandrel_deflection(0.5, 90.0, support="fixed-pinned") < d
    assert g.mandrel_bending_stress(0.5, 90.0) == pytest.approx(0.5 * 90 / 4 * 0.4 / (math.pi * 0.8 ** 4 / 64))
