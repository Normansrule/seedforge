# Printable parts checklist

## test
- Z01 `Z01_fit_calibration_coupon` — qty 1 — PETG — 110.0 x 55.0 x 5.0 mm. Hole sizes for M2/M3/M4/M5, 8 mm rod and LM8UU; channel widths for wet veneer. Print before the rest of the system.

## common
- C01 `C01_module_base_160x120` — qty 7 — PETG — 160.0 x 120.0 x 6.0 mm. Common 25 mm M3 grid and four M5 slots. Bolt modules to plywood or 2020 rails.
- C02 `C02_cable_clip_dual` — qty 10 — PETG — 28.0 x 16.0 x 12.0 mm. Two small cable channels; use zip ties for strain relief.
- C03 `C03_electronics_box` — qty 1 — PETG — 170.0 x 110.0 x 42.0 mm. Holds Uno, ESP32 bridge, A4988s, DC modules, terminal blocks. Keep motor power and logic wiring separated.
- C04 `C04_electronics_vented_lid` — qty 1 — PETG — 170.0 x 110.0 x 3.0 mm. Ventilated lid; use M3 screws.
- C05 `C05_ili9341_bezel` — qty 1 — PETG — 84.0 x 64.0 x 5.0 mm. Generic 2.2 inch ILI9341 bezel. Verify your PCB outline before final print.

## M1 feed
- F01 `F01_spool_stand_left` — qty 1 — PETG — 70.0 x 36.0 x 86.0 mm. Pair supports a 5 mm axle with 608 bearings; 120 mm maximum spool diameter.
- F02 `F02_spool_stand_right` — qty 1 — PETG — 70.0 x 36.0 x 86.0 mm. Pair supports a 5 mm axle with 608 bearings; 120 mm maximum spool diameter.
- F03 `F03_spool_hub` — qty 2 — PETG — 62.0 x 62.0 x 18.0 mm. Two hubs clamp the veneer reel on 5 mm axle. Add felt washers for passive drag.
- F04 `F04_dancer_arm` — qty 1 — PETG — 82.0 x 14.0 x 6.0 mm. Spring-loaded dancer arm; potentiometer or hall sensor may track position.
- F05 `F05_dancer_roller` — qty 2 — PETG — 30.0 x 30.0 x 10.0 mm. Use M3 shoulder screw or smooth axle; optionally sleeve with silicone tube.
- F06 `F06_veneer_guide_45deg_lower` — qty 1 — PETG+PTFE — 55.0 x 28.0 x 8.0 mm. 4.6 x 1.2 mm smooth guide channel. Rotate entire bracket to calibrated winding angle.
- F07 `F07_veneer_guide_lid` — qty 1 — PETG — 55.0 x 28.0 x 2.5 mm. Light lid for F06; M2 screws, do not pinch strip.

## M2 winder
- W01 `W01_nema17_rotation_mount` — qty 1 — PETG — 66.0 x 66.0 x 66.0 mm. NEMA17 face mount; use purchased flexible coupler + small collet/pin vise for 0.8 mm mandrel.
- W02 `W02_608_mandrel_support` — qty 1 — PETG — 56.0 x 32.0 x 42.0 mm. 608 bearing support for driven chuck/shaft; mandrel itself is metal, not printed.
- W03 `W03_lm8uu_linear_carriage` — qty 1 — PETG — 90.0 x 70.0 x 30.0 mm. Two 15.4 mm LM8UU bores, 56 mm apart. Clamp bearings with zip ties through slots.
- W04 `W04_t8_nut_carrier` — qty 1 — PETG — 50.0 x 42.0 x 28.0 mm. Fits common flange T8 anti-backlash nut. Confirm your nut hole pattern; ream if needed.
- W05 `W05_mandrel_end_guide` — qty 1 — PETG — 42.0 x 36.0 x 40.0 mm. 2.2 mm bore accepts a short brass/PTFE guide tube around the steel mandrel.
- W06 `W06_camera_tilt_mount` — qty 1 — PETG — 58.0 x 42.0 x 40.0 mm. Adjustable RealSense/USB camera adapter mount; add camera-specific plate with M3 slots.
- W07 `W07_micro_release_clamp_lower` — qty 1 — PETG+silicone — 34.0 x 12.0 x 26.0 mm. Split demold collar. Tune the silicone-lined opening to the measured wet coil OD; closes lightly while mandrel retracts.
- W08 `W08_micro_release_clamp_upper` — qty 1 — PETG+silicone — 34.0 x 12.0 x 26.0 mm. Mate W07. This is a fit-test mechanism; wet demolding must be validated before unattended operation.

