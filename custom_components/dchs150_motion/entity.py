"""DlinkDchHassEntity class"""
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .const import DOMAIN


class DlinkDchHassEntity(CoordinatorEntity):
    """Coordinating entity for DLink DCH-S150 and DCH-S160"""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": str(self.coordinator.data.get("device_name")),
            "model": str(self.coordinator.data.get("model_name")),
            "manufacturer": str(self.coordinator.data.get("vendor_name")),
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        mac_id = self.coordinator.data.get("mac_address")

        return {
            "attribution": ATTRIBUTION,
            "id": mac_id.replace(":", "_"),
            "integration": DOMAIN,
        }
