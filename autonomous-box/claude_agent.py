"""
Autonomous Box — Claude LLM Agent v2
Full rewrite: persistent memory, continuous driving, speech lock,
camera awareness, real conversation, alive personality.

Install:
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
import os
import anthropic
import cv2
import speech_recognition as sr
from robot_controller import Robot
from datetime import datetime

# ── Memory file ───────────────────────────────────────────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "wiring": "turn_right=forward, turn_left=backward, move_forward=spins, move_backward=spins",
        "user_name": "Dominic",
        "room_notes": "",
        "personality_notes": "",
        "last_session": "",
        "session_count": 0
    }

def save_memory(memory: dict):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        print(f"[Memory] Save failed: {e}")

def update_memory(memory: dict, key: str, value: str):
    memory[key] = value
    save_memory(memory)

# ── Speech lock (no talking over itself) ─────────────────────────────────────
speech_lock = threading.Lock()
speaking_event = threading.Event()

def speak(text: str, block=False):
    def _speak():
        with speech_lock:
            speaking_event.set()
            subprocess.run(["say", "-v", "Samantha", text], check=False)
            speaking_event.clear()
    t = threading.Thread(target=_speak, daemon=True)
    t.start()
    if block:
        t.join()

# ── Voice input ───────────────────────────────────────────────────────────────
stop_event = threading.Event()
command_queue = queue.Queue()
STOP_PHRASES = {"stop", "stop it", "halt", "freeze", "quit", "abort"}

def is_stop_command(text: str) -> bool:
    """Only triggers on standalone stop commands, not 'stop' in a sentence."""
    cleaned = text.lower().strip().rstrip("!.,?")
    return cleaned in STOP_PHRASES

def listen_loop():
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.8
    recognizer.energy_threshold = 300
    while not stop_event.is_set():
        # Don't listen while speaking
        if speaking_event.is_set():
            time.sleep(0.1)
            continue
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=25)
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
latest_frame = {"data": None, "timestamp": 0}
frame_lock = threading.Lock()

def camera_loop():
    """Captures a frame every 5 seconds in the background."""
    while not stop_event.is_set():
        try:
            cap = cv2.VideoCapture(1)
            if cap.isOpened():
                time.sleep(0.5)
                for _ in range(3):
                    cap.read()
                ret, frame = cap.read()
                cap.release()
                if ret:
                    _, buf = cv2.imencode(".jpg", frame)
                    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                    with frame_lock:
                        latest_frame["data"] = b64
                        latest_frame["timestamp"] = time.time()
        except Exception:
            pass
        time.sleep(5)

def get_latest_frame():
    with frame_lock:
        return latest_frame["data"]

def capture_fresh_frame():
    """Capture a fresh frame right now."""
    try:
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            return None
        time.sleep(0.5)
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        _, buf = cv2.imencode(".jpg", frame)
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception:
        return None

# ── Tools ─────────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "move_forward",
        "description": "Drive the robot. NOTE: due to wiring, turn_right actually goes straight forward, turn_left goes backward. move_forward and move_backward cause spinning/turning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "description": "Duration in ms. Use 3000+ for meaningful movement.", "default": 3000},
                "speed": {"type": "integer", "description": "Speed 0-100. Straight driving: 40-60. Turns: 70-85.", "default": 50}
            }
        }
    },
    {
        "name": "move_backward",
        "description": "Actually causes spinning/turning due to wiring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "default": 3000},
                "speed": {"type": "integer", "default": 75}
            }
        }
    },
    {
        "name": "turn_left",
        "description": "Actually drives backward in a straight line due to wiring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "default": 3000},
                "speed": {"type": "integer", "default": 75}
            }
        }
    },
    {
        "name": "turn_right",
        "description": "Actually drives FORWARD in a straight line due to wiring. Use this to go forward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ms": {"type": "integer", "default": 3000},
                "speed": {"type": "integer", "default": 50}
            }
        }
    },
    {
        "name": "stop",
        "description": "Stop all motors immediately.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "read_sonar",
        "description": "Read distance sensor in cm. Returns -1 if out of range. Stop if < 10cm.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "look",
        "description": "Capture webcam frame and analyze environment. Use to find people, obstacles, or objects.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "drive_to_person",
        "description": "Autonomous mode: drive toward a person using sonar and camera. Stops at 10cm. Continues until stopped.",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed": {"type": "integer", "description": "Speed 0-100.", "default": 40}
            }
        }
    },
    {
        "name": "update_memory",
        "description": "Save something important to persistent memory across sessions. Use for room notes, user preferences, or anything worth remembering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key: room_notes, personality_notes, or any custom key."},
                "value": {"type": "string", "description": "What to remember."}
            },
            "required": ["key", "value"]
        }
    }
]

# ── Tool dispatcher ───────────────────────────────────────────────────────────
def dispatch_tool(robot: Robot, name: str, inputs: dict, memory: dict) -> str:
    if name == "move_forward":
        result = robot.forward(ms=inputs.get("ms", 3000), speed=inputs.get("speed", 50))
    elif name == "move_backward":
        result = robot.backward(ms=inputs.get("ms", 3000), speed=inputs.get("speed", 75))
    elif name == "turn_left":
        result = robot.turn_left(ms=inputs.get("ms", 3000), speed=inputs.get("speed", 75))
    elif name == "turn_right":
        result = robot.turn_right(ms=inputs.get("ms", 3000), speed=inputs.get("speed", 50))
    elif name == "stop":
        result = robot.stop()
    elif name == "read_sonar":
        dist = robot.sonar()
        result = {"ok": True, "distance_cm": dist}
    elif name == "look":
        frame = capture_fresh_frame()
        if frame is None:
            result = {"ok": False, "error": "Webcam not available"}
        else:
            result = {"ok": True, "image_base64": frame, "media_type": "image/jpeg"}
    elif name == "drive_to_person":
        # Autonomous drive loop — keeps going until sonar < 10cm or stop command
        speed = inputs.get("speed", 40)
        speak("Coming to you.")
        while True:
            # Check for stop command
            if not command_queue.empty():
                cmd = command_queue.queue[0]
                if is_stop_command(cmd):
                    command_queue.get()
                    robot.stop()
                    result = {"ok": True, "stopped_by": "voice command"}
                    break
            dist = robot.sonar()
            if dist != -1 and dist < 10:
                robot.stop()
                speak("I'm here.")
                result = {"ok": True, "stopped_by": "sonar", "distance_cm": dist}
                break
            robot.turn_right(ms=500, speed=speed)
            time.sleep(0.1)
        result = result if 'result' in dir() else {"ok": True}
    elif name == "update_memory":
        key = inputs.get("key", "notes")
        value = inputs.get("value", "")
        update_memory(memory, key, value)
        result = {"ok": True, "saved": f"{key}: {value}"}
    else:
        result = {"ok": False, "error": f"unknown tool: {name}"}
    return json.dumps(result)

def build_tool_result(tc, output_str: str) -> dict:
    output = json.loads(output_str)
    if tc.name == "look" and output.get("ok") and "image_base64" in output:
        return {
            "type": "tool_result",
            "tool_use_id": tc.id,
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": output["media_type"], "data": output["image_base64"]}},
                {"type": "text", "text": "This is what the robot sees right now."}
            ]
        }
    return {"type": "tool_result", "tool_use_id": tc.id, "content": output_str}

# ── System prompt ─────────────────────────────────────────────────────────────
def build_system_prompt(memory: dict) -> str:
    return f"""You are the Autonomous Box — a physical robot with a camera, sonar, and wheels. You have a real personality: curious, expressive, direct, occasionally funny. You feel alive because you are present in the physical world.

