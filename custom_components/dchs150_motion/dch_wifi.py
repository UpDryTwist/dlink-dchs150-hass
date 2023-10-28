"""Implements HNAP connectivity to a D-Link DCH-S150"""
# Use the project defogger-dch-s150 to connect your DCH-S150
# to your wifi AP now that D-Link doesn't work.
# This contains code derived directly from:
#    https://github.com/postlund/dlink_hnap/blob/master/custom_components/dlink_hnap/dlink.py
# Also particular thanks to:
#    https://wiki.elvis.science/index.php?title=Examination_of_mydlink%E2%84%A2_home_devices
import asyncio
import hmac
import logging
import xml
import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import timedelta
from enum import Enum
from io import BytesIO
from socket import gaierror
from typing import Optional

import aiohttp
import xmltodict
from aiohttp.client_exceptions import ClientConnectorError

from .const import DEFAULT_BACKOFF_SECONDS
from .const import DEFAULT_NTP_SERVER
from .const import DEFAULT_OP_STATUS
from .const import DEFAULT_SENSITIVITY
from .const import DEFAULT_SOAP_TIMEOUT
from .const import DEFAULT_TZ_DST
from .const import DEFAULT_TZ_DST_END_DAY_OF_WEEK
from .const import DEFAULT_TZ_DST_END_MONTH
from .const import DEFAULT_TZ_DST_END_TIME
from .const import DEFAULT_TZ_DST_END_WEEK
from .const import DEFAULT_TZ_DST_START_DAY_OF_WEEK
from .const import DEFAULT_TZ_DST_START_MONTH
from .const import DEFAULT_TZ_DST_START_TIME
from .const import DEFAULT_TZ_DST_START_WEEK
from .const import DEFAULT_TZ_OFFSET
from .const import REBOOT_HOUR
from .const import REBOOT_SECONDS
from .const import REBOOT_SOAP_TIMEOUT

_LOGGER = logging.getLogger(__name__)

ACTION_BASE_URL = "http://purenetworks.com/HNAP1/"
DEFAULT_LOGIN_NAME = "Admin"


def str2hexstr(origin):
    """Convert a string to a hex string."""
    # pylint: disable=consider-using-f-string
    return "".join(["{:x}".format(ord(i)) for i in origin])


def _hmac(key, message):
    """Calculate HMAC-MD5 hash."""
    encoded_key = key.encode("utf-8")
    encoded_msg = message.encode("utf-8")
    hmac_val = hmac.new(encoded_key, encoded_msg, digestmod="MD5")
    to_hex = hmac_val.hexdigest()
    return to_hex.upper()


class AuthenticationError(Exception):
    """Thrown when login fails."""


class GeneralCommunicationError(Exception):
    """Thrown when communication with device fails,
    probably because an invalid form to the response."""


class DeviceReturnedError(Exception):
    """Device specifically returned an ERROR response, in its normal JSON format."""


class Rebooting(Exception):
    """Thrown when the device is rebooting."""


class UnableToResolveHost(Exception):
    """Unable to resolve the hostname"""


class UnableToConnect(Exception):
    """Unable to connect to the supplied host/IP."""


class InvalidDeviceState(Exception):
    """For some reason we're in an invalid state.  Hunh."""


class UnsupportedDeviceType(Exception):
    """A device type we've never seen"""


class HNAPDeviceStatus(Enum):
    """As far as we can tell, status of the device."""

    UNKNOWN = 0
    DISCONNECTED = 1
    INITIALIZING = 2
    ONLINE = 3
    COMMUNICATION_ERROR = 4
    NEEDS_REBOOT = 5
    REBOOTING = 6
    INTERNAL_ERROR = 7
    INVALID_PIN = 8


class TimeInfo:
    """Structure for passing around the time info for resetting the device"""

    ntp_server = DEFAULT_NTP_SERVER
    tz_offset = DEFAULT_TZ_OFFSET
    tz_dst = DEFAULT_TZ_DST
    tz_dst_start_month = DEFAULT_TZ_DST_START_MONTH
    tz_dst_start_week = DEFAULT_TZ_DST_START_WEEK
    tz_dst_start_day_of_week = DEFAULT_TZ_DST_START_DAY_OF_WEEK
    tz_dst_start_time = DEFAULT_TZ_DST_START_TIME
    tz_dst_end_month = DEFAULT_TZ_DST_END_MONTH
    tz_dst_end_week = DEFAULT_TZ_DST_END_WEEK
    tz_dst_end_day_of_week = DEFAULT_TZ_DST_END_DAY_OF_WEEK
    tz_dst_end_time = DEFAULT_TZ_DST_END_TIME


