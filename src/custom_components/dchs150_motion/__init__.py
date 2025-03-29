"""
Custom integration to integrate dlink_dchs150_hass with Home Assistant.

For more details about this integration, please refer to
https://github.com/updrytwist/dlink-dchs150-hass
"""

import logging

__version__ = "0.3.0-dev0"

__all__: list[str] = []

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .hass_integration import HassIntegration

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant) -> bool:
    """Perform setup.  Setup using YAML not supported . . ."""
    return await HassIntegration.async_setup(hass)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Perform initial setup."""
    return await HassIntegration.async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await HassIntegration.async_unload_entry(hass, entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await HassIntegration.async_reload_entry(hass, entry)
