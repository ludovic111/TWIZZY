"""Permission enforcement for TWIZZY.

This module checks every agent action against user-configured permissions.
"""
import fnmatch
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .config import CapabilityConfig, PermissionsConfig, load_permissions

logger = logging.getLogger(__name__)


class PermissionResult(Enum):
    """Result of a permission check."""

    ALLOWED = "allowed"
    DENIED_DISABLED = "denied_disabled"
    DENIED_RESTRICTED = "denied_restricted"


@dataclass
class PermissionCheckResult:
    """Result of checking a permission."""

    result: PermissionResult
    reason: str | None = None


class PermissionEnforcer:
    """Enforces user-configured permissions on agent actions.

    This is the gatekeeper - EVERY action must pass through here before execution.
    """

    def __init__(self, config: PermissionsConfig | None = None):
        self.config = config or load_permissions()
        self._reload_callbacks: list = []

    def reload(self):
        """Reload permissions from disk."""
        self.config = load_permissions()
        logger.info("Permissions reloaded")
        for callback in self._reload_callbacks:
            callback(self.config)

    def on_reload(self, callback):
        """Register a callback for when permissions are reloaded."""
        self._reload_callbacks.append(callback)

    # ========================
    # Terminal permissions
    # ========================

    def check_terminal_command(self, command: str) -> PermissionCheckResult:
        """Check if a terminal command is allowed."""
        cap = self.config.terminal

        if not cap.enabled:
            return PermissionCheckResult(
                PermissionResult.DENIED_DISABLED,
                "Terminal capability is disabled"
            )

        # Check for sudo if not allowed
        if not cap.restrictions.allow_sudo:
            if re.match(r"^\s*sudo\s+", command) or "| sudo" in command:
                return PermissionCheckResult(
                    PermissionResult.DENIED_RESTRICTED,
                    "sudo commands are not allowed"
                )

        # Check blocked commands
        for blocked in cap.restrictions.blocked_commands:
            if blocked in command:
                return PermissionCheckResult(
                    PermissionResult.DENIED_RESTRICTED,
                    f"Command contains blocked pattern: {blocked}"
                )

        return PermissionCheckResult(PermissionResult.ALLOWED)

    # ========================
    # Filesystem permissions
    # ========================

    def check_file_read(self, path: str) -> PermissionCheckResult:
        """Check if reading a file is allowed."""
        return self._check_filesystem_access(path, "read")

    def check_file_write(self, path: str) -> PermissionCheckResult:
        """Check if writing to a file is allowed."""
        return self._check_filesystem_access(path, "write")

    def check_file_delete(self, path: str) -> PermissionCheckResult:
        """Check if deleting a file is allowed."""
        return self._check_filesystem_access(path, "delete")

    def _check_filesystem_access(self, path: str, operation: str) -> PermissionCheckResult:
        """Check if a filesystem operation is allowed."""
        cap = self.config.filesystem

        if not cap.enabled:
            return PermissionCheckResult(
                PermissionResult.DENIED_DISABLED,
                "Filesystem capability is disabled"
            )

        # Normalize and expand path
        try:
            normalized = str(Path(path).expanduser().resolve())
        except Exception:
            return PermissionCheckResult(
                PermissionResult.DENIED_RESTRICTED,
                f"Invalid path: {path}"
            )

        # Check blocked paths first (takes precedence)
        for blocked in cap.restrictions.blocked_paths:
            blocked_expanded = str(Path(blocked).expanduser().resolve())
            if normalized.startswith(blocked_expanded):
                return PermissionCheckResult(
                    PermissionResult.DENIED_RESTRICTED,
                    f"Path is in blocked location: {blocked}"
                )

        # If allowed_paths is empty, allow all (except blocked)
        if not cap.restrictions.allowed_paths:
            return PermissionCheckResult(PermissionResult.ALLOWED)

        # Check if path is in allowed paths
        for allowed in cap.restrictions.allowed_paths:
            allowed_expanded = str(Path(allowed).expanduser().resolve())
            if normalized.startswith(allowed_expanded):
                return PermissionCheckResult(PermissionResult.ALLOWED)

        return PermissionCheckResult(
            PermissionResult.DENIED_RESTRICTED,
            f"Path is not in allowed locations for {operation}"
        )

    # ========================
    # Application permissions
    # ========================

    def check_app_launch(self, app_name: str) -> PermissionCheckResult:
        """Check if launching an application is allowed."""
        return self._check_app_access(app_name, "launch")

    def check_app_quit(self, app_name: str) -> PermissionCheckResult:
        """Check if quitting an application is allowed."""
        return self._check_app_access(app_name, "quit")

    def check_app_control(self, app_name: str) -> PermissionCheckResult:
        """Check if controlling an application is allowed."""
        return self._check_app_access(app_name, "control")

    def _check_app_access(self, app_name: str, operation: str) -> PermissionCheckResult:
        """Check if an application operation is allowed."""
        cap = self.config.applications

        if not cap.enabled:
            return PermissionCheckResult(
                PermissionResult.DENIED_DISABLED,
                "Applications capability is disabled"
            )

        # Check blocked apps
        for blocked in cap.restrictions.blocked_apps:
            if fnmatch.fnmatch(app_name.lower(), blocked.lower()):
                return PermissionCheckResult(
                    PermissionResult.DENIED_RESTRICTED,
                    f"Application is blocked: {app_name}"
                )

        # Check allowed apps
        allowed_list = cap.restrictions.allowed_apps
        if "*" in allowed_list:
            return PermissionCheckResult(PermissionResult.ALLOWED)

        for allowed in allowed_list:
            if fnmatch.fnmatch(app_name.lower(), allowed.lower()):
                return PermissionCheckResult(PermissionResult.ALLOWED)

        return PermissionCheckResult(
            PermissionResult.DENIED_RESTRICTED,
            f"Application not in allowed list: {app_name}"
        )

    # ========================
    # Convenience methods
    # ========================

    def is_terminal_enabled(self) -> bool:
        """Check if terminal capability is enabled."""
        return self.config.terminal.enabled

    def is_filesystem_enabled(self) -> bool:
        """Check if filesystem capability is enabled."""
        return self.config.filesystem.enabled

    def is_applications_enabled(self) -> bool:
        """Check if applications capability is enabled."""
        return self.config.applications.enabled

    def get_enabled_capabilities(self) -> list[str]:
        """Get list of enabled capability names."""
        enabled = []
        if self.config.terminal.enabled:
            enabled.append("terminal")
        if self.config.filesystem.enabled:
            enabled.append("filesystem")
        if self.config.applications.enabled:
            enabled.append("applications")
        if self.config.browser.enabled:
            enabled.append("browser")
        if self.config.system.enabled:
            enabled.append("system")
        if self.config.ui_control.enabled:
            enabled.append("ui_control")
        return enabled


