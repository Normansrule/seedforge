# SeedForge R3 Wiring Quick Reference

This is the simplified development wiring. The detailed point-to-point schedule remains in `wiring/connection_table.csv`.

## Power

`65 W USB-C PD supply -> USB-C PD trigger (20 V) -> fused input`

From the fused input:

`20 V -> 12 V buck -> E-stop-switched 12 V actuator rail -> A4988 VMOT x2`

`12 V -> 5 V buck -> PCA9685 V+ / servos / low-voltage auxiliaries`

Logic during development:

`PC/USB -> Arduino Uno USB`

`PC/USB or 5 V USB supply -> ESP32-C3 USB-C`

All logic and actuator returns meet at one star ground. Do not parallel multiple positive USB supplies.

## A4988 - rotation driver

- VMOT -> switched 12 V actuator rail
- GND next to VMOT -> actuator ground
- VDD -> Uno 5 V
- logic GND -> Uno GND
- STEP -> Uno D2
- DIR -> Uno D3
- ENABLE -> Uno D6
- RESET and SLEEP -> tied together and pulled to VDD
- MS1/MS2/MS3 -> set for the selected microstep mode; for 1/16 on A4988 they are normally HIGH/HIGH/HIGH
- motor A1/A2/B1/B2 -> keyed 4-pin motor connector
- place at least 100 uF electrolytic close to VMOT/GND

Set current limit for the specific A4988 board and motor before mechanical loading. Rsense values vary by module, so do not use one universal Vref number.

## A4988 - linear driver

Same as above except:
- STEP -> Uno D4
- DIR -> Uno D5
- ENABLE -> shared Uno D6

## Uno core inputs

- D7 -> START button to GND, INPUT_PULLUP
- D8 -> E-stop feedback, normally closed to GND, INPUT_PULLUP; open circuit = unsafe
- D9 -> linear HOME switch, NC to GND
- D10 -> linear END switch, NC to GND
- D11 -> HX711 DOUT
- D12 -> HX711 SCK
- A0 -> optional dancer potentiometer, 0-5 V only
- A4/A5 -> I2C SDA/SCL for ICM-20948 and optional PCA9685/MCP23017

## Uno <-> ESP32-C3 link

Recommended during development:
- Uno A1 configured as SoftwareSerial RX <- ESP32 TX, direct 3.3 V logic
- Uno A2 configured as SoftwareSerial TX -> 1 kohm resistor -> ESP32 RX node; 2 kohm from ESP32 RX node to GND. This divides 5 V Uno TX to about 3.3 V.
- common GND required

Do not drive an ESP32 input directly from a 5 V Uno output.

## ESP32-C3 responsibilities

- BLE/Wi-Fi bridge to host
- 2.2-inch ILI9341 display
- optional coarse ultrasonic sensor through appropriate 3.3 V-safe interface
- operator status and non-safety UI

The Uno must still stop safely if the ESP32 disappears.

## Servo controller

PCA9685:
- VCC -> controller logic voltage appropriate to your board/module
- GND -> common ground
- SDA/SCL -> I2C
- V+ -> separate 5 V servo rail
- CH0 clamp
- CH1 cutter actuator
- CH2 tail sweep
- CH3 tail clamp
- CH4 transfer gripper
- CH5 transfer Z

Do not power several servos from the Uno 5 V pin.

## Slow auxiliary steppers

MCP23017 outputs drive ULN2003 boards for 28BYJ-48 motors. These are appropriate for slow seed indexing and syringe motion, not for synchronized winding.

## Motor wiring check

Before connecting any stepper:
1. use a multimeter to identify the two coil pairs;
2. connect one pair to A1/A2 and the other to B1/B2;
3. power off before changing motor wiring;
4. never unplug a stepper from a powered A4988.
