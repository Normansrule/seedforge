## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Evidence

- [ ] No evidence level was raised, **or** the data that justifies it is included (logs, photos, measurements, recipe, commit)
- [ ] Simulated or synthetic results are labelled as such

## Checks

- [ ] `python -m pytest` passes
- [ ] `make -C tests/firmware` passes (if firmware changed)
- [ ] `sf_controller.cpp` and `software/seedforge/simulator/core.py` changed together (if controller behaviour changed)
- [ ] CAD changed in source, then `python tools/build_cad.py` was run (no hand-edited meshes)
- [ ] Generated files rebuilt (BOM, wiring, module docs) if their sources changed
- [ ] `python tools/check_links.py` passes
- [ ] No unverified supplier links, no third-party material we cannot license, no figures from the paper

## Safety

- [ ] Does not weaken the hardware E-stop, limits or tension trip, and does not add chemical processing or seed-release automation
