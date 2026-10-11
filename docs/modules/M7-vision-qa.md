# M7 - Computer-vision QA

**Build phase:** 6  |  **Status:** core camera in Phase 1; software tested on synthetic images only

## 1. Purpose

Measure the coil deterministically and stop the machine on a defect: body length, turn count, pitch, gap, overlap, gross deformation (later: tails, tip, seed).

## 2. Inputs

* back-lit overhead image of the coil
* recipe thresholds and calibrated px/mm

## 3. Outputs

* VISION_OK / FAULT_GAP / FAULT_OVERLAP / FAULT_LENGTH / FAULT_CAMERA
* LENGTH_MM
* annotated QA image

## 4. Printed components

* W17 mast foot
* W18 camera arm (board camera on 4 x M2)

## 5. Purchased components

* 38 x 38 mm USB board camera, manual-focus M12 lens (about 6 mm focal length), M2 holes
* 5 V white LED strip + printed diffuser as back-light
* plywood mast strip cut from the base offcut

## 6. Electronics

* camera on the host; only events go to the controller

## 7. Software responsibility

* seedforge.vision: Otsu segmentation, PCA alignment, edge-notch spacing = local pitch, bulge test separates overlap from gap
* HEARTBEAT every 500 ms; the Uno stops if it is missing for 3 s in WIND or VERIFY

## 8. Calibration method

* px/mm from a target in the coil plane
* thresholds from a labelled set of real good and bad coils

## 9. Acceptance criteria

* labelled real-image validation set
* documented true/false accept/reject counts
* heartbeat fail-safe demonstrated

## 10. Known risks

* synthetic images were designed alongside the pipeline: their 16/16 score is a software test, not validation
* overlap is inferred, not seen, in a silhouette

## 11. CAD preview

Interactive: the website module explorer loads `phase1_core_cell.glb`. Files: `hardware/cad/glb/phase1_core_cell.glb`, STEP/STL/3MF of every part in `hardware/cad/`.

## 12. Assembly figure

![Computer-vision QA](../images/vision_station.png)

Figures are CAD renders, not photographs, and are not evidence that the module works.
