"""Applications plugin - macOS app control.

This plugin allows the agent to launch, quit, and control macOS applications
using AppleScript and system APIs.
"""
import asyncio
import logging
import subprocess
from typing import Any

from ..base import CapabilityPlugin, Tool, ToolResult
from ...core.permissions import check_permission, PermissionResult

logger = logging.getLogger(__name__)


class ApplicationsPlugin(CapabilityPlugin):
    """Plugin for controlling macOS applications."""

    @property
    def name(self) -> str:
        return "applications"

    @property
    def description(self) -> str:
        return "Launch, quit, and control macOS applications"

    @property
    def capability(self) -> str:
        return "applications"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="launch_application",
                description="Launch a macOS application",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application (e.g., 'Safari', 'Finder')"
                        }
                    },
                    "required": ["app_name"]
                },
                handler=self._launch_application,
                required_permission=("applications", "launch"),
            ),
            Tool(
                name="quit_application",
                description="Quit a running macOS application",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force quit if true (default false)"
                        }
                    },
                    "required": ["app_name"]
                },
                handler=self._quit_application,
                required_permission=("applications", "quit"),
            ),
            Tool(
                name="list_running_apps",
                description="List all currently running applications",
                parameters={
                    "type": "object",
                    "properties": {}
                },
                handler=self._list_running_apps,
                required_permission=("applications", "list"),
            ),
            Tool(
                name="activate_application",
                description="Bring an application to the foreground",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application"
                        }
                    },
                    "required": ["app_name"]
                },
                handler=self._activate_application,
                required_permission=("applications", "control"),
            ),
            Tool(
                name="get_app_info",
                description="Get information about an application",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application"
                        }
                    },
                    "required": ["app_name"]
                },
                handler=self._get_app_info,
                required_permission=("applications", "list"),
            ),
        ]

    async def _run_applescript(self, script: str) -> tuple[bool, str]:
        """Run an AppleScript and return (success, output)."""
        try:
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return True, stdout.decode("utf-8").strip()
            else:
                return False, stderr.decode("utf-8").strip()
        except Exception as e:
            return False, str(e)

    async def _launch_application(self, app_name: str) -> ToolResult:
        """Launch an application."""
        # Check permission
        perm_check = check_permission("applications", "launch", app_name=app_name)
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        logger.info(f"Launching application: {app_name}")

        script = f'tell application "{app_name}" to activate'
        success, output = await self._run_applescript(script)

        if success:
            return ToolResult(
                success=True,
                output=f"Launched {app_name}"
            )
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to launch {app_name}: {output}"
            )

    async def _quit_application(self, app_name: str, force: bool = False) -> ToolResult:
        """Quit an application."""
        # Check permission
        perm_check = check_permission("applications", "quit", app_name=app_name)
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        logger.info(f"Quitting application: {app_name} (force={force})")

        if force:
            # Force quit using killall
            try:
                process = await asyncio.create_subprocess_exec(
                    "killall", app_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                return ToolResult(
                    success=True,
                    output=f"Force quit {app_name}"
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    output=None,
                    error=str(e)
                )
        else:
            script = f'tell application "{app_name}" to quit'
            success, output = await self._run_applescript(script)

            if success:
                return ToolResult(
                    success=True,
                    output=f"Quit {app_name}"
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Failed to quit {app_name}: {output}"
                )

    async def _list_running_apps(self) -> ToolResult:
        """List running applications."""
        script = '''
        tell application "System Events"
            set appList to name of every process whose background only is false
        end tell
        return appList
        '''

        success, output = await self._run_applescript(script)

        if success:
            # Parse AppleScript list output
            apps = [app.strip() for app in output.split(",")]
            return ToolResult(
                success=True,
                output=apps
            )
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to list apps: {output}"
            )

    async def _activate_application(self, app_name: str) -> ToolResult:
        """Bring an application to the foreground."""
        # Check permission
        perm_check = check_permission("applications", "control", app_name=app_name)
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        script = f'tell application "{app_name}" to activate'
        success, output = await self._run_applescript(script)

        if success:
            return ToolResult(
                success=True,
                output=f"Activated {app_name}"
            )
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to activate {app_name}: {output}"
            )

    async def _get_app_info(self, app_name: str) -> ToolResult:
        """Get information about an application."""
        script = f'''
        tell application "System Events"
            set appProcess to first process whose name is "{app_name}"
            set appInfo to {{name:name of appProcess, frontmost:frontmost of appProcess, visible:visible of appProcess}}
        end tell
        return appInfo
        '''

        success, output = await self._run_applescript(script)

        if success:
            # Parse the result
            return ToolResult(
                success=True,
                output={
                    "name": app_name,
                    "raw_info": output,
                }
            )
        else:
            # Try to get path info as fallback
            try:
                process = await asyncio.create_subprocess_exec(
                    "mdfind",
                    f"kMDItemKind == 'Application' && kMDItemDisplayName == '{app_name}'",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                paths = stdout.decode().strip().split("\n")

                if paths and paths[0]:
                    return ToolResult(
                        success=True,
                        output={
                            "name": app_name,
                            "path": paths[0],
                        }
                    )
            except Exception:
                pass

            return ToolResult(
                success=False,
                output=None,
                error=f"Could not get info for {app_name}: {output}"
            )
