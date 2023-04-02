# dlink_dchs150_hass

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**This component will set up the following platforms.**

| Platform        | Description                                                               |
| --------------- | ------------------------------------------------------------------------- |
| `binary_sensor` | Show something `True` or `False`.                                         |

![DCH-S150][dch-s150]

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `dchs150_motion`.
4. Download _all_ the files from the `custom_components/dchs150_motion/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "DLink"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/dchs150_motion/translations/en.json
custom_components/dchs150_motion/translations/fr.json
custom_components/dchs150_motion/translations/nb.json
custom_components/dchs150_motion/__init__.py
custom_components/dchs150_motion/api.py
custom_components/dchs150_motion/binary_sensor.py
custom_components/dchs150_motion/config_flow.py
custom_components/dchs150_motion/const.py
custom_components/dchs150_motion/dch_wifi.py
custom_components/dchs150_motion/entity.py
custom_components/dchs150_motion/hass_integration.py
custom_components/dchs150_motion/manifest.json
custom_components/dchs150_motion/strings.json
```

## Configuration is done in the UI

<!---->

You can do a lot of additional configuration by clicking "Configuration" in the device setup.
Some of this is even more than you could do in the initial phone app!

*NOTE:* Pushing these parameters has only been tested a bit on my devices -- no guarantees it
won't screw up your device somehow.  But given that these devices are close to dead, anyhow, why
not experiment!

Here are some parameters you can tinker with:

| Parameter       | Description
| --------------- | -------------------------------------------------------------------------
| `Update Interval` | Sets the polling frequency from HASS.  You can set this to any number; it's in seconds (fractional seconds appear to work). Note that the smaller the number, the more network traffic, and the more server load -- but the faster the responsiveness.
| `Device Wait`     | Otherwise known as "backoff".  This is how long the device ignores additional motion, before detecting a "new" motion.  By default, this was set to 30 seconds in the device - you probably noticed that it would ignore your motion.  If you're trying to get a motion sensor that keeps triggered when you keep moving (this is, I think, the normal case), then set this down low, like 1-2 seconds.  Just the ability to bump this down made the device so much better for me!
| `Sensitivity`     | I'm not sure exactly how this works, but you can tweak it to see how it goes . . .
| `Disable Detector` | It's a setting, so I included it . . . but why bother?
| `Nickname`        | I don't know that this is useful, but it can be set.  NOTE:  I couldn't get the HNAP command `SetDeviceSettings` to work, so I couldn't reset the basic device name, which is what would be really useful.  If you know the parameters to that command, please let me know!
| `Description`     | Another one that may not be useful . . . but you can set it on the device . . .
| `NTP server`      | The device _really_ needs to get to a good NTP server, or it won't work.  By default it goes to ntp1.dlink.com.  That DNS entry was offline for a while, but recently (2023-03-30) has been repointed to time2.google.com.  I default this to time.google.com.
| Time zone stuff   | You should set this all appropriately for your location.

## Initializing a device

If for some reason you have a DCH-S150 that you never configured, or if you have to
factory-reset your device (hopefully not because you were futzing with parameters with this
component!), then you can check out my script [here](https://raw.githubusercontent.com/UpDryTwist/defogger-dch-s150/master/dch-wifi.py)

* You can probably ignore the rest of the project it’s in. I initially cloned bmork’s cool DCS-8000LH defogger (i.e., cloud remover) project, and started tinkering with that, until I remembered that I’d never been successful setting up my devices using Bluetooth from my phone – so I never got the BTLE stuff to work – and, frankly, you don’t need to.

* You need to connect your wifi to the access point the device advertises. Afterwards, it’ll probably show up at IP 192.168.0.60. Make sure you can access that cleanly before anything else (you can go try logging in at that IP - won’t accomplish much, but proves you can get there).  I do all this from a Linux box - that's probably the easiest way.

* In theory, this code supports both password-protected wi-fi and open wi-fi. I wrote all the code to work with a password, and debugged it through to the point that the D-Link device was accepting my requests without error, but not connecting to my network . . . and then I finally remembered that I had to set up a whole separate 2.4Ghz open network (filtered by MAC address) for these devices, as they didn’t like connecting to my main network. SO . . . if your network is password protected, this may or may not work for you.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

Couldn't say enough good things about [@postlund](https://github.com/postlund)'s [original D-Link HNAP integration](https://github.com/postlund/dlink_hnap), which formed the initial base for the HNAP communications!

Some additional work added from [@openhab](https://github.com/openhab)'s [D-Link implementation](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.dlinksmarthome/src/main/java/org/openhab/binding/dlinksmarthome/internal)

Double-checked against [@iobroker-community-adapters](https://iobroker-community-adapters) [D-Link implementation](https://github.com/iobroker-community-adapters/ioBroker.mydlink)

You can find HNAP documentation (a bit old) [here](https://wiki.elvis.science/images/5/58/HNAP_Protocol.pdf), which was useful for probing the device.

For deconstructing what might be happening in the firmware, take a look at [@0xdead8ead](https://github.com/0xdead8ead)'s copy of the [DIR-865 firmware](https://github.com/0xdead8ead/dlink_dir-865L/tree/master/DIR-865L_REVA_FIRMWARE_1.07.B01/fmk/rootfs/etc/templates/hnap) or [@jhbsz](https://github.com/jhbsz)'s copy of the [DIR-850L_A1 firmware](https://github.com/jhbsz/DIR-850L_A1/tree/master/templates/aries/progs/htdocs/hnap) -- this was helpful in guessing parameters in general for the D-Link HNAP implementation.

In terms of understanding the authentication handshake, check out the Embedded Lab Vienna for IoT & Security (ELVIS)'s [HNAPown](https://wiki.elvis.science/index.php?title=HNAP0wn:_The_Home_Network_Administration_Protocol_Owner) for a good discussion of brute forcing the embedded HTTP server.



---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/updrytwist
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/updrytwist/dlink-dchs150-hass.svg?style=for-the-badge
[commits]: https://github.com/updrytwist/dlink-dchs150-hass/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[dch-s150]: dch-s150.jpg
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/updrytwist/dlink-dchs150-hass.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40updrytwist-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/updrytwist/dlink-dchs150-hass.svg?style=for-the-badge
[releases]: https://github.com/updrytwist/dlink-dchs150-hass/releases
[user_profile]: https://github.com/updrytwist
