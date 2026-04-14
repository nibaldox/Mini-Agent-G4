"""Telegram channel for MiniAgent G4."""

import asyncio
import logging
from typing import Optional

from .gateway import Channel, InboundMessage

try:
    import telegram
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Update = None
    Application = None


logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """Telegram bot channel."""

    name = "telegram"

    def __init__(
        self,
        token: str,
        allowed_users: Optional[list[str]] = None,
    ):
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError("python-telegram-bot not installed. Run: uv add python-telegram-bot")

        self.token = token
        self.allowed_users = set(allowed_users or [])
        self._app: Optional["Application"] = None
        self._dispatcher: Optional[callable] = None
        self._agent = None
        self._agent_lock = asyncio.Lock()

    def set_dispatcher(self, fn: callable) -> None:
        """Set the message handler."""
        self._dispatcher = fn

    def set_agent_fn(self, fn: callable) -> None:
        """Set the agent factory."""
        self._agent = fn

    def start(self) -> None:
        """Start the Telegram bot."""
        if self._app is not None:
            return

        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )

        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        self._app.add_handler(MessageHandler(filters.Document.ALL, self._on_document))

        self._app.run_webhook(
            listen="0.0.0.0",
            port=8450,
            secret_token=None,
        )
        logger.info("Telegram bot started on port 8450")

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "MiniAgent G4 is running. Send me a message and I'll help you!\n\n"
            "Available commands:\n"
            "/status - Check agent status\n"
            "/skills - List available skills\n"
            "/help - Show this help"
        )

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        user_id = str(update.effective_user.id if update.effective_user else "unknown")
        text = update.message.text

        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("Access denied.")
            return

        if self._dispatcher:
            inbound = InboundMessage(channel="telegram", user_id=user_id, text=text, raw=update)
            self._dispatcher(inbound)

    async def _on_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads."""
        await update.message.reply_text(
            "Received a file. I'll process it when I have file handling ready."
        )

    def send(self, user_id: str, text: str) -> None:
        """Send a message to a Telegram user (async, non-blocking)."""
        if self._app is None:
            return

        async def _send():
            try:
                await self._app.bot.send_message(chat_id=user_id, text=text)
            except Exception as e:
                logger.error(f"Telegram send error: {e}")

        asyncio.create_task(_send())

    def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            self._app.stop()
            self._app = None
