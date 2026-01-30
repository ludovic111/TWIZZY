# TWIZZY

An autonomous, self-improving Mac agent powered by **Kimi Code API** that controls your entire system through natural language.

![macOS](https://img.shields.io/badge/macOS-14.0+-purple)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Kimi](https://img.shields.io/badge/Kimi-Code-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal)

## Features

### Core Capabilities
- **Natural Language Control** - Chat interface to control your Mac
- **Full System Access** - Terminal, files, and application control
- **Customizable Permissions** - Toggle what TWIZZY can access
- **Persistent Conversations** - Resume previous conversations across restarts
- **Auto-Start** - Runs as a background service, starts on login

### Web-Based Interface
- **Browser GUI** - Modern dark-themed web interface
- **Real-time Chat** - WebSocket-powered streaming responses
- **Auto-Reload** - Server reloads automatically when code changes
- **Cross-Platform** - Works in any browser

### Powered by Kimi Code API
- **Kimi Code Integration** - Uses kimi.com/code API (default)
- **Thinking Mode** - Advanced reasoning with `reasoning_content` support
- **Tool Calling** - Native function calling for system control
- **128K Context** - Long conversation memory
- **Multiple Providers** - Supports Kimi Code or Moonshot Open Platform

### Multi-Channel Gateway
Connect TWIZZY to your favorite messaging platforms:
- **Telegram** - Bot integration with secure pairing
- **Slack** - Workspace integration with mentions
- **Discord** - DM and mention support
- More channels coming soon...

### Voice Interface (Optional)
Hands-free interaction with your Mac:
- **Text-to-Speech** - macOS `say`, pyttsx3, or ElevenLabs
- **Speech-to-Text** - Whisper (local/API) or Vosk
- **Wake Word Detection** - "Hey Twizzy" activation

### Browser Automation (Optional)
Control the web through natural language:
- **Playwright Integration** - Chrome/Chromium automation
- **Page Snapshots** - Convert web pages to LLM-readable format
- **Stealth Mode** - Hide automation indicators

### Visual Canvas (Optional)
Rich visual outputs beyond text:
- **Markdown, Code, Images**
- **Charts** (Chart.js integration)
- **Tables, Cards, Forms**
- **HTML Export** for sharing

### Task Scheduler (Optional)
Automate recurring tasks:
- **Cron Expressions** - "0 9 * * 1-5" for 9am weekdays
- **Fixed Intervals** - Every 30 minutes
- **One-time Tasks** - Scheduled future execution

### Skills Platform (Optional)
Modular capabilities system:
- **Built-in Skills** - Echo, Time, etc.
- **Custom Skills** - Create your own
- **Dynamic Loading** - Load from workspace/skills/

### Self-Improvement System (Always-On)
TWIZZY can analyze and improve its own code **anytime**:

1. **Detection** - Monitors for failures, slow operations, missing capabilities
2. **Trigger** - Click "Improve Now" in web UI or wait for idle detection
3. **Generation** - Uses Kimi to write improvements
4. **Testing** - Validates changes before applying
5. **Deployment** - Commits to Git with `AUTO-IMPROVEMENT` tag
6. **Auto-Reload** - Server reloads automatically, no restart needed
7. **Rollback** - One-click revert if something breaks

### Enterprise-Grade Architecture
- **Multi-tier Caching** - File, command, and app info caching with TTL
- **Health Monitoring** - Component health checks and circuit breakers
- **Structured Logging** - Centralized logs with rotation
- **Error Recovery** - Retry strategies with exponential backoff
- **Conversation Storage** - Persistent JSON storage with search

## Quick Start

### 1. Install

```bash
cd ~/Desktop/TWIZZY
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Set Your API Key

Get your **Kimi Code API key** from [kimi.com/code](https://www.kimi.com/code) → Settings → API Keys:

```bash
# Interactive setup (recommended)
python scripts/setup-api-key.py

# Or manually to Keychain
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY_HERE')"
```

**Alternative:** Use Moonshot Open Platform instead:
1. Set `KIMI_API_PROVIDER=moonshot` in `.env`
2. Get key from [platform.moonshot.ai](https://platform.moonshot.ai/)

### 3. Run

**Start everything:**
```bash
./scripts/twizzy-start.sh
```

This will:
- Start the uvicorn web server with auto-reload
- Open your browser to http://127.0.0.1:7777

**Or manually:**
```bash
source .venv/bin/activate
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 7777 --reload
# Then open http://127.0.0.1:7777 in your browser
```

## Web Interface

### Chat Page
- **Real-time streaming** - Watch responses appear in real-time via WebSocket
- **Status indicator** - Shows connection status (connected/disconnected)
- **Clear conversation** - Start fresh with the clear button
- **Auto-scroll** - Messages automatically scroll into view

### Settings Page
- **API Key** - Configure your Kimi API key
- **Permissions** - Toggle capabilities on/off
  - Terminal: Execute shell commands
  - Filesystem: Read/write/delete files
  - Applications: Launch/quit/control apps

### Improvements Page
- **Improvement History** - View all self-improvements from git history
- **Improve Now** - Trigger manual self-improvement
- **Rollback** - Revert any improvement with one click
- **Focus Area** - Request improvements in specific areas

## Usage

### Example Commands
```
"List all files on my Desktop"
"Create a file called notes.txt with my meeting notes"
"Open Safari and Finder"
"Run the command 'brew update'"
"What apps are running?"
"Quit Slack"
"Read your own code and improve yourself"
"What API do you use?"
```

### Self-Improvement Commands
```
"Improve your error handling"
"Add a new capability to read PDFs"
"Optimize your caching system"
"Show me your source code"
```

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/twizzy-start.sh` | Start TWIZZY web server + open browser |
| `./scripts/twizzy-kill.sh` | **Emergency stop** - kills everything |
| `./scripts/twizzy-doctor.py` | System diagnostics and repair |
| `./scripts/setup-api-key.py` | Interactive API key configuration |
| `./scripts/install.sh` | Full installation setup |

## Diagnostics

Run the Doctor tool to check system health:

```bash
# Check system health
python scripts/twizzy-doctor.py

# Auto-fix issues
python scripts/twizzy-doctor.py --fix

# Export report
python scripts/twizzy-doctor.py --report health.json
```

## Auto-Start on Login

```bash
# Enable auto-start
launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist

# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist
```

## Configuration

### API Configuration

Create `.env` file for configuration:

```bash
cp .env.example .env
```

Edit `.env`:
```
# Kimi Code API (default)
KIMI_API_PROVIDER=kimi-code
KIMI_API_KEY=your_kimi_code_api_key

# Or use Moonshot Open Platform
# KIMI_API_PROVIDER=moonshot
# KIMI_API_KEY=your_moonshot_key
```

### Permissions

Control via web UI or edit `config/permissions.json`:

| Capability | Description | Default |
|------------|-------------|---------|
| Terminal | Execute shell commands | On |
| Filesystem | Read/write/delete files | On |
| Applications | Launch/quit/control apps | On |
| Browser | Web automation | Off |
| System | System settings | Off |
| UI Control | Mouse/keyboard control | Off |

**Restrictions:**
- **Blocked commands**: `rm -rf /`, `shutdown`, `reboot`, `mkfs`
- **Blocked paths**: `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/Library/Keychains`
- **No sudo** by default

## Architecture

```
TWIZZY/
├── src/
│   ├── web/                       # Web-based GUI
│   │   ├── app.py                 # FastAPI application
│   │   ├── websocket.py           # WebSocket connection manager
│   │   ├── routes/
│   │   │   ├── chat.py            # Chat REST endpoints
│   │   │   ├── config.py          # Settings endpoints
│   │   │   └── improvement.py     # Self-improvement dashboard
│   │   ├── static/
│   │   │   ├── css/style.css      # Dark theme styling
│   │   │   └── js/app.js          # Frontend WebSocket client
│   │   └── templates/
│   │       ├── index.html         # Main chat page
│   │       ├── settings.html      # Settings page
│   │       └── improvements.html  # Improvement history
│   │
│   ├── core/                      # Python agent core
│   │   ├── agent.py               # Main orchestrator
│   │   ├── llm/                   # Kimi API client
│   │   │   └── kimi_client.py     # API client (Kimi Code/Moonshot)
│   │   ├── cache.py               # Multi-tier caching system
│   │   ├── conversation_store.py  # Persistent conversations
│   │   ├── health.py              # Health monitoring
│   │   ├── error_handler.py       # Retry & circuit breakers
│   │   ├── logging_config.py      # Structured logging
│   │   ├── config.py              # Configuration management
│   │   └── permissions.py         # Permission enforcement
│   │
│   ├── plugins/                   # Capability plugins
│   │   ├── terminal/              # Shell command execution
│   │   ├── filesystem/            # File operations with caching
│   │   └── applications/          # App control via AppleScript
│   │
│   ├── improvement/               # Self-improvement system
│   │   ├── analyzer.py            # Opportunity detection
│   │   ├── generator.py           # Code generation
│   │   ├── scheduler.py           # On-demand + idle scheduling
│   │   └── rollback.py            # Git versioning
│   │
│   ├── gateway/                   # Multi-channel messaging (NEW)
│   │   ├── gateway.py             # Gateway control plane
│   │   ├── channel.py             # Base channel interface
│   │   └── channels/              # Channel adapters
│   │       ├── telegram.py        # Telegram bot
│   │       ├── slack.py           # Slack integration
│   │       └── discord.py         # Discord bot
│   │
│   ├── voice/                     # Voice interface (NEW)
│   │   ├── tts.py                 # Text-to-speech
│   │   ├── stt.py                 # Speech-to-text
│   │   └── wake_word.py           # Wake word detection
│   │
│   ├── browser/                   # Browser automation (NEW)
│   │   ├── controller.py          # Playwright controller
│   │   └── snapshot.py            # Page snapshots
│   │
│   ├── canvas/                    # Visual workspace (NEW)
│   │   ├── canvas.py              # Canvas system
│   │   └── renderer.py            # HTML renderer
│   │
│   ├── scheduler/                 # Task scheduling (NEW)
│   │   ├── scheduler.py           # APScheduler wrapper
│   │   └── triggers.py            # Trigger types
│   │
│   ├── skills/                    # Skills platform (NEW)
│   │   ├── skill.py               # Base skill class
│   │   ├── registry.py            # Skill registry
│   │   └── loader.py              # Dynamic loader
│   │
│   ├── doctor/                    # Diagnostics (NEW)
│   │   ├── doctor.py              # Doctor tool
│   │   └── checks.py              # Health checks
│   │
│   └── daemon/
│       └── main.py                # Entry point (uvicorn)
│
├── config/
│   ├── permissions.json           # Permission settings
│   └── launchd/                   # Auto-start config
│
├── logs/                          # Server logs
│   └── twizzy.log
│
└── scripts/
    ├── twizzy-start.sh            # Start web server + browser
    ├── twizzy-kill.sh             # Emergency stop
    ├── twizzy-doctor.py           # Diagnostics
    └── setup-api-key.py           # API key setup
```

## Core Modules

### Web Server (`src/web/`)
- **FastAPI** application with CORS support
- **WebSocket** endpoint for real-time chat
- **Jinja2** templates for HTML pages
- **Static files** served for CSS/JS
- **Auto-reload** via uvicorn --reload

### Kimi API Client (`src/core/llm/kimi_client.py`)
- OpenAI-compatible API client
- Supports **Kimi Code API** (default) and **Moonshot Open Platform**
- Thinking mode with `reasoning_content`
- Tool calling support
- Streaming responses

### Gateway (`src/gateway/`)
- Multi-channel messaging control plane
- DM pairing for security
- Channel adapters for Telegram, Slack, Discord

### Voice (`src/voice/`)
- Multiple TTS engines (macOS say, pyttsx3, ElevenLabs)
- STT via Whisper or Vosk
- Wake word detection via Porcupine

### Browser (`src/browser/`)
- Playwright-based automation
- Page snapshots for LLM consumption
- Stealth mode support

### Canvas (`src/canvas/`)
- Visual workspace for rich outputs
- Multiple element types
- HTML/JSON export

### Scheduler (`src/scheduler/`)
- Cron, interval, and one-time tasks
- APScheduler integration
- Task callbacks for agent integration

### Skills (`src/skills/`)
- Modular capability system
- Dynamic loading
- Lifecycle management

### Agent (`src/core/agent.py`)
- Main orchestrator for all activities
- Conversation state management
- Tool execution with caching
- Self-modifying capabilities

### Caching System (`src/core/cache.py`)
- In-memory cache with TTL
- File content caching
- Command output caching (read-only commands)
- App info caching
- Automatic invalidation on writes

### Conversation Store (`src/core/conversation_store.py`)
- Persistent JSON storage
- Conversation listing and search
- Resume previous conversations
- Metadata support

### Health Monitor (`src/core/health.py`)
- Component health checks
- System resource monitoring
- Circuit breaker pattern
- Status aggregation

### Error Handler (`src/core/error_handler.py`)
- Retry strategies with exponential backoff
- Error boundaries
- Circuit breakers
- Severity classification

## Optional Dependencies

Install extras for additional features:

```bash
# Gateway (Telegram, Slack, Discord)
pip install python-telegram-bot slack-bolt discord.py

# Voice (TTS/STT/Wake word)
pip install pyaudio openai-whisper elevenlabs pvporcupine

# Browser automation
pip install playwright && playwright install

# Task scheduler
pip install apscheduler croniter
```

## Self-Improvement System

### View Improvements
```bash
git log --oneline --grep="AUTO-IMPROVEMENT"
```

### Manual Rollback
```bash
git reset --hard HEAD~1
./scripts/twizzy-start.sh
```

Or use the **Rollback** button in the Improvements page!

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send a message (non-streaming) |
| `/api/status` | GET | Get agent status |
| `/api/clear` | POST | Clear conversation |
| `/api/history` | GET | Get conversation history |
| `/api/permissions` | GET/PUT | Manage permissions |
| `/api/api-key` | POST | Set API key |
| `/api/improvements` | GET | List improvements |
| `/api/improve-now` | POST | Trigger improvement |
| `/api/rollback/{hash}` | POST | Rollback to commit |

### WebSocket

Connect to `/ws/chat` for real-time streaming:

```javascript
const ws = new WebSocket('ws://127.0.0.1:7777/ws/chat');

// Send message
ws.send(JSON.stringify({ type: 'message', content: 'Hello!' }));

// Receive streaming response
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'chunk') {
        console.log(data.content);  // Streaming text
    } else if (data.type === 'done') {
        console.log('Response complete');
    }
};
```

### Available Tools

| Tool | Description |
|------|-------------|
| `execute_terminal_command` | Run shell commands |
| `read_file` | Read file contents |
| `write_file` | Write/create files |
| `list_directory` | List directory contents |
| `move_file` | Move/rename files |
| `delete_file` | Delete files |
| `launch_application` | Open apps |
| `quit_application` | Close apps |
| `list_running_apps` | Get running apps |
| `activate_application` | Bring app to front |

## Logs

```bash
# Server logs
tail -f logs/twizzy.log

# Or if using daemon
tail -f ~/.twizzy/logs/daemon.log
```

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :7777

# Kill existing process
./scripts/twizzy-kill.sh

# Check logs
tail -20 logs/twizzy.log
```

### API key not found
```bash
# Interactive setup
python scripts/setup-api-key.py

# Or manual setup
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY')"
```

Or set it via the web UI at http://127.0.0.1:7777/settings

### Model not available (404)
Your API key may not have access to certain models. Check which models work:
```bash
source .venv/bin/activate
python -c "
import keyring, httpx
from src.core.config import get_kimi_api_key, get_api_provider

key = get_kimi_api_key()
provider = get_api_provider()
base_url = 'https://kimi.com/api/v1' if provider == 'kimi-code' else 'https://api.moonshot.ai/v1'

models = ['kimi-k2.5', 'kimi-k2']
for m in models:
    r = httpx.post(f'{base_url}/chat/completions',
        headers={'Authorization': f'Bearer {key}'},
        json={'model': m, 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 5},
        timeout=30)
    print(f'{m}: {\"OK\" if r.status_code == 200 else r.status_code}')
"
```

### WebSocket not connecting
```bash
# Check server is running
curl http://127.0.0.1:7777/api/status

# Restart everything
./scripts/twizzy-kill.sh
./scripts/twizzy-start.sh
```

### Self-improvement broke something
```bash
cd ~/Desktop/TWIZZY
git reset --hard HEAD~1
./scripts/twizzy-start.sh
```

Or use the **Rollback** button in the Improvements page!

## Requirements

- macOS 14.0+
- Python 3.11+
- Kimi Code API key from [kimi.com/code](https://www.kimi.com/code) (Settings → API Keys)
- Or Moonshot Open Platform key from [platform.moonshot.ai](https://platform.moonshot.ai/)
- Modern web browser (Chrome, Safari, Firefox)

## License

MIT

---

Built with Kimi Code API by TWIZZY (and Claude)

## Acknowledgments

Features inspired by [OpenClaw](https://github.com/openclaw/openclaw):
- Multi-channel Gateway architecture
- Voice interface (Wake + Talk Mode)
- Browser automation
- Canvas visual workspace
- Task scheduling
- Skills platform
- Doctor diagnostic tool
