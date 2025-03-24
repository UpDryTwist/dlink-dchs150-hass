"""Test dlink_dchs150_hass setup process."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.dchs150_motion import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.dchs150_motion.const import (
    DOMAIN,
)
from custom_components.dchs150_motion.hass_integration import (
    DlinkDchHassDataUpdateCoordinator,
)


# We can pass fixtures as defined in conftest.py to tell pytest to use the fixture
# for a given test. We can also leverage fixtures and mocks that are available in
# Home Assistant using the pytest_homeassistant_custom_component plugin.
# Assertions allow you to verify that the return value of whatever is on the left
# side of the assertion matches with the right side.
async def test_setup_unload_and_reload_entry(
    hass: HomeAssistant,
    bypass_get_data,  # noqa: ANN001
    config_entry,  # noqa: ANN001
) -> None:
    """Test entry setup and unload."""
    # Set up the entry and assert that the values set during setup are where we expect
    # them to be. Because we have patched the DlinkDchs150HassDataUpdateCoordinator.async_get_data
    # call, no code from custom_components/dlink_dchs150_hass/api.py actually runs.
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    assert (
        type(hass.data[DOMAIN][config_entry.entry_id])
        is DlinkDchHassDataUpdateCoordinator
    )

    # Reload the entry and assert that the data from above is still there
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    assert (
        type(hass.data[DOMAIN][config_entry.entry_id])
        is DlinkDchHassDataUpdateCoordinator
    )

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_exception(
    hass: HomeAssistant,
    error_on_get_data,  # noqa: ANN001
    config_entry,  # noqa: ANN001
) -> None:
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    # In this case we are testing the condition where async_setup_entry raises
    # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
    # an error.
    with pytest.raises(ConfigEntryNotReady):
        assert await async_setup_entry(hass, config_entry)
