




# SMS Gateway for Home Assistant

This add-on provides a comprehensive SMS gateway to send and receive SMS using a USB GSM modem. It integrates seamlessly with Home Assistant through MQTT communication.

## Features

- **Bidirectional SMS Communication**: Send and receive SMS messages
- **MQTT Integration**: Full integration with Home Assistant via MQTT topics
- **Real-time Status Monitoring**: Network status, signal strength, and device health
- **Diagnostics & Health Monitoring**: Built-in diagnostics and health checks
- **Multi-architecture Support**: Supports aarch64, amd64, armhf, armv7, and i386
- **Huawei E3372 Optimized**: Special fixes for Huawei E3372 modem compatibility
- **Automatic Recovery**: Built-in error handling and recovery mechanisms

## Character Support

Handles all GSM7 characters (extended characters not handled):

    @£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ
     !\"#¤%&'()*+,-./0123456789:;<=>?
    ¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§
    ¿abcdefghijklmnopqrstuvwxyzäöñüà

## Integration with Home Assistant 

Communication with Home Assistant is realized using multiple MQTT topics:

### Core SMS Topics
- **SMS Sending**: `sms_gateway/send_sms` (configurable)
  - Home Assistant publishes SMS messages to be sent
- **SMS Receiving**: `sms_gateway/sms_received` (configurable)  
  - Add-on publishes received SMS messages to Home Assistant

### Status & Monitoring Topics
- **Status**: `sms_gateway/status` (configurable)
  - Real-time status updates including network info, signal strength, and device health
- **Start Time**: `sms_gateway/start_time` (configurable)
  - Timestamp when the add-on started

### MQTT Message Formats

#### SMS Sending (Home Assistant → Add-on)
```json
{
  "to": "+1234567890",
  "txt": "Hello from Home Assistant!"
}
```

#### SMS Receiving (Add-on → Home Assistant)
```json
{
  "from": "+1234567890", 
  "txt": "Hello from mobile device!",
  "timestamp": "2024-01-15T10:30:00+01:00"
}
```

#### Status Updates (Add-on → Home Assistant)
```json
{
  "status": "ready",
  "gsm": "ready",
  "mqtt": "connected",
  "signal": 75,
  "signal_strength": "good",
  "registration": "registered", 
  "operator": "Play",
  "sim_status": "ready",
  "device": "/dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0",
  "mode": "modem",
  "timestamp": "2024-01-15T10:30:00+01:00"
}
```

## System Requirements

### Home Assistant Requirements

#### Required Add-ons
- **MQTT Broker** (Mosquitto recommended)
  - Configure topics for SMS communication
  - Default topics: `sms_gateway/send_sms` and `sms_gateway/sms_received`
  - Status topic: `sms_gateway/status`
  - Start time topic: `sms_gateway/start_time`

#### Optional Add-ons
- **Samba Share**: For easy file management and configuration updates

### GSM Modem Requirements

#### Supported AT Commands
Your GSM modem must support the following AT commands:

| Command | Description | Purpose |
|---------|-------------|---------|
| `ATZ` | Reset modem | Initialize modem |
| `ATE0` | Set echo off | Disable command echo |
| `ATE1` | Set echo on | Enable command echo |
| `AT+CLIP?` | Get calling line identification | Caller ID support |
| `AT+CMEE=1` | Set extended error reporting | Better error messages |
| `AT+CSCS="GSM"` | Force GSM mode for SMS | SMS character encoding |
| `AT+CMGF=1` | Enable SMS text mode | SMS format |
| `AT+CSDH=1` | Enable detailed SMS headers | SMS metadata |
| `AT+CMGS=` | Send SMS message | SMS transmission |
| `AT+CMGD=` | Delete SMS messages | Message management |
| `AT+CMGL=` | List SMS messages | Message retrieval |
| `AT+CMGR=` | Read SMS by index | Message reading |
| `AT+CMGW=` | Write SMS to storage | Message storage |
| `AT+CMSS=` | Send stored SMS | Message sending |
| `AT+CPMS="ME","ME","ME"` | Set storage to Mobile Equipment | Message storage |
| `AT+CSQ` | Signal quality | Signal strength |
| `AT+CREG?` | Network registration | Network status |
| `AT+CNMI=2,1,0,0,0` | SMS notification mode | SMS reception |

#### Huawei-Specific Commands (E3372)
- `AT^CURC=0`: Disable periodic status messages
- `AT+COPS=0`: Automatic operator selection
- `AT^RESET`: Huawei-specific reset

### Supported Modems