## M3 clamp-cut
- X01 `X01_sg90_clamp_mount` — qty 1 — PETG — 68.0 x 44.0 x 32.0 mm. SG90/MG90S-class clamp bracket; verify exact servo body dimensions.
- X02 `X02_soft_clamp_jaw` — qty 2 — PETG+silicone — 34.0 x 13.0 x 12.0 mm. Bond 1 mm silicone pad to jaw. Clamp sacrificial tail/handling tab, not active coils.
- X03 `X03_guarded_shear_mount` — qty 1 — PETG — 88.0 x 58.0 x 41.0 mm. Universal mount for purchased spring-return micro shear. Do not print the blade.
- X04 `X04_cutter_guard` — qty 1 — PETG prototype / polycarbonate final — 96.0 x 66.0 x 44.0 mm. Bench guard shell. Production guard should be transparent impact-rated polycarbonate with interlock.

## M4 tail former
- T01 `T01_tail_former_left` — qty 2 — PETG — 23.8 x 44.0 x 8.8 mm. Split wet-forming mandrel, 14 mm radius, 4.8 mm channel. Experimental geometry.
- T02 `T02_tail_former_right` — qty 2 — PETG — 23.8 x 44.0 x 8.8 mm. Mate with T01. Split enables wet release without dragging over an undercut.
- T03 `T03_tail_sweep_shoe` — qty 1 — PETG+PTFE — 43.6 x 31.0 x 5.0 mm. Servo-driven smooth sweep shoe. Line strip-contact surface with PTFE tape.
- T04 `T04_tail_blank_clamp` — qty 2 — PETG+silicone — 46.0 x 22.0 x 24.0 mm. Light clamp for auxiliary tail blank during forming.

## M5 seed+glue
- S01 `S01_seed_hopper` — qty 1 — PETG — 95.0 x 95.0 x 98.0 mm. Species-specific low-cost gravity hopper. Use only dry seeds; pocket disk below throat meters one seed.
- S02 `S02_seed_singulator_disk_6mm` — qty 1 — PETG — 72.0 x 72.0 x 5.0 mm. Six 6.8 mm pockets over 180 degrees for a 28BYJ-48 indexing mechanism. Regenerate pocket size per seed species.
- S03 `S03_28byj_seed_indexer_mount` — qty 1 — PETG — 68.0 x 56.0 x 42.0 mm. Mounts 28BYJ-48 below singulator disk; use metal M3 standoffs if needed.
- S04 `S04_three_tail_assembly_nest` — qty 1 — PETG+silicone — 116.0 x 116.0 x 8.0 mm. Three 120 degree tail channels around central tip cavity. Use soft inserts where body contacts fixture.
- S05 `S05_10ml_syringe_holder` — qty 1 — PETG — 72.0 x 52.0 x 28.0 mm. Nominal 20-21 mm syringe barrel. Measure syringe before final print.
- S06 `S06_syringe_plunger_carriage` — qty 1 — PETG — 48.0 x 30.0 x 16.0 mm. M5 threaded-rod plunger carriage driven by 28BYJ-48. Add current/time limit to prevent overpressure.
- S07 `S07_tip_mold_half_A` — qty 2 — PETG mold master / silicone working insert — 72.0 x 48.0 x 14.0 mm. Two identical mold masters; clamp face-to-face around the seed/tail junction. Validate paste, release and seed viability; do not heat live seed.
- S08 `S08_tip_mold_half_B` — qty 2 — PETG mold master / silicone working insert — 72.0 x 48.0 x 14.0 mm. Two identical mold masters; clamp face-to-face around the seed/tail junction. Validate paste, release and seed viability; do not heat live seed.

