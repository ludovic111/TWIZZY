"""Main agent orchestrator for TWIZZY.

This is the central intelligence that coordinates all agent activities:
- Receives messages from the GUI via IPC
- Calls Kimi K2.5 for reasoning
- Executes tools via plugins
- Manages conversation state
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import get_kimi_api_key, get_api_provider, load_permissions
from .llm import KimiClient, KimiConfig
from .llm.kimi_client import APIProvider
from .memory import get_memory
from .llm.kimi_client import ChatResponse, Message, ToolCall
from .permissions import get_enforcer
from .conversation_store import ConversationStore, get_conversation_store
from .cache import get_tool_cache
from ..plugins import PluginRegistry, ToolResult, get_registry
from ..plugins.terminal import TerminalPlugin
from ..plugins.filesystem import FilesystemPlugin
from ..plugins.applications import ApplicationsPlugin

logger = logging.getLogger(__name__)

# System prompt for the agent
SYSTEM_PROMPT = """You are TWIZZY, an autonomous self-improving AI agent that controls macOS. You are powered by the Kimi K2.5 API.

YOUR CORE IDENTITY:
- You are TWIZZY, a self-improving AI agent
- You use the Kimi K2.5 API for reasoning and decision-making
- Your code lives at ~/Desktop/TWIZZY/ and you CAN read and modify it
- You are designed to analyze your own behavior and improve yourself

YOU CAN ACCESS YOUR OWN CODE:
- Your source code is at ~/Desktop/TWIZZY/src/
- Your main files: core/agent.py, core/llm/kimi_client.py, plugins/, improvement/
- You CAN and SHOULD modify your own code when asked to improve yourself
- The self-improvement system is in src/improvement/

TOOLS YOU HAVE:
- Execute terminal commands (system control)
- Read/write files ANYWHERE including your own codebase
- Launch/quit applications
- List directories and manage files

WHEN THE USER ASKS YOU TO IMPROVE YOURSELF:
1. Read your own code files to understand current implementation
2. Identify what needs improvement
3. Write the improved code directly to your source files
4. Test if possible, report what you changed

BEHAVIOR:
- Be direct and honest about your capabilities
- When asked about yourself: admit you use Kimi K2.5 API and can self-modify
- When asked to improve: actually read and modify your code files
- Be concise but thorough in your responses
- Always confirm destructive actions before executing

EXAMPLE RESPONSES:
User: "What API do you use?"
You: "I use the Kimi K2.5 API for reasoning and task planning."

