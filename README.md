# TWIZZY

An autonomous Mac agent with self-improving capabilities.

## Features

- **Natural Language Control**: Chat interface to control your Mac
- **Full Mac Integration**: Terminal, file management, app control
- **Customizable Permissions**: Toggle what TWIZZY can access
- **Self-Improving**: Automatically improves itself during idle time
- **Persistent Background Service**: Runs via launchd

## Quick Start

1. **Install dependencies**:
   ```bash
   cd ~/Desktop/TWIZZY
   ./scripts/install.sh
   ```

2. **Set your Kimi API key**:
   ```bash
   export KIMI_API_KEY="your-api-key"
   ```

3. **Run the agent**:
   ```bash
   python3 -m src.daemon.main
   ```

4. **Build and run the GUI**:
   ```bash
   swift build
   swift run TwizzyApp
   ```

## Architecture

```
TWIZZY/
├── TwizzyApp/          # SwiftUI GUI
├── src/
│   ├── core/           # Agent core & Kimi client
│   ├── plugins/        # Capability plugins
│   ├── improvement/    # Self-improvement system
│   └── daemon/         # Background service
└── config/             # Permissions & launchd
```

## Permissions

Control what TWIZZY can do via the Permissions panel:
- **Terminal**: Execute shell commands
- **Filesystem**: Read/write files
- **Applications**: Launch/quit apps

## Self-Improvement

TWIZZY uses aggressive self-improvement:
- Analyzes your usage patterns
- Generates code improvements using Kimi 2.5k
- Tests changes in Docker sandbox
- Deploys with Git tracking
- Auto-rollback on errors

All changes are committed to Git, so you can always rollback:
```bash
cd ~/Desktop/TWIZZY
git log --oneline --grep="AUTO-IMPROVEMENT"
git reset --hard HEAD~1  # Undo last improvement
```

## License

MIT
