"""Filesystem plugin - File and directory operations.

This plugin allows the agent to read, write, and manage files with permission checking.
"""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from ..base import CapabilityPlugin, Tool, ToolResult
from ...core.permissions import check_permission, PermissionResult

logger = logging.getLogger(__name__)


class FilesystemPlugin(CapabilityPlugin):
    """Plugin for filesystem operations."""

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Read, write, and manage files and directories"

    @property
    def capability(self) -> str:
        return "filesystem"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="read_file",
                description="Read the contents of a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the file"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._read_file,
                required_permission=("filesystem", "read"),
            ),
            Tool(
                name="write_file",
                description="Write content to a file (creates or overwrites)",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the file"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        }
                    },
                    "required": ["path", "content"]
                },
                handler=self._write_file,
                required_permission=("filesystem", "write"),
            ),
            Tool(
                name="list_directory",
                description="List files and folders in a directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the directory"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._list_directory,
                required_permission=("filesystem", "read"),
            ),
            Tool(
                name="move_file",
                description="Move or rename a file/folder",
                parameters={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path"
                        }
                    },
                    "required": ["source", "destination"]
                },
                handler=self._move_file,
                required_permission=("filesystem", "write"),
            ),
            Tool(
                name="delete_file",
                description="Delete a file or empty folder",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to delete"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._delete_file,
                required_permission=("filesystem", "delete"),
            ),
            Tool(
                name="create_directory",
                description="Create a new directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path for the new directory"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._create_directory,
                required_permission=("filesystem", "write"),
            ),
            Tool(
                name="file_info",
                description="Get information about a file or directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the file or directory"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._file_info,
                required_permission=("filesystem", "read"),
            ),
        ]

    async def _read_file(self, path: str) -> ToolResult:
        """Read a file's contents."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "read", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        if not resolved.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"File does not exist: {path}"
            )

        if not resolved.is_file():
            return ToolResult(
                success=False,
                output=None,
                error=f"Not a file: {path}"
            )

        try:
            content = resolved.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except UnicodeDecodeError:
            # Try reading as binary for non-text files
            content = resolved.read_bytes()
            return ToolResult(
                success=True,
                output=f"<binary file, {len(content)} bytes>"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _write_file(self, path: str, content: str) -> ToolResult:
        """Write content to a file."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "write", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        try:
            # Create parent directories if needed
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _list_directory(self, path: str) -> ToolResult:
        """List directory contents."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "read", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        if not resolved.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"Directory does not exist: {path}"
            )

        if not resolved.is_dir():
            return ToolResult(
                success=False,
                output=None,
                error=f"Not a directory: {path}"
            )

        try:
            items = []
            for item in sorted(resolved.iterdir()):
                item_type = "dir" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else 0
                items.append({
                    "name": item.name,
                    "type": item_type,
                    "size": size,
                })

            return ToolResult(success=True, output=items)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _move_file(self, source: str, destination: str) -> ToolResult:
        """Move or rename a file."""
        src_resolved = Path(source).expanduser().resolve()
        dst_resolved = Path(destination).expanduser().resolve()

        # Check permissions for both source (read) and destination (write)
        perm_check = check_permission("filesystem", "read", path=str(src_resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied (source): {perm_check.reason}"
            )

        perm_check = check_permission("filesystem", "write", path=str(dst_resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied (destination): {perm_check.reason}"
            )

        if not src_resolved.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"Source does not exist: {source}"
            )

        try:
            shutil.move(str(src_resolved), str(dst_resolved))
            return ToolResult(
                success=True,
                output=f"Moved {source} to {destination}"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _delete_file(self, path: str) -> ToolResult:
        """Delete a file or empty directory."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "delete", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        if not resolved.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"Path does not exist: {path}"
            )

        try:
            if resolved.is_file():
                resolved.unlink()
            elif resolved.is_dir():
                resolved.rmdir()  # Only removes empty directories
            return ToolResult(
                success=True,
                output=f"Deleted {path}"
            )
        except OSError as e:
            if "not empty" in str(e).lower():
                return ToolResult(
                    success=False,
                    output=None,
                    error="Directory is not empty. Use terminal 'rm -r' for recursive delete."
                )
            return ToolResult(success=False, output=None, error=str(e))

    async def _create_directory(self, path: str) -> ToolResult:
        """Create a new directory."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "write", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        try:
            resolved.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                output=f"Created directory: {path}"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _file_info(self, path: str) -> ToolResult:
        """Get file/directory information."""
        resolved = Path(path).expanduser().resolve()

        # Check permission
        perm_check = check_permission("filesystem", "read", path=str(resolved))
        if perm_check.result != PermissionResult.ALLOWED:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied: {perm_check.reason}"
            )

        if not resolved.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"Path does not exist: {path}"
            )

        try:
            stat = resolved.stat()
            info = {
                "path": str(resolved),
                "name": resolved.name,
                "type": "directory" if resolved.is_dir() else "file",
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_birthtime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
            }
            return ToolResult(success=True, output=info)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
