"""
Slack channel adapter for TWIZZY Gateway.

Requires: pip install slack-bolt
"""

import logging
from typing import Optional

try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

from ..channel import Channel, ChannelType

logger = logging.getLogger(__name__)


class SlackChannel(Channel):
    """
    Slack Bolt API channel adapter.
    
    Usage:
        1. Create a Slack app at https://api.slack.com/apps
        2. Enable Socket Mode
        3. Add bot token scopes: chat:write, app_mentions:read, im:read, im:write
        4. Get your tokens
        5. Configure: SlackChannel("slack", {"bot_token": "xoxb-...", "app_token": "xapp-..."})
    """
    
    def __init__(self, name: str = "slack", config: dict = None):
        super().__init__(name, ChannelType.SLACK, config)
        self.bot_token = config.get("bot_token") if config else None
        self.app_token = config.get("app_token") if config else None
        self._app: Optional["AsyncApp"] = None
        self._handler: Optional["AsyncSocketModeHandler"] = None
        
    async def start(self) -> None:
        """Start the Slack app."""
        if not SLACK_AVAILABLE:
            logger.error("slack-bolt not installed. Run: pip install slack-bolt")
            return
            
        if not self.bot_token or not self.app_token:
            logger.error("Slack tokens not configured")
            return
            
        self._app = AsyncApp(token=self.bot_token)
        
        # Register handlers
        self._app.message(self._handle_message)
        self._app.event("app_mention")(self._handle_mention)
        self._app.command("/twizzy")(self._handle_command)
        
        # Start socket mode
        self._handler = AsyncSocketModeHandler(self._app, self.app_token)
        await self._handler.start_async()
        
        self._running = True
        logger.info("Slack channel started")
        
    async def stop(self) -> None:
        """Stop the Slack app."""
        if self._handler:
            await self._handler.close_async()
        self._running = False
        logger.info("Slack channel stopped")
        
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a message to a channel or user."""
        if not self._app:
            return False
            
        try:
            await self._app.client.chat_postMessage(
                channel=recipient,
                text=content[:4000]  # Slack limit
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
            
    async def broadcast(self, content: str) -> int:
        """Broadcast is not directly supported in Slack."""
        # Slack doesn't have a simple broadcast mechanism
        # Would need to track all channels the bot is in
        logger.warning("Slack broadcast not implemented - track channels manually")
        return 0
        
    async def _handle_message(self, body, say):
        """Handle direct messages."""
        event = body.get("event", {})
        channel_type = event.get("channel_type")
        
        # Only process DMs and mentions (not all channel messages)
        if channel_type != "im":
            return
            
        user = event.get("user")
        text = event.get("text", "")
        
        # Notify gateway
        await self._notify_message(f"slack:{user}", text)
        
    async def _handle_mention(self, body, say):
        """Handle @mentions."""
        event = body.get("event", {})
        user = event.get("user")
        text = event.get("text", "").replace(f"<@{body.get('authorizations', [{}])[0].get('user_id')}>", "").strip()
        
        # Notify gateway
        await self._notify_message(f"slack:{user}", text)
        
    async def _handle_command(self, ack, command, say):
        """Handle /twizzy slash command."""
        await ack()
        
        user = command.get("user_id")
        text = command.get("text", "")
        
        if not text:
            await say("Hello! I'm TWIZZY. Send me a message to get started.")
            return
            
        # Notify gateway
        await self._notify_message(f"slack:{user}", text)