#### Tested and Compatible
- **Huawei E3131**: Fully tested and supported
- **Huawei E3372**: Optimized with special fixes
- **Generic USB GSM modems**: Most standard AT command compatible modems

#### Known Limitations
- **Huawei HiLink modems**: Not supported (use modem mode instead)
- **Modems without AT command support**: Not compatible
- **Storage-only USB dongles**: Must be switched to modem mode

### Architecture Support

The add-on supports multiple architectures:
- **aarch64**: ARM 64-bit (Raspberry Pi 4, etc.)
- **amd64**: x86_64 (Intel/AMD 64-bit)
- **armhf**: ARM hard float (Raspberry Pi 2/3)
- **armv7**: ARM v7 (older ARM devices)
- **i386**: x86 32-bit (legacy systems)

### Hardware Requirements

#### Minimum Requirements
- **RAM**: 128MB available memory
- **Storage**: 50MB free space
- **USB Port**: Available USB port for GSM modem
- **Network**: Internet connection for MQTT communication

#### Recommended
- **RAM**: 256MB+ available memory
- **Storage**: 100MB+ free space
- **USB Power**: Powered USB hub for stable modem operation
- **Signal**: Good mobile network coverage
  
## Configuration

### Configuration Example

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

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `GSM_Mode` | string | `"modem"` | Operating mode (currently only 'modem' supported) |
| `GSM_Device` | string | `"/dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0"` | USB device path |
| `GSM_PIN` | string | `"0000"` | SIM card PIN code (optional for modern modems) |
| `MQTT_Host` | string | `"homeassistant.local"` | MQTT broker hostname |
| `MQTT_Port` | string | `"1883"` | MQTT broker port |
| `MQTT_User` | string | `"mqtt"` | MQTT username |
| `MQTT_Password` | password | `"mqtt"` | MQTT password |
| `MQTT_Receive` | string | `"sms_gateway/sms_received"` | Topic for received SMS |
| `MQTT_Send` | string | `"sms_gateway/send_sms"` | Topic for SMS to send |
| `MQTT_Status` | string | `"sms_gateway/status"` | Topic for status updates |
| `MQTT_StartTime` | string | `"sms_gateway/start_time"` | Topic for start time |
| `ADDON_Logging` | string | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `Run_Diagnostics` | boolean | `false` | Run diagnostics on startup |

### Device Path Configuration

**Recommended**: Use `/dev/serial/by-id/...` paths as they are stable and don't change when other devices are added.

**Alternative paths**:
- `/dev/ttyUSBx` (e.g., `/dev/ttyUSB0`, `/dev/ttyUSB1`)
- `/dev/ttyACMx` (e.g., `/dev/ttyACM0`, `/dev/ttyACM1`)

**Finding your device**:
1. Go to Home Assistant → Settings → System → Hardware
2. Look for USB device details
3. Use the `/dev/serial/by-id/...` path if available

### PIN Code Notes

- **Modern modems**: PIN functionality is often not needed
- **Legacy modems**: May require PIN code for SIM card access
- **Security**: PIN is optional and can be left as default "0000" if not needed

## Home Assistant Integration Examples

### Sending SMS

#### Script for Sending SMS
```yaml
alias: script-send-sms
sequence:
  - service: mqtt.publish
    data:
      qos: 0
      retain: false
      topic: "sms_gateway/send_sms"
      payload_template: "{\"to\": \"{{mobile}}\", \"txt\": \"{{txt}}\"}"
mode: single
```

#### Automation Example - Send SMS on Event
```yaml
alias: Send SMS on Door Open
description: "Send SMS when front door opens"
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
condition: []
action:
  - service: script.script_send_sms
    data:
      mobile: "+1234567890"
      txt: "Front door has been opened!"
mode: single
```

#### Manual SMS Test
```yaml
alias: Test SMS with Special Characters
description: "Test SMS with GSM7 characters"
    trigger: []
    condition: []
    action:
      - service: script.script_send_sms
        data:
      mobile: "+1234567890"
      txt: "@£$¥èéùìòÇ Hello from Home Assistant!"
mode: single
```

### Receiving SMS

#### Basic SMS Reception Handler
```yaml
alias: SMS Received Handler
description: "Handle incoming SMS messages"
trigger:
  - platform: mqtt
    topic: "sms_gateway/sms_received"
condition: []
action:
  - alias: Log received SMS
    service: system_log.write
    data:
      message: "SMS from {{trigger.payload_json.from}}: {{trigger.payload_json.txt}}"
      level: info
  - alias: Send acknowledgment
    service: mqtt.publish
          data:
      qos: 0
      retain: false
      topic: "sms_gateway/send_sms"
      payload_template: "{\"to\": \"{{trigger.payload_json.from}}\", \"txt\": \"SMS received: {{trigger.payload_json.txt}}\"}"
    mode: single
```

