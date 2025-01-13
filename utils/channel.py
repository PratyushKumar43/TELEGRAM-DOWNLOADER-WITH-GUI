"""Utility functions for handling Telegram channel links."""
import re
from typing import Optional


def extract_channel_id(channel_link: str) -> Optional[str]:
    """
    Extract channel username or ID from various Telegram channel link formats.

    Parameters
    ----------
    channel_link: str
        Telegram channel link in various formats:
        - https://t.me/channel_name
        - t.me/channel_name
        - @channel_name
        - channel_name
        - -100123456789 (channel ID)

    Returns
    -------
    Optional[str]
        Channel username or ID if valid, None otherwise
    """
    # If it's already a username without any URL
    if channel_link.startswith('@'):
        return channel_link[1:]
    
    # If it's a numeric channel ID
    if channel_link.startswith('-100') and channel_link[4:].isdigit():
        return channel_link
    
    # Try to extract username from t.me URL
    url_pattern = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)'
    match = re.match(url_pattern, channel_link)
    if match:
        return match.group(1)
    
    # If it's just the username
    if re.match(r'^[a-zA-Z0-9_]+$', channel_link):
        return channel_link
    
    return None
