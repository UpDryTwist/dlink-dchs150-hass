# This exists to set the Wi-Fi (client) settings for a DLink DCH-S150 motion detector
# This became particularly relevant after DLink abandoned this line (look, I don't blame them)
# in December 2022, meaning that you could no longer reset one of the motion detectors.  The
# detectors aren't the greatest, but they're decent, and you can run them w/o any other hubs
# or cloud (using code such as that from Postlund, linked below), and, well, I have a bunch
# sitting around, and they occasionally need to be reset!

# This contains code derived directly from:  https://github.com/postlund/dlink_hnap/blob/master/custom_components/dlink_hnap/dlink.py
# Also particular thanks to:  https://wiki.elvis.science/index.php?title=Examination_of_mydlink%E2%84%A2_home_devices
# To figure some of this out, I did as in the above link:  connect to the motion detector
# as an AP, and then start digging through the javascript (particularly to sort out getting
# the password AES-128 encryption correct).

import argparse
import xml
import hmac
import logging
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime
import xmltodict
from Crypto.Cipher import AES
import binascii

_LOGGER = logging.getLogger(__name__)

ACTION_BASE_URL = "http://purenetworks.com/HNAP1/"

def str2hexstr(origin):
    return ''.join(['{:x}'.format(ord(i)) for i in origin])

def _hmac(key, message):
    encodedKey = key.encode("utf-8")
    encodedMsg = message.encode("utf-8")
    hmacVal = hmac.new(encodedKey, encodedMsg, digestmod="MD5" )
    toHex = hmacVal.hexdigest()
    toUpper = toHex.upper()
    return toUpper

class AuthenticationError(Exception):
    """Thrown when login fails."""
    pass


