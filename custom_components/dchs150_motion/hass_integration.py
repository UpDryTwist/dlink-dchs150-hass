"""
Custom integration to integrate dlink_dchs150_hass with Home Assistant.

For more details about this integration, please refer to
https://github.com/updrytwist/dlink-dchs150-hass
"""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import DlinkDchs150HassApiClient, fill_in_timezone, fill_in_motion
from .const import CONF_PIN
from .const import CONF_HOST
from .const import CONF_INTERVAL
from .const import BINARY_SENSOR
from .const import DOMAIN
from .const import STARTUP_MESSAGE
from .const import DEVICE_POLLING_FREQUENCY
from .const import UPDATE_LISTENER_REMOVE

_LOGGER: logging.Logger = logging.getLogger(__name__)
_PACKAGE_LOGGER: logging.Logger = logging.getLogger(__package__)


class HassIntegration:
    """Implements the integration methods for HASS.
    (In other examples you might find this stuffed into __init__.py)"""

    @staticmethod
    async def async_setup(
        hass: HomeAssistant, config: Config
    ):  # pylint: disable=unused-argument
        """Set up this integration using YAML is not supported."""
        return True

    @staticmethod
    async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
        """Set up this integration using UI."""
        if hass.data.get(DOMAIN) is None:
            hass.data.setdefault(DOMAIN, {})
            _LOGGER.info(STARTUP_MESSAGE)

        host = entry.data.get(CONF_HOST)
        pin = entry.data.get(CONF_PIN)
        interval = entry.options.get(CONF_INTERVAL)
        if not interval:
            interval = DEVICE_POLLING_FREQUENCY
        interval = float(interval)
        update_interval = timedelta(seconds=interval)

        time_info = fill_in_timezone(hass.config.time_zone, entry)
        motion_info = fill_in_motion(entry)

        session = async_get_clientsession(hass)
        client = DlinkDchs150HassApiClient(host, pin, session, time_info, motion_info)

        coordinator = DlinkDchs150HassDataUpdateCoordinator(
            hass, client=client, update_interval=update_interval
        )
        await coordinator.async_refresh()

        if not coordinator.last_update_success:
            _LOGGER.DEBUG("Coordinator failed last_update_success()")
            raise ConfigEntryNotReady

        hass.data[DOMAIN][entry.entry_id] = coordinator

        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, BINARY_SENSOR)
        )

        # If we haven't already, register to get update messages . . . but only once!
        if (
            not UPDATE_LISTENER_REMOVE in hass.data[DOMAIN]
            or not hass.data[DOMAIN][UPDATE_LISTENER_REMOVE]
        ):
            hass.data[DOMAIN][UPDATE_LISTENER_REMOVE] = entry.add_update_listener(
                HassIntegration.async_reload_entry
            )

        return True

    @staticmethod
    async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """Handle removal of an entry."""
        # coordinator = hass.data[DOMAIN][entry.entry_id]
        unloaded = await hass.config_entries.async_forward_entry_unload(
            entry, BINARY_SENSOR
        )
        if unloaded:
            hass.data[DOMAIN].pop(entry.entry_id)

        return unloaded

    @staticmethod
    async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Reload config entry."""
        await HassIntegration.async_unload_entry(hass, entry)
        await HassIntegration.async_setup_entry(hass, entry)


class DlinkDchs150HassDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DlinkDchs150HassApiClient,
        update_interval: int,
    ) -> None:
        """Initialize."""
        self.api = client

        _LOGGER.debug(
            "Setting up %s with update interval of %s seconds", DOMAIN, update_interval
        )

        super().__init__(
            hass, _PACKAGE_LOGGER, name=DOMAIN, update_interval=update_interval
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except Exception as exception:
            raise UpdateFailed() from exception
