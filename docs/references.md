# References

## Primary research reference

**Luo, D., Maheshwari, A., Danielescu, A., Li, J., Yang, Y., Tao, Y., Sun, L., Patel, D. K.,
Wang, G., Yang, S., Zhang, T. & Yao, L.** Autonomous self-burying seed carriers for aerial seeding.
*Nature* **614**, 463-470 (2023). <https://doi.org/10.1038/s41586-022-05656-3>

How this repository uses it:

* SOURCE-SUPPORTED values taken from the paper and its supplementary material: a 0.8 mm mandrel,
  a seven-coil body of 2.5 x 0.5 mm ribbon over 35 mm, three tails, tail path lengths, and the
  large whitebark-pine variant dimensions (see [carrier-geometry.md](carrier-geometry.md)).
* RECONSTRUCTED: tail curvature, tip shape and fibre clearance in the reference CAD.
* Not used: no figures, images or text from the paper are reproduced. Renders in this repository
  are original CAD renders.

The paper's authors are **not** authors of SeedForge, have not reviewed it and do not endorse it.
Cite the paper for the carrier science and SeedForge ([CITATION.cff](../CITATION.cff)) for this
manufacturing platform.

## Project history

* EECS 149 group project "eecs149-group3-woodwinder" (UC Berkeley course work), archived in
  [`archive/eecs149-original/`](../archive/eecs149-original/). Course work, not endorsed by the
  university.
* SeedForge R1/R2/R3 packages, archived in [`archive/seedforge-r3-package/`](../archive/seedforge-r3-package/).

## Algorithms

* Bresenham, J. E. Algorithm for computer control of a digital plotter. *IBM Systems Journal*
  **4**(1), 25-30 (1965). <https://doi.org/10.1147/sj.41.0025> - integer synchronisation of the two
  axes.
* Otsu, N. A threshold selection method from gray-level histograms. *IEEE Transactions on Systems,
  Man, and Cybernetics* **9**(1), 62-66 (1979). <https://doi.org/10.1109/TSMC.1979.4310076> -
  silhouette segmentation.
* Euler-Bernoulli beam deflection (standard textbook result) - mandrel stiffness estimate.

## Component documentation

Read the datasheet of the exact part you buy; breakout boards differ.

* Allegro MicroSystems A4988 DMOS microstepping driver datasheet; Pololu A4988 carrier #1182
  (current-limit procedure): <https://www.pololu.com/product/1182>
* Avia Semiconductor HX711 24-bit ADC datasheet; SparkFun HX711 breakout SEN-13879:
  <https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html>
* TDK InvenSense ICM-20948 datasheet; SparkFun breakout SEN-15335:
  <https://www.sparkfun.com/sparkfun-9dof-imu-breakout-icm-20948-qwiic.html>
* NXP PCA9685 16-channel PWM controller datasheet.
* Microchip ATmega328P datasheet (Timer1 CTC mode, port registers).
* Espressif ESP32-C3 technical reference and Seeed Studio XIAO ESP32-C3 wiki (pin-out, strapping
  pins).

## Software used

* CadQuery (parametric CAD, OpenCascade) - <https://github.com/CadQuery/cadquery>
* trimesh (mesh QA) - <https://github.com/mikedh/trimesh>
* OpenCV and NumPy (vision) - <https://opencv.org>, <https://numpy.org>
* Three.js (web viewers) - <https://threejs.org>
* Vite and TypeScript (website build)
* Mermaid (diagrams) - <https://mermaid.js.org>
* Arduino CLI, Arduino AVR core, Espressif Arduino-ESP32 core
* ArduPilot (concept reference for Phase 8 only) - <https://ardupilot.org>
