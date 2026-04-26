"""
Autonomous Box — ESP32-S3 Firmware (MicroPython)

Pin map (from build instructions):
  GPIO 1  → IN1  (Left Forward)
  GPIO 2  → IN2  (Left Backward)
  GPIO 41 → IN3  (Right Forward)
  GPIO 42 → IN4  (Right Backward)
  GPIO 5  → Sonar TRIG  (optional HC-SR04)
  GPIO 6  → Sonar ECHO  (optional HC-SR04)

Communication: JSON lines over UART0 (USB-C cable to MacBook)
  Baud rate: 115200

Command format  →  {"action": "...", ...}
Response format →  {"ok": true/false, ...}
"""

import machine
import time
import json
import sys

# ── Motor pins ──────────────────────────────────────────────────────────────
IN1 = machine.Pin(1,  machine.Pin.OUT)   # Left  Forward
IN2 = machine.Pin(2,  machine.Pin.OUT)   # Left  Backward
IN3 = machine.Pin(41, machine.Pin.OUT)   # Right Forward
IN4 = machine.Pin(42, machine.Pin.OUT)   # Right Backward

# ── Sonar pins (optional) ───────────────────────────────────────────────────
TRIG = machine.Pin(5, machine.Pin.OUT)
ECHO = machine.Pin(6, machine.Pin.IN)

# ── UART (USB-C serial to Mac) ──────────────────────────────────────────────
uart = machine.UART(0, baudrate=115200, tx=machine.Pin(43), rx=machine.Pin(44))

def all_stop():
    IN1.value(0); IN2.value(0)
    IN3.value(0); IN4.value(0)

def drive(left_fwd, left_bck, right_fwd, right_bck, ms=0):
    IN1.value(left_fwd);  IN2.value(left_bck)
    IN3.value(right_fwd); IN4.value(right_bck)
    if ms > 0:
        time.sleep_ms(ms)
        all_stop()

def sonar_cm():
    """Returns distance in cm from HC-SR04, or -1 on timeout."""
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
    timeout = 30000  # 30 ms max wait
    t_start = time.ticks_us()
    while ECHO.value() == 0:
        if time.ticks_diff(time.ticks_us(), t_start) > timeout:
            return -1
    pulse_start = time.ticks_us()
    while ECHO.value() == 1:
        if time.ticks_diff(time.ticks_us(), pulse_start) > timeout:
            return -1
    pulse_end = time.ticks_us()
    duration = time.ticks_diff(pulse_end, pulse_start)
    return round(duration / 58.0, 1)

def handle(cmd: dict) -> dict:
    action = cmd.get("action", "")
    ms     = int(cmd.get("ms", 0))       # optional duration in milliseconds

    if action == "forward":
        drive(1, 0, 1, 0, ms)
        return {"ok": True}

    elif action == "backward":
        drive(0, 1, 0, 1, ms)
        return {"ok": True}

    elif action == "left":
        # Spin left: right motors forward, left motors backward
        drive(0, 1, 1, 0, ms)
        return {"ok": True}

    elif action == "right":
        # Spin right: left motors forward, right motors backward
        drive(1, 0, 0, 1, ms)
        return {"ok": True}

    elif action == "stop":
        all_stop()
        return {"ok": True}

    elif action == "sonar":
        dist = sonar_cm()
        return {"ok": True, "distance_cm": dist}

    elif action == "ping":
        return {"ok": True, "msg": "pong"}

    else:
        return {"ok": False, "error": f"unknown action: {action}"}

# ── Main loop ────────────────────────────────────────────────────────────────
all_stop()
uart.write(b'{"ok":true,"msg":"box ready"}\n')

buf = b""
while True:
    if uart.any():
        buf += uart.read(uart.any())
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                cmd = json.loads(line)
                resp = handle(cmd)
            except Exception as e:
                resp = {"ok": False, "error": str(e)}
            uart.write((json.dumps(resp) + "\n").encode())
    time.sleep_ms(10)
