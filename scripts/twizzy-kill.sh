#!/bin/bash
# TWIZZY Emergency Kill Switch
# Run this if TWIZZY goes crazy

echo "🛑 TWIZZY EMERGENCY KILL SWITCH"
echo "================================"

# Stop the launchd service
echo "Stopping launchd service..."
launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist 2>/dev/null

# Kill all Python processes related to TWIZZY
echo "Killing TWIZZY daemon..."
pkill -f "src.daemon.main" 2>/dev/null

# Kill the GUI
echo "Killing TWIZZY GUI..."
pkill -f "TwizzyApp" 2>/dev/null

# Remove the socket
echo "Cleaning up socket..."
rm -f /tmp/twizzy.sock 2>/dev/null

echo ""
echo "✅ TWIZZY has been killed!"
echo ""
echo "To restart later:"
echo "  launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist"
echo ""
echo "To rollback last self-improvement:"
echo "  cd ~/Desktop/TWIZZY && git reset --hard HEAD~1"
