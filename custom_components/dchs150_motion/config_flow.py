"""Adds config flow for dlink_dchs150_hass."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from voluptuous import All
from voluptuous import Length

from .api import DlinkDchs150HassApiClient
from .api import fill_in_motion
from .api import fill_in_timezone
from .const import CONF_BACKOFF
from .const import CONF_DESCRIPTION
from .const import CONF_HOST
from .const import CONF_INTERVAL
from .const import CONF_NICK_NAME
from .const import CONF_NTP_SERVER
from .const import CONF_OP_STATUS
from .const import CONF_PIN
from .const import CONF_SENSITIVITY
from .const import CONF_TZ_DST
from .const import CONF_TZ_DST_END_DAY_OF_WEEK
from .const import CONF_TZ_DST_END_MONTH
from .const import CONF_TZ_DST_END_TIME
from .const import CONF_TZ_DST_END_WEEK
from .const import CONF_TZ_DST_START_DAY_OF_WEEK
from .const import CONF_TZ_DST_START_MONTH
from .const import CONF_TZ_DST_START_TIME
from .const import CONF_TZ_DST_START_WEEK
from .const import CONF_TZ_OFFSET
from .const import DEVICE_POLLING_FREQUENCY
from .const import DOMAIN
from .dch_wifi import AuthenticationError
from .dch_wifi import DeviceReturnedError
from .dch_wifi import GeneralCommunicationError
from .dch_wifi import InvalidDeviceState
from .dch_wifi import MotionInfo
from .dch_wifi import Rebooting
from .dch_wifi import UnableToConnect
from .dch_wifi import UnableToResolveHost

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DlinkDchs150HassFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for dlink_dchs150_hass."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            try:
                await self._test_credentials(
                    user_input[CONF_HOST], user_input[CONF_PIN]
                )
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )
            except AuthenticationError:
                self._errors[CONF_PIN] = "authentication_error"
            except GeneralCommunicationError:
                self._errors[CONF_HOST] = "general_communication"
            except DeviceReturnedError:
                self._errors["base"] = "device_returned_error"
            except Rebooting:
                self._errors["base"] = "rebooting"
            except UnableToResolveHost:
                self._errors[CONF_HOST] = "unable_to_resolve_host"
            except UnableToConnect:
                self._errors[CONF_HOST] = "unable_to_connect"
            except InvalidDeviceState:
                self._errors["base"] = "invalid_device_state"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DlinkDchs150HassOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit device connection data."""
        host = None
        pin = None
        interval = DEVICE_POLLING_FREQUENCY
        if user_input is not None:
            host = user_input[CONF_HOST]
            pin = user_input[CONF_PIN]
            interval = float(user_input[CONF_INTERVAL])
        _LOGGER.debug("Showing config form for interval %s", interval)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    vol.Required(CONF_PIN, default=pin): All(str, Length(6)),
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, host, pin):
        """Try to use the credentials.  Will return exception if not so."""
        session = async_create_clientsession(self.hass)
        time_info = fill_in_timezone(self.hass.config.time_zone, None)
        client = DlinkDchs150HassApiClient(host, pin, session, time_info, None)
        await client.async_get_data()