# Global permission enforcer instance
_enforcer: PermissionEnforcer | None = None


def get_enforcer() -> PermissionEnforcer:
    """Get the global permission enforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = PermissionEnforcer()
    return _enforcer


def check_permission(capability: str, action: str, **kwargs) -> PermissionCheckResult:
    """Check if an action is allowed.

    This is the main entry point for permission checks.

    Args:
        capability: The capability (terminal, filesystem, applications)
        action: The specific action
        **kwargs: Action-specific parameters

    Returns:
        PermissionCheckResult indicating if the action is allowed
    """
    enforcer = get_enforcer()

    if capability == "terminal":
        return enforcer.check_terminal_command(kwargs.get("command", ""))

    elif capability == "filesystem":
        path = kwargs.get("path", "")
        if action == "read":
            return enforcer.check_file_read(path)
        elif action == "write":
            return enforcer.check_file_write(path)
        elif action == "delete":
            return enforcer.check_file_delete(path)
        else:
            return enforcer.check_file_read(path)  # Default to read check

    elif capability == "applications":
        app_name = kwargs.get("app_name", "")
        if action == "launch":
            return enforcer.check_app_launch(app_name)
        elif action == "quit":
            return enforcer.check_app_quit(app_name)
        else:
            return enforcer.check_app_control(app_name)

    # Default: allow if not explicitly handled
    return PermissionCheckResult(PermissionResult.ALLOWED)
