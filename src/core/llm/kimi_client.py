"""Kimi 2.5k API client for TWIZZY.

Kimi 2.5k is Moonshot AI's latest model with strong reasoning and tool use capabilities.
API docs: https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


@dataclass
class KimiConfig:
    """Configuration for Kimi 2.5k API client."""

    api_key: str
    base_url: str = "https://api.moonshot.ai/v1"
    model: str = "kimi-k2.5"
    temperature: float = 0.6  # Instant mode (use 1.0 for thinking mode)
    top_p: float = 0.95
    max_tokens: int = 8192
    timeout: float = 120.0


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant", or "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


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


class KimiClient:
    """Async client for Kimi 2.5k API with tool calling support."""

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
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
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
        thinking: bool = False,
    ) -> ChatResponse:
        """Send a chat completion request to Kimi 2.5k.

        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions for function calling
            thinking: If True, use thinking mode (temp=1.0) for complex reasoning

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
            payload_messages.append(m)

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": payload_messages,
            "temperature": 1.0 if thinking else self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # Disable thinking mode explicitly if not requested
        if not thinking:
            payload["extra_body"] = {
                "chat_template_kwargs": {"thinking": False}
            }

        logger.debug(f"Sending chat request: {len(messages)} messages, {len(tools or [])} tools")

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

        return ChatResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
        )

    async def stream_chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion for real-time UI updates.

        Yields text chunks as they arrive from the API.
        Note: Tool calls are not supported in streaming mode.
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
