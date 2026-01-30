#!/bin/bash
# TWIZZY Installation Script
# This script sets up TWIZZY on your Mac

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       TWIZZY Installation Script          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TWIZZY_HOME="$HOME/.twizzy"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "Project directory: $PROJECT_DIR"
echo "TWIZZY home: $TWIZZY_HOME"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "Found Python $PYTHON_VERSION"

    # Check if version is 3.11 or higher
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
        echo -e "${RED}Error: Python 3.11 or higher required${NC}"
        exit 1
    fi
else
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

# Create TWIZZY home directory
echo -e "${YELLOW}Creating TWIZZY home directory...${NC}"
mkdir -p "$TWIZZY_HOME/logs"
echo "Created $TWIZZY_HOME"

# Create virtual environment and install dependencies
echo -e "${YELLOW}Creating virtual environment...${NC}"
cd "$PROJECT_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -e . --quiet
echo "Virtual environment created and dependencies installed"
echo ""
echo -e "${GREEN}To activate the environment, run:${NC}"
echo "  source $PROJECT_DIR/.venv/bin/activate"

# Setup launchd agent
echo -e "${YELLOW}Setting up launchd agent...${NC}"
mkdir -p "$LAUNCH_AGENTS"

# Create plist with correct paths
PLIST_FILE="$LAUNCH_AGENTS/com.twizzy.agent.plist"
sed "s|/Users/USER|$HOME|g" "$PROJECT_DIR/config/launchd/com.twizzy.agent.plist" > "$PLIST_FILE"
echo "Created $PLIST_FILE"

# Check for API key
echo ""
echo -e "${YELLOW}Checking for Kimi API key...${NC}"
if [ -z "$KIMI_API_KEY" ]; then
    echo -e "${YELLOW}No KIMI_API_KEY environment variable found.${NC}"
    echo ""
    read -p "Enter your Kimi API key (or press Enter to skip): " API_KEY
    if [ -n "$API_KEY" ]; then
        # Store in environment file
        echo "export KIMI_API_KEY=\"$API_KEY\"" >> "$TWIZZY_HOME/.env"
        echo "API key saved to $TWIZZY_HOME/.env"
        echo ""
        echo -e "${YELLOW}Add this to your ~/.zshrc or ~/.bashrc:${NC}"
        echo "source $TWIZZY_HOME/.env"
    fi
else
    echo "API key found in environment"
fi

# Build SwiftUI app
echo ""
echo -e "${YELLOW}Building SwiftUI app...${NC}"
cd "$PROJECT_DIR"
if swift build 2>/dev/null; then
    echo "SwiftUI app built successfully"
else
    echo -e "${YELLOW}SwiftUI build skipped (run manually later)${NC}"
fi

# Load launchd agent
echo ""
echo -e "${YELLOW}Loading launchd agent...${NC}"
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"
echo "Agent loaded"

# Initialize git if needed
echo ""
echo -e "${YELLOW}Checking git repository...${NC}"
cd "$PROJECT_DIR"
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit"
    echo "Git repository initialized"
else
    echo "Git repository already exists"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Installation Complete!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "TWIZZY is now running as a background service."
echo ""
echo "Next steps:"
echo "  1. Make sure KIMI_API_KEY is set in your shell"
echo "  2. Run the SwiftUI app: swift run TwizzyApp"
echo "  3. Or use the Python daemon directly: python3 -m src.daemon.main"
echo ""
echo "Useful commands:"
echo "  - Check status: launchctl list | grep twizzy"
echo "  - View logs: tail -f ~/.twizzy/logs/daemon.log"
echo "  - Stop agent: launchctl unload ~/Library/LaunchAgents/com.twizzy.agent.plist"
echo "  - Start agent: launchctl load ~/Library/LaunchAgents/com.twizzy.agent.plist"
echo ""
echo -e "${GREEN}Enjoy TWIZZY!${NC}"