class DlinkDchs150HassOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options handler for dlink_dchs150_hass."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.defaults = None
        self.motion_defaults = None

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def load_motion_defaults(self):
        """Load the motion detection defaults"""
        session = async_create_clientsession(self.hass)
        host = self.config_entry.data.get(CONF_HOST)
        pin = self.config_entry.data.get(CONF_PIN)
        client = DlinkDchs150HassApiClient(host, pin, session, None, None)
        settings = await client.async_get_motion_detector_settings()
        _LOGGER.debug("Got motion detector settings of: %s", settings)
        self.motion_defaults = fill_in_motion(self.config_entry)
        if not self.motion_defaults:
            self.motion_defaults = MotionInfo()
        self.motion_defaults.backoff = int(settings["Backoff"])
        self.motion_defaults.nick_name = settings["NickName"]
        self.motion_defaults.description = settings["Description"]
        self.motion_defaults.sensitivity = int(settings["Sensitivity"])
        self.motion_defaults.op_status = settings["OPStatus"] != "false"

    def get_default(self, key):
        """Get the pre-existing option, or look up a default if it doesn't exist."""

        if not self.defaults:
            time_zone_info = fill_in_timezone(self.hass.config.time_zone, None)
            self.defaults = {
                CONF_INTERVAL: DEVICE_POLLING_FREQUENCY,
                CONF_BACKOFF: self.motion_defaults.backoff,
                CONF_SENSITIVITY: self.motion_defaults.sensitivity,
                CONF_OP_STATUS: self.motion_defaults.op_status,
                CONF_NICK_NAME: self.motion_defaults.nick_name,
                CONF_DESCRIPTION: self.motion_defaults.description,
                CONF_NTP_SERVER: time_zone_info.ntp_server,
                CONF_TZ_OFFSET: time_zone_info.tz_offset,
                CONF_TZ_DST: time_zone_info.tz_dst,
                CONF_TZ_DST_START_MONTH: time_zone_info.tz_dst_start_month,
                CONF_TZ_DST_START_WEEK: time_zone_info.tz_dst_start_week,
                CONF_TZ_DST_START_DAY_OF_WEEK: time_zone_info.tz_dst_start_day_of_week,
                CONF_TZ_DST_START_TIME: time_zone_info.tz_dst_start_time,
                CONF_TZ_DST_END_MONTH: time_zone_info.tz_dst_end_month,
                CONF_TZ_DST_END_WEEK: time_zone_info.tz_dst_end_week,
                CONF_TZ_DST_END_DAY_OF_WEEK: time_zone_info.tz_dst_end_day_of_week,
                CONF_TZ_DST_END_TIME: time_zone_info.tz_dst_end_time,
            }

        if key in self.options:
            return self.options.get(key, True)
        else:
            if key in self.defaults:
                return self.defaults[key]
            return None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(
                title="",
                data=self.options,
            )

        if not self.motion_defaults:
            await self.load_motion_defaults()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL, default=str(self.get_default(CONF_INTERVAL))
                    ): str,
                    vol.Required(
                        CONF_BACKOFF, default=self.get_default(CONF_BACKOFF)
                    ): int,
                    vol.Required(
                        CONF_SENSITIVITY, default=self.get_default(CONF_SENSITIVITY)
                    ): int,
                    vol.Required(
                        CONF_OP_STATUS, default=self.get_default(CONF_OP_STATUS)
                    ): bool,
                    vol.Required(
                        CONF_NICK_NAME, default=self.get_default(CONF_NICK_NAME)
                    ): str,
                    vol.Required(
                        CONF_DESCRIPTION, default=self.get_default(CONF_DESCRIPTION)
                    ): str,
                    vol.Required(
                        CONF_NTP_SERVER, default=self.get_default(CONF_NTP_SERVER)
                    ): str,
                    vol.Required(
                        CONF_TZ_OFFSET, default=self.get_default(CONF_TZ_OFFSET)
                    ): int,
                    vol.Required(
                        CONF_TZ_DST, default=self.get_default(CONF_TZ_DST)
                    ): bool,
                    vol.Required(
                        CONF_TZ_DST_START_MONTH,
                        default=self.get_default(CONF_TZ_DST_START_MONTH),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_START_WEEK,
                        default=self.get_default(CONF_TZ_DST_START_WEEK),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_START_DAY_OF_WEEK,
                        default=self.get_default(CONF_TZ_DST_START_DAY_OF_WEEK),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_START_TIME,
                        default=self.get_default(CONF_TZ_DST_START_TIME),
                    ): str,
                    vol.Required(
                        CONF_TZ_DST_END_MONTH,
                        default=self.get_default(CONF_TZ_DST_END_MONTH),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_END_WEEK,
                        default=self.get_default(CONF_TZ_DST_END_WEEK),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_END_DAY_OF_WEEK,
                        default=self.get_default(CONF_TZ_DST_END_DAY_OF_WEEK),
                    ): int,
                    vol.Required(
                        CONF_TZ_DST_END_TIME,
                        default=self.get_default(CONF_TZ_DST_END_TIME),
                    ): str,
                }
            ),
        )
