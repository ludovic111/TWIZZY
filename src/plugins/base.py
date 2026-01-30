"""Base classes for TWIZZY capability plugins.

All capability plugins inherit from CapabilityPlugin and implement
their specific tools.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Tool:
    """Definition of a tool that can be called by the agent."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, "ToolResult"]]
    required_permission: tuple[str, str] | None = None  # (capability, action)


@dataclass
class ToolResult:
    """Result from executing a tool."""

    success: bool
    output: Any
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


class PluginError(Exception):
    """Base exception for plugin errors."""

    pass


class CapabilityPlugin(ABC):
    """Base class for capability plugins.

    Each plugin provides a set of tools that the agent can use.
    Plugins are responsible for checking permissions before executing actions.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this plugin does."""
        pass

    @property
    @abstractmethod
    def capability(self) -> str:
        """The capability category (terminal, filesystem, applications, etc.)."""
        pass

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Get all tools provided by this plugin.

        Returns:
            List of Tool objects that can be called by the agent
        """
        pass

    async def initialize(self) -> None:
        """Initialize the plugin. Called once when the plugin is loaded."""
        pass

    async def shutdown(self) -> None:
        """Cleanup when the plugin is unloaded."""
        pass

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get tool definitions in OpenAI function calling format.

        This format is compatible with Kimi K2.5's tool calling API.
        """
        definitions = []
        for tool in self.get_tools():
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return definitions

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments to pass to the tool

        Returns:
            ToolResult with success status and output
        """
        for tool in self.get_tools():
            if tool.name == tool_name:
                try:
                    return await tool.handler(**kwargs)
                except Exception as e:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=str(e)
                    )

        return ToolResult(
            success=False,
            output=None,
            error=f"Tool not found: {tool_name}"
        )
