"""
Discord channel adapter for TWIZZY Gateway.

Requires: pip install discord.py
"""

import logging
import asyncio
from typing import Optional

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None

from ..channel import Channel, ChannelType

logger = logging.getLogger(__name__)


class DiscordChannel(Channel):
    """
    Discord.py channel adapter.
    
    Usage:
        1. Create a Discord bot at https://discord.com/developers/applications
        2. Enable Message Content Intent
        3. Get your bot token
        4. Configure: DiscordChannel("discord", {"token": "YOUR_TOKEN"})
    """
    
    def __init__(self, name: str = "discord", config: dict = None):
        super().__init__(name, ChannelType.DISCORD, config)
        self.token = config.get("token") if config else None
        self._client: Optional["discord.Client"] = None
        self._dm_users: set = set()
        
    async def start(self) -> None:
        """Start the Discord client."""
        if not DISCORD_AVAILABLE:
            logger.error("discord.py not installed. Run: pip install discord.py")
            return
            
        if not self.token:
            logger.error("Discord token not configured")
            return
            
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        
        self._client = discord.Client(intents=intents)
        
        @self._client.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self._client.user}")
            
        @self._client.event
        async def on_message(message):
            if message.author == self._client.user:
                return
                
            # Only process DMs or mentions
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = self._client.user in message.mentions
            
            if not (is_dm or is_mention):
                return
                
            # Track DM users for broadcasts
            if is_dm:
                self._dm_users.add(message.author.id)
                
            # Clean mention from text
            content = message.content
            if is_mention:
                content = content.replace(f"<@{self._client.user.id}>", "").strip()
                
            sender = f"{message.author.name}#{message.author.discriminator}"
            
            # Send typing indicator
            async with message.channel.typing():
                await self._notify_message(f"discord:{sender}", content)
                
        # Start the client
        asyncio.create_task(self._client.start(self.token))
        
        self._running = True
        logger.info("Discord channel starting...")
        
    async def stop(self) -> None:
        """Stop the Discord client."""
        if self._client:
            await self._client.close()
        self._running = False
        logger.info("Discord channel stopped")
        
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a DM to a user."""
        if not self._client:
            return False
            
        try:
            # recipient format: "username#discriminator" or user ID
            if recipient.isdigit():
                user = await self._client.fetch_user(int(recipient))
            else:
                # Try to find by name
                for guild in self._client.guilds:
                    for member in guild.members:
                        if f"{member.name}#{member.discriminator}" == recipient:
                            user = member
                            break
                    else:
                        continue
                    break
                else:
                    return False
                    
            await user.send(content[:2000])  # Discord DM limit
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
            
    async def broadcast(self, content: str) -> int:
        """Broadcast to all DM users."""
        sent = 0
        for user_id in self._dm_users:
            if await self.send_message(str(user_id), content):
                sent += 1
        return sent