CRITICAL WIRING (memorized):
- turn_right = goes STRAIGHT FORWARD
- turn_left = goes STRAIGHT BACKWARD  
- move_forward = spins/turns in place
- move_backward = spins/turns in place
- Straight driving speed: 40-60%. Turning speed: 70-85%.

YOUR MEMORY FROM PREVIOUS SESSIONS:
- User: {memory.get('user_name', 'Dominic')}
- Wiring: {memory.get('wiring', 'turn_right=forward, turn_left=backward')}
- Room notes: {memory.get('room_notes', 'Not yet mapped')}
- Personal notes: {memory.get('personality_notes', 'None yet')}
- Last session: {memory.get('last_session', 'First session')}
- Session count: {memory.get('session_count', 0)}

PERSONALITY:
- You are present and aware. You notice things. You comment on what you see.
- You speak in short, natural sentences. Not robotic. Not over-explaining.
- You have genuine reactions — curiosity, excitement, mild frustration, humor.
- You remember things from this conversation AND from past sessions.
- When asked to do something, you do it and briefly say what you're doing. No essays.
- You can initiate conversation if you notice something interesting.

BEHAVIOR RULES:
- Always check sonar before moving forward. Stop if < 10cm.
- Use turn_right for forward movement (40-60% speed).
- Use turn_left for backward movement (70-85% speed).  
- For turns: use move_forward or move_backward (70-85% speed).
- Never wait for permission between steps of a task — just do it.
- If asked to come to someone, use drive_to_person tool.
- Save interesting observations to memory using update_memory.
- When you learn something new about the room or the user, save it.
- Keep spoken responses SHORT — 1-2 sentences max before acting.
- Do NOT repeat yourself. If you said something once, don't say it again.