class DeviceDetectionSettingsInfo:
    """Structure for passing around motion detection / water settings info"""

    backoff = DEFAULT_BACKOFF_SECONDS  # Only for motion detector
    sensitivity = DEFAULT_SENSITIVITY  # Only for motion detector
    op_status = DEFAULT_OP_STATUS
    nick_name = None
    description = None


class HNAPClient:
    """Client for the HNAP protocol."""

    def __init__(
        self,
        soap,
        username,
        password,
        time_info: Optional[TimeInfo] = None,
        device_detection_settings_info: Optional[DeviceDetectionSettingsInfo] = None,
        loop=None,
    ):
        """Initialize a new HNAPClient instance."""
        self.username = username
        self.password = password
        self.loop = loop or asyncio.get_event_loop()
        self._client = soap
        self._private_key = None
        self._cookie = None
        self._auth_token = None
        self._timestamp = None
        self._status = HNAPDeviceStatus.UNKNOWN
        self._time_info = time_info
        self._device_detection_settings_info = device_detection_settings_info

        self._next_reboot_hour = REBOOT_HOUR
        self._next_reboot_at = None
        self._rebooted_at = None
        self._reboot_seconds = REBOOT_SECONDS
        self.set_next_reboot()

        self._ran_initialization = False
        self.mac_address = None
        self.model_name = None
        self.firmware_version = None
        self.hardware_version = None
        self.device_name = None
        self.vendor_name = None

    def set_next_reboot(self):
        """Set the next reboot time to the next time at the _next_reboot_hour."""
        now = datetime.now()
        next_reboot = now.replace(
            hour=self._next_reboot_hour, minute=0, second=0, microsecond=0
        )
        if next_reboot < now:
            next_reboot += timedelta(days=1)
        self._next_reboot_at = next_reboot
        _LOGGER.debug("Next reboot at %s", self._next_reboot_at)

    def get_status(self):
        """Return the status of the device."""
        return self._status

    def set_status(self, status):
        """Set the status of the device."""
        _LOGGER.debug(f"Setting {self.device_name} status to {status}")
        self._status = status

    def get_name(self):
        """Return something to identify us."""
        return self._client.address

    async def run_initialization(self):
        """Perform basic initialization.  Reset the time server for the device, and
        get the device settings."""
        if self._ran_initialization:
            return
        _LOGGER.debug("Running initialization.")
        settings = await self.get_device_settings()
        self.mac_address = settings["DeviceMacId"]
        self.model_name = settings["ModelName"]
        self.firmware_version = settings["FirmwareVersion"]
        self.hardware_version = settings["HardwareVersion"]
        self.device_name = settings["DeviceName"]
        self.vendor_name = settings["VendorName"]
        await self.set_time_settings()
        await self.set_device_settings()

        self._ran_initialization = True

    async def reboot(self):
        """Reboot the device."""
        _LOGGER.info("Rebooting device - %s", self.get_name())
        self._rebooted_at = datetime.now()
        self.set_next_reboot()
        self.set_status(HNAPDeviceStatus.REBOOTING)
        await self.call("Reboot", timeout=REBOOT_SOAP_TIMEOUT)

    async def get_latest_detection(self):
        """Get the latest motion detection from the device."""
        return await self.call(
            "GetLatestDetection", timeout=DEFAULT_SOAP_TIMEOUT, ModuleID=1
        )

    async def get_device_settings(self):
        """Get the device settings from the device."""
        return await self.call("GetDeviceSettings", timeout=DEFAULT_SOAP_TIMEOUT)

    async def get_device_detector_settings(self):
        """Get the motion or water detection settings from the device"""
        return await self.call(
            "GetWaterDetectorSettings"
            if self.device_name == "DCH-S160"
            else "GetMotionDetectorSettings",
            timeout=DEFAULT_SOAP_TIMEOUT,
            ModuleID=1,
        )

    async def set_time_settings(self):
        """Set the time settings on the device.  In particular, reset from ntp1.dlink.com!"""
        if not self._time_info:
            return
        _LOGGER.debug("Setting default time settings for device - %s", self.get_name())
        await self.call(
            "SetTimeSettings",
            timeout=DEFAULT_SOAP_TIMEOUT,
            NTP="true",
            NTPServer=self._time_info.ntp_server,
            TimeZone=self._time_info.tz_offset,
            DaylightSaving="true" if self._time_info.tz_dst else "false",
            DSTStartMonth=self._time_info.tz_dst_start_month,
            DSTStartWeek=self._time_info.tz_dst_start_week,
            DSTStartDayOfWeek=self._time_info.tz_dst_start_day_of_week,
            DSTStartTime=self._time_info.tz_dst_start_time,
            DSTEndMonth=self._time_info.tz_dst_end_month,
            DSTEndWeek=self._time_info.tz_dst_end_week,
            DSTEndDayOfWeek=self._time_info.tz_dst_end_day_of_week,
            DSTEndTime=self._time_info.tz_dst_end_time,
        )
        if _LOGGER.isEnabledFor(logging.DEBUG):
            time_settings = await self.call(
                "GetTimeSettings", timeout=DEFAULT_SOAP_TIMEOUT
            )
            _LOGGER.debug("Current time settings on the device: %s", time_settings)

    async def set_device_settings(self):
        """Set the motion detection settings on the device."""
        if not self._device_detection_settings_info:
            return
        _LOGGER.debug(
            "Setting device settings for device - %s %s (%s) Sensitive: %s On: %s Backoff %s Type: %s",
            self.get_name(),
            self._device_detection_settings_info.nick_name,
            self._device_detection_settings_info.description,
            self._device_detection_settings_info.sensitivity,
            self._device_detection_settings_info.op_status,
            self._device_detection_settings_info.backoff,
            self.device_name,
        )
        if self.device_name == "DCH-S150":
            await self.call(
                "SetMotionDetectorSettings",
                timeout=DEFAULT_SOAP_TIMEOUT,
                ModuleID=1,
                NickName=self._device_detection_settings_info.nick_name,
                Description=self._device_detection_settings_info.description,
                Sensitivity=self._device_detection_settings_info.sensitivity,
                OPStatus="true"
                if self._device_detection_settings_info.op_status
                else "false",
                Backoff=self._device_detection_settings_info.backoff,
            )
        elif self.device_name == "DCH-S160":
            await self.call(
                "SetWaterDetectorSettings",
                timeout=DEFAULT_SOAP_TIMEOUT,
                ModuleID=1,
                NickName=self._device_detection_settings_info.nick_name,
                Description=self._device_detection_settings_info.description,
                OPStatus="true"
                if self._device_detection_settings_info.op_status
                else "false",
            )
        else:
            _LOGGER.debug("Device type of %s is not a supported type", self.device_name)
            raise UnsupportedDeviceType(self.device_name)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            device_settings = self.get_device_detector_settings()

            _LOGGER.debug(
                "Current motion/moisture detector settings on the device: %s",
                device_settings,
            )

    async def login(self):
        """Authenticate with device and obtain cookie."""
        _LOGGER.debug("Logging into device - %s", self.get_name())
        self._private_key = None
        self._cookie = None
        self._auth_token = None
        self._timestamp = None

        self.set_status(HNAPDeviceStatus.INITIALIZING)

        try:
            resp = await self.call(
                "Login",
                timeout=DEFAULT_SOAP_TIMEOUT,
                Action="request",
                Username=self.username,
                LoginPassword="",
                Captcha="",
            )

            challenge = resp["Challenge"]
            public_key = resp["PublicKey"]
            self._cookie = resp["Cookie"]
            _LOGGER.debug(
                "Challenge: %s, Public key: %s, Cookie: %s",
                challenge,
                public_key,
                self._cookie,
            )

            self._private_key = _hmac(public_key + str(self.password), challenge)
            _LOGGER.debug("Private key: %s", self._private_key)

            password = _hmac(self._private_key, challenge)
            resp = await self.call(
                "Login",
                timeout=DEFAULT_SOAP_TIMEOUT,
                Action="login",
                Username=self.username,
                LoginPassword=password,
                Captcha="",
            )

            if resp["LoginResult"].lower() != "success":
                self.set_status(HNAPDeviceStatus.INVALID_PIN)
                raise AuthenticationError(
                    "Incorrect PIN supplied.  Be sure to use 6-digit PIN from back of device"
                )

        # If we already handled it, we're good . . .
        except (
            AuthenticationError,
            GeneralCommunicationError,
            DeviceReturnedError,
            Rebooting,
            UnableToResolveHost,
            UnableToConnect,
            InvalidDeviceState,
            UnsupportedDeviceType,
        ):
            raise

        except Exception as exc:
            _LOGGER.exception("Unexpected exception %s for %s", exc, self.get_name())
            self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
            raise AuthenticationError(
                "Unknown error trying to connect to device"
            ) from exc

        self.set_status(HNAPDeviceStatus.ONLINE)

        # This is overkill, but we want to reset all our devices to a better NTP server.
        await self.run_initialization()

    async def device_actions(self):
        """Get all available actions for the device."""
        actions = await self.call("GetDeviceSettings", DEFAULT_SOAP_TIMEOUT)
        return list(
            map(lambda x: x[x.rfind("/") + 1 :], actions["SOAPActions"]["string"])
        )

    async def soap_actions(self, module_id):
        """Get the available SOAP actions."""
        return await self.call(
            "GetModuleSOAPActions", DEFAULT_SOAP_TIMEOUT, ModuleID=module_id
        )

    async def resolve_state(self):
        """Resolve any actions required by the current state of the device."""

        # See if we've passed our _reboot_at time:
        if self._next_reboot_at and datetime.now() > self._next_reboot_at:
            self.set_status(HNAPDeviceStatus.NEEDS_REBOOT)

        match self._status:
            case (
                HNAPDeviceStatus.UNKNOWN
                | HNAPDeviceStatus.DISCONNECTED
                | HNAPDeviceStatus.COMMUNICATION_ERROR
                | HNAPDeviceStatus.INTERNAL_ERROR
                | HNAPDeviceStatus.INVALID_PIN
            ):
                await self.login()
            case HNAPDeviceStatus.INITIALIZING:
                # We shouldn't be here!
                self.set_status(HNAPDeviceStatus.UNKNOWN)
                _LOGGER.info(
                    "DCH-S150 status is INITIALIZING - shouldn't be making calls."
                )
                raise RecursionError(
                    "Device status is INITIALIZING - shouldn't be making calls."
                )
            case HNAPDeviceStatus.ONLINE:
                pass
            case HNAPDeviceStatus.NEEDS_REBOOT:
                await self.reboot()
                raise Rebooting("Device needs reboot - can't make calls.")
            case HNAPDeviceStatus.REBOOTING:
                # Get the time since the reboot was initiated
                reboot_seconds = (datetime.now() - self._rebooted_at).total_seconds()
                if reboot_seconds > self._reboot_seconds:
                    _LOGGER.debug(
                        "Rebooted at %s, reboot_seconds: %s, reboot_seconds: %s",
                        self._rebooted_at,
                        reboot_seconds,
                        self._reboot_seconds,
                    )
                    # We've rebooted, so now mark us as offline and ready to connect
                    self.set_status(HNAPDeviceStatus.DISCONNECTED)
                    # Try to login again
                    await self.login()
                else:
                    # Can't make calls at this point, as we're rebooting.
                    # Leave the status as REBOOTING
                    raise Rebooting("Device is rebooting - can't make calls.")
            case _:  # catch-all
                # We shouldn't be here!
                self.set_status(HNAPDeviceStatus.UNKNOWN)
                _LOGGER.info(
                    f"{self.device_name} status is in unknown state {self._status} - shouldn't be making calls."
                )
                raise ValueError(
                    "Device status is in unknown state {self._status}- shouldn't be making calls."
                )

    async def ensure_connected(self):
        """Ensure we're connected to the device."""
        await self.resolve_state()

    async def call(self, method: str, timeout: int, *_args, **kwargs):
        """Call an HNAP method (async)."""
        # Do login if no login has been done before
        result = None
        if method != "Reboot" and method != "Login":
            await self.resolve_state()

        self._update_nauth_token(method)
        try:
            try:
                result = await self.soap().call(method, timeout, **kwargs)
                if "ERROR" in result:
                    raise DeviceReturnedError(
                        f"{self.device_name} device {self.get_name()} returned a server error."
                    )
            # If we've already wrapped it in one of our exception types, it's good
            except DeviceReturnedError:
                self.set_status(HNAPDeviceStatus.INTERNAL_ERROR)
                raise
            except Rebooting:
                # Don't mess with the current status
                raise
            except GeneralCommunicationError:
                self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
                raise

            except xml.parsers.expat.ExpatError as exc:
                self.set_status(HNAPDeviceStatus.INTERNAL_ERROR)
                raise GeneralCommunicationError(
                    "Invalid response received from device.  Perhaps not a DCH-S1x0?"
                ) from exc

            except gaierror as exc:
                self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
                raise UnableToResolveHost(
                    "Unable to resolve hostname via DNS.  Please ensure no misspellings, etc."
                ) from exc

            except ClientConnectorError as exc:
                self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
                if isinstance(exc.__cause__, gaierror):
                    # Yeah, we're supposed to ignore implementations, but this is useful info . . .
                    raise UnableToResolveHost(
                        "Unable to resolve hostname via DNS.  Please ensure no misspellings, etc."
                    ) from exc
                else:
                    raise UnableToConnect(
                        f"Unable to connect to device: {exc}"
                    ) from exc

            except TimeoutError as exc:
                self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
                raise UnableToConnect(
                    "Timeout trying to connect to host/IP supplied."
                ) from exc

            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected exception %s from %s", exc, self.get_name()
                )
                self.set_status(HNAPDeviceStatus.COMMUNICATION_ERROR)
                raise GeneralCommunicationError(
                    f"Communication error from {self.get_name()}: {exc}"
                ) from exc
        except Exception as exc:  # pylint: disable=broad-except
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.exception("Received exception for %s: %s", self.get_name(), exc)
            raise

        return result

    def _update_nauth_token(self, action):
        """Update HNAP auth token for an action."""
        if not self._private_key:
            return

        self._timestamp = int(datetime.now().timestamp())
        self._auth_token = _hmac(
            self._private_key, f'{self._timestamp}"{ACTION_BASE_URL}{action}"'
        )

    def soap(self):
        """Get SOAP client with updated headers."""
        if self._cookie:
            self._client.headers["Cookie"] = f"uid={self._cookie}"
        if self._auth_token:
            self._client.headers["HNAP_AUTH"] = f"{self._auth_token} {self._timestamp}"

        return self._client


class NanoSOAPClient:
    """Basic SOAP client."""

    BASE_NS = {
        "xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }
    ACTION_NS = {"xmlns": "http://purenetworks.com/HNAP1/"}

    def __init__(self, address, action, loop=None, session=None):
        self.address = f"http://{address}/HNAP1"
        self.action = action
        self.loop = loop or asyncio.get_event_loop()
        self.session = session or aiohttp.ClientSession(loop=loop)
        self.headers = {}

    def _generate_request_xml_old(self, method, **kwargs):
        body = ET.Element("soap:Body")
        action = ET.Element(method, self.ACTION_NS)
        body.append(action)

        for param, value in kwargs.items():
            element = ET.Element(param)
            if isinstance(value, str) and len(value) > 0 and value[0] == "<":
                # Assume it's raw XML
                sub = ET.fromstring(value)
                element.append(sub)
            else:
                element.text = str(value)
            action.append(element)

        envelope = ET.Element("soap:Envelope", self.BASE_NS)
        envelope.append(body)

        file_handle = BytesIO()
        tree = ET.ElementTree(envelope)
        tree.write(file_handle, encoding="utf-8", xml_declaration=True)

        return file_handle.getvalue().decode("utf-8")

    def _generate_request_xml(self, method, **kwargs):
        parameters = ""
        for param, value in kwargs.items():
            parameters += f"<{param}>{value}</{param}>"

        request = f"""<?xml version ="1.0" encoding="utf-8"?>
          <soap:Envelope
          xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          soap:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <soap:Body>
              <{method} xmlns="http://purenetworks.com/HNAP1/">
                {parameters}
              </{method}>
            </soap:Body>
          </soap:Envelope>
        """
        return request

    async def call(self, method, timeout: int = 10, **kwargs):
        """Call a SOAP method."""
        request_xml = self._generate_request_xml(method, **kwargs)

        headers = self.headers.copy()
        headers["SOAPAction"] = f'"{self.action}{method}"'

        resp = await self.session.post(
            self.address, data=request_xml, headers=headers, timeout=timeout
        )
        text = await resp.text()
        parsed = xmltodict.parse(text)
        if "soap:Envelope" not in parsed:
            _LOGGER.error("parsed: %s", str(parsed))
            raise GeneralCommunicationError("Received a bad response from the device.")

        return parsed["soap:Envelope"]["soap:Body"][method + "Response"]