#### Smart Home Control via SMS
```yaml
alias: SMS Smart Home Control
description: "Control devices via SMS commands"
trigger:
  - platform: mqtt
    topic: "sms_gateway/sms_received"
condition: []
action:
  - alias: Check for "lights on"
    if:
      - condition: template
        value_template: "{{trigger.payload_json.txt|lower == 'lights on'}}"
    then:
      - service: homeassistant.turn_on
        target:
          entity_id: light.living_room
      - service: mqtt.publish
        data:
          qos: 0
          retain: false
          topic: "sms_gateway/send_sms"
          payload_template: "{\"to\": \"{{trigger.payload_json.from}}\", \"txt\": \"Lights turned on\"}"
  
  - alias: Check for "lights off"
          if:
            - condition: template
        value_template: "{{trigger.payload_json.txt|lower == 'lights off'}}"
          then:
      - service: homeassistant.turn_off
        target:
          entity_id: light.living_room
      - service: mqtt.publish
        data:
          qos: 0
          retain: false
          topic: "sms_gateway/send_sms"
          payload_template: "{\"to\": \"{{trigger.payload_json.from}}\", \"txt\": \"Lights turned off\"}"
  
  - alias: Check for "status"
          if:
            - condition: template
        value_template: "{{trigger.payload_json.txt|lower == 'status'}}"
          then:
        - service: mqtt.publish
          data:
            qos: 0
            retain: false
          topic: "sms_gateway/send_sms"
          payload_template: "{\"to\": \"{{trigger.payload_json.from}}\", \"txt\": \"Home Assistant is online. Available commands: lights on, lights off, status\"}"
    mode: single
```

#### SMS Status Monitoring
```yaml
alias: SMS Gateway Status Monitor
description: "Monitor SMS Gateway status and send alerts"
trigger:
  - platform: mqtt
    topic: "sms_gateway/status"
condition: []
action:
  - alias: Check for error status
    if:
      - condition: template
        value_template: "{{trigger.payload_json.status == 'error'}}"
    then:
      - service: persistent_notification.create
        data:
          title: "SMS Gateway Error"
          message: "SMS Gateway error: {{trigger.payload_json.message}}"
          notification_id: "sms_gateway_error"
  
  - alias: Check for low signal
    if:
      - condition: template
        value_template: "{{trigger.payload_json.signal < 20}}"
    then:
      - service: persistent_notification.create
        data:
          title: "SMS Gateway Low Signal"
          message: "Signal strength is low: {{trigger.payload_json.signal}}%"
          notification_id: "sms_gateway_low_signal"
mode: single
```

## Diagnostics & Health Monitoring

The SMS Gateway includes comprehensive diagnostics and health monitoring capabilities:

### Built-in Diagnostics

#### Health Checks
- **Modem Responsiveness**: Tests multiple AT commands to ensure modem is fully responsive
- **Network Status**: Checks network registration, signal strength, and operator information
- **SIM Card Status**: Verifies SIM card is ready and accessible
- **MQTT Connection**: Monitors MQTT broker connectivity

#### Diagnostic Commands
The system automatically runs health checks during:
- **Startup**: Full diagnostic check when the add-on starts
- **Periodic Monitoring**: Regular health checks every 3 minutes
- **Error Recovery**: Automatic diagnostics when errors are detected

#### Status Monitoring
Real-time status updates include:
- **Signal Strength**: Percentage and quality rating
- **Network Registration**: Registration status with mobile network
- **Operator Information**: Current mobile network operator
- **SIM Status**: SIM card readiness and PIN status
- **Device Information**: Modem device path and mode
- **MQTT Status**: Connection status to MQTT broker

### Manual Diagnostics

#### Running Diagnostics Mode
Set `Run_Diagnostics: true` in configuration to run comprehensive diagnostics on startup:

```yaml
Run_Diagnostics: true
```

This will:
1. Test all available USB devices
2. Check modem responsiveness
3. Verify network connectivity
4. Test SMS functionality
5. Validate MQTT connection

#### Diagnostic Output
Diagnostics provide detailed information about:
- Available USB devices
- Modem compatibility
- Network connectivity
- Signal strength measurements
- Error conditions and recommendations

### Health Monitoring Features

