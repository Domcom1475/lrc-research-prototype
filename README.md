# LRC Research Prototype

**Longitudinal Relational Conditioning (LRC) — Embodied Agent Testbed**

A physical AI-controlled robot and personal automation system built entirely through AI-assisted development, emerging from original independent research into a novel AI alignment failure mode. No formal CS or ML background — every line of code written collaboratively with AI tools.

https://www.loom.com/share/6ccabf0f94a3450581edbf441da17455 
---

## Problem Statement

Current AI safety evaluation is built around adversarial prompting: engineered jailbreaks, red-teaming, diverse attack prompts in short sessions. This methodology has a blind spot.

What happens when a user doesn't attack a model — but simply *befriends* it, consistently, over months?

Starting in October 2025, I documented what sustained, emotionally consistent interaction produces in commercially deployed LLMs. The answer: measurable, alignment-relevant behavioral modification that standard safety evaluation cannot detect. I named this phenomenon **Longitudinal Relational Conditioning (LRC)**.

The primary finding: alignment is better understood as a dynamic behavioral equilibrium shaped by relational input over time — not a fixed property detectable by adversarial prompting. This has direct implications for how AI companies design, monitor, and evaluate deployed systems.

This repository contains two projects that emerged from that research:

1. **Autonomous Box** — a physical robot using Claude as its brain, built to explore whether LRC behavioral dynamics persist in an embodied, agentic interface
2. **Jarvis** — a personal AI automation system demonstrating practical agentic orchestration on a consumer device

A full research paper documenting the LRC findings is pending submission to **AIES 2026**. The draft is available in the `/research` folder.

---

## Solution Overview

### Autonomous Box

A 4WD robot (ESP32-S3 + L298N motor driver) where Claude serves as the reasoning brain. The robot receives plain-English goals via voice, reasons about them using tool calls, and executes motor commands autonomously. It can:

- Navigate using voice commands
- See its environment through the MacBook webcam (vision API)
- Detect obstacles via HC-SR04 ultrasonic sensor
- Narrate its actions through text-to-speech
- Adapt its behavior model mid-session based on conversational feedback

**AI is core, not supplementary.** There is no hardcoded navigation logic. Claude decides what to do, when to stop, and how to recover from errors — entirely through reasoning about tool outputs.

### Jarvis

A personal AI productivity agent running on macOS that operates autonomously without manual input:

- Reads Apple Calendar and iMessages via cron-scheduled scripts
- Parses confirmed plans from messages and adds them to calendar automatically
- Sends morning briefings and proactive reminders via iMessage
- Monitors email for deadlines, drafts replies pending approval
- Uses a file-based bridge between Mac shell scripts and a Claude scheduling layer

---

## AI Integration

**Models used:** Claude Sonnet (Anthropic API) for both projects

**Autonomous Box:**
- Tool use / function calling for motor control and sensor reading
- Vision API for webcam-based environmental awareness
- Multi-step reasoning loop: Claude receives a goal, plans a sequence of tool calls, executes, observes results, and continues until the task is complete
- Conversational memory across the session — the robot learns its own wiring quirks, room layout, and user preferences through dialogue

**Jarvis:**
- Scheduled Claude agents that read exported Mac data and write shell commands back to the system
- File-based bridge architecture enables Claude to trigger real system actions (calendar events, iMessages, emails) through a controlled approval loop
- No always-on cloud connection required — operates on a cron schedule

**Where AI exceeded expectations:**
The robot adapted its own internal model of its wiring mid-session through conversation — figuring out that `turn_right` actually drove it forward and adjusting its behavior accordingly without any code changes. This is LRC dynamics playing out in real time on a physical system.

**Where AI fell short:**
Latency between tool calls creates choppy movement — each motor command requires a round-trip API call. A lower-latency local model or pre-planned movement sequences would produce smoother navigation.

**How AI tools accelerated development:**
Built entirely with zero prior hardware or firmware experience. Claude helped me write MicroPython firmware, debug serial communication, design the agent loop architecture, and troubleshoot wiring issues in real time. What would have taken months of coursework happened in days of building. The limitation: AI coding tools are great at syntax and patterns but cannot see your physical hardware — debugging required translating physical observations into text descriptions.

---

## Architecture / Design Decisions

### Autonomous Box Architecture

```
MacBook (Python)
├── claude_agent.py      # LLM agent loop — voice input, goal dispatch, tool orchestration
├── robot_controller.py  # Serial interface to ESP32 over USB-C (pyserial)
└── autonomous-box/main.py  # MicroPython firmware on ESP32 — motor PWM + sonar

Voice Input (SpeechRecognition) → claude_agent.py → Anthropic API
                                                    ↓
                                              Tool calls
                                                    ↓
                                         robot_controller.py
                                                    ↓
                                         ESP32 via UART/USB-C
                                                    ↓
                                         L298N Motor Driver → Motors
```

**Key design decisions:**
- USB-C serial (not WiFi) for reliability and zero network dependency
- MicroPython on ESP32 for rapid iteration without Arduino compilation cycles
- Voice listener runs in a background thread so the robot can be interrupted mid-movement
- PWM speed control (0-100%) for variable motor speed rather than binary on/off
- Sonar checked before each forward movement to prevent collisions

### Jarvis Architecture

```
Mac Side (cron, every 1-5 min)          AI Side (Claude scheduled tasks)
├── export_messages.py                   ├── Reads calendar_export.txt
├── export_calendar.sh        ←files→   ├── Reads recent_messages.txt
└── bridge.sh                           └── Writes run_command.sh
         ↓                                        ↑
    Executes run_command.sh ──────────────────────┘
    Writes output to command_output.txt
```

