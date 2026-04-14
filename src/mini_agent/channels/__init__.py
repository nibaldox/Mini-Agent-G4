"""Channels module — multi-channel gateway for MiniAgent G4."""

from .gateway import ChannelGateway, Channel, InboundMessage
from .telegram import TelegramChannel
from .slack import SlackChannel

__all__ = ["ChannelGateway", "Channel", "InboundMessage", "TelegramChannel", "SlackChannel"]
