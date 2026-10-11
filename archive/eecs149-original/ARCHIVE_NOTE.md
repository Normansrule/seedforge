# EECS 149 original code (archived)

Source: the group course repository `N0rmansrule/eecs149-group3-woodwinder` ("Working towards
automating the manufacturing of small seed harnesses for reforestation efforts") plus four local
sketches (`local-sketches/`). Its own `README.md` is kept unchanged next to this note.

* Group coursework from UC Berkeley EECS 149. Archived for provenance. **No licence is granted** for
  this folder by this repository, and the university does not endorse SeedForge.
* Duplicates between the course repository and the R3 package were removed after byte comparison;
  one copy of each file remains.
* Known issues (why it is superseded): stepping from `loop()` with timing polls, `EMERGENCY_STOP`
  ignored while paused, no homing, no tension sensing, different pin map. `local-sketches/ESP_CAM.ino`
  contains a default access-point password; do not flash it.

Replacement: `firmware/arduino/seedforge_core`, `firmware/esp32/seedforge_bridge`, `software/seedforge`.
