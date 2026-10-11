# Contributing to SeedForge

Thanks for helping. SeedForge is a research prototype, so the most valuable contributions are
**measured results** and **honest corrections**, not features.

## Most wanted

1. **Phase-0 material data**: wet/dry width and thickness, damage and break tension, for named
   veneer species and preparation (no chemical procedures, see below).
2. **Phase-1 build reports**: what printed, what fitted, what did not, measured mandrel deflection,
   home repeatability, turn-count accuracy, 20-cycle results. Use
   [`validation/RUN_LOG_TEMPLATE.csv`](validation/RUN_LOG_TEMPLATE.csv) and
   [`validation/CALIBRATION_WORKSHEET.csv`](validation/CALIBRATION_WORKSHEET.csv).
3. **Labelled real coil images** for the vision set ([datasets/README.md](datasets/README.md)).
4. Fixes to CAD, firmware, host software or documentation.

## Evidence rules

Every claim has an evidence level ([docs/validation.md](docs/validation.md#evidence-levels)).
A pull request that raises a status (for example from *CAD-VALIDATED* to *PHYSICALLY TESTED*) must
include the data: logs, photos, measurements, the recipe and the commit you built from. Do not
upgrade a status because something "worked once".

## Ground rules

* Do not add chemical wood-processing procedures, automation of chemical dosing, or anything that
  encourages releasing seeds without permission ([docs/safety.md](docs/safety.md)).
* Do not add supplier links you have not checked, or third-party CAD/images you cannot license
  under this repository's licences ([LICENSE](LICENSE)).
* Do not copy figures from the Nature paper. Cite it.
* Safety functions stay in hardware: never replace the E-stop power contact with software.

## Development

```bash
python -m pip install -e ".[dev]"   # Python package + test tools
python -m pytest                    # Python tests
make -C tests/firmware              # firmware core tests on the host (g++, ASan/UBSan)
python tools/build_cad.py --fast    # regenerate CAD exports without the interference sweep
cd website && npm ci && npm run dev # website
```

* CAD: edit the Python source in `hardware/cad/source/` (or the STEP file for R3 parts that have
  no generator), then run `python tools/build_cad.py`. Never hand-edit an STL.
* Firmware: keep `software/seedforge/simulator/core.py` in step with `sf_controller.cpp`;
  `tests/host/test_sim_parity.py` fails if the two disagree.
* BOM, wiring and module docs are generated: edit `tools/bom_source.py`,
  `tools/build_wiring.py` or `tools/modules_source.py` and rebuild.

## Pull requests

Small, focused PRs with a clear description. Fill in the PR template checklist. By contributing you
agree that your contribution is licensed under the licence of the directory it lands in.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
