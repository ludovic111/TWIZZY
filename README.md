# TWIZZY

An autonomous, self-improving Mac agent powered by **Kimi K2.5** that controls your entire system through natural language.

![macOS](https://img.shields.io/badge/macOS-14.0+-purple)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Swift](https://img.shields.io/badge/Swift-5.9+-orange)
![Kimi K2.5](https://img.shields.io/badge/Kimi-K2.5-green)

## Features

### Core Capabilities
- **Natural Language Control** - Chat interface to control your Mac
- **Full System Access** - Terminal, files, and application control
- **Customizable Permissions** - Toggle what TWIZZY can access
- **Persistent Conversations** - Resume previous conversations across restarts
- **Auto-Start** - Runs as a background service, starts on login

### Powered by Kimi K2.5
- **Thinking Mode** - Advanced reasoning with `reasoning_content` support
- **Tool Calling** - Native function calling for system control
- **128K Context** - Long conversation memory
- **Vision Support** - Can understand images (coming soon)

### Self-Improvement System
- **Automatic Analysis** - Detects failures and slow operations during idle time
- **Code Generation** - Uses Kimi K2.5 to write improvements
- **Safe Testing** - Tests in Docker sandbox before deploying
- **Git Integration** - All changes committed with automatic rollback
- **Can Modify Itself** - Direct access to its own source code

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
swift build
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

**Or manually:**
```bash
# Terminal 1: Start daemon
source .venv/bin/activate
python -m src.daemon.main

# Terminal 2: Open GUI
open TwizzyApp.app
```

## Usage

### GUI App
- **Dock Icon** - Purple brain icon in your dock
- **Chat** - Type commands naturally
- **Permissions** - Toggle capabilities in the sidebar
- **Menu Bar** - Quick access from menu bar icon

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
| `./scripts/twizzy-start.sh` | Start TWIZZY (daemon + GUI) |
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

Control via GUI or edit `config/permissions.json`:

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
├── TwizzyApp.app/              # macOS app bundle (GUI)
├── TwizzyApp/                  # SwiftUI source code
│   ├── Views/                  # Chat, Permissions, Settings
│   ├── Services/               # AgentBridge (Unix socket client)
│   └── Models/                 # Data models
├── src/
│   ├── core/                   # Python agent core
│   │   ├── agent.py            # Main orchestrator
│   │   ├── llm/                # Kimi K2.5 client
│   │   │   └── kimi_client.py  # API client with thinking mode
│   │   ├── ipc/                # Unix socket server (JSON-RPC)
│   │   ├── cache.py            # Multi-tier caching system
│   │   ├── conversation_store.py # Persistent conversations
│   │   ├── health.py           # Health monitoring
│   │   ├── error_handler.py    # Retry & circuit breakers
│   │   ├── logging_config.py   # Structured logging
│   │   ├── config.py           # Configuration management
│   │   └── permissions.py      # Permission enforcement
│   ├── plugins/                # Capability plugins
│   │   ├── terminal/           # Shell command execution
│   │   ├── filesystem/         # File operations with caching
│   │   └── applications/       # App control via AppleScript
│   ├── improvement/            # Self-improvement system
│   │   ├── analyzer.py         # Opportunity detection
│   │   ├── generator.py        # Code generation
│   │   ├── scheduler.py        # Idle-time scheduling
│   │   └── sandbox.py          # Docker sandbox testing
│   └── daemon/                 # Background service
│       └── main.py             # Entry point
├── config/
│   ├── permissions.json        # Permission settings
│   └── launchd/                # Auto-start config
└── scripts/
    ├── twizzy-start.sh         # Start everything
    └── twizzy-kill.sh          # Emergency stop
```

## Core Modules

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

TWIZZY can analyze and improve its own code:

1. **Detection** - Monitors for failures, slow operations, missing capabilities
2. **Analysis** - During idle time (5+ min), analyzes improvement opportunities
3. **Generation** - Uses Kimi K2.5 to write improvements
4. **Testing** - Tests in Docker sandbox
5. **Deployment** - Commits to Git with `AUTO-IMPROVEMENT` tag
6. **Rollback** - Automatic revert if errors increase

### View Improvements
```bash
git log --oneline --grep="AUTO-IMPROVEMENT"
```

### Manual Rollback
```bash
git reset --hard HEAD~1
./scripts/twizzy-start.sh
```

## Logs

```bash
# Daemon logs
tail -f ~/.twizzy/logs/daemon.log

# Stdout/stderr
tail -f ~/.twizzy/logs/stdout.log
tail -f ~/.twizzy/logs/stderr.log

# Error log (structured)
tail -f ~/.twizzy/logs/error.log
```

## Troubleshooting

### App won't start
```bash
# Check daemon
ps aux | grep "src.daemon.main"

# Check logs
tail -20 ~/.twizzy/logs/daemon.log
```

### API key not found
```bash
source .venv/bin/activate
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY')"
```

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

### GUI not connecting
```bash
# Check socket exists
ls -la /tmp/twizzy.sock

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

## API Reference

### IPC Protocol (JSON-RPC 2.0)

TWIZZY uses Unix socket at `/tmp/twizzy.sock`:

```bash
# Send a chat message
echo '{"jsonrpc":"2.0","method":"chat","params":{"user_message":"hello"},"id":1}' | nc -U /tmp/twizzy.sock

# Get status
echo '{"jsonrpc":"2.0","method":"status","params":{},"id":1}' | nc -U /tmp/twizzy.sock

# Clear conversation
echo '{"jsonrpc":"2.0","method":"clear","params":{},"id":1}' | nc -U /tmp/twizzy.sock
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

## Requirements

- macOS 14.0+
- Python 3.11+
- Swift 5.9+
- Kimi API key from [Moonshot AI](https://platform.moonshot.ai/)

## License

MIT

---

Built with Kimi K2.5 by TWIZZY (and Claude)
