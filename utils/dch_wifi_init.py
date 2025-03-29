"""
Exists to set the Wi-Fi (client) settings for a DLink DCH-S150 motion detector.

This became particularly relevant after DLink abandoned this line (look, I don't blame them)
in December 2022, meaning that you could no longer reset one of the motion detectors.  The
detectors aren't the greatest, but they're decent, and you can run them w/o any other hubs
or cloud (using code such as that from Postlund, linked below), and, well, I have a bunch
sitting around, and they occasionally need to be reset!

This contains code derived directly from:  https://github.com/postlund/dlink_hnap/blob/master/custom_components/dlink_hnap/dlink.py
Also particular thanks to:  https://wiki.elvis.science/index.php?title=Examination_of_mydlink%E2%84%A2_home_devices
To figure some of this out, I did as in the above link:  connect to the motion detector
as an AP, and then start digging through the javascript (particularly to sort out getting
the password AES-128 encryption correct).
"""

from __future__ import annotations

import argparse
import asyncio
import binascii
import logging

import aiohttp
from Crypto.Cipher import AES  # nosec

from custom_components.dchs150_motion.const import DEFAULT_SOAP_TIMEOUT
from custom_components.dchs150_motion.dch_wifi import (
    HNAPClient,
    NanoSOAPClient,
    str2hexstr,
)

_LOGGER = logging.getLogger(__name__)

ACTION_BASE_URL = "http://purenetworks.com/HNAP1/"


def code_wifi_password(wifi_password: str, private_key: str | None) -> str:
    """Encode the wifi password for the DCH-S150 device."""
    if not private_key:
        raise ValueError("No private key provided.")
    hex_password = str2hexstr(wifi_password)
    if len(private_key) > 32:  # noqa: PLR2004
        private_key = private_key[0:32]
    private_key_bytes = binascii.unhexlify(private_key).ljust(32, b"\0")
    password_bytes = binascii.unhexlify(hex_password).ljust(64, b"\0")

    cipher = AES.new(private_key_bytes, AES.MODE_ECB)
    encoded = cipher.encrypt(password_bytes)
    return bytes.hex(encoded)  # Convert bytes to a hex string


async def do_our_stuff(
    ip: str,
    pin: str,  # get this from the label on the back
    mac_address: str,  # get this from the label on the back
    access_point_ssid: str,
    wifi_password: str | None = None,
) -> None:  # use None to indicate no security
    """Set the wifi settings for the DCH-S150 device."""
    # Connect to the motion detector (as an AP) and login
    session = aiohttp.ClientSession()
    soap = NanoSOAPClient(ip, ACTION_BASE_URL, session=session)
    client = HNAPClient(soap, "Admin", pin)
    await client.login()

    # If you're curious . . .
    #  print(f"Supported actions:")
    #  print("\n".join(client.actions))
    #  resp = await client.call( "GetInternetSettings" )
    #  print( resp )
    #  resp = await client.call("GetWLanRadios")
    #  print( resp )
    #  resp = await client.call("GetAPClientSettings", RadioID="RADIO_2.4GHz")
    #  print( resp )

    # Format here was largely gotten at through guessing, and by looking at some of the XML
    # used by DLink HNAP-based access points.  For sure it works for open access; it /may/
    # work for WPA2-PSK (never got that to work, but that's also related to my networking
    # environment).

    if not wifi_password:
        supported_security = "<SecurityInfo><SecurityType>NONE</SecurityType><Encryptions><string>NONE</string></Encryptions></SecurityInfo>"
        wifi_password = "x"  # noqa: S105  # nosec
    else:
        supported_security = "<SecurityInfo><SecurityType>WPA2-PSK</SecurityType><Encryptions><string>AES</string></Encryptions></SecurityInfo>"

    encoded_key = code_wifi_password(wifi_password, client.private_key)

    resp = await client.call(
        "SetAPClientSettings",
        RadioID="RADIO_2.4GHz",
        Enabled="true",
        SSID=access_point_ssid,
        ChannelWidth=1,
        MacAddress=mac_address,
        Key=encoded_key,
        SupportedSecurity=supported_security,
        timeout=DEFAULT_SOAP_TIMEOUT,
    )

    print(resp)  # noqa: T201
    await session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wifi connector")
    parser.add_argument(
        "--ip",
        help="IP of our DCH-S150 device after connecting to wifi",
        nargs="?",
        default="192.168.0.60",
    )
    parser.add_argument(
        "--pin",
        help="PIN for the DCH-S150 device - get from label on back",
    )
    parser.add_argument(
        "--mac",
        help="MAC address for the DCH-S150 device - get from label on back",
    )
    parser.add_argument("--ssid", help="SSID of the AP you're connecting to")
    parser.add_argument(
        "--password",
        help="Password to connect to the AP - don't provide if no security",
        default=None,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    our_loop = asyncio.get_event_loop()

    our_loop.run_until_complete(
        do_our_stuff(
            args.ip,
            args.pin,
            args.mac,
            args.ssid,
            args.password,
        ),
    )