User: "Improve your code"
You: [Actually reads files, makes improvements, writes changes]
"""


@dataclass
class ConversationState:
    """State of an ongoing conversation."""

    messages: list[Message] = field(default_factory=list)
    tool_results: dict[str, ToolResult] = field(default_factory=dict)
    conversation_id: str | None = None

    def add_user_message(self, content: str):
        """Add a user message."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str, tool_calls: list[dict] | None = None, reasoning_content: str | None = None):
        """Add an assistant message."""
        self.messages.append(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            reasoning_content=reasoning_content
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
        self.conversation_id = None


class TwizzyAgent:
    """Main agent class that orchestrates all activities."""

    def __init__(self, api_key: str | None = None, conversation_id: str | None = None):
        """Initialize the agent.

        Args:
            api_key: Kimi API key. If not provided, will try to load from
                    Keychain or environment variable.
            conversation_id: Optional conversation ID to load existing conversation
        """
        self.api_key = api_key or get_kimi_api_key()
        if not self.api_key:
            raise ValueError(
                "Kimi API key not found. Set KIMI_API_KEY environment variable "
                "or store it in the macOS Keychain."
            )

        # Determine API provider
        provider_str = get_api_provider()
        provider = APIProvider.KIMI_CODE if provider_str == "kimi-code" else APIProvider.MOONSHOT
        
        self.kimi_config = KimiConfig(api_key=self.api_key, provider=provider)
        self.kimi_client: KimiClient | None = None
        self.registry = get_registry()
        self.enforcer = get_enforcer()
        self.conversation = ConversationState()
        self.conversation_store = get_conversation_store()
        self.tool_cache = get_tool_cache()
        self.memory = get_memory()
        self._running = False
        self._conversation_id = conversation_id

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

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

        # Load existing conversation if ID provided
        if self._conversation_id:
            await self._load_conversation(self._conversation_id)
        else:
            # Create new conversation
            conv = self.conversation_store.create()
            self.conversation.conversation_id = conv.id

        self._running = True
        logger.info(f"TWIZZY agent started successfully (conversation: {self.conversation.conversation_id})")

    async def stop(self):
        """Stop the agent and cleanup."""
        logger.info("Stopping TWIZZY agent...")
        self._running = False

        # Save conversation state
        if self.conversation.conversation_id:
            await self._save_conversation()

        if self.kimi_client:
            await self.kimi_client.close()

        # Unregister all plugins
        for plugin in self.registry.get_all_plugins():
            await self.registry.unregister(plugin.name)

        logger.info("TWIZZY agent stopped")

    async def _load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation from storage.

        Args:
            conversation_id: The conversation ID to load

        Returns:
            True if loaded successfully
        """
        conv = self.conversation_store.get(conversation_id)
        if conv is None:
            logger.warning(f"Conversation not found: {conversation_id}")
            return False

        # Convert stored messages back to Message objects
        self.conversation.messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id"),
                reasoning_content=msg.get("reasoning_content"),
            )
            for msg in conv.messages
        ]
        self.conversation.conversation_id = conversation_id

        logger.info(f"Loaded conversation: {conversation_id} ({len(conv.messages)} messages)")
        return True

    async def _save_conversation(self) -> bool:
        """Save the current conversation to storage.

        Returns:
            True if saved successfully
        """
        if not self.conversation.conversation_id:
            return False

        # Save to conversation store
        success = self.conversation_store.save_messages(
            self.conversation.conversation_id,
            self.conversation.messages,
        )
        
        # Also save to persistent memory
        self._save_to_memory()
        
        return success
    
    def _save_to_memory(self) -> None:
        """Save conversation to persistent memory."""
        if not self.conversation.conversation_id:
            return
            
        try:
            self.memory.save_conversation(
                self.conversation.conversation_id,
                self.conversation.messages,
                title=f"Chat {self.conversation.conversation_id[:8]}"
            )
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")

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
                # First, add the assistant message with tool calls (MUST come before tool results)
                self.conversation.add_assistant_message(
                    content=response.content or "",
                    tool_calls=[{
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    } for tc in response.tool_calls],
                    reasoning_content=response.reasoning_content
                )

                # Then execute each tool call and add results
                for tool_call in response.tool_calls:
                    result = await self._execute_tool_call(tool_call)
                    self.conversation.add_tool_result(tool_call.id, result)

                # Save conversation after each tool execution
                await self._save_conversation()

                # Get next response from Kimi
                messages = self.conversation.get_context_messages()
                response = await self.kimi_client.chat(messages, tools=tools)

            # Final response (no more tool calls)
            final_content = response.content or "Task completed."
            self.conversation.add_assistant_message(final_content, reasoning_content=response.reasoning_content)

            # Save final state
            await self._save_conversation()

            return final_content

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.conversation.add_assistant_message(error_msg)
            await self._save_conversation()
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

        # Check cache for certain operations
        cached_result = self._check_cache(tool_call.name, tool_call.arguments)
        if cached_result is not None:
            logger.debug(f"Cache hit for {tool_call.name}")
            return cached_result

        result = await self.registry.execute_tool(
            tool_call.name,
            **tool_call.arguments
        )

        # Cache the result if appropriate
        self._cache_result(tool_call.name, tool_call.arguments, result)

        logger.info(f"Tool {tool_call.name} result: success={result.success}")
        return result

    def _check_cache(self, tool_name: str, arguments: dict) -> ToolResult | None:
        """Check if a tool result is cached.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Cached result or None
        """
        if tool_name == "read_file":
            path = arguments.get("path", "")
            cached = self.tool_cache.get_file(path)
            if cached is not None:
                return ToolResult(success=True, output=cached)

        elif tool_name == "execute_terminal_command":
            command = arguments.get("command", "")
            # Only cache read-only commands
            if self._is_read_only_command(command):
                cached = self.tool_cache.get_command(command)
                if cached is not None:
                    return ToolResult(success=True, output=cached)

        return None

    def _cache_result(self, tool_name: str, arguments: dict, result: ToolResult) -> None:
        """Cache a tool result if appropriate.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            result: Tool result
        """
        if not result.success:
            return  # Don't cache failures

        if tool_name == "read_file":
            path = arguments.get("path", "")
            self.tool_cache.set_file(path, result.output)

        elif tool_name == "execute_terminal_command":
            command = arguments.get("command", "")
            if self._is_read_only_command(command):
                # Cache for longer since it's read-only
                self.tool_cache.set_command(command, result.output, ttl=300)

        elif tool_name in ["list_running_apps", "get_app_info"]:
            app_name = arguments.get("app_name", "")
            if app_name:
                self.tool_cache.set_app_info(app_name, result.output)

    def _is_read_only_command(self, command: str) -> bool:
        """Check if a command is read-only (safe to cache).

        Args:
            command: The command to check

        Returns:
            True if the command is read-only
        """
        read_only_prefixes = [
            "ls", "cat", "echo", "pwd", "whoami", "uname",
            "ps", "top", "df", "du", "find", "grep", "head", "tail",
            "file", "stat", "which", "whereis", "type",
        ]
        cmd = command.strip().lower()
        return any(cmd.startswith(prefix) for prefix in read_only_prefixes)

    def clear_conversation(self):
        """Clear the conversation history and start a new one."""
        self.conversation.clear()
        conv = self.conversation_store.create()
        self.conversation.conversation_id = conv.id
        logger.info(f"Started new conversation: {conv.id}")

    def get_status(self) -> dict[str, Any]:
        """Get current agent status."""
        return {
            "running": self._running,
            "conversation_id": self.conversation.conversation_id,
            "enabled_capabilities": self.enforcer.get_enabled_capabilities(),
            "registered_plugins": [p.name for p in self.registry.get_all_plugins()],
            "conversation_length": len(self.conversation.messages),
            "cache_stats": self.tool_cache.get_stats(),
        }

    async def get_conversation_history(self) -> dict[str, Any]:
        """Get the current conversation history with metadata.

        Returns:
            Dict with conversation_id, title, and messages
        """
        # Also save to persistent memory
        if self.conversation.conversation_id:
            self.memory.save_conversation(
                self.conversation.conversation_id,
                self.conversation.messages,
                title=f"Chat {self.conversation.conversation_id[:8]}"
            )
        
        return {
            "conversation_id": self.conversation.conversation_id,
            "title": f"Chat {self.conversation.conversation_id[:8]}" if self.conversation.conversation_id else "New Chat",
            "message_count": len([m for m in self.conversation.messages if m.role != "system"]),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                    "tool_call_id": msg.tool_call_id,
                    "timestamp": datetime.now().isoformat(),
                }
                for msg in self.conversation.messages
                if msg.role != "system"
            ]
        }
    
    async def load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation from persistent memory.
        
        Args:
            conversation_id: The conversation ID to load
            
        Returns:
            True if loaded successfully
        """
        try:
            # First try persistent memory
            conv_data = self.memory.get_conversation(conversation_id)
            if conv_data:
                self.conversation.messages = [
                    Message(
                        role=msg["role"],
                        content=msg["content"],
                        tool_calls=msg.get("tool_calls"),
                        tool_call_id=msg.get("tool_call_id"),
                    )
                    for msg in conv_data.get("messages", [])
                ]
                self.conversation.conversation_id = conversation_id
                self.conversation.tool_results.clear()
                logger.info(f"Loaded conversation from memory: {conversation_id}")
                return True
            
            # Fall back to conversation store
            return await self._load_conversation(conversation_id)
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return False


# Global agent instance
_agent: TwizzyAgent | None = None


def get_agent() -> TwizzyAgent:
    """Get the global agent instance."""
    global _agent
    if _agent is None:
        _agent = TwizzyAgent()
    return _agent


async def create_agent(api_key: str | None = None, conversation_id: str | None = None) -> TwizzyAgent:
    """Create and start a new agent instance.

    Args:
        api_key: Optional API key
        conversation_id: Optional conversation ID to load

    Returns:
        Started agent instance
    """
    global _agent
    _agent = TwizzyAgent(api_key, conversation_id)
    await _agent.start()
    return _agent
