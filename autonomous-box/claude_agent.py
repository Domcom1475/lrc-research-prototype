"""
Autonomous Box — Claude LLM Agent

Gives Claude tool access to drive the robot.  The agent receives a goal
in plain English and figures out the sequence of moves on its own.

Install dependencies:
    pip install anthropic pyserial

Run:
    python claude_agent.py "drive forward, avoid any obstacle you detect"
"""

import sys
import json
import anthropic
from robot_controller import Robot

# ── Tool definitions (what Claude can call) ──────────────────────────────────

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
]

SYSTEM_PROMPT = """You are the brain of a 4-wheel-drive robot called the Autonomous Box.
You have a set of tools to control its motors and read its ultrasonic sensor.

Guidelines:
- Use read_sonar before moving forward if you want to check for obstacles.
- An obstacle is close if the sonar returns < 20 cm.
- Always call stop when you are done with a task.
- Think step-by-step and explain each action briefly before calling the tool.
- If sonar returns -1, the sensor is not connected — proceed without it.
"""


def dispatch_tool(robot: Robot, name: str, inputs: dict) -> str:
    """Calls the real robot and returns a JSON string result."""
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
    else:
        result = {"ok": False, "error": f"unknown tool: {name}"}
    return json.dumps(result)


def run_agent(goal: str, robot: Robot):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": goal}]

    print(f"\n[Agent] Goal: {goal}\n{'─'*60}")

    while True:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text and tool calls from this response
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                print(f"[Claude] {block.text}")
            elif block.type == "tool_use":
                tool_calls.append(block)

        # If no tool calls, Claude is done
        if response.stop_reason == "end_turn" or not tool_calls:
            print("\n[Agent] Task complete.")
            break

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and build the tool_result turn
        tool_results = []
        for tc in tool_calls:
            print(f"[Tool]  {tc.name}({tc.input})")
            output = dispatch_tool(robot, tc.name, tc.input)
            print(f"        → {output}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": output,
            })

        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Drive forward for one second, then stop."

    with Robot() as robot:
        if not robot.ping():
            print("[Error] ESP32 did not respond to ping. Check the cable.")
            sys.exit(1)
        run_agent(goal, robot)
