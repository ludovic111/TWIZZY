# 🔐 TWIZZY API Key Setup Guide

TWIZZY needs a Kimi API key to function. This guide explains how to get and store your API key securely.

---

## 🚀 Quick Start (Choose One Method)

### Method 1: Interactive Setup (Recommended)

```bash
python scripts/setup-api-key.py
```

This will:
- Prompt for your API key
- Store it securely in your macOS Keychain
- Optionally create a `.env` file

---

### Method 2: Environment Variable (Temporary)

```bash
export KIMI_API_KEY="sk-your-key-here"
./scripts/twizzy-start.sh
```

⚠️ **Note:** This only lasts for your current terminal session.

---

### Method 3: .env File (Development)

```bash
# Copy the example file
cp .env.example .env

# Edit with your API key
nano .env  # or use any editor
```

Add your key:
```
KIMI_API_KEY=sk-your-actual-key-here
```

---

### Method 4: macOS Keychain (Most Secure)

```bash
# Store in Keychain (survives reboots)
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', 'sk-your-key-here')"
```

---

## 📋 Where to Get Your API Key

1. Go to [https://platform.moonshot.ai/](https://platform.moonshot.ai/)
2. Sign up or log in
3. Go to "API Keys" section
4. Create a new key
5. Copy the key (starts with `sk-`)

---

## 🔍 Storage Priority

TWIZZY checks for your API key in this order:

1. **Environment Variable** (`KIMI_API_KEY`) - Highest priority, overrides others
2. **macOS Keychain** - Secure persistent storage
3. **.env File** - Convenient for development

---

## 🛡️ Security Recommendations

### For Daily Use (Most Secure)
```bash
python scripts/setup-api-key.py
# Choose option 1 (Keychain)
```

### For Development
```bash
python scripts/setup-api-key.py
# Choose option 3 (Both)
```

This stores in both Keychain (primary) and `.env` (backup).

**Important:** The `.env` file is automatically added to `.gitignore` so you won't accidentally commit it.

---

## ✅ Verify Your Setup

```bash
# Run diagnostics
python scripts/twizzy-doctor.py

# Or test the API key directly
python -c "
from src.core.config import get_kimi_api_key
key = get_kimi_api_key()
if key:
    print(f'✅ API key configured: {key[:8]}...{key[-4:]}')
else:
    print('❌ No API key found')
"
```

---

## 🔄 Switching Storage Methods

### Move from .env to Keychain
```bash
# Read from .env and store in Keychain
export $(cat .env | grep KIMI_API_KEY | xargs)
python -c "import keyring; keyring.set_password('com.twizzy.agent', 'kimi_api_key', '$KIMI_API_KEY')"
rm .env  # Optional: remove .env file
```

### Move from Keychain to .env
```bash
python scripts/setup-api-key.py
# Choose option 2 (.env file)
```

---

## 🐛 Troubleshooting

### "API key not found" error

1. Check if key is set:
```bash
python -c "from src.core.config import get_kimi_api_key; print(get_kimi_api_key()[:10] if get_kimi_api_key() else 'Not found')"
```

2. Try setting via environment:
```bash
export KIMI_API_KEY="sk-your-key"
python -m uvicorn src.web.app:app --reload
```

### Keychain access denied

If you get keychain permission errors:
1. Open "Keychain Access" app
2. Find "com.twizzy.agent" entry
3. Right-click → Get Info → Access Control
4. Add your Python/Terminal

### .env file not loading

Make sure you're running from the project root:
```bash
cd ~/Desktop/TWIZZY
source .venv/bin/activate
python -m uvicorn src.web.app:app --reload
```

---

## 🔑 Additional API Keys (Optional)

Some features need additional keys. Edit `.env` file:

```bash
# ElevenLabs for better voice (optional)
ELEVENLABS_API_KEY=your_key_here

# OpenAI for Whisper STT fallback (optional)
OPENAI_API_KEY=your_key_here

# Discord bot (optional)
DISCORD_TOKEN=your_token_here

# Telegram bot (optional)
TELEGRAM_TOKEN=your_token_here

# Slack bot (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
```

---

## 📊 Storage Comparison

| Method | Persistence | Security | Best For |
|--------|-------------|----------|----------|
| Keychain | ✅ Permanent | 🔐 Encrypted | Daily use |
| .env file | ✅ Permanent | ⚠️ Plain text | Development |
| Environment | ❌ Session only | 🔐 Encrypted | CI/CD, Docker |
| Web UI | ✅ Keychain | 🔐 Encrypted | One-time setup |

---

## 🆘 Still Having Issues?

1. Run diagnostics:
```bash
python scripts/twizzy-doctor.py --fix
```

2. Check the logs:
```bash
tail -f logs/twizzy.log
```

3. Reset and try again:
```bash
# Clear any existing keys
python -c "import keyring; keyring.delete_password('com.twizzy.agent', 'kimi_api_key')"
rm -f .env

# Start fresh
python scripts/setup-api-key.py
```
