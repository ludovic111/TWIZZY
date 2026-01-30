"""
Base channel interface and message types for gateway.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List


class ChannelType(Enum):
    """Types of messaging channels."""
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SIGNAL = "signal"
    IMESSAGE = "imessage"
    WEBCHAT = "webchat"


@dataclass
class ChannelMessage:
    """A message from any channel."""
    message_id: str
    channel_type: ChannelType
    channel_name: str
    sender_id: str
    sender_name: Optional[str]
    content: str
    timestamp: datetime
    reply_to: Optional[str] = None
    attachments: List[dict] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class Channel(ABC):
    """
    Abstract base class for channel adapters.
    
    All channel implementations (Telegram, Slack, etc.) must inherit from this.
    """
    
    def __init__(self, name: str, channel_type: ChannelType, config: dict = None):
        self.name = name
        self.channel_type = channel_type
        self.config = config or {}
        self._message_callback: Optional[Callable] = None
        self._running = False
        
    def set_message_callback(self, callback: Callable) -> None:
        """Set the callback for incoming messages."""
        self._message_callback = callback
        
    async def _notify_message(self, sender: str, content: str) -> None:
        """Notify the gateway of an incoming message."""
        if self._message_callback:
            await self._message_callback(self.name, sender, content)
            
    @abstractmethod
    async def start(self) -> None:
        """Start the channel connection."""
        pass
        
    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel connection."""
        pass
        
    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a message to a recipient."""
        pass
        
    @abstractmethod
    async def broadcast(self, content: str) -> int:
        """Broadcast a message to all connected users. Returns count sent."""
        pass
        
    def is_running(self) -> bool:
        """Check if channel is running."""
        return self._running
