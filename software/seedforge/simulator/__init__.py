"""SeedForge hardware-free simulator (logic and timing only, not physics).

    python -m seedforge.simulator --list
    python -m seedforge.simulator normal
    python -m seedforge.simulator tension-high --log runs/tension_high.csv
"""
from .core import Controller, Hal, Inputs, Motion, Recipe  # noqa: F401
from .plant import Plant, run_scenario_file, run_script  # noqa: F401
