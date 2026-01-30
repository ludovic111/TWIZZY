"""Plugin registry for TWIZZY.

Manages loading, unloading, and accessing capability plugins.
"""
import logging
from typing import Any

from .base import CapabilityPlugin, Tool, ToolResult

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for managing capability plugins.

    The registry is responsible for:
    - Loading and unloading plugins
    - Routing tool calls to the correct plugin
    - Providing tool definitions for the LLM
    """

    def __init__(self):
        self._plugins: dict[str, CapabilityPlugin] = {}
        self._tools: dict[str, tuple[CapabilityPlugin, Tool]] = {}

    async def register(self, plugin: CapabilityPlugin) -> None:
        """Register a plugin with the registry.

        Args:
            plugin: The plugin to register
        """
        if plugin.name in self._plugins:
            logger.warning(f"Plugin {plugin.name} already registered, replacing")
            await self.unregister(plugin.name)

        await plugin.initialize()
        self._plugins[plugin.name] = plugin

        # Register all tools from this plugin
        for tool in plugin.get_tools():
            if tool.name in self._tools:
                logger.warning(f"Tool {tool.name} already registered, replacing")
            self._tools[tool.name] = (plugin, tool)
            logger.debug(f"Registered tool: {tool.name}")

        logger.info(f"Registered plugin: {plugin.name} with {len(plugin.get_tools())} tools")

    async def unregister(self, plugin_name: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_name: Name of the plugin to unregister
        """
        if plugin_name not in self._plugins:
            return

        plugin = self._plugins[plugin_name]

        # Remove all tools from this plugin
        tools_to_remove = [
            name for name, (p, _) in self._tools.items()
            if p.name == plugin_name
        ]
        for tool_name in tools_to_remove:
            del self._tools[tool_name]

        await plugin.shutdown()
        del self._plugins[plugin_name]

        logger.info(f"Unregistered plugin: {plugin_name}")

    def get_plugin(self, name: str) -> CapabilityPlugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def get_all_plugins(self) -> list[CapabilityPlugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        if name in self._tools:
            return self._tools[name][1]
        return None

    def get_all_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return [tool for _, tool in self._tools.values()]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI function calling format."""
        definitions = []
        for plugin in self._plugins.values():
            definitions.extend(plugin.get_tool_definitions())
        return definitions

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments to pass to the tool

        Returns:
            ToolResult with success status and output
        """
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {tool_name}"
            )

        plugin, tool = self._tools[tool_name]

        try:
            logger.debug(f"Executing tool {tool_name} with args: {kwargs}")
            result = await plugin.execute_tool(tool_name, **kwargs)
            logger.debug(f"Tool {tool_name} result: success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def get_enabled_tool_definitions(self, enabled_capabilities: list[str]) -> list[dict[str, Any]]:
        """Get tool definitions for enabled capabilities only.

        Args:
            enabled_capabilities: List of enabled capability names

        Returns:
            List of tool definitions for enabled capabilities
        """
        definitions = []
        for plugin in self._plugins.values():
            if plugin.capability in enabled_capabilities:
                definitions.extend(plugin.get_tool_definitions())
        return definitions


# Global registry instance
_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
