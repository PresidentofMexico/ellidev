"""
Channel-based business unit configuration.

Maps Slack channels to business units, and business units to Salesforce
RecordTypeIds and default field values.

Configuration is loaded from environment variables at startup:
- CHANNEL_BU_MAPPING: JSON mapping channel IDs to business unit names
- BU_RECORD_TYPES: JSON mapping business unit names to Salesforce RecordTypeIds
- BU_FIELD_DEFAULTS: JSON mapping business unit names to default field values

Example environment configuration:
    CHANNEL_BU_MAPPING='{"C12345ABC":"private_credit","C67890DEF":"re_credit"}'
    BU_RECORD_TYPES='{"private_credit":"012xxx","re_credit":"012yyy","default":"012zzz"}'
    BU_FIELD_DEFAULTS='{"private_credit":{"Strategy__c":"Corporate Credit"}}'
"""
import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from services.logger import logger


@dataclass
class BusinessUnitConfig:
    """Configuration for a business unit."""
    name: str
    record_type_id: Optional[str]
    default_fields: Dict[str, Any]

    def __repr__(self) -> str:
        return f"BusinessUnitConfig(name='{self.name}', record_type_id='{self.record_type_id}')"


class ChannelConfigManager:
    """
    Manages channel-to-business-unit mapping and record type configuration.

    Configuration is loaded from environment variables at startup and can be
    refreshed dynamically by calling reload().

    Usage:
        from config.channel_config import channel_config

        # Get business unit for a channel
        bu = channel_config.get_business_unit("C12345ABC")

        # Get RecordTypeId for opportunity creation
        record_type_id = channel_config.get_record_type_id("C12345ABC")

        # Get complete configuration
        config = channel_config.get_config_for_channel("C12345ABC")
    """

    def __init__(self):
        self._channel_bu_map: Dict[str, str] = {}
        self._bu_record_types: Dict[str, str] = {}
        self._bu_field_defaults: Dict[str, Dict[str, Any]] = {}
        self._default_record_type: Optional[str] = None
        self.reload()

    def reload(self) -> None:
        """Reload configuration from environment variables."""
        # Channel to Business Unit mapping
        mapping_json = os.environ.get("CHANNEL_BU_MAPPING", "{}")
        try:
            self._channel_bu_map = json.loads(mapping_json)
            if self._channel_bu_map:
                logger.info(
                    f"Loaded channel mapping for {len(self._channel_bu_map)} channels",
                    service="config",
                    channels=list(self._channel_bu_map.keys())
                )
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid CHANNEL_BU_MAPPING JSON: {e}",
                service="config",
                raw_value=mapping_json[:100]
            )
            self._channel_bu_map = {}

        # Business Unit to RecordTypeId mapping
        record_types_json = os.environ.get("BU_RECORD_TYPES", "{}")
        try:
            self._bu_record_types = json.loads(record_types_json)
            self._default_record_type = self._bu_record_types.get("default")
            if self._bu_record_types:
                logger.info(
                    f"Loaded RecordType mapping for {len(self._bu_record_types)} business units",
                    service="config",
                    business_units=list(self._bu_record_types.keys())
                )
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid BU_RECORD_TYPES JSON: {e}",
                service="config",
                raw_value=record_types_json[:100]
            )
            self._bu_record_types = {}

        # Business Unit field defaults
        defaults_json = os.environ.get("BU_FIELD_DEFAULTS", "{}")
        try:
            self._bu_field_defaults = json.loads(defaults_json)
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid BU_FIELD_DEFAULTS JSON: {e}",
                service="config",
                raw_value=defaults_json[:100]
            )
            self._bu_field_defaults = {}

    def get_business_unit(self, channel_id: str) -> Optional[str]:
        """
        Get the business unit for a Slack channel.

        Args:
            channel_id: Slack channel ID (e.g., "C12345ABC")

        Returns:
            Business unit name or None if not mapped
        """
        return self._channel_bu_map.get(channel_id)

    def get_record_type_id(self, channel_id: str) -> Optional[str]:
        """
        Get the Salesforce RecordTypeId for a channel.

        Args:
            channel_id: Slack channel ID

        Returns:
            RecordTypeId or default if channel not mapped
        """
        bu = self.get_business_unit(channel_id)
        if bu:
            return self._bu_record_types.get(bu, self._default_record_type)
        return self._default_record_type

    def get_field_defaults(self, channel_id: str) -> Dict[str, Any]:
        """
        Get default field values for a channel's business unit.

        Args:
            channel_id: Slack channel ID

        Returns:
            Dictionary of field defaults (empty dict if none)
        """
        bu = self.get_business_unit(channel_id)
        if bu:
            return self._bu_field_defaults.get(bu, {}).copy()
        return {}

    def get_config_for_channel(self, channel_id: str) -> BusinessUnitConfig:
        """
        Get complete configuration for a channel.

        Args:
            channel_id: Slack channel ID

        Returns:
            BusinessUnitConfig with all settings
        """
        bu = self.get_business_unit(channel_id) or "default"
        record_type_id = self.get_record_type_id(channel_id)
        defaults = self.get_field_defaults(channel_id)

        return BusinessUnitConfig(
            name=bu,
            record_type_id=record_type_id,
            default_fields=defaults
        )

    def is_configured(self) -> bool:
        """
        Check if channel configuration is set up.

        Returns:
            True if at least one channel mapping exists
        """
        return bool(self._channel_bu_map)

    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get all channel to business unit mappings.

        Returns:
            Dictionary of channel_id -> business_unit
        """
        return self._channel_bu_map.copy()


# Singleton instance - lazy loaded
_config_instance: Optional[ChannelConfigManager] = None


def get_channel_config() -> ChannelConfigManager:
    """Get singleton channel config manager."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ChannelConfigManager()
    return _config_instance


# Default export for easy importing
channel_config = get_channel_config()
