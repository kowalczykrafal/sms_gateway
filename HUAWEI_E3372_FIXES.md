# Huawei E3372 Timeout Fixes

## Problem
Huawei E3372 modem experiences frequent timeouts with AT+CSQ command, causing error messages every 3 minutes:
```
❌ Error sending AT command : Timeout waiting for OK response after 5s for command: b'AT+CSQ'
```

## Implemented Solutions

### 1. AT^CURC=0 Command
- **Purpose**: Disables periodic status messages from the modem
- **Location**: Added to GSM initialization in `gsm_core.py`
- **Effect**: Prevents modem from sending unsolicited status updates that can interfere with AT commands

### 2. Huawei E3372 Specific Commands
Added during initialization:
- `AT^CURC=0` - Disable periodic status messages
- `AT+COPS=0` - Automatic operator selection
- ~~`AT^SYSCFGEX`~~ - **REMOVED** (causes timeouts on some modems)

### 3. Controlled Signal Checking
- **Problem**: AT+CSQ command called in multiple places causes timeouts
- **Solution**: Added `skip_signal_check` parameter to `checkNetworkStatus()`
- **Effect**: Signal strength is checked only in specific places (startup and periodic status), not in other diagnostic functions

### 4. Improved Error Handling
- Reduced timeout for AT+CSQ from 5s to 3s
- Changed timeout errors from warnings to debug messages
- Added Huawei-specific reset commands

### 5. Additional Reset Commands
Added to reset sequence in `gsm_reset.py`:
- `AT^CURC=0` - Disable periodic status messages
- `AT^RESET` - Huawei specific reset

## Files Modified
- `gsm_core.py` - Added Huawei E3372 initialization commands
- `gsm_commands.py` - Added Huawei command constants
- `gsm_diagnostics.py` - Added skip_signal_check option
- `gsm_reset.py` - Added Huawei reset commands
- `sms_launcher.py` - Use skip_signal_check for periodic status

## Alternative Solutions (if problems persist)

### 1. USB Power Management
```bash
# Disable USB power management
echo 'on' | sudo tee /sys/bus/usb/devices/*/power/control
```

### 2. Modem Mode Switch
```bash
# Switch to modem mode (if in storage mode)
usb_modeswitch -v 12d1 -p 1f01 -M '55534243123456780000000000000011063000000100000000000000000000'
```

### 3. Driver Issues
```bash
# Check if cdc_ether driver is loaded
lsmod | grep cdc_ether

# If loaded, blacklist it
echo 'blacklist cdc_ether' | sudo tee -a /etc/modprobe.d/blacklist.conf
```

### 4. Serial Port Settings
Ensure proper serial port configuration:
- Baud rate: 115200
- Data bits: 8
- Stop bits: 1
- Parity: None
- Flow control: None

## Testing
After implementing these fixes:
1. Monitor logs for reduced timeout errors
2. Check that SMS functionality still works
3. Verify periodic status updates continue without timeouts
4. Test modem reset functionality

## Notes
- These fixes are specifically designed for Huawei E3372
- Other modems may not support all Huawei-specific commands
- The system will gracefully handle unsupported commands
- Signal strength information may be less frequent but system stability should improve
