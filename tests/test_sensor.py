"""Test dlink_dchs150_hass switch."""

# from unittest.mock import call
# from unittest.mock import patch
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.dchs150_motion import (
    async_setup_entry,
)

# from custom_components.dchs150_motion.const import (
#     DEFAULT_NAME,
#    DOMAIN,
# )


@pytest.mark.asyncio
async def test_sensor_services(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Test sensor services."""
    # Create a mock entry so we don't have to go through config flow
    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()


# TODO(tathamg@gmail.com):  Write some actual tests . . .  # noqa: TD003 FIX002
