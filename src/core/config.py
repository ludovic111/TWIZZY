"""Configuration management for TWIZZY.

Handles loading config from files, environment variables, and the macOS Keychain.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import keyring

logger = logging.getLogger(__name__)

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded .env from {env_path}")
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Default paths
TWIZZY_HOME = Path(os.environ.get("TWIZZY_HOME", Path.home() / ".twizzy"))
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
PERMISSIONS_FILE = CONFIG_DIR / "permissions.json"


@dataclass
class CapabilityRestrictions:
    """Restrictions for a capability."""

    allow_sudo: bool = False
    blocked_commands: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    allowed_apps: list[str] = field(default_factory=lambda: ["*"])
    blocked_apps: list[str] = field(default_factory=list)


@dataclass
class CapabilityConfig:
    """Configuration for a single capability."""

    enabled: bool = True
    restrictions: CapabilityRestrictions = field(default_factory=CapabilityRestrictions)


@dataclass
class PermissionsConfig:
    """User-configurable permissions for agent capabilities."""

    terminal: CapabilityConfig = field(default_factory=CapabilityConfig)
    filesystem: CapabilityConfig = field(default_factory=CapabilityConfig)
    applications: CapabilityConfig = field(default_factory=CapabilityConfig)
    browser: CapabilityConfig = field(default_factory=CapabilityConfig)
    system: CapabilityConfig = field(default_factory=CapabilityConfig)
    ui_control: CapabilityConfig = field(default_factory=CapabilityConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PermissionsConfig":
        """Create from dictionary (e.g., loaded from JSON)."""
        caps = data.get("capabilities", {})

        def parse_capability(name: str) -> CapabilityConfig:
            cap_data = caps.get(name, {})
            restrictions_data = cap_data.get("restrictions", {})
            return CapabilityConfig(
                enabled=cap_data.get("enabled", True),
                restrictions=CapabilityRestrictions(
                    allow_sudo=restrictions_data.get("allow_sudo", False),
                    blocked_commands=restrictions_data.get("blocked_commands", []),
                    allowed_paths=restrictions_data.get("allowed_paths", []),
                    blocked_paths=restrictions_data.get("blocked_paths", []),
                    allowed_apps=restrictions_data.get("allowed_apps", ["*"]),
                    blocked_apps=restrictions_data.get("blocked_apps", []),
                ),
            )

        return cls(
            terminal=parse_capability("terminal"),
            filesystem=parse_capability("filesystem"),
            applications=parse_capability("applications"),
            browser=parse_capability("browser"),
            system=parse_capability("system"),
            ui_control=parse_capability("ui_control"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        def cap_to_dict(cap: CapabilityConfig) -> dict:
            return {
                "enabled": cap.enabled,
                "restrictions": {
                    "allow_sudo": cap.restrictions.allow_sudo,
                    "blocked_commands": cap.restrictions.blocked_commands,
                    "allowed_paths": cap.restrictions.allowed_paths,
                    "blocked_paths": cap.restrictions.blocked_paths,
                    "allowed_apps": cap.restrictions.allowed_apps,
                    "blocked_apps": cap.restrictions.blocked_apps,
                },
            }

        return {
            "capabilities": {
                "terminal": cap_to_dict(self.terminal),
                "filesystem": cap_to_dict(self.filesystem),
                "applications": cap_to_dict(self.applications),
                "browser": cap_to_dict(self.browser),
                "system": cap_to_dict(self.system),
                "ui_control": cap_to_dict(self.ui_control),
            }
        }


class SecureConfig:
    """Secure storage for API keys using macOS Keychain."""

    SERVICE_NAME = "com.twizzy.agent"

    @staticmethod
    def get_api_key(key_name: str) -> str | None:
        """Get an API key from the Keychain."""
        try:
            return keyring.get_password(SecureConfig.SERVICE_NAME, key_name)
        except Exception as e:
            logger.warning(f"Failed to get API key from Keychain: {e}")
            return None

    @staticmethod
    def set_api_key(key_name: str, value: str) -> bool:
        """Store an API key in the Keychain."""
        try:
            keyring.set_password(SecureConfig.SERVICE_NAME, key_name, value)
            return True
        except Exception as e:
            logger.error(f"Failed to store API key in Keychain: {e}")
            return False

    @staticmethod
    def delete_api_key(key_name: str) -> bool:
        """Delete an API key from the Keychain."""
        try:
            keyring.delete_password(SecureConfig.SERVICE_NAME, key_name)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete API key from Keychain: {e}")
            return False


def load_permissions() -> PermissionsConfig:
    """Load permissions from config file."""
    if PERMISSIONS_FILE.exists():
        try:
            with open(PERMISSIONS_FILE) as f:
                data = json.load(f)
            return PermissionsConfig.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")

    return PermissionsConfig()


def save_permissions(config: PermissionsConfig) -> bool:
    """Save permissions to config file."""
    try:
        PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PERMISSIONS_FILE, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save permissions: {e}")
        return False


def get_kimi_api_key() -> str | None:
    """Get Kimi API key from Keychain, .env file, or environment variable.
    
    Priority order:
    1. Environment variable (KIMI_API_KEY) - highest priority
    2. Keychain (secure storage)
    3. .env file (KIMI_API_KEY in .env)
    """
    # 1. Check environment variable first (allows runtime override)
    env_key = os.environ.get("KIMI_API_KEY")
    if env_key:
        return env_key
    
    # 2. Try Keychain (most secure persistent storage)
    key = SecureConfig.get_api_key("kimi_api_key")
    if key:
        return key
    
    # 3. Return None if not found
    return None


def set_kimi_api_key(api_key: str, method: str = "keychain") -> bool:
    """Store Kimi API key securely.
    
    Args:
        api_key: The API key to store
        method: "keychain" (default), "env", or "both"
        
    Returns:
        True if stored successfully
    """
    if method in ("keychain", "both"):
        if SecureConfig.set_api_key("kimi_api_key", api_key):
            logger.info("API key stored in Keychain")
            if method == "keychain":
                return True
        else:
            logger.error("Failed to store API key in Keychain")
            if method == "keychain":
                return False
    
    if method in ("env", "both"):
        env_path = Path(__file__).parent.parent.parent / ".env"
        try:
            # Read existing content
            if env_path.exists():
                content = env_path.read_text()
            else:
                content = "# TWIZZY Environment Configuration\n"
            
            # Update or add KIMI_API_KEY
            lines = content.split('\n')
            new_lines = []
            found = False
            for line in lines:
                if line.startswith('KIMI_API_KEY='):
                    new_lines.append(f'KIMI_API_KEY={api_key}')
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(f'KIMI_API_KEY={api_key}')
            
            env_path.write_text('\n'.join(new_lines))
            logger.info(f"API key stored in {env_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write .env file: {e}")
            return False
    
    return False
