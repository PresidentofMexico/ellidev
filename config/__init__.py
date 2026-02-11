"""
Configuration module for Elli.

Contains channel-based business unit configuration and other app settings.
"""
from config.channel_config import channel_config, ChannelConfigManager, BusinessUnitConfig

__all__ = ["channel_config", "ChannelConfigManager", "BusinessUnitConfig"]
