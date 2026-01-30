"""Terminal plugin - Execute shell commands.

This plugin allows the agent to run terminal commands with permission checking.
"""
import asyncio
import logging
import os
import shlex
from pathlib import Path

from ..base import CapabilityPlugin, Tool, ToolResult
from ...core.permissions import check_permission, PermissionResult

logger = logging.getLogger(__name__)


class TerminalPlugin(CapabilityPlugin):
    """Plugin for executing terminal commands."""

    @property
    def name(self) -> str:
        return "terminal"

    @property
    def description(self) -> str:
        return "Execute shell commands in the terminal"

    @property
    def capability(self) -> str:
        return "terminal"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="execute_terminal_command",
                description="Execute a shell command and return the output",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Directory to run command in (optional)"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds (default 60)"
                        }
                    },
                    "required": ["command"]
                },
                handler=self._execute_command,
                required_permission=("terminal", "execute"),
            ),
        ]

    async def _execute_command(
        self,
        command: str,
        working_directory: str | None = None,
        timeout: float = 60.0,
    ) -> ToolResult:
        """Execute a shell command.

        Args:
            command: The command to execute
            working_directory: Optional directory to run in
            timeout: Command timeout in seconds

        Returns:
            ToolResult with command output
        """
        # Check permission
        perm_check = check_permission("terminal", "execute", command=command)
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        # Resolve working directory
        cwd = None
        if working_directory:
            cwd = Path(working_directory).expanduser().resolve()
            if not cwd.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Working directory does not exist: {working_directory}"
                )

        logger.info(f"Executing command: {command}")

        try:
            # Run command in shell
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=os.environ.copy(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command timed out after {timeout} seconds"
                )

            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            # Combine output
            output = stdout_str
            if stderr_str:
                if output:
                    output += f"\n\nStderr:\n{stderr_str}"
                else:
                    output = stderr_str

            success = process.returncode == 0

            if not success:
                output = f"Command exited with code {process.returncode}\n\n{output}"

            return ToolResult(
                success=success,
                output=output,
                error=None if success else f"Exit code: {process.returncode}"
            )

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
