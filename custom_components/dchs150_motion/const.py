"""Constants for dlink_dchs150_hass."""
# Base component constants
NAME = "DLink DCHS150"
# This needs to match what's in manifest.json
DOMAIN = "dchs150_motion"
VERSION = "0.2.0"

ATTRIBUTION = "https://github.com/updrytwist/dlink-dchs150-hass"
ISSUE_URL = "https://github.com/updrytwist/dlink-dchs150-hass/issues"

# Icons
MOTION_ICON = "mdi:motion-sensor"
MOISTURE_ICON = "mdi:water"

# Device classes
# BINARY_SENSOR_DEVICE_CLASS = "motion"

# Platforms
BINARY_SENSOR = "binary_sensor"

# Configuration and options
CONF_ENABLED = "enabled"
CONF_HOST = "host"
CONF_PIN = "pin"
CONF_INTERVAL = "update_interval"
CONF_BACKOFF = "backoff"
CONF_SENSITIVITY = "sensitivity"
CONF_OP_STATUS = "op_status"
CONF_NICK_NAME = "nick_name"
CONF_DESCRIPTION = "description"

CONF_NTP_SERVER = "ntp_server"
CONF_TZ_OFFSET = "tz_offset"
CONF_TZ_DST = "tz_dst"
CONF_TZ_DST_START_MONTH = "tz_dst_start_month"
CONF_TZ_DST_START_WEEK = "tz_start_week"
CONF_TZ_DST_START_DAY_OF_WEEK = "tz_dst_start_day_of_week"
CONF_TZ_DST_START_TIME = "tz_dst_start_time"
CONF_TZ_DST_END_MONTH = "tz_dst_end_month"
CONF_TZ_DST_END_WEEK = "tz_dst_end_week"
CONF_TZ_DST_END_DAY_OF_WEEK = "tz_dst_end_day_of_week"
CONF_TZ_DST_END_TIME = "tz_dst_end_time"

# Device Parameters
BACKOFF_SECONDS = 30  # Time it takes itself to reset
DEVICE_POLLING_FREQUENCY = 1  # In seconds - detection time
DEFAULT_SENSITIVITY = 90
DEFAULT_OP_STATUS = True
DEFAULT_BACKOFF_SECONDS = 30

# Rebooting
REBOOT_SECONDS = 40
REBOOT_HOUR = 3

# SOAP parameters (in seconds)
DEFAULT_SOAP_TIMEOUT = 10
REBOOT_SOAP_TIMEOUT = 60

# Time Zone Info (until I do it properly - this is Chicago!)
DEFAULT_NTP_SERVER = "time.google.com"  # Reset this from ntp1.dlink.com!!
DEFAULT_TZ_OFFSET = -6
DEFAULT_TZ_DST = True
DEFAULT_TZ_DST_START_MONTH = 3
DEFAULT_TZ_DST_START_WEEK = 2
DEFAULT_TZ_DST_START_DAY_OF_WEEK = 0
DEFAULT_TZ_DST_START_TIME = "2:00AM"
DEFAULT_TZ_DST_END_MONTH = 11
DEFAULT_TZ_DST_END_WEEK = 1
DEFAULT_TZ_DST_END_DAY_OF_WEEK = 0
DEFAULT_TZ_DST_END_TIME = "2:00AM"

# Defaults
DEFAULT_NAME = "dlink_dchs150"
DEFAULT_SENSOR_NAME = "dlink_sensor"

# For state management
UPDATE_LISTENER_REMOVE = "update_listener_remove"


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This custom integration has been built to support the no-longer-supported
D-Link DCH-S150 motion sensor and DCH-S160 moisture sensor.
It is not affiliated with D-Link in any way.
Issues found may be reported here (but no fix promises):
{ISSUE_URL}
-------------------------------------------------------------------
"""
