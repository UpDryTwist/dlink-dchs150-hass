"""Binary sensor platform for dlink_dchs150_hass."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import homeassistant.util.dt
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import UndefinedType

from .const import CONF_BACKOFF, DEFAULT_BACKOFF_SECONDS, DEFAULT_SENSOR_NAME, DOMAIN
from .dch_wifi import UnsupportedDeviceTypeError
from .entity import DlinkDchHassEntity

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Adding devices for coordinator %s and entry %s", coordinator, entry)
    async_add_devices([DlinkDchHassBinarySensor(coordinator, entry)])


class DlinkDchHassBinarySensor(DlinkDchHassEntity, BinarySensorEntity):  # pyright: ignore
    """dlink_DCH_hass_sensor class."""

    # TODO(tathamg@gmail.com): Resolve the incompatibility between Entity.available and CoordinatorEntity.available (want to use the latter) # noqa: TD003 FIX002

    @property
    def name(self) -> str | UndefinedType | None:  # pyright: ignore
        """Return the name of the binary_sensor."""
        name = self.coordinator.data.get("device_name")
        if not name:
            name = DEFAULT_SENSOR_NAME
        return name

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:  # pyright: ignore
        """Return the class of this binary_sensor."""
        model_name = self.coordinator.data.get("model_name")
        if model_name == "DCH-S150":
            return BinarySensorDeviceClass.MOTION
        if model_name == "DCH-S160":
            return BinarySensorDeviceClass.MOISTURE
        raise UnsupportedDeviceTypeError

    @property
    def is_on(self) -> bool | None:  # pyright: ignore
        """Return true if the binary_sensor is on."""
        backoff_seconds = self.config_entry.data.get(CONF_BACKOFF)
        if not backoff_seconds:
            backoff_seconds = DEFAULT_BACKOFF_SECONDS
        last_detect_time = self.coordinator.data.get("last_detection")
        current_time = datetime.now(
            tz=homeassistant.util.dt.DEFAULT_TIME_ZONE,
        )
        timeout_time = (
            last_detect_time + timedelta(seconds=backoff_seconds)
            if last_detect_time
            else None
        )
        return not timeout_time or current_time < timeout_time

        # _LOGGER.debug(
        #    "Current time is %s, timeout time is %s, last detection time is %s, on = %s",
        #    current_time,
        #    timeout_time,
        #    last_detect_time,
        #    is_on,
        # )
