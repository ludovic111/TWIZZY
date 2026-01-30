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
    """Get Kimi API key from Keychain or environment."""
    # Try Keychain first
    key = SecureConfig.get_api_key("kimi_api_key")
    if key:
        return key

    # Fall back to environment variable
    return os.environ.get("KIMI_API_KEY")
