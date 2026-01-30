"""Main agent orchestrator for TWIZZY.

This is the central intelligence that coordinates all agent activities:
- Receives messages from the GUI via IPC
- Calls Kimi 2.5k for reasoning
- Executes tools via plugins
- Manages conversation state
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .config import get_kimi_api_key, load_permissions
from .llm import KimiClient, KimiConfig
from .llm.kimi_client import ChatResponse, Message, ToolCall
from .permissions import get_enforcer
from ..plugins import PluginRegistry, ToolResult, get_registry
from ..plugins.terminal import TerminalPlugin
from ..plugins.filesystem import FilesystemPlugin
from ..plugins.applications import ApplicationsPlugin

logger = logging.getLogger(__name__)

# System prompt for the agent
SYSTEM_PROMPT = """You are TWIZZY, a helpful autonomous assistant that can control macOS.

You have access to tools that let you:
- Execute terminal commands
- Read, write, and manage files
- Launch, quit, and control applications

When the user asks you to do something:
1. Think about what tools you need
2. Use tools one at a time, checking results
3. Report back what you did

Be concise but thorough. If a task fails, explain why and suggest alternatives.

Important:
- Always confirm destructive actions before executing
- Respect the user's permission settings
- If a permission is denied, explain this to the user
"""


@dataclass
class ConversationState:
    """State of an ongoing conversation."""

    messages: list[Message] = field(default_factory=list)
    tool_results: dict[str, ToolResult] = field(default_factory=dict)

    def add_user_message(self, content: str):
        """Add a user message."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str, tool_calls: list[dict] | None = None):
        """Add an assistant message."""
        self.messages.append(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls
        ))

    def add_tool_result(self, tool_call_id: str, result: ToolResult):
        """Add a tool result."""
        self.tool_results[tool_call_id] = result
        # Add as message for context
        self.messages.append(Message(
            role="tool",
            content=json.dumps(result.to_dict()),
            tool_call_id=tool_call_id
        ))

    def get_context_messages(self, max_messages: int = 50) -> list[Message]:
        """Get recent messages for context."""
        # Always include system message
        system = Message(role="system", content=SYSTEM_PROMPT)

        # Get recent messages, keeping tool calls and results together
        recent = self.messages[-max_messages:]

        return [system] + recent

    def clear(self):
        """Clear conversation state."""
        self.messages.clear()
        self.tool_results.clear()


class TwizzyAgent:
    """Main agent class that orchestrates all activities."""

    def __init__(self, api_key: str | None = None):
        """Initialize the agent.

        Args:
            api_key: Kimi API key. If not provided, will try to load from
                    Keychain or environment variable.
        """
        self.api_key = api_key or get_kimi_api_key()
        if not self.api_key:
            raise ValueError(
                "Kimi API key not found. Set KIMI_API_KEY environment variable "
                "or store it in the macOS Keychain."
            )

        self.kimi_config = KimiConfig(api_key=self.api_key)
        self.kimi_client: KimiClient | None = None
        self.registry = get_registry()
        self.enforcer = get_enforcer()
        self.conversation = ConversationState()
        self._running = False

    async def start(self):
        """Start the agent and initialize all components."""
        logger.info("Starting TWIZZY agent...")

        # Initialize Kimi client
        self.kimi_client = KimiClient(self.kimi_config)
        await self.kimi_client._ensure_client()

        # Register plugins
        await self.registry.register(TerminalPlugin())
        await self.registry.register(FilesystemPlugin())
        await self.registry.register(ApplicationsPlugin())

        self._running = True
        logger.info("TWIZZY agent started successfully")

    async def stop(self):
        """Stop the agent and cleanup."""
        logger.info("Stopping TWIZZY agent...")
        self._running = False

        if self.kimi_client:
            await self.kimi_client.close()

        # Unregister all plugins
        for plugin in self.registry.get_all_plugins():
            await self.registry.unregister(plugin.name)

        logger.info("TWIZZY agent stopped")

    async def process_message(self, user_message: str) -> str:
        """Process a user message and return the agent's response.

        This is the main entry point for user interactions.

        Args:
            user_message: The user's message

        Returns:
            The agent's response text
        """
        if not self._running:
            return "Agent is not running. Please start the agent first."

        logger.info(f"Processing message: {user_message[:100]}...")

        # Add user message to conversation
        self.conversation.add_user_message(user_message)

        # Get enabled capabilities
        enabled = self.enforcer.get_enabled_capabilities()
        logger.debug(f"Enabled capabilities: {enabled}")

        # Get tool definitions for enabled capabilities
        tools = self.registry.get_enabled_tool_definitions(enabled)

        # Build messages for Kimi
        messages = self.conversation.get_context_messages()

        try:
            # Call Kimi for response
            response = await self.kimi_client.chat(messages, tools=tools)

            # Handle tool calls
            while response.tool_calls:
                # Execute each tool call
                tool_messages = []
                for tool_call in response.tool_calls:
                    result = await self._execute_tool_call(tool_call)
                    self.conversation.add_tool_result(tool_call.id, result)
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result.to_dict())
                    })

                # Add assistant message with tool calls
                self.conversation.add_assistant_message(
                    content=response.content or "",
                    tool_calls=[{
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    } for tc in response.tool_calls]
                )

                # Get next response from Kimi
                messages = self.conversation.get_context_messages()
                response = await self.kimi_client.chat(messages, tools=tools)

            # Final response (no more tool calls)
            final_content = response.content or "Task completed."
            self.conversation.add_assistant_message(final_content)

            return final_content

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.conversation.add_assistant_message(error_msg)
            return error_msg

    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call.

        Args:
            tool_call: The tool call from Kimi

        Returns:
            ToolResult from executing the tool
        """
        logger.info(f"Executing tool: {tool_call.name}")
        logger.debug(f"Tool arguments: {tool_call.arguments}")

        result = await self.registry.execute_tool(
            tool_call.name,
            **tool_call.arguments
        )

        logger.info(f"Tool {tool_call.name} result: success={result.success}")
        return result

    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation.clear()
        logger.info("Conversation cleared")

    def get_status(self) -> dict[str, Any]:
        """Get current agent status."""
        return {
            "running": self._running,
            "enabled_capabilities": self.enforcer.get_enabled_capabilities(),
            "registered_plugins": [p.name for p in self.registry.get_all_plugins()],
            "conversation_length": len(self.conversation.messages),
        }


# Global agent instance
_agent: TwizzyAgent | None = None


def get_agent() -> TwizzyAgent:
    """Get the global agent instance."""
    global _agent
    if _agent is None:
        _agent = TwizzyAgent()
    return _agent


async def create_agent(api_key: str | None = None) -> TwizzyAgent:
    """Create and start a new agent instance."""
    global _agent
    _agent = TwizzyAgent(api_key)
    await _agent.start()
    return _agent