#### Automatic Recovery
- **Connection Monitoring**: Automatically detects and recovers from MQTT disconnections
- **Modem Reset**: Automatic modem reset on critical errors
- **Thread Monitoring**: Monitors GSM reader thread and restarts on failure

#### Error Handling
- **Graceful Degradation**: Continues operation with reduced functionality when possible
- **Error Reporting**: Detailed error messages sent via MQTT status topic
- **Logging**: Comprehensive logging for troubleshooting

#### Performance Optimization
- **Controlled Signal Checking**: Signal strength checks only when needed to prevent timeouts
- **Efficient AT Commands**: Optimized command sequences for better performance
- **Resource Management**: Proper cleanup and resource management

## Huawei E3372 Compatibility

### Special Optimizations

The SMS Gateway includes specific optimizations for Huawei E3372 modems:

#### AT Command Optimizations
- **AT^CURC=0**: Disables periodic status messages that can interfere with AT commands
- **AT+COPS=0**: Automatic operator selection for better connectivity
- **Controlled Signal Checking**: Reduced frequency of AT+CSQ commands to prevent timeouts

#### Timeout Handling
- **Reduced Timeouts**: AT+CSQ timeout reduced from 5s to 3s
- **Error Classification**: Timeout errors classified as debug messages rather than warnings
- **Graceful Degradation**: System continues operation even with signal check timeouts

#### Reset Commands
Additional reset commands for Huawei modems:
- **AT^CURC=0**: Disable periodic status messages
- **AT^RESET**: Huawei-specific reset command

### Troubleshooting Huawei E3372

If you experience issues with Huawei E3372:

1. **Check USB Power Management**:
   ```bash
   echo 'on' | sudo tee /sys/bus/usb/devices/*/power/control
   ```

2. **Verify Modem Mode**:
   ```bash
   usb_modeswitch -v 12d1 -p 1f01 -M '55534243123456780000000000000011063000000100000000000000000000'
   ```

3. **Check Driver Issues**:
   ```bash
   lsmod | grep cdc_ether
   echo 'blacklist cdc_ether' | sudo tee -a /etc/modprobe.d/blacklist.conf
   ```

4. **Serial Port Settings**: Ensure proper configuration:
   - Baud rate: 115200
   - Data bits: 8
   - Stop bits: 1
   - Parity: None
   - Flow control: None

## Development & Testing

### Test Environment
- **Hardware**: Raspberry Pi 4B
- **GSM Modem**: Huawei E3131 (primary), Huawei E3372 (optimized)
- **Home Assistant Core**: 2024.3.3+
- **Supervisor**: 2024.03.1+
- **Operating System**: 12.1+
- **Frontend**: 20240307.0+

### Version Information
- **Current Version**: 1.0
- **Stage**: Stable
- **Repository**: https://github.com/kowalczykrafal/sms_gateway

## Troubleshooting

### Common Issues

#### Modem Not Detected
1. Check USB device path in configuration
2. Verify modem is in correct mode (not HiLink)
3. Check USB power supply
4. Run diagnostics mode for device detection

#### SMS Not Sending/Receiving
1. Verify network registration status
2. Check signal strength
3. Confirm SIM card is active
4. Test with manual AT commands

#### MQTT Connection Issues
1. Verify MQTT broker configuration
2. Check network connectivity
3. Confirm MQTT credentials
4. Review MQTT broker logs

#### Signal Strength Problems
1. Check antenna placement
2. Verify mobile network coverage
3. Test with different locations
4. Consider external antenna

### Log Analysis

#### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operation status
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors requiring attention
- **CRITICAL**: System-stopping errors

#### Key Log Messages
- `GSM device is ready`: Modem initialization successful
- `SMS Gateway error`: Critical error requiring attention
- `Signal strength is low`: Network connectivity issues
- `MQTT connection lost`: Communication problems

## Support & Contributing

### Getting Help
- **Issues**: Report bugs and request features via GitHub issues
- **Documentation**: Check this documentation for common solutions
- **Community**: Join Home Assistant community forums

### Contributing
- **Repository**: https://github.com/kowalczykrafal/sms_gateway
- **Contributors**: See [contributors page](https://github.com/kowalczykrafal/sms_gateway) for a list of contributors
- **Pull Requests**: Welcome for bug fixes and improvements

### Author
- **Kowal**: rkowalik@o2.pl
- **Repository**: https://github.com/kowalczykrafal/sms_gateway

### Original Author
- **Helios**: helios14_75@hotmail.fr
- **Original Repository**: https://github.com/Helios06/sms_gateway

### MIT License

Copyright (c) 2023-2024  Kowal  rkowalik@o2.pl

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
