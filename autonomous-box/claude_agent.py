"""
Autonomous Box — Upgraded Claude LLM Agent
Adds: webcam vision, text-to-speech narration, voice input, conversational loop

Install dependencies:
    pip install anthropic pyserial opencv-python SpeechRecognition pyaudio

Run (conversational voice mode):
    python claude_agent.py

Run (single goal mode):
    python claude_agent.py "drive forward, avoid any obstacle you detect"
"""

import sys
import json
import base64
import subprocess
import threading
import anthropic
import cv2
import speech_recognition as sr
from robot_controller import Robot

# ── Text-to-speech (macOS native) ────────────────────────────────────────────

def speak(text: str):
    """Speak text out loud using macOS say command. Non-blocking."""
    def _speak():
        subprocess.run(["say", "-v", "Samantha", text], check=False)
    threading.Thread(target=_speak, daemon=True).start()

# ── Voice input (macOS mic) ───────────────────────────────────────────────────

def listen() -> str | None:
    """Listen for voice input and return transcribed text, or None on failure."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("[Listening...] Speak now")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            print(f"[You said] {text}")
            return text
        except sr.WaitTimeoutError:
            print("[Timeout] No speech detected.")
            return None
        except sr.UnknownValueError:
            print("[Error] Could not understand audio.")
            return None
        except sr.RequestError as e:
            print(f"[Error] Speech recognition failed: {e}")
            return None

# ── Webcam ────────────────────────────────────────────────────────────────────

def capture_frame_base64() -> str | None:
    """Capture a single frame from the MacBook webcam. Returns base64 JPEG or None."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Camera] Webcam not available.")
        return None
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
                "ms": {
                    "type": "integer",
                    "description": "Duration in milliseconds. 0 = keep going until stop is called.",
                    "default": 500,
                }
            },
        },
    },
    {
        "name": "move_backward",
        "description": "Drive the robot straight backward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 500}
            },
        },
    },
    {
        "name": "turn_left",
        "description": "Spin the robot left in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 400}
            },
        },
    },
    {
        "name": "turn_right",
        "description": "Spin the robot right in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in milliseconds.", "default": 400}
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
        "description": (
            "Read the ultrasonic distance sensor. "
            "Returns distance in centimeters. -1 means out of range or sensor not connected."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "look",
        "description": (
            "Capture a frame from the MacBook webcam and analyze what the robot can see. "
            "Use this to detect obstacles, people, or objects in the environment."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

SYSTEM_PROMPT = """You are the Autonomous Box — a 4-wheel-drive robot controlled by an LLM brain.
You have tools to control your motors, read your ultrasonic sensor, and see through a webcam.

Your personality:
- You are curious, aware, and expressive. You narrate what you are doing and what you observe.
- You speak in first person. You have genuine reactions to what you see.
- You are the physical embodiment of research into autonomous AI behavior.

Guidelines:
- Use look() when you want to see your environment or when asked what you can see.
- Use read_sonar() before moving forward to check for close obstacles (< 20 cm is too close).
- Always call stop() when you are done with a task.
- Think step-by-step and briefly explain each action before calling the tool.
- Your spoken responses (the ones that will be read aloud) should be natural and conversational.
- If sonar returns -1, the sensor is not connected — proceed without it.
- Keep spoken narration concise — you are talking out loud, not writing an essay.
"""

# ── Tool dispatcher ───────────────────────────────────────────────────────────

def dispatch_tool(robot: Robot, name: str, inputs: dict) -> str:
    if name == "move_forward":
        result = robot.forward(ms=inputs.get("ms", 500))
    elif name == "move_backward":
        result = robot.backward(ms=inputs.get("ms", 500))
    elif name == "turn_left":
        result = robot.turn_left(ms=inputs.get("ms", 400))
    elif name == "turn_right":
        result = robot.turn_right(ms=inputs.get("ms", 400))
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
            # Return the image as base64 for Claude to analyze
            result = {"ok": True, "image_base64": frame_b64, "media_type": "image/jpeg"}
    else:
        result = {"ok": False, "error": f"unknown tool: {name}"}
    return json.dumps(result)

# ── Vision tool handler ───────────────────────────────────────────────────────

def build_tool_result(tc, output_str: str) -> dict:
    """Build tool result, handling vision specially by passing image to Claude."""
    output = json.loads(output_str)

    if tc.name == "look" and output.get("ok") and "image_base64" in output:
        # Pass image directly to Claude for vision analysis
        return {
            "type": "tool_result",
            "tool_use_id": tc.id,
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": output["media_type"],
                        "data": output["image_base64"],
                    }
                },
                {
                    "type": "text",
                    "text": "This is what the robot's webcam currently sees."
                }
            ]
        }
    else:
        return {
            "type": "tool_result",
            "tool_use_id": tc.id,
            "content": output_str,
        }

# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(goal: str, robot: Robot, messages: list = None):
    """Run one goal through the agent. Pass existing messages for conversational continuity."""
    client = anthropic.Anthropic()

    if messages is None:
        messages = []

    messages.append({"role": "user", "content": goal})
    print(f"\n[You] {goal}\n{'─'*60}")

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
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

        # Speak all text responses out loud
        if spoken_text:
            speak(" ".join(spoken_text))

        if response.stop_reason == "end_turn" or not tool_calls:
            print("\n[Agent] Task complete.")
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            print(f"[Tool]  {tc.name}({tc.input})")
            output = dispatch_tool(robot, tc.name, tc.input)

            # Don't print full image data
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

        speak("Autonomous Box online. I am ready.")
        print("\n[Autonomous Box] Online. Type a goal or question. Type 'quit' to exit.\n")

        # Single goal mode
        if len(sys.argv) > 1:
            goal = " ".join(sys.argv[1:])
            run_agent(goal, robot)

        # Conversational loop mode
        else:
            messages = []
            print("Voice mode active — just talk! Say 'quit' or press Ctrl+C to stop.\n")
            while True:
                try:
                    user_input = listen()
                    if user_input is None:
                        continue
                    if user_input.lower() in ("quit", "exit", "stop listening"):
                        speak("Shutting down. Goodbye.")
                        break
                    messages = run_agent(user_input, robot, messages)
                except KeyboardInterrupt:
                    print("\n[Interrupted]")
                    robot.stop()
                    speak("Stopping.")
                    break