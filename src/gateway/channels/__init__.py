"""Channel adapters for various messaging platforms."""

# These would be implemented with actual SDKs
# For now, we provide the base structure

from .telegram import TelegramChannel
from .slack import SlackChannel
from .discord import DiscordChannel

__all__ = ["TelegramChannel", "SlackChannel", "DiscordChannel"]
