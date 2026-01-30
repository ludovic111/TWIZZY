"""
Gateway control plane for multi-channel message routing.

Routes messages from various channels (Telegram, Slack, etc.) to the agent.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RoutingMode(Enum):
    """How to route inbound messages."""
    DIRECT = "direct"           # Route directly to agent
    APPROVAL = "approval"       # Require approval before processing
    PAIRING = "pairing"         # Require pairing code for new users


@dataclass
class GatewayConfig:
    """Configuration for the gateway."""
    enabled_channels: List[str] = field(default_factory=list)
    routing_mode: RoutingMode = RoutingMode.PAIRING
    allowed_senders: List[str] = field(default_factory=list)
    admin_senders: List[str] = field(default_factory=list)
    message_ttl: int = 86400    # 24 hours


@dataclass
class PendingApproval:
    """A message waiting for approval."""
    message_id: str
    channel: str
    sender: str
    content: str
    timestamp: datetime
    pairing_code: Optional[str] = None


class Gateway:
    """
    Control plane for multi-channel messaging.
    
    Routes messages from external channels (Telegram, Slack, etc.)
    to the agent, handling authentication and approval workflows.
    """
    
    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self._channels: Dict[str, Any] = {}
        self._message_handlers: List[Callable] = []
        self._pending_approvals: Dict[str, PendingApproval] = {}
        self._paired_senders: set = set()
        self._running = False
        
    def register_channel(self, name: str, channel: Any) -> None:
        """Register a channel adapter."""
        self._channels[name] = channel
        channel.set_message_callback(self._handle_inbound_message)
        logger.info(f"Registered channel: {name}")
        
    def unregister_channel(self, name: str) -> None:
        """Unregister a channel adapter."""
        if name in self._channels:
            del self._channels[name]
            logger.info(f"Unregistered channel: {name}")
            
    def add_message_handler(self, handler: Callable) -> None:
        """Add a handler for incoming messages."""
        self._message_handlers.append(handler)
        
    def remove_message_handler(self, handler: Callable) -> None:
        """Remove a message handler."""
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
            
    async def _handle_inbound_message(self, channel: str, sender: str, content: str) -> None:
        """Handle an incoming message from any channel."""
        message_id = f"{channel}:{sender}:{datetime.now().timestamp()}"
        
        # Check if sender is allowed
        if not self._is_sender_allowed(channel, sender):
            if self.config.routing_mode == RoutingMode.PAIRING:
                # Generate pairing code
                import random
                pairing_code = f"{random.randint(1000, 9999)}"
                pending = PendingApproval(
                    message_id=message_id,
                    channel=channel,
                    sender=sender,
                    content=content,
                    timestamp=datetime.now(),
                    pairing_code=pairing_code
                )
                self._pending_approvals[message_id] = pending
                
                # Notify sender they need to pair
                await self.send_message(
                    channel, 
                    sender, 
                    f"🔐 Please pair with TWIZZY using code: {pairing_code}\n"
                    f"An admin must approve this with: /approve {channel} {pairing_code}"
                )
                logger.info(f"Pairing required for {sender} on {channel}: {pairing_code}")
                return
            else:
                logger.warning(f"Blocked message from unauthorized sender: {sender}")
                return
                
        # Route to handlers
        for handler in self._message_handlers:
            try:
                await handler(channel, sender, content)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                
    def _is_sender_allowed(self, channel: str, sender: str) -> bool:
        """Check if a sender is allowed to send messages."""
        sender_key = f"{channel}:{sender}"
        
        # Check paired senders
        if sender_key in self._paired_senders:
            return True
            
        # Check explicit allowlist
        if sender in self.config.allowed_senders or sender_key in self.config.allowed_senders:
            return True
            
        return False
        
    async def approve_pairing(self, channel: str, pairing_code: str, admin_sender: str) -> bool:
        """Approve a pairing request."""
        # Verify admin
        if admin_sender not in self.config.admin_senders:
            logger.warning(f"Unauthorized approval attempt by {admin_sender}")
            return False
            
        # Find pending approval
        for message_id, pending in self._pending_approvals.items():
            if pending.channel == channel and pending.pairing_code == pairing_code:
                # Add to paired senders
                sender_key = f"{channel}:{pending.sender}"
                self._paired_senders.add(sender_key)
                del self._pending_approvals[message_id]
                
                # Notify sender
                await self.send_message(
                    channel,
                    pending.sender,
                    "✅ Pairing approved! You can now use TWIZZY."
                )
                logger.info(f"Approved pairing for {pending.sender} on {channel}")
                return True
                
        return False
        
    async def send_message(self, channel: str, recipient: str, content: str) -> bool:
        """Send a message through a channel."""
        if channel not in self._channels:
            logger.error(f"Channel not found: {channel}")
            return False
            
        try:
            await self._channels[channel].send_message(recipient, content)
            return True
        except Exception as e:
            logger.error(f"Failed to send message on {channel}: {e}")
            return False
            
    async def broadcast(self, content: str, channels: Optional[List[str]] = None) -> Dict[str, int]:
        """Broadcast a message to multiple channels."""
        results = {}
        target_channels = channels or list(self._channels.keys())
        
        for channel_name in target_channels:
            if channel_name not in self._channels:
                continue
                
            try:
                channel = self._channels[channel_name]
                sent = await channel.broadcast(content)
                results[channel_name] = sent
            except Exception as e:
                logger.error(f"Broadcast failed on {channel_name}: {e}")
                results[channel_name] = 0
                
        return results
        
    async def start(self) -> None:
        """Start the gateway and all registered channels."""
        self._running = True
        logger.info("Starting gateway...")
        
        for name, channel in self._channels.items():
            try:
                await channel.start()
                logger.info(f"Started channel: {name}")
            except Exception as e:
                logger.error(f"Failed to start channel {name}: {e}")
                
    async def stop(self) -> None:
        """Stop the gateway and all channels."""
        self._running = False
        logger.info("Stopping gateway...")
        
        for name, channel in self._channels.items():
            try:
                await channel.stop()
                logger.info(f"Stopped channel: {name}")
            except Exception as e:
                logger.error(f"Failed to stop channel {name}: {e}")
                
    def get_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        return {
            "running": self._running,
            "channels": list(self._channels.keys()),
            "pending_approvals": len(self._pending_approvals),
            "paired_senders": len(self._paired_senders),
            "routing_mode": self.config.routing_mode.value
        }


# Global gateway instance
_gateway: Optional[Gateway] = None


def get_gateway(config: Optional[GatewayConfig] = None) -> Gateway:
    """Get or create the global gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = Gateway(config)
    return _gateway
