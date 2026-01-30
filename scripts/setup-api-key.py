#!/usr/bin/env python3
"""
TWIZZY API Key Setup - Interactive configuration tool.

Usage:
    python scripts/setup-api-key.py
    
This will:
1. Check current API key status
2. Prompt for your Kimi API key
3. Store it securely in your Keychain
4. Optionally create a .env file as backup
"""

import getpass
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import get_kimi_api_key, set_kimi_api_key


def main():
    print("🔐 TWIZZY API Key Setup\n")
    print("=" * 50)
    
    # Check current status
    existing_key = get_kimi_api_key()
    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        print(f"✅ API key already configured: {masked}")
        print()
        response = input("Do you want to update it? (y/N): ").lower()
        if response != 'y':
            print("Keeping existing API key.")
            return
    else:
        print("⚠️  No API key configured yet.")
    
    print()
    print("Get your Kimi API key from: https://platform.moonshot.ai/")
    print()
    
    # Get API key from user
    api_key = getpass.getpass("Enter your Kimi API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    if not api_key.startswith("sk-"):
        print("⚠️  Warning: Kimi API keys usually start with 'sk-'")
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            return
    
    print()
    print("Where would you like to store the API key?")
    print("  1. Keychain (macOS Secure Storage) - Recommended")
    print("  2. .env file (plain text, easier for development)")
    print("  3. Both")
    print()
    
    choice = input("Choice (1/2/3) [1]: ").strip() or "1"
    
    method_map = {
        "1": "keychain",
        "2": "env",
        "3": "both"
    }
    
    method = method_map.get(choice, "keychain")
    
    # Store the key
    if set_kimi_api_key(api_key, method=method):
        print()
        print("✅ API key saved successfully!")
        
        if method in ("env", "both"):
            env_path = Path(__file__).parent.parent / ".env"
            print(f"   Stored in: {env_path}")
            
            # Add to .gitignore if not already there
            gitignore = Path(__file__).parent.parent / ".gitignore"
            if gitignore.exists():
                content = gitignore.read_text()
                if ".env" not in content:
                    with open(gitignore, "a") as f:
                        f.write("\n# Environment variables\n.env\n")
                    print("   Added .env to .gitignore")
        
        if method in ("keychain", "both"):
            print("   Stored in: macOS Keychain (Keychain Access app)")
        
        print()
        print("You can now run TWIZZY:")
        print("  ./scripts/twizzy-start.sh")
        
    else:
        print()
        print("❌ Failed to save API key.")
        print("You can manually set it with:")
        print("  export KIMI_API_KEY=your_key_here")


if __name__ == "__main__":
    main()
