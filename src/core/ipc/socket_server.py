"""Unix socket server for IPC with SwiftUI GUI.

This server handles communication between the Python agent daemon
and the SwiftUI frontend via JSON-RPC over Unix sockets.
"""
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Default socket path
SOCKET_PATH = Path(os.environ.get(
    "TWIZZY_SOCKET",
    "/tmp/twizzy.sock"
))


@dataclass
class RPCRequest:
    """JSON-RPC request."""

    method: str
    params: dict[str, Any]
    id: str | int | None = None


@dataclass
class RPCResponse:
    """JSON-RPC response."""

    result: Any = None
    error: dict[str, Any] | None = None
    id: str | int | None = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        data = {"jsonrpc": "2.0", "id": self.id}
        if self.error:
            data["error"] = self.error
        else:
            data["result"] = self.result
        return json.dumps(data)


class IPCServer:
    """Unix socket server for GUI communication.

    Protocol: JSON-RPC 2.0 over Unix socket
    Each message is a line of JSON terminated by newline.
    """

    def __init__(self, socket_path: Path = SOCKET_PATH):
        self.socket_path = socket_path
        self._server: asyncio.Server | None = None
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._running = False

    def register_handler(
        self,
        method: str,
        handler: Callable[..., Coroutine[Any, Any, Any]]
    ):
        """Register a handler for an RPC method.

        Args:
            method: The RPC method name
            handler: Async function to handle the method
        """
        self._handlers[method] = handler
        logger.debug(f"Registered handler for method: {method}")

    async def start(self):
        """Start the IPC server."""
        # Remove existing socket if present
        if self.socket_path.exists():
            self.socket_path.unlink()

        # Create parent directory if needed
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Start server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path)
        )

        # Set socket permissions (user only)
        os.chmod(self.socket_path, 0o600)

        self._running = True
        logger.info(f"IPC server started on {self.socket_path}")

    async def stop(self):
        """Stop the IPC server."""
        self._running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Cleanup socket file
        if self.socket_path.exists():
            self.socket_path.unlink()

        logger.info("IPC server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Handle a client connection."""
        peer = writer.get_extra_info("peername") or "unknown"
        logger.debug(f"Client connected: {peer}")

        try:
            while self._running:
                # Read line (JSON-RPC message)
                line = await reader.readline()
                if not line:
                    break

                try:
                    data = json.loads(line.decode("utf-8"))
                    request = RPCRequest(
                        method=data.get("method", ""),
                        params=data.get("params", {}),
                        id=data.get("id")
                    )

                    response = await self._handle_request(request)

                except json.JSONDecodeError as e:
                    response = RPCResponse(
                        error={"code": -32700, "message": f"Parse error: {e}"},
                        id=None
                    )

                # Send response
                writer.write((response.to_json() + "\n").encode("utf-8"))
                await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.debug(f"Client disconnected: {peer}")

    async def _handle_request(self, request: RPCRequest) -> RPCResponse:
        """Handle an RPC request."""
        logger.debug(f"Handling RPC: {request.method}")

        if request.method not in self._handlers:
            return RPCResponse(
                error={"code": -32601, "message": f"Method not found: {request.method}"},
                id=request.id
            )

        try:
            handler = self._handlers[request.method]
            result = await handler(**request.params)
            return RPCResponse(result=result, id=request.id)
        except Exception as e:
            logger.error(f"Handler error for {request.method}: {e}")
            return RPCResponse(
                error={"code": -32000, "message": str(e)},
                id=request.id
            )

    async def run_forever(self):
        """Run the server until stopped."""
        if not self._server:
            await self.start()

        async with self._server:
            await self._server.serve_forever()


async def start_server(
    socket_path: Path = SOCKET_PATH,
    agent=None
) -> IPCServer:
    """Start the IPC server with agent handlers.

    Args:
        socket_path: Path for the Unix socket
        agent: TwizzyAgent instance to handle requests

    Returns:
        Started IPCServer instance
    """
    server = IPCServer(socket_path)

    # Register handlers
    if agent:
        server.register_handler("chat", agent.process_message)
        server.register_handler("status", lambda: agent.get_status())
        server.register_handler("clear", lambda: agent.clear_conversation())

        # Permission management
        from ..config import load_permissions, save_permissions
        from ..permissions import get_enforcer

        async def get_permissions():
            return load_permissions().to_dict()

        async def set_permissions(permissions: dict):
            from ..config import PermissionsConfig
            config = PermissionsConfig.from_dict(permissions)
            if save_permissions(config):
                get_enforcer().reload()
                return {"success": True}
            return {"success": False, "error": "Failed to save permissions"}

        server.register_handler("get_permissions", get_permissions)
        server.register_handler("set_permissions", set_permissions)

    await server.start()
    return server
