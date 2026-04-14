"""Multi-channel gateway — Telegram, Slack, Discord bridge for MiniAgent G4."""

import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class InboundMessage:
    """Unified inbound message from any channel."""
    channel: str          # "telegram" | "slack" | "discord"
    user_id: str
    text: str
    raw: Optional[object] = None


class Channel(ABC):
    """Base class for a messaging channel."""

    name: str = "base"

    @abstractmethod
    def start(self) -> None:
        """Start listening for messages."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the channel."""
        ...

    @abstractmethod
    def send(self, user_id: str, text: str) -> None:
        """Send a message to a user on this channel."""
        ...


class ChannelGateway:
    """
    Unified gateway that bridges multiple messaging channels to MiniAgent.

    Usage:
        gateway = ChannelGateway(agent_fn=lambda: MiniAgent(config))
        gateway.register_telegram(token="BOT_TOKEN")
        gateway.register_slack(token="xoxb-...", channel_id="C...")
        gateway.start()
    """

    def __init__(self, agent_fn: Callable):
        """
        Args:
            agent_fn: Callable that returns (or creates) a MiniAgent instance.
                      Called lazily so the agent isn't created until needed.
        """
        self._agent_fn = agent_fn
        self._channels: dict[str, Channel] = {}
        self._loop_thread: Optional[threading.Thread] = None
        self._running = False
        self._dispatcher: Optional[Callable[[InboundMessage], None]] = None

    def set_dispatcher(self, fn: Callable[[InboundMessage], None]) -> None:
        """Set the message handler (dispatches inbound messages to agent)."""
        self._dispatcher = fn

    def register_telegram(self, token: str, allowed_users: Optional[list[str]] = None) -> "TelegramChannel":
        """Register Telegram bot."""
        from .telegram import TelegramChannel
        ch = TelegramChannel(token=token, allowed_users=allowed_users or [])
        self._channels["telegram"] = ch
        return ch

    def register_slack(self, token: str, channel_id: str, bot_token: Optional[str] = None) -> "SlackChannel":
        """Register Slack bot."""
        from .slack import SlackChannel
        ch = SlackChannel(token=token, channel_id=channel_id, bot_token=bot_token)
        self._channels["slack"] = ch
        return ch

    def start(self) -> None:
        """Start all registered channels."""
        if self._running:
            return
        self._running = True
        self._loop_thread = threading.Thread(target=self._run_async, daemon=True)
        self._loop_thread.start()

    def stop(self) -> None:
        """Stop all channels."""
        self._running = False
        for ch in self._channels.values():
            ch.stop()
        self._channels.clear()

    def _run_async(self) -> None:
        """Run the async event loop for all channels."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._start_all())
        finally:
            loop.close()

    async def _start_all(self) -> None:
        """Start all channels concurrently."""
        tasks = []
        for ch in self._channels.values():
            t = asyncio.create_task(self._run_channel(ch))
            tasks.append(t)
        if tasks:
            await asyncio.gather(*tasks)

    async def _run_channel(self, ch: Channel) -> None:
        """Run a single channel, handling its messages."""
        ch.start()
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
