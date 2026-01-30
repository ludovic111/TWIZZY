"""
TWIZZY Gateway - Multi-channel control plane for messaging integrations.

Inspired by OpenClaw's Gateway architecture.
"""

from .gateway import Gateway, get_gateway
from .channel import Channel, ChannelMessage, ChannelType

__all__ = ["Gateway", "get_gateway", "Channel", "ChannelMessage", "ChannelType"]
