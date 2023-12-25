"""Test dlink_dchs150_hass switch."""
# from unittest.mock import call
# from unittest.mock import patch

from custom_components.dchs150_motion import (
    async_setup_entry,
)

# from custom_components.dchs150_motion.const import (
#     DEFAULT_NAME,
#    DOMAIN,
# )


async def test_sensor_services(hass, config_entry):
    """Test sensor services."""
    # Create a mock entry so we don't have to go through config flow
    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()


# TODO:  Write some actual tests . . .
