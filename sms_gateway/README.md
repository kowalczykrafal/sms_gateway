# SMS Gateway

This add-on provides a comprehensive SMS gateway to send and receive SMS using a USB GSM modem. It integrates seamlessly with Home Assistant through MQTT communication.

## Features

- **Bidirectional SMS Communication**: Send and receive SMS messages
- **MQTT Integration**: Full integration with Home Assistant via MQTT topics
- **Real-time Status Monitoring**: Network status, signal strength, and device health
- **Diagnostics & Health Monitoring**: Built-in diagnostics and health checks
- **Multi-architecture Support**: Supports aarch64, amd64, armhf, armv7, and i386
- **Huawei E3372 Optimized**: Special fixes for Huawei E3372 modem compatibility
- **Automatic Recovery**: Built-in error handling and recovery mechanisms

## Installation

1. Add the repository to Home Assistant: `https://github.com/kowalczykrafal/sms_gateway`
2. Install the "SMS Gateway" add-on from the add-on store
3. Configure your GSM modem device path
4. Set up MQTT topics for SMS communication
5. Start the add-on

## Configuration

See the main repository documentation for detailed configuration options and examples.

## Documentation

For detailed documentation, configuration options, and examples, see the main repository [DOCS.md](../DOCS.md).

## Support

- **Repository**: https://github.com/kowalczykrafal/sms_gateway
- **Author**: Kowal (rkowalik@o2.pl)
- **Issues**: Report bugs and request features via GitHub issues
