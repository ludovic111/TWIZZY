# Ideas Stolen from OpenClaw 🦞

This document summarizes the features adapted from [OpenClaw](https://github.com/openclaw/openclaw) for TWIZZY.

## Overview

OpenClaw is a personal AI assistant with impressive multi-channel capabilities. We've adapted several of its key architectural patterns to enhance TWIZZY.

---

## 🌐 Multi-Channel Gateway (`src/gateway/`)

**OpenClaw Feature:** Gateway control plane for WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, Matrix, Zalo, WebChat

**TWIZZY Implementation:**
- Abstract `Channel` base class for any messaging platform
- `Gateway` control plane for routing and security
- Built-in adapters for Telegram, Slack, Discord
- DM pairing codes for security (untrusted input handling)
- Allowlist-based sender authentication

**Files:**
- `src/gateway/gateway.py` - Main gateway control plane
- `src/gateway/channel.py` - Base channel interface
- `src/gateway/channels/telegram.py` - Telegram bot adapter
- `src/gateway/channels/slack.py` - Slack Bolt adapter  
- `src/gateway/channels/discord.py` - Discord.py adapter

**Usage:**
```python
from src.gateway import get_gateway
from src.gateway.channels.telegram import TelegramChannel

gateway = get_gateway()
gateway.register_channel("telegram", TelegramChannel(config={"token": "..."}))
await gateway.start()
```

---

## 🎤 Voice Interface (`src/voice/`)

**OpenClaw Feature:** Voice Wake + Talk Mode with ElevenLabs

**TWIZZY Implementation:**
- `TextToSpeech` - Multiple engine support (macOS `say`, pyttsx3, ElevenLabs)
- `SpeechToText` - Whisper (local or API), Vosk (offline)
- `WakeWordDetector` - Porcupine for hands-free activation

**Files:**
- `src/voice/tts.py` - Text-to-speech
- `src/voice/stt.py` - Speech-to-text
- `src/voice/wake_word.py` - Wake word detection

**Usage:**
```python
from src.voice import get_tts_engine, get_stt_engine, get_wake_detector

# Speak
tts = get_tts_engine()
await tts.speak("Hello from TWIZZY!")

# Transcribe
stt = get_stt_engine()
text = await stt.record_and_transcribe(duration=5)

# Wake word
wake = get_wake_detector()
wake.add_callback(lambda: print("Wake word detected!"))
wake.start()
```

---

## 🌐 Browser Automation (`src/browser/`)

**OpenClaw Feature:** Dedicated Chrome/Chromium control with snapshots

**TWIZZY Implementation:**
- `BrowserController` - Playwright-based automation
- `PageSnapshot` - Convert pages to LLM-readable format
- Stealth mode to hide automation

**Files:**
- `src/browser/controller.py` - Browser automation
- `src/browser/snapshot.py` - Page snapshot for LLM

**Usage:**
```python
from src.browser import get_browser_controller

browser = await get_browser_controller()
result = await browser.navigate("https://example.com")
await browser.click("#submit")
screenshot = await browser.screenshot()
```

---

## 🎨 Canvas / Visual Workspace (`src/canvas/`)

**OpenClaw Feature:** A2UI push/reset, eval, snapshot - agent-driven visual workspace

**TWIZZY Implementation:**
- `Canvas` - Shared visual workspace
- Multiple element types: text, markdown, code, image, chart, table, form, card, list
- `CanvasRenderer` - Convert to HTML/JSON

**Files:**
- `src/canvas/canvas.py` - Canvas system
- `src/canvas/renderer.py` - HTML/JSON renderer

**Usage:**
```python
from src.canvas import get_canvas

canvas = get_canvas()
canvas.add_markdown("# Analysis Results")
canvas.add_table(
    headers=["Metric", "Value"],
    rows=[["CPU", "45%"], ["Memory", "2.3GB"]]
)
canvas.add_chart("bar", {
    "labels": ["A", "B", "C"],
    "datasets": [{"data": [10, 20, 30]}]
})
html = CanvasRenderer(canvas).to_html()
```

---

## ⏰ Cron / Scheduling System (`src/scheduler/`)

**OpenClaw Feature:** Cron + wakeups for automated tasks

**TWIZZY Implementation:**
- `TaskScheduler` - APScheduler-based
- Cron expressions, intervals, one-time tasks
- Task callbacks for agent integration

**Files:**
- `src/scheduler/scheduler.py` - Task scheduler
- `src/scheduler/triggers.py` - Trigger types

**Usage:**
```python
from src.scheduler import get_scheduler

scheduler = get_scheduler()
await scheduler.start()

# Daily at 9am
scheduler.schedule_cron("morning_report", "0 9 * * *", "Generate daily report")

# Every 30 minutes
scheduler.schedule_interval("health_check", minutes=30, action="Check system health")
```

---

## 🧩 Skills Platform (`src/skills/`)

**OpenClaw Feature:** Bundled, managed, and workspace skills with install gating

**TWIZZY Implementation:**
- `Skill` base class for modular capabilities
- `SkillRegistry` - Manage installed skills
- `SkillLoader` - Dynamic discovery and loading
- Categories: productivity, communication, development, media, system, integration, utility

**Files:**
- `src/skills/skill.py` - Base skill class
- `src/skills/registry.py` - Skill registry
- `src/skills/loader.py` - Skill loader

**Usage:**
```python
from src.skills import Skill, SkillContext, SkillResult, SkillCategory, SkillManifest

class MySkill(Skill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="my_skill",
            version="1.0.0",
            description="Does something cool",
            category=SkillCategory.UTILITY,
            author="User",
            entry_point="my_skill"
        )
        
    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, message="Done!")

# Register and install
from src.skills import get_skill_registry

registry = get_skill_registry()
registry.register(MySkill)
await registry.install("my_skill")
```

---

## 🔧 Doctor Diagnostic Tool (`src/doctor/`)

**OpenClaw Feature:** `openclaw doctor` - System diagnostics and repair

**TWIZZY Implementation:**
- `Doctor` - Diagnostic runner
- Multiple checks: Python version, dependencies, API keys, git repo, permissions
- Auto-fix capabilities
- Report export

**Files:**
- `src/doctor/doctor.py` - Doctor tool
- `src/doctor/checks.py` - Diagnostic checks
- `scripts/twizzy-doctor.py` - CLI entry point

**Usage:**
```bash
# Run diagnostics
python scripts/twizzy-doctor.py

# Auto-fix issues
python scripts/twizzy-doctor.py --fix

# Export report
python scripts/twizzy-doctor.py --report report.json
```

---

## Dependencies

These features require additional dependencies:

```bash
# Gateway channels
pip install python-telegram-bot slack-bolt discord.py

# Voice
pip install pyaudio openai-whisper elevenlabs pvporcupine

# Browser
pip install playwright && playwright install

# Scheduler
pip install apscheduler croniter

# Skills (dynamic loading - built-in)
# No additional deps needed

# Doctor (built-in)
# No additional deps needed
```

---

## Architecture Comparison

| Aspect | OpenClaw | TWIZZY Adaptation |
|--------|----------|-------------------|
| **Language** | TypeScript/Node.js | Python |
| **Gateway** | WebSocket control plane | Asyncio + WebSocket |
| **Voice** | ElevenLabs exclusive | Multiple engine support |
| **Browser** | Puppeteer | Playwright |
| **Canvas** | A2UI protocol | HTML/JSON renderer |
| **Scheduler** | Built-in cron | APScheduler |
| **Skills** | npm-based | Python module loading |
| **Doctor** | CLI + doctor command | Python CLI tool |

---

## Future Enhancements

Potential additions from OpenClaw:
- [ ] macOS menu bar app companion
- [ ] iOS/Android companion nodes
- [ ] Tailscale Serve/Funnel integration
- [ ] Gmail Pub/Sub integration
- [ ] Webhooks for external events
- [ ] Session pruning and management
- [ ] Presence and typing indicators
- [ ] Usage tracking and quotas
