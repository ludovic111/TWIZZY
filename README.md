# TWIZZY 🧠

An autonomous, self-improving Mac agent that can control your entire system through natural language.

![macOS](https://img.shields.io/badge/macOS-14.0+-purple)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Swift](https://img.shields.io/badge/Swift-5.9+-orange)

## Features

- **🗣️ Natural Language Control** - Chat interface to control your Mac
- **💻 Full System Access** - Terminal, files, and app control
- **🔒 Customizable Permissions** - Toggle what TWIZZY can access
- **🧬 Self-Improving** - Automatically improves itself during idle time
- **🔄 Persistent** - Runs as a background service, starts on login
- **🛡️ Safe** - Git-tracked improvements with instant rollback

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
- **Chat** - Type commands like "list files on my Desktop" or "open Safari"
- **Permissions** - Toggle capabilities in the sidebar
- **Menu Bar** - Quick access from menu bar icon

### Commands You Can Give
```
"List all files on my Desktop"
"Create a file called notes.txt with my meeting notes"
"Open Safari and Finder"
"Run the command 'brew update'"
"What apps are running?"
"Quit Slack"
```

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/twizzy-start.sh` | Start TWIZZY (daemon + GUI) |
| `./scripts/twizzy-kill.sh` | **Emergency stop** - kills everything |
| `./scripts/install.sh` | Full installation setup |

## Auto-Start on Login

TWIZZY can start automatically when you log in:

```bash
# Enable auto-start
launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist

# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist
```

## Self-Improvement System

TWIZZY uses **aggressive self-improvement**:

1. **Analyzes** your usage patterns during idle time (5+ min)
2. **Detects** failures, slow operations, missing capabilities
3. **Generates** code improvements using Kimi 2.5k
4. **Tests** in Docker sandbox before deploying
5. **Commits** all changes to Git
6. **Rolls back** automatically if errors increase

### View Improvements
```bash
git log --oneline --grep="AUTO-IMPROVEMENT"
```

### Rollback
```bash
# Undo last improvement
git reset --hard HEAD~1

# Or use kill script which shows rollback command
./scripts/twizzy-kill.sh
```

## Permissions

Control what TWIZZY can do via the GUI or `config/permissions.json`:

| Capability | Description | Default |
|------------|-------------|---------|
| Terminal | Execute shell commands | ✅ On |
| Filesystem | Read/write/delete files | ✅ On |
| Applications | Launch/quit/control apps | ✅ On |
| Browser | Web automation | ❌ Off |
| System | System settings | ❌ Off |
| UI Control | Mouse/keyboard control | ❌ Off |

### Restrictions
- **Blocked commands**: `rm -rf /`, `shutdown`, `reboot`
- **Blocked paths**: `~/.ssh`, `~/.aws`, `~/.gnupg`
- **No sudo** by default

## Architecture

```
TWIZZY/
├── TwizzyApp.app/        # macOS app bundle (GUI)
├── TwizzyApp/            # SwiftUI source code
│   ├── Views/            # Chat, Permissions, Settings
│   ├── Services/         # Agent communication
│   └── Models/           # Data models
├── src/
│   ├── core/             # Python agent core
│   │   ├── agent.py      # Main orchestrator
│   │   ├── llm/          # Kimi 2.5k client
│   │   └── ipc/          # Unix socket server
│   ├── plugins/          # Capability plugins
│   │   ├── terminal/     # Shell commands
│   │   ├── filesystem/   # File operations
│   │   └── applications/ # App control
│   ├── improvement/      # Self-improvement system
│   └── daemon/           # Background service
├── config/
│   ├── permissions.json  # Your permission settings
│   └── launchd/          # Auto-start config
└── scripts/
    ├── twizzy-start.sh   # Start everything
    └── twizzy-kill.sh    # Emergency stop
```

## Logs

```bash
# Daemon logs
tail -f ~/.twizzy/logs/daemon.log

# Stdout/stderr
tail -f ~/.twizzy/logs/stdout.log
tail -f ~/.twizzy/logs/stderr.log
```

## Troubleshooting

### App won't start
```bash
# Check if daemon is running
ps aux | grep "src.daemon.main"

# Check logs
cat ~/.twizzy/logs/daemon.log | tail -20
```

### API key not found
```bash
# Re-add key
source .venv/bin/activate
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'YOUR_KEY')"
```

### GUI not connecting
```bash
# Restart daemon
./scripts/twizzy-kill.sh
./scripts/twizzy-start.sh
```

### Self-improvement broke something
```bash
# Rollback
cd ~/Desktop/TWIZZY
git reset --hard HEAD~1
./scripts/twizzy-start.sh
```

## Requirements

- macOS 14.0+
- Python 3.11+
- Swift 5.9+
- Kimi API key from [Moonshot AI](https://platform.moonshot.ai/)

## License

MIT

---

Built with 🧠 by TWIZZY (and Claude)
