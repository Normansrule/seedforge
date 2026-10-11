# Security and safety reporting

## What to report

* **Safety defects**: anything in the design, wiring, firmware or documentation that could hurt
  someone (for example a fault that leaves motors powered, a wiring instruction that could short a
  supply, a missing guard).
* **Software security issues**: for example the ESP32-C3 bridge accepting commands from an
  unexpected network client, or secrets committed to the repository.

## How to report

Use GitHub's **private vulnerability reporting** ("Security" tab -> "Report a vulnerability") on
this repository. Please do not open a public issue for something that could hurt people before it
is fixed. Include the commit, the files involved and how to reproduce it.

We aim to acknowledge reports within 7 days. This is a volunteer research project; there is no bug
bounty.

## Design notes relevant to security

* The ESP32-C3 bridge is **not** a safety device. Network and BLE access can start and stop cycles,
  so only enable Wi-Fi (`secrets.h`) on a trusted network, and keep the physical E-stop within reach.
* Wi-Fi credentials live in `firmware/esp32/seedforge_bridge/secrets.h`, which is git-ignored;
  only `secrets.example.h` is committed.
* The archived R3/EECS 149 sketches contain a default access-point password; they are archived for
  provenance and must not be flashed as-is.
