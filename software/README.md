# Python package `seedforge`

Host-side software. Licence: MIT. Python 3.10+.

```bash
python -m pip install -e ".[dev]"     # from the repository root
python -m pytest
```

| module | command | purpose |
|---|---|---|
| `seedforge.geometry` | `python -m seedforge.geometry [--pitch P \| --angle A] [--width W ...]` | first-order helix model: pitch, strip/guide angle, gap/overlap, butt-joint pitch, mandrel deflection |
| `seedforge.protocol` | (library) | line protocol, mirrors the firmware parser |
| `seedforge.recipe` | `python -m seedforge.host --check-recipe NAME` | recipe JSON, validation against travel, CAD windows and geometry |
| `seedforge.simulator` | `python -m seedforge.simulator [scenario]` | Python port of the Uno state machine + virtual plant |
| `seedforge.host` | `python -m seedforge.host --port sim\|COMx\|/dev/ttyACM0\|tcp:HOST:3333 --recipe R --vision V` | runs cycles, heartbeats, vision verdicts, CSV logs |
| `seedforge.vision` | `python -m seedforge.vision demo\|inspect\|evaluate` | deterministic silhouette QA and synthetic test set |
| `seedforge.runlog` | (library) | `carriers.csv` / `trace.csv` |
| `seedforge.deploy.ledger` | (library) | drop-point ledger for the optional deployment concept |

Built-in recipes (`seedforge/recipes/`):

| recipe | geometry | note |
|---|---|---|
| `paper_reference` | 2.5 x 0.5 mm, 5.0 mm/rev, 7 + 1 turns | SOURCE-SUPPORTED geometry; machine values are assumptions |
| `course_target_45deg` | 4.0 x 0.5 mm, 45 deg (4.084 mm/rev) | commissioning only: predicted to overlap (finding C1) |
| `butt_joint_2p5mm` | 2.5 x 0.5 mm, 3.162 mm/rev | model-predicted butt joint |

Dependencies: `numpy`, `opencv-python-headless` (vision), `pyserial` (real hardware). CAD tools
need the `cad` extra. Docs: [simulator](../docs/simulator.md), [vision](../docs/computer-vision.md),
[protocol](../docs/protocol.md).
