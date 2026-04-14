"""Slack channel for MiniAgent G4."""

import logging
from typing import Optional

from .gateway import Channel, InboundMessage

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    WebClient = None
    SocketModeClient = None


logger = logging.getLogger(__name__)


class SlackChannel(Channel):
    """Slack bot channel using Socket Mode."""

    name = "slack"

    def __init__(
        self,
        token: str,
        channel_id: str,
        bot_token: Optional[str] = None,
    ):
        if not SLACK_AVAILABLE:
            raise RuntimeError("slack-sdk not installed. Run: uv add slack-sdk")

        self.token = token
        self.channel_id = channel_id
        self.bot_token = bot_token or token
        self._client: Optional["WebClient"] = None
        self._socket: Optional["SocketModeClient"] = None
        self._dispatcher: Optional[callable] = None

    def set_dispatcher(self, fn: callable) -> None:
        """Set the message handler."""
        self._dispatcher = fn

    def start(self) -> None:
        """Start the Slack Socket Mode bot."""
        self._client = WebClient(token=self.token)

        self._socket = SocketModeClient(
            app_token=self.bot_token,
            web_client=self._client,
            trace_enabled=False,
        )
        self._socket.socket_mode_request_listeners.append(self._on_socket_request)
        self._socket.connect()
        logger.info("Slack bot connected via Socket Mode")

    def _on_socket_request(self, client: "SocketModeClient", req: "SocketModeRequest"):
        """Handle incoming Slack Socket Mode events."""
        if req.type != "events_api":
            return
        event = req.payload.get("event", {})
        if event.get("type") not in ("message", "app_mention"):
            return
        user_id = event.get("user", "unknown")
        text = event.get("text", "")
        channel = event.get("channel", self.channel_id)

        if self._dispatcher:
            inbound = InboundMessage(
                channel="slack",
                user_id=user_id,
                text=text,
                raw=event,
            )
            self._dispatcher(inbound)

    def send(self, user_id: str, text: str) -> None:
        """Send a message to a Slack channel or user."""
        if not self._client:
            return
        try:
            self._client.chat_postMessage(channel=user_id or self.channel_id, text=text)
        except SlackApiError as e:
            logger.error(f"Slack send error: {e}")

    def stop(self) -> None:
        """Disconnect the Slack socket."""
        if self._socket:
            self._socket.close()
            self._socket = None
