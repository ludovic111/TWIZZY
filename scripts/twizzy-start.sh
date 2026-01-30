#!/bin/bash
# Start TWIZZY

echo "🚀 Starting TWIZZY..."

# Load the launchd service
launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist 2>/dev/null

# Start the GUI app
open ~/Desktop/TWIZZY/TwizzyApp.app

echo "✅ TWIZZY started!"
echo "   - Daemon running in background"
echo "   - GUI launched"
echo "   - Check dock for TWIZZY icon"
