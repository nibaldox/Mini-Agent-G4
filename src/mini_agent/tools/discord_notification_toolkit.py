"""Discord notification toolkit for Mini Agent G4"""

from typing import Optional
from agno.tools.discord import DiscordTools
from agno.tools import tool


class DiscordNotificationToolkit:
    """Wrapper around DiscordTools with default channel support for alerts."""

    def __init__(self, bot_token: str, default_channel_id: Optional[str] = None):
        self.default_channel_id = default_channel_id
        self._discord_tools = DiscordTools(
            bot_token=bot_token,
            enable_send_message=True,
            enable_get_channel_messages=True,
            enable_get_channel_info=True,
            enable_list_channels=True,
        )

    @tool
    def send_alert(
        self,
        message: str,
        channel_id: Optional[str] = None,
        urgent: bool = False
    ) -> str:
        """Send an alert message to Discord channel.

        Args:
            message: The alert message to send
            channel_id: Discord channel ID. Uses default channel if not provided
            urgent: If True, prepends 🚨 to the message

        Returns:
            Confirmation message
        """
        target_channel = channel_id or self.default_channel_id

        if not target_channel:
            return "Error: No channel_id provided and no default channel configured. Please provide channel_id or set discord_default_alert_channel in config."

        if urgent:
            message = f"🚨 {message}"

        return self._discord_tools.send_message(
            channel_id=target_channel,
            message=message
        )

    @tool
    def send_notification(
        self,
        title: str,
        description: str,
        channel_id: Optional[str] = None
    ) -> str:
        """Send a formatted notification to Discord.

        Args:
            title: Notification title
            description: Notification body
            channel_id: Discord channel ID. Uses default channel if not provided

        Returns:
            Confirmation message
        """
        target_channel = channel_id or self.default_channel_id

        if not target_channel:
            return "Error: No channel_id provided and no default channel configured. Please provide channel_id or set discord_default_alert_channel in config."

        formatted_message = f"**{title}**\n{description}"

        return self._discord_tools.send_message(
            channel_id=target_channel,
            message=formatted_message
        )

    @tool
    def get_channel_id_by_name(self, server_id: str, channel_name: str) -> str:
        """Get channel ID by searching channels in a server.

        Args:
            server_id: Discord server ID
            channel_name: Name of the channel to find

        Returns:
            Channel ID or error message
        """
        channels = self._discord_tools.list_channels(server_id=server_id)

        # Parse the response to find the channel
        if isinstance(channels, str) and "not found" in channels.lower():
            return f"Error: {channels}"

        # Try to find channel by name
        for line in channels.split('\n'):
            if channel_name.lower() in line.lower():
                # Extract channel ID from the line
                # Format is typically "Channel Name - ID: 123456789"
                if 'ID:' in line:
                    return line.split('ID:')[-1].strip()

        return f"Channel '{channel_name}' not found in server {server_id}"

    @tool
    def list_server_channels(self, server_id: str) -> str:
        """List all channels in a Discord server.

        Args:
            server_id: Discord server ID

        Returns:
            List of channels
        """
        return self._discord_tools.list_channels(server_id=server_id)