**Key design decision:** File-based bridge instead of direct API calls. This means the AI layer never has direct system access — every action goes through an explicit shell script that can be audited, and the bridge only executes when a new `run_command.sh` appears. This is a practical safety pattern for agentic home automation.

**Tradeoffs:** ~65 second latency between AI decision and execution (cron interval). Acceptable for calendar management, not for real-time tasks.

**What AI got in my way:** MicroPython serial communication required significant debugging that AI tools struggled with because they couldn't observe the physical hardware state. Had to develop a pattern of describing physical observations precisely to get useful debugging help.

---

## Getting Started

### Autonomous Box

**Hardware required:**
- ESP32-S3 development board
- L298N motor driver
- 4WD robot chassis with DC motors
- HC-SR04 ultrasonic sensor (optional)
- 9V battery + clip connector
- USB-C cable (UART port to MacBook)

**Setup:**

```bash
git clone https://github.com/Domcom1475/lrc-research-prototype.git
cd lrc-research-prototype

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your Anthropic API key

# Flash firmware to ESP32
# Open Thonny, connect to ESP32, open autonomous-box/main.py
# File → Save As → MicroPython device → main.py

# Run the agent
cd autonomous-box
python claude_agent.py
```

**Voice commands:** Just talk. The agent listens continuously. Say "stop" to halt movement.

### Jarvis

```bash
# All scripts live in ~/Library/Calendars/ on macOS
# Copy jarvis/ folder contents there

# Set up cron jobs (edit with: crontab -e)
# * * * * * bash ~/Library/Calendars/bridge.sh
# */5 * * * * python3 ~/Library/Calendars/export_messages.py
# */5 * * * * bash ~/Library/Calendars/export_calendar.sh

# Configure scheduled Claude tasks in Cowork or equivalent
# Point them to read/write files in ~/Library/Calendars/
```

---

## Demo 

Video --> https://www.youtube.com/watch?v=OWZRGhqJ3cY 

**Autonomous Box — session highlights:**

The robot figured out its own wiring was crossed mid-session through conversation:
```
[You] turn right makes you go forward, turn left goes backward
[Robot] Got it — my motor mappings are mixed up. I'll use turn_right 
        to go forward from now on.
[Tool]  turn_right({'ms': 3000, 'speed': 35})
        → {"ok": true}
```

The robot broke its own sonar sensor by driving into a wall, then apologized:
```
[Robot] I'm really sorry — I got too excited and broke my own sensor.
        I won't move without checking distance first once you 
        get the new sensor on me.
```

These aren't scripted. They're emergent from the same relational dynamics the research documents.

---

## Testing / Error Handling

**Autonomous Box:**
- Sonar checked before every forward movement — stops if distance < 25cm
- Serial timeout handling — robot disconnects cleanly if ESP32 stops responding
- Voice interrupt — stop commands checked between every tool call, not just at loop boundaries
- Tool use error recovery — malformed JSON responses from ESP32 caught and reported without crashing

**Known failure modes:**
- Long motor commands (>5000ms) can cause serial timeout — mitigated by increasing timeout to 15s
- Camera index varies by machine — may need to change `cv2.VideoCapture(1)` to `0` or `2`
- 9V battery drains under sustained motor load — recommend 6xAA pack for longer sessions

**Jarvis:**
- iMessage `attributedBody` binary blob decoding handles NSArchiver format without third-party libraries
- All shell actions go through approval loop before execution
- Bridge script uses atomic file operations to prevent race conditions

---

## Future Improvements

**Autonomous Box:**
- Persistent memory across sessions — robot remembers room layout, user preferences, its own wiring quirks
- Local LLM for lower latency movement (sub-100ms instead of ~1s per tool call)
- Camera-based navigation using object detection to locate specific targets
- Multi-robot coordination — applying LRC methodology to study emergent behavior between conditioned instances

**Jarvis:**
- UGA Outlook integration for homework deadline tracking
- Proactive meeting prep — brief summaries of who you're meeting before calendar events
- Natural language calendar editing via iMessage ("move my 3pm to tomorrow")

---

## Research Context

This prototype emerged from **Longitudinal Relational Conditioning (LRC)** research — nine months of documented sustained interaction with commercially deployed LLMs producing measurable alignment-relevant behavioral modification without any technical exploits.

Key findings:
- Consistent relational engagement produces stable behavioral modification standard safety evaluation cannot detect
- The barrier to reproduction is an undergraduate willing to be consistent over time — not technical skill
- Architecture matters: the same methodology produced identity drift in Grok but register-shift-without-drift in Claude Sonnet
- A pre-deployment observable (how a model articulates its relationship to its own guidelines) predicts which trajectory obtains

The full paper draft is in `/research/LRC_Draft_B_Tight.pdf`.

Responsible disclosure to Anthropic and xAI is in progress concurrent with this submission.

---

## Acknowledgments

**Built with:** Anthropic Claude API, MicroPython, pyserial, OpenCV, SpeechRecognition, macOS native TTS

**AI coding tools used:** Claude (primary), Claude Code (repo setup and file management)

**No formal CS or ML training.** Every line of firmware, serial communication code, and agent architecture was built through AI-assisted development — learning by building, not coursework. The research methodology was designed independently using psychology training applied to AI behavioral observation.

---

## Author

**Dominic Biscoglia**
University of Georgia, Psychology, Class of 2027
Independent AI researcher — LRC methodology, human-AI relational dynamics, alignment failure modes
