"""Kimi API client for TWIZZY.

Supports both:
- Kimi Code API (kimi.com/code) - Default
- Moonshot Open Platform (api.moonshot.ai) - Alternative

Get Kimi Code API key from: https://www.kimi.com/code (Settings → API Keys)
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    """Available API providers."""
    KIMI_CODE = "kimi-code"           # kimi.com/code API
    MOONSHOT = "moonshot"             # api.moonshot.ai Open Platform


@dataclass
class KimiConfig:
    """Configuration for Kimi API client.
    
    Kimi Code API (default):
    - base_url: https://kimi.com/api/v1
    - Models: kimi-k2.5, kimi-k2, etc.
    - Get key: https://www.kimi.com/code → Settings → API Keys
    
    Moonshot Open Platform (alternative):
    - base_url: https://api.moonshot.ai/v1
    - Models: kimi-k2.5, kimi-k2-0905-preview, etc.
    - Get key: https://platform.moonshot.ai/
    """

    api_key: str
    provider: APIProvider = APIProvider.KIMI_CODE
    base_url: str = "https://kimi.com/api/v1"  # Default to Kimi Code
    model: str = "kimi-k2.5"  # Kimi K2.5 - latest model
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 8192
    timeout: float = 120.0
    thinking: bool = True

    def __post_init__(self):
        """Set base_url based on provider if not explicitly provided."""
        if self.provider == APIProvider.KIMI_CODE:
            self.base_url = "https://kimi.com/api/v1"
        elif self.provider == APIProvider.MOONSHOT:
            self.base_url = "https://api.moonshot.ai/v1"


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant", or "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    reasoning_content: str | None = None


@dataclass
class ToolCall:
    """A tool call from the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    """Response from a chat completion request."""

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: str | None = None


class KimiClient:
    """Async client for Kimi API with tool calling support."""

    def __init__(self, config: KimiConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            
            # Kimi Code API may use different auth format
            if self.config.provider == APIProvider.KIMI_CODE:
                headers["X-API-Provider"] = "kimi-code"
            
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        thinking: bool | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to Kimi API.

        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions for function calling
            thinking: If False, disable thinking mode

        Returns:
            ChatResponse with content and/or tool calls
        """
        client = await self._ensure_client()

        # Build messages payload
        payload_messages = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            if msg.reasoning_content:
                m["reasoning_content"] = msg.reasoning_content
            payload_messages.append(m)

        # Determine thinking mode
        use_thinking = False if tools else (self.config.thinking if thinking is None else thinking)

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": payload_messages,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }

        # Disable thinking if requested
        if not use_thinking:
            payload["thinking"] = {"type": "disabled"}

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        logger.debug(f"Sending chat request to {self.config.provider.value}: {len(messages)} messages, {len(tools or [])} tools")

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        # Parse response
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = []
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                ))

        reasoning = message.get("reasoning_content")

        return ChatResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            reasoning_content=reasoning,
        )

    async def stream_chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion for real-time UI updates.

        Yields text chunks as they arrive from the API.
        """
        client = await self._ensure_client()

        payload_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        payload = {
            "model": self.config.model,
            "messages": payload_messages,
            "stream": True,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }

        if tools:
            payload["tools"] = tools

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue


# Tool definitions for agent capabilities
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_terminal_command",
            "description": "Execute a shell command in the terminal and return the output",
            "parameters": {
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
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
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
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move or rename a file/folder",
            "parameters": {
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
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or empty folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to delete"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Launch a macOS application",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application (e.g., 'Safari', 'Finder')"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quit_application",
            "description": "Quit a running macOS application",
            "parameters": {
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
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_apps",
            "description": "List all currently running applications",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "activate_application",
            "description": "Bring an application to the foreground",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application"
                    }
                },
                "required": ["app_name"]
            }
        }
    }
]
