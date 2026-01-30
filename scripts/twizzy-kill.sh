#!/bin/bash
# TWIZZY Emergency Kill Switch
# Run this if TWIZZY goes crazy

echo "TWIZZY EMERGENCY KILL SWITCH"
echo "============================"

# Stop the launchd service (if using)
echo "Stopping launchd service..."
launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist 2>/dev/null

# Kill uvicorn web server
echo "Killing web server..."
pkill -f "uvicorn.*src.web.app" 2>/dev/null

# Kill any remaining Python processes related to TWIZZY
echo "Killing TWIZZY processes..."
pkill -f "src.daemon.main" 2>/dev/null
pkill -f "src.web.app" 2>/dev/null

echo ""
echo "TWIZZY has been stopped!"
echo ""
echo "To restart:"
echo "  ./scripts/twizzy-start.sh"
echo ""
echo "To rollback last self-improvement:"
echo "  cd ~/Desktop/TWIZZY && git reset --hard HEAD~1"
echo ""
echo "To view recent improvements:"
echo "  git log --oneline --grep=AUTO-IMPROVEMENT -10"
