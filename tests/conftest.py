"""Global fixtures for dlink_dchs150_hass integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

if TYPE_CHECKING:
    from collections.abc import Generator

from custom_components.dchs150_motion.const import (
    CONF_BACKOFF,
    CONF_DESCRIPTION,
    CONF_HOST,
    CONF_INTERVAL,
    CONF_NICK_NAME,
    CONF_OP_STATUS,
    CONF_PIN,
    CONF_SENSITIVITY,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture() -> Generator[Any]:
    """Skip notification calls."""
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield


# This fixture, when used, will result in calls to async_get_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture() -> Generator[Any]:
    """Skip calls to get data from API."""
    with patch(
        "custom_components.dlink_dchs150_hass.DlinkDchHassApiClient.async_get_data",
    ):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture() -> Generator[Any]:
    """Simulate error when retrieving data from API."""
    with patch(
        "custom_components.dlink_dchs150_hass.DlinkDchHassApiClient.async_get_data",
        side_effect=Exception,
    ):
        yield


@pytest.fixture(name="config_data")
def config_data() -> dict[str, str]:
    """Create a mock config data."""
    return {CONF_HOST: "10.1.1.1", CONF_PIN: "123456"}


@pytest.fixture(name="config_entry")
def config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=config_data(),
        entry_id="test",
    )


@pytest.fixture(name="config_options")
def config_options() -> dict[str, int | bool | str]:
    """Create a mock set of options."""
    return {
        CONF_INTERVAL: 1,
        CONF_BACKOFF: 30,
        CONF_SENSITIVITY: 90,
        CONF_OP_STATUS: True,
        CONF_NICK_NAME: "Testing Sensor",
        CONF_DESCRIPTION: "This is my testing sensor.",
    }
