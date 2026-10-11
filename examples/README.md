# Examples

Everything here is runnable without hardware. Nothing here is measured data.

| file | what it shows | run |
|---|---|---|
| `scenarios/paper_reference_with_length.txt` | paper-reference recipe (5.0 mm/rev), host reports a length, accepts | `python -m seedforge.simulator examples/scenarios/paper_reference_with_length.txt` |
| `scenarios/skipped_steps.txt` | carriage loses 0.5 mm per cycle; home re-check stops it after two cycles | `python -m seedforge.simulator examples/scenarios/skipped_steps.txt` |
| `recipes/my_lot_A_trial.json` | shape of a material-trial recipe with tension limits (**placeholder values**) | `python -m seedforge.host --check-recipe examples/recipes/my_lot_A_trial.json` |
| `simulated_run_log/` | `carriers.csv` and `trace.csv` from `python -m seedforge.simulator normal --log ...` | open in a spreadsheet; `data_source` says SIMULATION |

Drive the simulator through the host program with synthetic vision:

```bash
python -m seedforge.host --port sim --recipe paper_reference --vision synthetic --log runs/
```

Inspect one synthetic image:

```bash
python -m seedforge.vision demo --out datasets/synthetic
python -m seedforge.vision inspect datasets/synthetic/synthetic_07_gap.png --pitch 5 --turns 7 --width 2.5
```
