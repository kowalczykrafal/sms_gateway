# Kowal's Home Assistant Add-ons

This repository contains Home Assistant add-ons developed by Kowal.

## SMS Gateway

A comprehensive SMS gateway add-on to send and receive SMS using a USB GSM modem. It integrates seamlessly with Home Assistant through MQTT communication.

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] ![Supports armhf Architecture][armhf-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports i386 Architecture][i386-shield]

## Features

- **Bidirectional SMS Communication**: Send and receive SMS messages
- **MQTT Integration**: Full integration with Home Assistant via MQTT topics
- **Real-time Status Monitoring**: Network status, signal strength, and device health
- **Diagnostics & Health Monitoring**: Built-in diagnostics and health checks
- **Huawei E3372 Optimized**: Special fixes for Huawei E3372 modem compatibility
- **Automatic Recovery**: Built-in error handling and recovery mechanisms

## Integration with Home Assistant 

Communication with Home Assistant is realized using multiple MQTT topics:

### Core SMS Topics
- **SMS Sending**: `sms_gateway/send_sms` (configurable)
- **SMS Receiving**: `sms_gateway/sms_received` (configurable)

### Status & Monitoring Topics
- **Status**: `sms_gateway/status` (configurable)
- **Start Time**: `sms_gateway/start_time` (configurable)

## Installation

1. **Add this repository** to Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu (⋮) in the top right
   - Select **Repositories**
   - Add this repository URL: `https://github.com/kowalczykrafal/sms_gateway`
   - Click **Add**

2. **Install the SMS Gateway add-on**:
   - Find "SMS Gateway" in the add-on store
   - Click **Install**

3. **Configure the add-on**:
   - Set your GSM modem device path
   - Configure MQTT settings
   - Start the add-on

## Quick Start

1. **Configure your GSM modem** device path in the add-on settings
2. **Set up MQTT topics** for SMS communication
3. **Create Home Assistant automations** to send/receive SMS

## Configuration Example

```yaml
GSM_Mode: "modem"
GSM_Device: "/dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0"
GSM_PIN: "0000"
MQTT_Host: "homeassistant.local"
MQTT_Port: "1883"
MQTT_User: "mqtt"
MQTT_Password: "mqtt"
MQTT_Receive: "sms_gateway/sms_received"
MQTT_Send: "sms_gateway/send_sms"
MQTT_Status: "sms_gateway/status"
MQTT_StartTime: "sms_gateway/start_time"
ADDON_Logging: "INFO"
Run_Diagnostics: false
```

## Supported Modems

- **Huawei E3131**: Fully tested and supported
- **Huawei E3372**: Optimized with special fixes
- **Generic USB GSM modems**: Most standard AT command compatible modems

## Documentation

For detailed documentation, configuration options, and examples, see [DOCS.md](DOCS.md).

## Repository and Contributors

- **Current Repository**: https://github.com/kowalczykrafal/sms_gateway
- **Author**: Kowal (rkowalik@o2.pl)
- **Original Author**: Helios (helios14_75@hotmail.fr)
- **Original Repository**: https://github.com/Helios06/sms_gateway


[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg