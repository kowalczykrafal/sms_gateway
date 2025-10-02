# Signal Strength Checking Behavior

## Current Implementation

### ✅ Places where signal strength IS checked (AT+CSQ executed):

1. **Startup Status** (`sms_launcher.py` line 95)
   - Function: `checkNetworkStatus(skip_signal_check=False)`
   - When: Once during GSM gateway initialization
   - Purpose: Get initial signal strength reading

2. **Periodic Status** (`sms_launcher.py` line 170)
   - Function: `checkNetworkStatus(skip_signal_check=False)`
   - When: Every 3 minutes in main loop
   - Purpose: Monitor signal strength over time

### ❌ Places where signal strength is NOT checked (AT+CSQ skipped):

1. **Device Info Retrieval** (`gsm_diagnostics.py` line 118)
   - Function: `getNetworkInfo()` → `checkNetworkStatus(skip_signal_check=True)`
   - When: Called to get device/mode information
   - Purpose: Avoid unnecessary signal checks when only device info is needed

2. **Diagnostic Functions**
   - Any other calls to `checkNetworkStatus()` without explicit parameter
   - Purpose: Prevent timeouts in diagnostic operations

## MQTT Status Messages

### Startup Status (with signal strength):
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
  "timestamp": "2025-09-30T07:21:41.609810+02:00"
}
```

### Periodic Status (every 3 minutes, with signal strength):
```json
{
  "status": "ready",
  "gsm": "ready",
  "mqtt": "connected", 
  "signal": 68,
  "signal_strength": "good",
  "registration": "registered",
  "operator": "Play",
  "sim_status": "ready",
  "device": "/dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0",
  "mode": "modem",
  "timestamp": "2025-09-30T07:24:41.609810+02:00"
}
```

## Benefits

1. **Signal Monitoring**: Regular signal strength updates every 3 minutes
2. **Reduced Timeouts**: Signal checks only where needed
3. **Stable Operation**: No unnecessary AT+CSQ commands in diagnostic functions
4. **Huawei E3372 Compatible**: Works with problematic modems

## Timeline

- **T=0**: Startup with full signal check
- **T=3min**: Periodic status with signal check
- **T=6min**: Periodic status with signal check
- **T=9min**: Periodic status with signal check
- **...**: Continues every 3 minutes

This ensures consistent signal strength monitoring while maintaining system stability.

