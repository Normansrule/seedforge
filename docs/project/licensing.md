# Licensing decision

| kind of work | licence | why |
|---|---|---|
| Software (firmware, Python, tools, tests, website code, CI) | **MIT** | short, permissive, compatible with Arduino/ESP32 libraries and with use in teaching and research code |
| Hardware design files (`hardware/`: CAD source, STEP/STL/3MF/GLB, drawings, wiring, BOM data) | **CERN-OHL-S-2.0** | written for hardware; the strongly reciprocal variant keeps improved machine designs open when they are distributed, which suits a community-built research tool |
| Documentation, renders, diagrams, animations, templates, synthetic dataset | **CC BY-SA 4.0** | attribution plus share-alike for text and media |

The brief suggested MIT or Apache-2.0 for software and CERN-OHL-S or -P for hardware. MIT was chosen
over Apache-2.0 for simplicity (no patent clause is needed for this code); CERN-OHL-S over -P so
that improved machine designs stay open. If you need a different arrangement, open an issue.

## What is excluded

* `archive/eecs149-original/` is group coursework from a UC Berkeley course, copied from a
  repository with no licence. It is kept for provenance only; **no licence is granted** for it here.
  The university does not endorse this project.
* `archive/seedforge-r3-package/` is the supplied input package, kept unchanged for traceability.
* The Nature paper is cited, not copied. No figures are reproduced.
* Names of products and companies in the BOM belong to their owners.

## SPDX

Source files carry `SPDX-License-Identifier` lines where practical. Full texts: `LICENSES/`.
