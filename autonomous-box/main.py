"""
Autonomous Box — ESP32-S3 Firmware (MicroPython)
PWM speed control version — supports variable motor speed 0-100%

Pin map:
  GPIO 1  -> IN1  (Left Forward)
  GPIO 2  -> IN2  (Left Backward)
  GPIO 41 -> IN3  (Right Forward)
  GPIO 42 -> IN4  (Right Backward)
  GPIO 5  -> Sonar TRIG (optional)
  GPIO 6  -> Sonar ECHO (optional)
"""

import machine
import time
import json
import sys

# ── PWM Motor setup ──────────────────────────────────────────────────────────
FREQ = 1000  # 1kHz PWM frequency

pwm1 = machine.PWM(machine.Pin(1),  freq=FREQ, duty=0)  # Left Forward
pwm2 = machine.PWM(machine.Pin(2),  freq=FREQ, duty=0)  # Left Backward
pwm3 = machine.PWM(machine.Pin(41), freq=FREQ, duty=0)  # Right Forward
pwm4 = machine.PWM(machine.Pin(42), freq=FREQ, duty=0)  # Right Backward

# ── Sonar pins ───────────────────────────────────────────────────────────────
TRIG = machine.Pin(5, machine.Pin.OUT)
ECHO = machine.Pin(6, machine.Pin.IN)

def speed_to_duty(speed: int) -> int:
    """Convert speed 0-100 to PWM duty cycle 0-1023."""
    return int((speed / 100) * 1023)

def all_stop():
    pwm1.duty(0); pwm2.duty(0)
    pwm3.duty(0); pwm4.duty(0)

def drive(l_fwd, l_bck, r_fwd, r_bck, speed=80, ms=0):
    """Drive motors with given direction and speed (0-100%)."""
    d = speed_to_duty(speed)
    pwm1.duty(d if l_fwd else 0)
    pwm2.duty(d if l_bck else 0)
    pwm3.duty(d if r_fwd else 0)
    pwm4.duty(d if r_bck else 0)
    if ms > 0:
        time.sleep_ms(ms)
        all_stop()

def sonar_cm():
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
    timeout = 30000
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

def send(data: dict):
    sys.stdout.write(json.dumps(data) + "\n")

def handle(cmd: dict) -> dict:
    action = cmd.get("action", "")
    ms = int(cmd.get("ms", 0))
    speed = int(cmd.get("speed", 80))  # default 80% speed

    if action == "forward":
        drive(1, 0, 1, 0, speed=speed, ms=ms)
        return {"ok": True}
    elif action == "backward":
        drive(0, 1, 0, 1, speed=speed, ms=ms)
        return {"ok": True}
    elif action == "left":
        drive(0, 1, 1, 0, speed=speed, ms=ms)
        return {"ok": True}
    elif action == "right":
        drive(1, 0, 0, 1, speed=speed, ms=ms)
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
        return {"ok": False, "error": "unknown action: " + action}

# ── Main loop ────────────────────────────────────────────────────────────────
all_stop()
send({"ok": True, "msg": "box ready"})

buf = ""
while True:
    try:
        char = sys.stdin.read(1)
        if char:
            if char == "\n":
                line = buf.strip()
                buf = ""
                if line:
                    try:
                        cmd = json.loads(line)
                        resp = handle(cmd)
                    except Exception as e:
                        resp = {"ok": False, "error": str(e)}
                    send(resp)
            else:
                buf += char
    except Exception:
        pass
    time.sleep_ms(5)