class HNAPClient:
    """Client for the HNAP protocol."""

    def __init__(self, soap, username, password, loop=None):
        """Initialize a new HNAPClient instance."""
        self.username = username
        self.password = password
        self.logged_in = False
        self.loop = loop or asyncio.get_event_loop()
        self.actions = None
        self._client = soap
        self._private_key = None
        self._cookie = None
        self._auth_token = None
        self._timestamp = None

    async def login(self):
        """Authenticate with device and obtain cookie."""
        _LOGGER.info("Logging into device")
        self.logged_in = False
        resp = await self.call(
            "Login",
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

        try:
            password = _hmac(self._private_key, challenge)
            resp = await self.call(
                "Login",
                Action="login",
                Username=self.username,
                LoginPassword=password,
                Captcha="",
            )

            if resp["LoginResult"].lower() != "success":
                raise AuthenticationError("Incorrect username or password")

            if not self.actions:
                self.actions = await self.device_actions()

        except xml.parsers.expat.ExpatError:
            raise AuthenticationError("Bad response from device")

        self.logged_in = True

    def codeWifiPassword ( self, wifiPassword : str ) -> str:
        hexPassword = str2hexstr(wifiPassword)
        privateKey = self._private_key
        if len(privateKey) > 32:
            privateKey = privateKey[0:32]
        privateKeyBytes = binascii.unhexlify(privateKey).ljust(32, b'\0')
        passwordBytes = binascii.unhexlify(hexPassword).ljust(64, b'\0')

        cipher = AES.new( privateKeyBytes, AES.MODE_ECB)
        encoded = cipher.encrypt(passwordBytes)
        return bytes.hex(encoded)  # Convert bytes to a hex string

    async def device_actions(self):
        actions = await self.call("GetDeviceSettings")
        return list(
            map(lambda x: x[x.rfind("/") + 1 :], actions["SOAPActions"]["string"])
        )

    async def soap_actions(self, module_id):
        return await self.call("GetModuleSOAPActions", ModuleID=module_id)

    async def call(self, method, *args, **kwargs):
        """Call an HNAP method (async)."""
        # Do login if no login has been done before
        result = None
        if not self._private_key and method != "Login":
            await self.login()

        self._update_nauth_token(method)
        try:
            result = await self.soap().call(method, **kwargs)
            if "ERROR" in result:
                self._bad_response(None)
        except Exception as e:
            self._bad_response(e)
        return result

    def _bad_response(self, e):
        _LOGGER.error("Got an error, resetting private key")
        self._private_key = None
        raise Exception(f"got error response from device: {e}")

    def _update_nauth_token(self, action):
        """Update HNAP auth token for an action."""
        if not self._private_key:
            return

        self._timestamp = int(datetime.now().timestamp())
        self._auth_token = _hmac(
            self._private_key,
            '{0}"{1}{2}"'.format(self._timestamp, ACTION_BASE_URL, action),
        )
        _LOGGER.debug(
            "Generated new token for %s: %s (time: %d)",
            action,
            self._auth_token,
            self._timestamp,
        )

    def soap(self):
        """Get SOAP client with updated headers."""
        if self._cookie:
            self._client.headers["Cookie"] = "uid={0}".format(self._cookie)
        if self._auth_token:
            self._client.headers["HNAP_AUTH"] = "{0} {1}".format(
                self._auth_token, self._timestamp
            )

        return self._client

class NanoSOAPClient:

    BASE_NS = {
        "xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }
    ACTION_NS = {"xmlns": "http://purenetworks.com/HNAP1/"}

    def __init__(self, address, action, loop=None, session=None):
        self.address = "http://{0}/HNAP1".format(address)
        self.action = action
        self.loop = loop or asyncio.get_event_loop()
        self.session = session or aiohttp.ClientSession(loop=loop)
        self.headers = {}

    def _generate_request_xml(self, method, **kwargs):
        body = ET.Element("soap:Body")
        action = ET.Element(method, self.ACTION_NS)
        body.append(action)

        for param, value in kwargs.items():
            element = ET.Element( param )
            if isinstance(value, str) and len(value) > 0 and value[0] == '<':
                # Assume it's raw XML
                sub = ET.fromstring(value)
                element.append(sub)
            else:
                element.text = str(value)
            action.append(element)

        envelope = ET.Element("soap:Envelope", self.BASE_NS)
        envelope.append(body)

        f = BytesIO()
        tree = ET.ElementTree(envelope)
        tree.write(f, encoding="utf-8", xml_declaration=True)

        return f.getvalue().decode("utf-8")

    async def call(self, method, **kwargs):
        xml = self._generate_request_xml(method, **kwargs)

        headers = self.headers.copy()
        headers["SOAPAction"] = '"{0}{1}"'.format(self.action, method)

        resp = await self.session.post(
            self.address, data=xml, headers=headers, timeout=10
        )
        text = await resp.text()
        parsed = xmltodict.parse(text)
        if "soap:Envelope" not in parsed:
            _LOGGER.error("parsed: " + str(parsed))
            raise Exception("probably a bad response")

        return parsed["soap:Envelope"]["soap:Body"][method + "Response"]

async def doOurStuff ( ip : str,
                       pin : str,  # get this from the label on the back
                       macAddress : str, # get this from the label on the back
                       accessPointSSID : str,
                       wifiPassword : str = None ) :  # use None to indicate no security

    # Connect to the motion detector (as an AP) and login
    session = aiohttp.ClientSession()
    soap = NanoSOAPClient(ip, ACTION_BASE_URL, loop=loop, session=session)
    client = HNAPClient(soap, "Admin", pin, loop=loop)
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

    if not wifiPassword:
        supportedSecurity = "<SecurityInfo><SecurityType>NONE</SecurityType><Encryptions><string>NONE</string></Encryptions></SecurityInfo>"
        wifiPassword = "x"
        encodedKey = client.codeWifiPassword( wifiPassword )
    else:
        supportedSecurity = "<SecurityInfo><SecurityType>WPA2-PSK</SecurityType><Encryptions><string>AES</string></Encryptions></SecurityInfo>"
        encodedKey = input("Enter key:")

    resp = await client.call("SetAPClientSettings",
                             RadioID="RADIO_2.4GHz",
                             Enabled="true",
                             SSID=accessPointSSID,
                             ChannelWidth=1,
                             MacAddress=macAddress,
                             Key=encodedKey,
                             SupportedSecurity=supportedSecurity )

    print( resp )
    await session.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Wifi connector")
    parser.add_argument("--ip", help="IP of our DCH-S150 device after connecting to wifi", nargs='?', default="192.168.0.60")
    parser.add_argument("--pin", help="PIN for the DCH-S150 device - get from label on back" )
    parser.add_argument("--mac", help="MAC address for the DCH-S150 device - get from label on back" )
    parser.add_argument("--ssid", help="SSID of the AP you're connecting to")
    parser.add_argument("--password", help="Password to connect to the AP - don't provide if no security", default=None )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(doOurStuff(args.ip, args.pin, args.mac, args.ssid, args.password ))
