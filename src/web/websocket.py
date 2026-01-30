"""WebSocket connection manager for TWIZZY.

Handles real-time chat communication between the web client and the agent.
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket

from ..core.agent import TwizzyAgent, create_agent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and agent interactions."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.agent: Optional[TwizzyAgent] = None
        self._agent_lock = asyncio.Lock()

    async def _ensure_agent(self) -> TwizzyAgent:
        """Ensure agent is initialized."""
        async with self._agent_lock:
            if self.agent is None:
                logger.info("Initializing TWIZZY agent...")
                self.agent = await create_agent()
            return self.agent

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

        # Ensure agent is ready
        await self._ensure_agent()

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to TWIZZY. How can I help you?"
        })

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def process_and_stream(self, websocket: WebSocket, message: str):
        """Process a message and stream the response."""
        try:
            agent = await self._ensure_agent()

            # Send "thinking" status
            await websocket.send_json({
                "type": "status",
                "status": "thinking"
            })

            # Process the message
            response = await agent.process_message(message)

            # Send the complete response
            await websocket.send_json({
                "type": "response",
                "message": response
            })

            # Send status update
            status = agent.get_status()
            await websocket.send_json({
                "type": "status_update",
                "status": status
            })

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Error: {str(e)}"
            })

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

    async def broadcast_improvement(self, improvement: dict):
        """Broadcast a self-improvement notification."""
        await self.broadcast({
            "type": "improvement",
            "data": improvement
        })

    async def broadcast_reload(self):
        """Notify clients that the server is reloading."""
        await self.broadcast({
            "type": "reload",
            "message": "Server reloading after self-improvement..."
        })

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.agent:
            await self.agent.stop()

        # Close all connections
        for connection in self.active_connections:
            try:
                await connection.close()
            except Exception:
                pass

        self.active_connections.clear()


# Global connection manager
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    """Get the global connection manager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
