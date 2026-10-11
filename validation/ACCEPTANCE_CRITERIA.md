# Acceptance criteria

One table per gate. A phase is **passed** only when every row has recorded evidence (log files,
worksheet rows, photos) referenced from `status.yaml`. Explanations: [docs/validation.md](../docs/validation.md).

| phase | ID | criterion | measure | evidence |
|---|---|---|---|---|
| 0 | P0.1 | wet and dry width/thickness measured | >= 10 strips per lot, mean and spread | worksheet `material` rows |
| 0 | P0.2 | damage and break tension measured | >= 5 pulls per lot | worksheet + photos |
| 0 | P0.3 | tension band chosen | `SET_TENSION_MAX` well below the lowest damage tension | recipe JSON with provenance |
| 1 | P1.1 | consecutive cycles | >= 20 consecutive commanded cycles on real material, no mechanical jam | `carriers.csv` |
| 1 | P1.2 | turn count | exact on every coil (COMPLETE line = camera = manual count) | `carriers.csv` + photos |
| 1 | P1.3 | no skipped steps | no `SKIPPED_STEPS`; every `HOME_ERROR_MM` <= 0.3 | `trace.csv` |
| 1 | P1.4 | tension | inside the P0.3 band for every cycle; every trip explained | `trace.csv` |
| 1 | P1.5 | stops | E-stop, START-stop, heartbeat loss and end limit each tested and logged | TP-1.3 sheet |
| 1 | P1.6 | vision stops a fault | a deliberately bad coil is rejected (camera or documented manual check) | `carriers.csv` |
| 1 | P1.7 | pitch | measured pitch within the recipe tolerance on >= 3 coils | worksheet C13 |
| 2 | P2.1 | cut + release | 20/20 clamp + cut + demold cycles | `carriers.csv` (`demold_result`) |
| 2 | P2.2 | no damage | no dragging over an undercut, delamination or uncoiling | photos |
| 2 | P2.3 | guard | cutter guard fitted, guard switch tested (if fitted) | TP-2.2 sheet |
| 3 | P3.1 | tail repeatability | >= 20 dried tails; angle, length, curvature within the nest tolerance | measurements |
| 4 | P4.1 | drying record | temperature, humidity, duration logged | environment log |
| 4 | P4.2 | geometry | dried geometry measured; no fixture-induced deformation | measurements |
| 5 | P5.1 | completeness | exactly one seed, exactly three tails, intact tip | inspection log |
| 5 | P5.2 | no glue on active coils | inspection under magnification | photos |
| 5 | P5.3 | handling | survives the defined handling test | test log |
| 5 | P5.4 | viability | seed viability compared with untreated controls before any biological claim | germination test |
| 6 | P6.1 | labelled real set | split by material lot; labels from measurement | `datasets/` |
| 6 | P6.2 | confusion matrix | test split: 0 false accepts on gap/overlap over >= 100 images; false rejects < 10 % | `report.md` |
| 7 | P7.1 | transfer | >= 50 consecutive transfers without drop or collision | transfer log |
| 8 | P8.1 | bench release | cassette release repeatability on the bench, no aircraft | test log |
| 8 | P8.2 | aircraft margin | mass, CG and thrust-margin analysis for a proven aircraft | calculation |
| 8 | P8.3 | permissions | landowner, ecological and aviation permissions in writing | documents |
