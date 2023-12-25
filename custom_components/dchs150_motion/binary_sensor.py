"""Binary sensor platform for dlink_dchs150_hass."""
from datetime import datetime
from datetime import timedelta

from typing import Union

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

from .const import CONF_BACKOFF
from .const import DEFAULT_BACKOFF_SECONDS
from .const import DEFAULT_SENSOR_NAME
from .const import DOMAIN
from .dch_wifi import UnsupportedDeviceType
from .entity import DlinkDchHassEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([DlinkDchHassBinarySensor(coordinator, entry)])


class DlinkDchHassBinarySensor(DlinkDchHassEntity, BinarySensorEntity):
    """dlink_DCH_hass_sensor class."""

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        name = self.coordinator.data.get("device_name")
        if not name:
            name = DEFAULT_SENSOR_NAME
        return name

    @property
    def device_class(self) -> Union[BinarySensorDeviceClass, None]:
        """Return the class of this binary_sensor."""
        model_name = self.coordinator.data.get("model_name")
        if model_name == "DCH-S150":
            return BinarySensorDeviceClass.MOTION
        elif model_name == "DCH-S160":
            return BinarySensorDeviceClass.MOISTURE
        else:
            raise UnsupportedDeviceType

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        backoff_seconds = self.config_entry.data.get(CONF_BACKOFF)
        if not backoff_seconds:
            backoff_seconds = DEFAULT_BACKOFF_SECONDS
        last_detect_time = self.coordinator.data.get("last_detection")
        timed_out = datetime.now() > last_detect_time + timedelta(
            seconds=backoff_seconds
        )
        return not timed_out
