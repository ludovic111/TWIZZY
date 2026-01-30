# TWIZZY

An autonomous, self-improving Mac agent powered by **Kimi K2.5** that controls your entire system through natural language.

![macOS](https://img.shields.io/badge/macOS-14.0+-purple)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Kimi K2.5](https://img.shields.io/badge/Kimi-K2.5-green)
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

### Powered by Kimi K2.5
- **Thinking Mode** - Advanced reasoning with `reasoning_content` support
- **Tool Calling** - Native function calling for system control
- **128K Context** - Long conversation memory
- **Vision Support** - Can understand images (coming soon)

### Self-Improvement System (Always-On)
- **Continuous Analysis** - Detects failures and slow operations anytime
- **On-Demand Improvement** - Trigger improvements from the web UI
- **Code Generation** - Uses Kimi K2.5 to write improvements
- **Safe Testing** - Tests before deploying
- **Git Integration** - All changes committed with automatic rollback
- **Auto-Reload** - Server automatically reloads after self-modification

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

Get your Kimi API key from [platform.moonshot.ai](https://platform.moonshot.ai/) and store it:

```bash
source .venv/bin/activate
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY_HERE')"
```

**Available Models** (check your API access):
| Model | Description |
|-------|-------------|
| `kimi-k2.5` | Latest with vision + tool use |
| `kimi-k2-0905-preview` | Kimi K2 (September 2025) |
| `kimi-k2-0711-preview` | Kimi K2 (July 2025) |
| `moonshot-v1-128k` | Legacy 128K context |

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
| `./scripts/install.sh` | Full installation setup |

## Auto-Start on Login

```bash
# Enable auto-start
launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist

# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist
```

## Configuration

### API Configuration

Edit `src/core/llm/kimi_client.py` to change model settings:

```python
@dataclass
class KimiConfig:
    api_key: str
    base_url: str = "https://api.moonshot.ai/v1"
    model: str = "kimi-k2.5"          # Model to use
    temperature: float = 0.6           # 0.6 for instant, 1.0 for thinking
    max_tokens: int = 8192
    thinking: bool = True              # Enable K2.5 thinking mode
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
│   │   ├── llm/                   # Kimi K2.5 client
│   │   │   └── kimi_client.py     # API client with thinking mode
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
│   ├── improvement/               # Self-improvement system (always-on)
│   │   ├── analyzer.py            # Opportunity detection
│   │   ├── generator.py           # Code generation
│   │   ├── scheduler.py           # On-demand + idle scheduling
│   │   └── rollback.py            # Git versioning
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
    └── twizzy-kill.sh             # Emergency stop
```

## Core Modules

### Web Server (`src/web/`)
- **FastAPI** application with CORS support
- **WebSocket** endpoint for real-time chat
- **Jinja2** templates for HTML pages
- **Static files** served for CSS/JS
- **Auto-reload** via uvicorn --reload

### Kimi K2.5 Client (`src/core/llm/kimi_client.py`)
- OpenAI-compatible API client
- Thinking mode with `reasoning_content`
- Tool calling support
- Streaming responses

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

## Self-Improvement System

TWIZZY can analyze and improve its own code **anytime** (not just during idle):

1. **Detection** - Monitors for failures, slow operations, missing capabilities
2. **Trigger** - Click "Improve Now" in web UI or wait for idle detection
3. **Generation** - Uses Kimi K2.5 to write improvements
4. **Testing** - Validates changes before applying
5. **Deployment** - Commits to Git with `AUTO-IMPROVEMENT` tag
6. **Auto-Reload** - Server reloads automatically, no restart needed
7. **Rollback** - One-click revert if something breaks

### View Improvements
```bash
git log --oneline --grep="AUTO-IMPROVEMENT"
```

### Manual Rollback
```bash
git reset --hard HEAD~1
./scripts/twizzy-start.sh
```

Or use the **Rollback** button in the web UI!

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
source .venv/bin/activate
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY')"
```

Or set it via the web UI at http://127.0.0.1:7777/settings

### Model not available (404)
Your API key may not have access to certain models. Check which models work:
```bash
source .venv/bin/activate
python -c "
import keyring, httpx
key = keyring.get_password('com.twizzy.agent', 'kimi_api_key')
models = ['kimi-k2.5', 'kimi-k2-0905-preview', 'moonshot-v1-128k']
for m in models:
    r = httpx.post('https://api.moonshot.ai/v1/chat/completions',
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
- Kimi API key from [Moonshot AI](https://platform.moonshot.ai/)
- Modern web browser (Chrome, Safari, Firefox)

## License

MIT

---

Built with Kimi K2.5 by TWIZZY (and Claude)
