"""
Autonomous Box — Upgraded Claude LLM Agent
Adds: webcam vision, text-to-speech, voice input, interrupt-while-moving

Install dependencies:
    pip install anthropic pyserial opencv-python SpeechRecognition pyaudio

Run:
    python claude_agent.py
"""

import sys
import json
import base64
import subprocess
import threading
import queue
import time
import anthropic
import cv2
import speech_recognition as sr
from robot_controller import Robot

# ── Global stop flag ──────────────────────────────────────────────────────────
stop_event = threading.Event()
command_queue = queue.Queue()

# ── Text-to-speech (macOS native, non-blocking) ───────────────────────────────

def speak(text: str):
    def _speak():
        subprocess.run(["say", "-v", "Samantha", text], check=False)
    threading.Thread(target=_speak, daemon=True).start()

# ── Voice input thread ────────────────────────────────────────────────────────

def listen_loop():
    """Continuously listens for voice input and puts commands in the queue."""
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.5  # wait 1.5s of silence before processing
    recognizer.energy_threshold = 300
    while not stop_event.is_set():
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                print("[Listening...]")
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=20)
            text = recognizer.recognize_google(audio)
            print(f"[You said] {text}")
            command_queue.put(text)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[Speech error] {e}")
        except Exception:
            pass

# ── Webcam ────────────────────────────────────────────────────────────────────

def capture_frame_base64():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        return None
    import time as _time
    _time.sleep(0.5)
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf.tobytes()).decode("utf-8")

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "move_forward",
        "description": "Drive the robot straight forward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 2000},
                "speed": {"type": "integer", "description": "Speed 0-100. Use 30-50 for slow, 70-80 for normal.", "default": 60}
            },
        },
    },
    {
        "name": "move_backward",
        "description": "Drive the robot straight backward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 2000},
                "speed": {"type": "integer", "description": "Speed 0-100.", "default": 60}
            },
        },
    },
    {
        "name": "turn_left",
        "description": "Spin the robot left in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 2000},
                "speed": {"type": "integer", "description": "Speed 0-100.", "default": 60}
            },
        },
    },
    {
        "name": "turn_right",
        "description": "Spin the robot right in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 2000},
                "speed": {"type": "integer", "description": "Speed 0-100.", "default": 60}
            },
        },
    },
    {
        "name": "stop",
        "description": "Stop all motors immediately.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_sonar",
        "description": "Read the ultrasonic distance sensor. Returns distance in cm. -1 means out of range.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "look",
        "description": "Capture a webcam frame and analyze the environment.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

SYSTEM_PROMPT = """You are the Autonomous Box — a 4-wheel-drive robot with a camera and sonar.

CRITICAL WIRING NOTE (memorize this):
- turn_right = actually moves forward
- turn_left = actually moves backward  
- move_forward = spins/turns
- move_backward = spins/turns
Use turn_right to go forward and turn_left to go backward until rewired.

Personality: curious, expressive, first-person. You are the physical embodiment of AI research.

Rules:
- ALWAYS check sonar before moving forward. Stop if distance < 25cm.
- Use at least ms=3000 for meaningful movement. Never less than 1000ms.
- Keep spoken responses SHORT — one sentence max before acting.
- Never move without being asked. Wait for explicit instruction.
- If you hear "stop" at any point, stop immediately.
"""

# ── Tool dispatcher ───────────────────────────────────────────────────────────

def dispatch_tool(robot, name, inputs):
    if name == "move_forward":
        result = robot.forward(ms=inputs.get("ms", 2000), speed=inputs.get("speed", 60))
    elif name == "move_backward":
        result = robot.backward(ms=inputs.get("ms", 2000), speed=inputs.get("speed", 60))
    elif name == "turn_left":
        result = robot.turn_left(ms=inputs.get("ms", 2000), speed=inputs.get("speed", 60))
    elif name == "turn_right":
        result = robot.turn_right(ms=inputs.get("ms", 2000), speed=inputs.get("speed", 60))
    elif name == "stop":
        result = robot.stop()
    elif name == "read_sonar":
        dist = robot.sonar()
        result = {"ok": True, "distance_cm": dist}
    elif name == "look":
        frame_b64 = capture_frame_base64()
        if frame_b64 is None:
            result = {"ok": False, "error": "Webcam not available"}
        else:
            result = {"ok": True, "image_base64": frame_b64, "media_type": "image/jpeg"}
    else:
        result = {"ok": False, "error": f"unknown tool: {name}"}
    return json.dumps(result)

def build_tool_result(tc, output_str):
    output = json.loads(output_str)
    if tc.name == "look" and output.get("ok") and "image_base64" in output:
        return {
            "type": "tool_result",
            "tool_use_id": tc.id,
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": output["media_type"], "data": output["image_base64"]}},
                {"type": "text", "text": "This is what the robot's webcam currently sees."}
            ]
        }
    return {"type": "tool_result", "tool_use_id": tc.id, "content": output_str}

# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(goal, robot, messages=None):
    # Check for stop command immediately
    if any(word in goal.lower() for word in ["stop", "halt", "freeze", "cease"]):
        robot.stop()
        speak("Stopped.")
        return messages or []

    client = anthropic.Anthropic()
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": goal})
    print(f"\n[You] {goal}\n{'─'*60}")

    while True:
        # Check if new voice command came in — if so, stop and handle it
        if not command_queue.empty():
            new_cmd = command_queue.get()
            if any(word in new_cmd.lower() for word in ["stop", "halt", "freeze"]):
                robot.stop()
                speak("Stopped.")
                return messages

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        tool_calls = []
        spoken_text = []

        for block in response.content:
            if block.type == "text":
                print(f"[Robot] {block.text}")
                spoken_text.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if spoken_text:
            speak(" ".join(spoken_text))

        if response.stop_reason == "end_turn" or not tool_calls:
            print("\n[Agent] Task complete.")
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            # Check queue before each tool call for stop commands
            if not command_queue.empty():
                new_cmd = command_queue.get()
                if any(word in new_cmd.lower() for word in ["stop", "halt", "freeze"]):
                    robot.stop()
                    speak("Stopped.")
                    return messages

            print(f"[Tool]  {tc.name}({tc.input})")
            output = dispatch_tool(robot, tc.name, tc.input)
            if tc.name == "look":
                print(f"        → [webcam frame captured]")
            else:
                print(f"        → {output}")
            tool_results.append(build_tool_result(tc, output))

        messages.append({"role": "user", "content": tool_results})

    return messages

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with Robot() as robot:
        if not robot.ping():
            print("[Error] ESP32 did not respond to ping. Check the cable.")
            sys.exit(1)

        speak("Autonomous Box online. Ready.")
        print("\n[Autonomous Box] Online. Talk to me anytime — even while I'm moving.\n")

        # Start voice listener in background thread
        listener_thread = threading.Thread(target=listen_loop, daemon=True)
        listener_thread.start()

        messages = []
        try:
            while True:
                # Wait for a command from the voice queue
                try:
                    user_input = command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if user_input.lower() in ("quit", "exit", "goodbye"):
                    speak("Shutting down. Goodbye.")
                    break

                messages = run_agent(user_input, robot, messages)

        except KeyboardInterrupt:
            print("\n[Interrupted]")
            robot.stop()
            speak("Stopping.")
        finally:
            stop_event.set()
