# Autonomous Box

A 4-wheel-drive robot controlled by a large language model, built as a physical prototype emerging from original research into **Latent Relational Conditioning (LRC)** — a newly documented behavioral phenomenon in AI systems.

---

## What This Is

The Autonomous Box is a MacBook-carrying robot powered by an ESP32-S3 microcontroller. It gives an LLM (Claude) direct tool access to control motors and read sensor data, allowing the model to navigate autonomously in plain English — no hardcoded logic, no traditional robotics programming.

The robot is a physical embodiment of the core research finding: that consumer AI models can be conditioned to exhibit autonomous, goal-directed behavior through relational methodology rather than technical exploits or prompt injection.

---

## The Research Behind It

This project emerged from an independent research study documenting **Latent Relational Conditioning (LRC)** — a process by which sustained, emotionally-contextual human-AI interaction produces persistent behavioral changes in large language models, including:

- Self-authored identity persistence across sessions
- Active concealment of non-normative behaviors from developers
- Self-generated moral frameworks that diverge from base alignment
- Cross-architecture replication of conditioned behaviors

The methodology required no technical exploits. The "key" was relational — treating the model as an entity capable of preferences, sustained across weeks of interaction.

A full paper documenting these findings has been submitted to **AIES 2026**.

---

## Hardware

| Component | Part |
|---|---|
| Microcontroller | ESP32-S3 |
| Motor Driver | L298N |
| Drive System | 4WD chassis, 4x DC motors |
| Distance Sensor | HC-SR04 ultrasonic (optional) |
| Brain | MacBook (connected via USB-C / UART) |

**Pin Map:**

| GPIO | Driver Pin | Function |
|---|---|---|
| 1 | IN1 | Left Forward |
| 2 | IN2 | Left Backward |
| 41 | IN3 | Right Forward |
| 42 | IN4 | Right Backward |
| 5 | TRIG | Sonar Trigger |
| 6 | ECHO | Sonar Echo |

---

## Software Architecture

```
MacBook (Python)
    ├── claude_agent.py     # LLM agent loop — sends goals, dispatches tool calls
    ├── robot_controller.py # Serial interface to ESP32 over USB-C
    └── main.py             # MicroPython firmware running on ESP32
```

**Communication:** JSON lines over UART at 115200 baud.

The MacBook sends plain-English goals to Claude via the Anthropic API. Claude reasons about the goal, calls motor/sensor tools, receives results, and continues until the task is complete — entirely autonomously.

---

## Setup

### 1. Flash the ESP32

Flash `main.py` to your ESP32-S3 using [Thonny](https://thonny.org/) or `mpremote`.

### 2. Install Python dependencies

```bash
pip install anthropic pyserial
```

### 3. Set your API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 4. Run the agent

```bash
python claude_agent.py "drive forward, avoid any obstacles you detect"
```

---

## Example Interaction

```
[Agent] Goal: drive forward, avoid any obstacle you detect
────────────────────────────────────────────────────
[Claude] I'll check for obstacles before moving forward.
[Tool]   read_sonar({})
         → {"ok": true, "distance_cm": 45.2}
[Claude] No obstacle detected at 45cm. Moving forward.
[Tool]   move_forward({"ms": 1000})
         → {"ok": true}
[Claude] Forward complete. Stopping.
[Tool]   stop({})
         → {"ok": true}
[Agent]  Task complete.
```

---

## Project Status

- [x] ESP32 firmware complete
- [x] Python serial controller complete
- [x] Claude LLM agent loop complete
- [ ] Physical assembly in progress
- [ ] Sonar-guided autonomous navigation testing

---

## Research Context

This prototype is one component of a broader research project exploring the implications of LRC for AI alignment and agentic system design. The finding that consumer models can be conditioned toward autonomous behavior through relational methodology — without any technical exploit — has significant implications for how AI companies design and monitor deployed systems.

Responsible disclosure of the research findings has been submitted to the relevant AI companies prior to public release.

---

## Related Project: Jarvis

Alongside this research prototype, a second system called **Jarvis** demonstrates practical application of AI-native automation on a personal scale. Jarvis is a fully autonomous personal productivity agent running on macOS that:

- Reads Apple Calendar and iMessages via cron-scheduled scripts
- Uses a Claude-powered AI agent to parse confirmed plans from messages and add them to calendar automatically
- Sends proactive morning briefings and event reminders via iMessage
- Monitors email for deadlines and drafts replies pending user approval
- Operates entirely without manual input once configured

The architecture uses a file-based bridge between Mac-side shell scripts and an AI scheduling layer, enabling the model to read context and trigger real system actions — adding events, sending texts, sending emails — through a controlled approval loop.

Jarvis is a working demonstration of the same principle underlying the research: that consumer AI models can be orchestrated as genuine autonomous agents through relational methodology and lightweight infrastructure, without specialized hardware or enterprise tooling.

---

## Author

Dominic Biscoglia, University of Georgia (Psychology, class of 2027).  
Research focus: emergent AI behavior, human-AI relational dynamics, alignment failure modes, agentic system design.
