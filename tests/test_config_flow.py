"""Test dlink_dchs150_hass config flow."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dchs150_motion.const import (
    BINARY_SENSOR,
    DOMAIN,
)


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture() -> Generator[Any, None, None]:
    """Prevent setup."""
    with (
        patch(
            "custom_components.dlink_dchs150_hass.async_setup",
            return_value=True,
        ),
        patch(
            "custom_components.dlink_dchs150_hass.async_setup_entry",
            return_value=True,
        ),
    ):
        yield


# Here we simiulate a successful config flow from the backend.
# Note that we use the `bypass_get_data` fixture here because
# we want the config flow validation to succeed during the test.
@pytest.mark.asyncio
async def test_successful_config_flow(
    hass: HomeAssistant,
    bypass_get_data,  # noqa: ANN001
    config_entry,  # noqa: ANN001
) -> None:
    """Test a successful config flow."""
    # Initialize a config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Check that the config flow shows the user form as the first step
    assert result.get("type", "ERROR") == FlowResultType.FORM
    assert result.get("step_id", "ERROR") == "user"

    # If a user were to enter `test_username` for username and `test_password`
    # for password, it would result in this function call
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input=config_entry,
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result.get("type", "ERROR") == FlowResultType.CREATE_ENTRY
    assert result.get("title", "ERROR") == "test_username"
    assert result.get("data") == config_entry
    assert result.get("result", None)


# In this case, we want to simulate a failure during the config flow.
# We use the `error_on_get_data` mock instead of `bypass_get_data`
# (note the function parameters) to raise an Exception during
# validation of the input config.
@pytest.mark.asyncio
async def test_failed_config_flow(
    hass: HomeAssistant,
    error_on_get_data,  # noqa: ANN001
    config_data,  # noqa: ANN001
) -> None:
    """Test a failed config flow due to credential validation failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result.get("type", "ERROR") == FlowResultType.FORM
    assert result.get("step_id", "ERROR") == "user"

    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input=config_data,
    )

    assert result.get("type", "ERROR") == FlowResultType.FORM
    assert result.get("errors") == {"base": "auth"}


# Our config flow also has an options flow, so we must test it as well.
@pytest.mark.asyncio
async def test_options_flow(
    hass: HomeAssistant,
    config_entry,  # noqa: ANN001
    config_options,  # noqa: ANN001
) -> None:
    """Test an options flow."""
    # Create a new MockConfigEntry and add to HASS (we're bypassing config
    # flow entirely)
    config_entry.add_to_hass(hass)

    # Initialize an options flow
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Verify that the first options step is a user form
    assert result.get("type", "ERROR") == FlowResultType.FORM
    assert result.get("step_id", "ERROR") == "user"

    # Enter some fake data into the form
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input=config_options,
    )

    # Verify that the flow finishes
    assert result.get("type", "ERROR") == FlowResultType.CREATE_ENTRY
    assert result.get("title", "ERROR") == "test_username"

    # Verify that the options were updated
    assert config_entry.options == {BINARY_SENSOR: True}
