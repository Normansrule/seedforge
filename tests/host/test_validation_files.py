"""Validation templates and status file stay consistent with the code."""
from pathlib import Path

import pytest

from seedforge.runlog import CARRIER_FIELDS, TRACE_FIELDS

ROOT = Path(__file__).resolve().parents[2]
LEVELS = {"SOURCE-SUPPORTED", "ENGINEERING ASSUMPTION", "RECONSTRUCTED REFERENCE", "CAD-VALIDATED", "SOFTWARE-TESTED",
          "PHYSICALLY TESTED", "BIOLOGICALLY VALIDATED", "FLIGHT-VALIDATED", "NOT STARTED"}


def header(name):
    return (ROOT / "validation" / name).read_text().strip().splitlines()[0].split(",")


def test_run_log_template_matches_runlog():
    assert header("RUN_LOG_TEMPLATE.csv") == TRACE_FIELDS


def test_carrier_template_matches_runlog():
    assert header("CARRIER_LOG_TEMPLATE.csv") == CARRIER_FIELDS


def test_status_levels_and_evidence_paths():
    yaml = pytest.importorskip("yaml")
    s = yaml.safe_load((ROOT / "validation" / "status.yaml").read_text())
    for item in s["items"]:
        assert item["level"] in LEVELS, item
        for e in item["evidence"]:
            assert (ROOT / e).exists(), e
    assert [p["phase"] for p in s["phases"]] == list(range(9))
    # physical evidence levels need a logged record under validation/records/
    for i in s["items"]:
        if i["level"] in {"PHYSICALLY TESTED", "BIOLOGICALLY VALIDATED", "FLIGHT-VALIDATED"}:
            assert any(e.startswith("validation/records/") for e in i["evidence"]), i
