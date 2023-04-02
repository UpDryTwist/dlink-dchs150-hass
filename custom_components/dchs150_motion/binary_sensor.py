"""Binary sensor platform for dlink_dchs150_hass."""

from datetime import timedelta, datetime

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import BINARY_SENSOR_DEVICE_CLASS
from .const import DOMAIN
from .const import BINARY_SENSOR_NAME
from .const import DEFAULT_BACKOFF_SECONDS
from .const import CONF_BACKOFF
from .entity import DlinkDchs150HassEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([DlinkDchs150HassBinarySensor(coordinator, entry)])


class DlinkDchs150HassBinarySensor(DlinkDchs150HassEntity, BinarySensorEntity):
    """dlink_dchs150_hass binary_sensor class."""

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        name = self.coordinator.data.get("device_name")
        if not name:
            name = f"{BINARY_SENSOR_NAME}"
        return name

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return BINARY_SENSOR_DEVICE_CLASS

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