## M6 dry+QA
- Q01 `Q01_free_dry_tray` — qty 4 — PETG+PTFE liner — 160.0 x 120.0 x 10.0 mm. Free-dry tray: no clamps on wet wood. Use PTFE/silicone mesh liner and room-temperature airflow.
- Q02 `Q02_120mm_usb_fan_bracket` — qty 1 — PETG — 130.0 x 28.0 x 30.0 mm. Holds a standard 120 mm USB fan above/beside trays. No heater required for R1.
- Q03 `Q03_camera_led_ring_plate` — qty 1 — PETG — 78.0 x 62.0 x 6.0 mm. Camera/LED ring plate for consistent defect-imaging illumination. Adapt center aperture to camera lens.

## M7 output
- O01 `O01_finished_seedpod_tray_12` — qty 2 — PETG — 160.0 x 120.0 x 14.0 mm. Twelve isolated finished-carrier nests. Increase pocket diameter after measuring dry carrier envelope.

## M8 transfer
- R01 `R01_gantry_tool_plate` — qty 1 — PETG — 80.0 x 60.0 x 6.0 mm. Universal plate for low-cost XY gantry or recycled 3D-printer carriage.
- R02 `R02_sg90_gripper_body` — qty 1 — PETG — 64.0 x 42.0 x 24.0 mm. SG90/MG90S body for transfer gripper. Grip only inactive tab/fixture, never squeeze active coil.
- R03 `R03_soft_gripper_finger` — qty 2 — PETG+silicone — 58.0 x 12.0 x 18.0 mm. Pair of padded fingers for inactive handling tab or transfer fixture.
- R04 `R04_vwheel_or_mgn12_carriage_adapter` — qty 1 — PETG — 72.0 x 56.0 x 8.0 mm. Generic adapter to a recycled Ender-style V-wheel carriage or MGN12 block.
- R05 `R05_gt2_nema17_corner_mount` — qty 2 — PETG — 70.0 x 46.0 x 64.0 mm. Corner motor mount for optional XY transfer gantry. Use 2020 extrusion and GT2 belt; two motors if no donor printer.
- R06 `R06_gt2_idler_corner_mount` — qty 2 — PETG — 58.0 x 44.0 x 38.0 mm. Adjustable idler mount for 5 mm bore GT2 idler. Tighten only enough to remove belt slack.
- R07 `R07_xy_tool_carriage` — qty 1 — PETG — 86.0 x 64.0 x 8.0 mm. Tool carriage accepts R01. Adapt to V-wheel or MGN12 donor hardware.
- R08 `R08_z_lift_servo_mount` — qty 1 — PETG — 54.0 x 36.0 x 40.0 mm. SG90/MG90S Z-lift mount for approximately 15-20 mm pickup travel. Keep end effector light.

## drone payload
- D01 `D01_four_cell_payload_cassette` — qty 1 — PETG — 150.0 x 150.0 x 78.0 mm. Four isolated cells prevent tail entanglement. Payload only: use a purchased, flight-tested quadcopter frame.
- D02 `D02_single_drop_door` — qty 4 — PETG — 66.0 x 66.0 x 5.0 mm. One door per cell. Use 3 mm metal hinge pin and retained metal servo linkage; bench-test fail-closed latch.
- D03 `D03_payload_servo_mount` — qty 4 — PETG — 44.0 x 32.0 x 32.0 mm. SG90/MG90S mount outside cassette walls.
- D04 `D04_payload_rail_adapter` — qty 1 — PETG prototype — 150.0 x 100.0 x 4.0 mm. Universal slotted payload plate. Do not use as motor/arm structure. Verify CG and landing gear clearance.
- D05 `D05_pi_zero2w_companion_plate` — qty 1 — PETG — 80.0 x 52.0 x 3.0 mm. Pi Zero 2 W / small companion plate. Use Pi 5 only if heavier onboard vision is needed.
- D06 `D06_downward_camera_mount` — qty 1 — PETG — 52.0 x 40.0 x 32.0 mm. Downward camera mount with lens opening; angle/height must be calibrated to ground sampling distance.
