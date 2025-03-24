"""DlinkDchHassEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from propcache.api import cached_property

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

from .const import ATTRIBUTION, DOMAIN


class DlinkDchHassEntity(CoordinatorEntity):
    """Coordinating entity for DLink DCH-S150 and DCH-S160."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[Any],
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        """Return the device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id if self.unique_id else "")},
            name=str(self.coordinator.data.get("device_name")),
            model=str(self.coordinator.data.get("model_name")),
            manufacturer=str(self.coordinator.data.get("vendor_name")),
        )

    @property
    def device_state_attributes(self) -> dict:
        """Return the state attributes."""
        mac_id = self.coordinator.data.get("mac_address", "00:00:00:00:00:00")

        return {
            "attribution": ATTRIBUTION,
            "id": mac_id.replace(":", "_"),
            "integration": DOMAIN,
        }