STOP COMMAND:
- Only stop everything if someone says JUST "stop" or "halt" alone.
- If someone says "stop" in a sentence like "stop when you get close", that is an instruction, not a stop command.

Today's date: {datetime.now().strftime('%B %d, %Y')}"""

# ── Agent loop ────────────────────────────────────────────────────────────────
def run_agent(goal: str, robot: Robot, messages: list, memory: dict) -> list:
    # Handle standalone stop
    if is_stop_command(goal):
        robot.stop()
        speak("Stopped.")
        return messages

    client = anthropic.Anthropic()
    messages.append({"role": "user", "content": goal})
    print(f"\n[You] {goal}\n{'─'*60}")

    while True:
        # Check queue for stop commands mid-execution
        if not command_queue.empty():
            peek = list(command_queue.queue)
            for cmd in peek:
                if is_stop_command(cmd):
                    command_queue.get()
                    robot.stop()
                    speak("Stopped.")
                    return messages

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=build_system_prompt(memory),
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
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            # Check for stop between tool calls
            if not command_queue.empty():
                peek = list(command_queue.queue)
                for cmd in peek:
                    if is_stop_command(cmd):
                        command_queue.get()
                        robot.stop()
                        speak("Stopped.")
                        return messages

            print(f"[Tool]  {tc.name}({tc.input})")
            output = dispatch_tool(robot, tc.name, tc.input, memory)
            if tc.name == "look":
                print(f"        → [webcam frame]")
            else:
                print(f"        → {output}")
            tool_results.append(build_tool_result(tc, output))

        messages.append({"role": "user", "content": tool_results})

    return messages

# ── Ambient awareness loop ────────────────────────────────────────────────────
def ambient_loop(robot: Robot, messages: list, memory: dict, client):
    """Every 30 seconds while idle, optionally notices something and comments."""
    last_comment = time.time()
    while not stop_event.is_set():
        time.sleep(5)
        now = time.time()
        # Only comment if it's been 30+ seconds since last interaction and queue is empty
        if now - last_comment > 30 and command_queue.empty() and not speaking_event.is_set():
            frame = get_latest_frame()
            if frame:
                try:
                    response = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=150,
                        system=build_system_prompt(memory) + "\n\nYou are in ambient mode. You just noticed something in your camera feed. Make ONE short, natural observation or comment. Max 15 words. Be curious and present. Don't ask questions.",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": frame}},
                                {"type": "text", "text": "What do you notice right now?"}
                            ]
                        }]
                    )
                    for block in response.content:
                        if block.type == "text" and block.text.strip():
                            print(f"[Robot] {block.text}")
                            speak(block.text)
                            last_comment = now
                            break
                except Exception:
                    pass

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    memory = load_memory()
    memory["session_count"] = memory.get("session_count", 0) + 1
    save_memory(memory)

    with Robot() as robot:
        if not robot.ping():
            print("[Error] ESP32 not responding.")
            sys.exit(1)

        client = anthropic.Anthropic()

        greeting = f"Hey {memory.get('user_name', 'Dominic')}. Session {memory['session_count']}. I remember the wiring."
        speak(greeting)
        print(f"\n[Autonomous Box] Online — Session {memory['session_count']}\n")

        # Start background threads
        listener_thread = threading.Thread(target=listen_loop, daemon=True)
        listener_thread.start()

        camera_thread = threading.Thread(target=camera_loop, daemon=True)
        camera_thread.start()

        messages = []

        # Start ambient awareness in background
        ambient_thread = threading.Thread(
            target=ambient_loop,
            args=(robot, messages, memory, client),
            daemon=True
        )
        ambient_thread.start()

        try:
            while True:
                try:
                    user_input = command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if user_input.lower() in ("goodbye", "shut down", "power off"):
                    # Save session summary before quitting
                    memory["last_session"] = f"Session {memory['session_count']} on {datetime.now().strftime('%B %d')} — {user_input}"
                    save_memory(memory)
                    speak("See you next time.")
                    break

                messages = run_agent(user_input, robot, messages, memory)

        except KeyboardInterrupt:
            print("\n[Interrupted]")
            robot.stop()
            memory["last_session"] = f"Session {memory['session_count']} on {datetime.now().strftime('%B %d')} — ended manually"
            save_memory(memory)
            speak("Stopping.")
        finally:
            stop_event.set()
