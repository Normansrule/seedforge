"""Minimal host-side example for SeedForge R3.

Install pyserial, select the serial port connected to the ESP32/Uno bridge,
and replace the placeholder vision function with the existing RealSense pipeline.
"""

import time
import serial

PORT = "COM5"      # change for your computer
BAUD = 19200


def vision_result():
    """Replace with your existing computer-vision output.

    Return one of: VISION_OK, FAULT_GAP, FAULT_OVERLAP, FAULT_LENGTH, FAULT_CAMERA.
    """
    return "VISION_OK"


with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
    ser.write(b"RESET\n")
    time.sleep(0.5)
    ser.write(b"PITCH=4.084\n")  # development starting value only
    ser.write(b"STEP_US=1500\n")
    ser.write(b"START\n")

    last_hb = 0.0
    while True:
        now = time.monotonic()
        if now - last_hb >= 0.5:
            ser.write(b"HEARTBEAT\n")
            last_hb = now

        line = ser.readline().decode(errors="replace").strip()
        if line:
            print(line)
            if "EVENT:WIND_COMPLETE_WAITING_FOR_VISION" in line:
                result = vision_result()
                ser.write((result + "\n").encode())
            if "EVENT:PART_ACCEPTED" in line:
                break
            if "state=SAFE_STOP" in line:
                raise RuntimeError("Machine entered SAFE_STOP; inspect cause before RESET")
