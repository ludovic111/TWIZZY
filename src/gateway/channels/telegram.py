"""
Telegram channel adapter for TWIZZY Gateway.

Requires: pip install python-telegram-bot
"""

import logging
from typing import Optional

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from ..channel import Channel, ChannelType

logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """
    Telegram Bot API channel adapter.
    
    Usage:
        1. Create a bot via @BotFather on Telegram
        2. Get your bot token
        3. Configure: TelegramChannel("telegram", {"token": "YOUR_TOKEN"})
    """
    
    def __init__(self, name: str = "telegram", config: dict = None):
        super().__init__(name, ChannelType.TELEGRAM, config)
        self.token = config.get("token") if config else None
        self._app: Optional["Application"] = None
        self._allowed_chats: set = set()
        
    async def start(self) -> None:
        """Start the Telegram bot."""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return
            
        if not self.token:
            logger.error("Telegram token not configured")
            return
            
        self._app = Application.builder().token(self.token).build()
        
        # Register handlers
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        
        # Start the bot
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        
        self._running = True
        logger.info("Telegram channel started")
        
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        self._running = False
        logger.info("Telegram channel stopped")
        
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a message to a chat."""
        if not self._app:
            return False
            
        try:
            await self._app.bot.send_message(chat_id=recipient, text=content[:4096])  # Telegram limit
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
            
    async def broadcast(self, content: str) -> int:
        """Broadcast to all allowed chats."""
        if not self._app:
            return 0
            
        sent = 0
        for chat_id in self._allowed_chats:
            try:
                await self._app.bot.send_message(chat_id=chat_id, text=content[:4096])
                sent += 1
            except Exception as e:
                logger.error(f"Broadcast failed to {chat_id}: {e}")
                
        return sent
        
    # Command handlers
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 *TWIZZY Gateway*\n"
            "Your personal AI assistant is ready.\n\n"
            "Send me any message and I'll process it.\n"
            "Use /help for commands.",
            parse_mode="Markdown"
        )
        
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "*Available Commands*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/status - Check TWIZZY status\n\n"
            "Just send me a message to chat with TWIZZY!",
            parse_mode="Markdown"
        )
        
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        await update.message.reply_text(
            "✅ *TWIZZY Gateway* is running\n"
            "Channel: Telegram\n"
            "Ready to process messages.",
            parse_mode="Markdown"
        )
        
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return
            
        chat_id = str(update.message.chat_id)
        sender = update.message.from_user.username or str(update.message.from_user.id)
        content = update.message.text
        
        # Track this chat for broadcasts
        self._allowed_chats.add(chat_id)
        
        # Send "typing" indicator
        await update.message.chat.send_action(action="typing")
        
        # Notify gateway
        await self._notify_message(f"{chat_id}:{sender}", content)
