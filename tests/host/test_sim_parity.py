"""The Python simulator must emit exactly what the compiled firmware core emits."""
import shutil
import subprocess
from importlib import resources
from pathlib import Path

import pytest

from seedforge.simulator import Plant, run_script

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "tests" / "firmware" / "build" / "sim_core"
SCEN = sorted((resources.files("seedforge.simulator") / "scenarios").iterdir(), key=lambda p: p.name)


@pytest.fixture(scope="module")
def sim_core():
    if not SIM.exists():
        if not shutil.which("g++") or not shutil.which("make"):
            pytest.skip("C++ toolchain not available")
        subprocess.run(["make", "-C", str(ROOT / "tests" / "firmware"), "build/sim_core"], check=True,
                       capture_output=True)
    return SIM


@pytest.mark.parametrize("scenario", [p for p in SCEN if p.name.endswith(".txt")], ids=lambda p: p.name)
def test_trace_identical(sim_core, scenario):
    text = scenario.read_text()
    py = [f"{ms} {line}" for ms, line in run_script(text, Plant()).trace][2:]
    cc = subprocess.run([str(sim_core), str(scenario)], capture_output=True, text=True, check=True).stdout.splitlines()[2:]
    assert py == cc
