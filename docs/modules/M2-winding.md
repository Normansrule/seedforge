# M2 - Synchronized winding

**Build phase:** 1  |  **Status:** core - designed, CAD-checked; firmware compile-tested + unit-tested

## 1. Purpose

Rotate the 0.8 mm mandrel while translating the guide so the strip forms a helix with the recipe pitch and exact turn count.

## 2. Inputs

* strip at controlled tension (M1)
* recipe: pitch, turns, sacrificial turns, rate, acceleration, start position

## 3. Outputs

* wet coil on the mandrel
* TURN events, COMPLETE line with rotation and linear step totals

## 4. Printed components

* W01 NEMA17 rotation mount (R3, defines the 37.0 mm axis)
* W05 end guide (R3) + W13 11 mm riser
* W09 linear motor end block
* W10 linear idler end block
* W11 LM8UU traverse carriage (replaces W03/W04)
* W12 angle-adjustable guide arm (+-60 deg)
* W14 limit-switch rod clamps x2
* W15/W16 NEMA17 body clamps (NEMA17 face holes are M3, so motors are clamped by the body with M2 screws)

## 5. Purchased components

* 2 x NEMA17
* 2 x A4988 (1/16 microstep)
* mini drill chuck on 5 mm arbor
* 0.8 mm steel mandrels (cut to 100 mm)
* PTFE bushing tube
* T8x8 lead screw 250 mm + flange nut
* 2 x 8 mm rod 250 mm
* 2 x LM8UU
* 5-8 mm coupler
* 608ZZ
* 2 x KW12 microswitch

## 6. Electronics

* A4988 rotation STEP/DIR -> D2/D3; linear STEP/DIR -> D4/D5; shared ENABLE D6 (active low, 10 k pull-up)
* home/end NC switches -> D9/D10
* 12 V switched actuator rail with 100 uF at each VMOT

## 7. Software responsibility

* Timer1 interrupt Bresenham: the axis with more steps is master; the other never steps more than once per tick; totals exact
* trapezoidal ramp; 8 kHz master ceiling
* homing before every cycle; home re-check flags skipped steps (2 strikes -> SAFE_STOP)

## 8. Calibration method

* linear: jog 50 mm and measure with calipers -> steps/mm
* rotation: mark the chuck, command 10 turns, count
* pitch: wind a test coil, measure length/turns on the mandrel
* set A4988 current (Vref) before connecting motors

## 9. Acceptance criteria

* >= 20 consecutive commanded cycles
* exact commanded turn count (vision + COMPLETE line)
* no skipped steps (home error < 0.3 mm)
* pitch repeatability within the tolerance the functional tests accept

## 10. Known risks

* 0.8 mm mandrel deflects ~1 mm at 0.5 N over 90 mm
* mini chuck runout unknown - measure
* F06 channel position is inferred - measure before relying on the 37.65 mm strip height
* carriage window depends on guide angle (+60 deg: x 85-150 mm only)

## 11. CAD preview

Interactive: the website module explorer loads `phase1_core_cell.glb`. Files: `hardware/cad/glb/phase1_core_cell.glb`, STEP/STL/3MF of every part in `hardware/cad/`.

## 12. Assembly figure

![Synchronized winding](../images/winder_isometric.png)

Figures are CAD renders, not photographs, and are not evidence that the module works.
