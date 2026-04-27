"""
Autonomous Box — Mac-side serial controller

Wraps the serial connection to the ESP32 and exposes clean Python methods.
Install dependency:  pip install pyserial

Usage:
    from robot_controller import Robot
    bot = Robot()          # auto-detects port, or pass port="/dev/tty.usbmodem..."
    bot.forward(ms=1000)
    bot.turn_left(ms=500)
    dist = bot.sonar()
    bot.close()
"""

import json
import time
import glob
import serial


def _find_esp32_port() -> str:
    """Best-effort auto-detection of the ESP32 USB serial port on macOS."""
    candidates = (
        glob.glob("/dev/tty.usbmodem*")
        + glob.glob("/dev/tty.SLAB_USBtoUART*")
        + glob.glob("/dev/tty.wchusbserial*")
        + glob.glob("/dev/cu.usbmodem*")
    )
    if not candidates:
        raise RuntimeError(
            "ESP32 not found. Plug in the USB-C cable and try again, "
            "or pass port= explicitly."
        )
    return candidates[0]


class Robot:
    def __init__(self, port: str = None, baud: int = 115200, timeout: float = 15.0):
        port = port or "/dev/cu.usbserial-10"
        self._ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(1.5)          # let ESP32 boot / send its ready message
        self._ser.reset_input_buffer()
        print(f"[Robot] Connected on {port}")

    # ── Low-level send/receive ───────────────────────────────────────────────

    def _send(self, cmd: dict) -> dict:
        payload = (json.dumps(cmd) + "\n").encode()
        self._ser.write(payload)
        raw = self._ser.readline()
        if not raw:
            return {"ok": False, "error": "timeout — no response from ESP32"}
        try:
            return json.loads(raw.decode().strip())
        except json.JSONDecodeError:
            return {"ok": False, "error": f"bad response: {raw!r}"}

    # ── Motion commands ──────────────────────────────────────────────────────

    def forward(self, ms: int = 0, speed: int = 60) -> dict:
        """Move forward. ms=0 means keep going until stop() is called."""
        return self._send({"action": "forward", "ms": ms, "speed": speed})

    def backward(self, ms: int = 0, speed: int = 60) -> dict:
        """Move backward."""
        return self._send({"action": "backward", "ms": ms, "speed": speed})

    def turn_left(self, ms: int = 0, speed: int = 60) -> dict:
        """Spin left in place."""
        return self._send({"action": "left", "ms": ms, "speed": speed})

    def turn_right(self, ms: int = 0, speed: int = 60) -> dict:
        """Spin right in place."""
        return self._send({"action": "right", "ms": ms, "speed": speed})

    def stop(self) -> dict:
        """Stop all motors immediately."""
        return self._send({"action": "stop"})

    # ── Sensor commands ──────────────────────────────────────────────────────

    def sonar(self) -> float:
        """Returns distance in cm from the HC-SR04. Returns -1 on timeout."""
        resp = self._send({"action": "sonar"})
        return resp.get("distance_cm", -1)

    def ping(self) -> bool:
        """Returns True if the ESP32 is alive."""
        resp = self._send({"action": "ping"})
        return resp.get("ok", False)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def close(self):
        self.stop()
        self._ser.close()
        print("[Robot] Disconnected")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
