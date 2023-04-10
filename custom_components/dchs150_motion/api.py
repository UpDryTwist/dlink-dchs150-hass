"""Sample API Client."""
import datetime
import logging

import aiohttp
import homeassistant.util.dt
import pytz
from homeassistant.config_entries import ConfigEntry

from .const import CONF_BACKOFF
from .const import CONF_DESCRIPTION
from .const import CONF_NICK_NAME
from .const import CONF_NTP_SERVER
from .const import CONF_OP_STATUS
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
from .const import DEFAULT_BACKOFF_SECONDS
from .const import DEFAULT_OP_STATUS
from .const import DEFAULT_SENSITIVITY
from .dch_wifi import HNAPClient
from .dch_wifi import MotionInfo
from .dch_wifi import NanoSOAPClient
from .dch_wifi import TimeInfo

ACTION_BASE_URL = "http://purenetworks.com/HNAP1/"
DEFAULT_LOGIN_NAME = "Admin"

_LOGGER: logging.Logger = logging.getLogger(__name__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


def set_if_set(entry: ConfigEntry, key: str, default):
    """If we have an option set, use it, otherwise stick to old."""
    value = entry.options.get(key)
    return value if value else default


def fill_in_motion(entry: ConfigEntry) -> MotionInfo:
    """Fill in the info we're going to use to set up the device's motion settings"""
    if entry.options.get(CONF_BACKOFF):
        motion_info = MotionInfo()
        motion_info.backoff = set_if_set(entry, CONF_BACKOFF, DEFAULT_BACKOFF_SECONDS)
        motion_info.sensitivity = set_if_set(
            entry, CONF_SENSITIVITY, DEFAULT_SENSITIVITY
        )
        motion_info.op_status = set_if_set(entry, CONF_OP_STATUS, DEFAULT_OP_STATUS)
        motion_info.nick_name = set_if_set(entry, CONF_NICK_NAME, None)
        motion_info.description = set_if_set(entry, CONF_DESCRIPTION, None)
        return motion_info
    else:
        return None


def fill_in_timezone(time_zone_string: str, entry: ConfigEntry) -> TimeInfo:
    """Fill in the info we're going to use to set up the device's time."""
    time_info = TimeInfo()

    if time_zone_string:
        tzinfo = homeassistant.util.dt.get_time_zone(time_zone_string)
        t_now = datetime.datetime.now(tzinfo)
        t_utcoffset = t_now.utcoffset().total_seconds()

        tz_info = pytz.timezone(time_zone_string)
        now = pytz.utc.localize(datetime.datetime.utcnow())
        is_dst = now.astimezone(tz_info).dst() != datetime.timedelta(0)

        time_info.tz_dst = is_dst
        time_info.tz_offset = t_utcoffset / (60 * 60)

        _LOGGER.debug(
            "Time zone settings: Time string from config = %s, "
            "UTC Offset = %s >> Daylight Savings = %s TZ Offset = %s",
            time_zone_string,
            t_utcoffset,
            is_dst,
            time_info.tz_offset,
        )
    if entry:
        time_info.ntp_server = set_if_set(entry, CONF_NTP_SERVER, time_info.ntp_server)
        time_info.tz_offset = set_if_set(entry, CONF_TZ_OFFSET, time_info.tz_offset)
        time_info.tz_dst = set_if_set(entry, CONF_TZ_DST, time_info.tz_dst)
        time_info.tz_dst_start_month = set_if_set(
            entry, CONF_TZ_DST_START_MONTH, time_info.tz_dst_start_month
        )
        time_info.tz_dst_start_week = set_if_set(
            entry, CONF_TZ_DST_START_WEEK, time_info.tz_dst_start_week
        )
        time_info.tz_dst_start_day_of_week = set_if_set(
            entry, CONF_TZ_DST_START_DAY_OF_WEEK, time_info.tz_dst_start_day_of_week
        )
        time_info.tz_dst_start_time = set_if_set(
            entry, CONF_TZ_DST_START_TIME, time_info.tz_dst_start_time
        )
        time_info.tz_dst_end_month = set_if_set(
            entry, CONF_TZ_DST_END_MONTH, time_info.tz_dst_end_month
        )
        time_info.tz_dst_end_week = set_if_set(
            entry, CONF_TZ_DST_END_WEEK, time_info.tz_dst_end_week
        )
        time_info.tz_dst_end_day_of_week = set_if_set(
            entry, CONF_TZ_DST_END_DAY_OF_WEEK, time_info.tz_dst_end_day_of_week
        )
        time_info.tz_dst_end_time = set_if_set(
            entry, CONF_TZ_DST_END_TIME, time_info.tz_dst_end_time
        )
    return time_info


class DlinkDchs150HassApiClient:
    """Implementation of the calls to the DCH-S150 API"""

    def __init__(
        self,
        host: str,
        pin: str,
        session: aiohttp.ClientSession,
        time_info: TimeInfo,
        motion_info: MotionInfo,
    ) -> None:
        """Integration API client for D-Link DCH-S150"""
        self._host = host
        self._pin = pin
        self._session = session

        self._soap = NanoSOAPClient(
            host, ACTION_BASE_URL, loop=None, session=self._session
        )

        self._client = HNAPClient(
            self._soap, DEFAULT_LOGIN_NAME, pin, time_info, motion_info, loop=None
        )
        self._prev_detect_time = None
        self._last_detect_time = None

    async def async_get_data(self) -> dict:
        """Get data from the API."""
        last_detection = await self.get_latest_detection()
        return {
            "last_detection": last_detection,
            "mac_address": self._client.mac_address,
            "model_name": self._client.model_name,
            "firmware_version": self._client.firmware_version,
            "hardware_version": self._client.hardware_version,
            "device_name": self._client.device_name,
            "vendor_name": self._client.vendor_name,
        }

    async def async_get_device_settings(self) -> dict:
        """Get device settings"""
        return await self._client.get_device_settings()

    async def async_get_motion_detector_settings(self) -> dict:
        """Get motion detector settings"""
        return await self._client.get_motion_detector_settings()

    async def get_latest_detection(self) -> datetime.date:
        """Get the last motion detected time."""

        resp = await self._client.get_latest_detection()
        if "LatestDetectTime" not in resp:
            # Not sure exactly what this means, but return something in the past.
            last_detected = datetime.datetime(
                year=2020, month=1, day=1, hour=1, minute=1, second=1
            )
        else:
            last_detected = datetime.datetime.fromtimestamp(
                float(resp["LatestDetectTime"])
            )
        if not self._last_detect_time or last_detected != self._last_detect_time:
            _LOGGER.debug(
                "Detected new motion on %s - was %s now %s",
                self._client.get_name(),
                self._last_detect_time,
                last_detected,
            )
            self._prev_detect_time = self._last_detect_time
            self._last_detect_time = last_detected
        return last_detected
