#!/usr/bin/with-contenv bashio

# Load USB modules for usbreset functionality
echo "run.sh: Loading USB modules..."
modprobe usb-storage 2>/dev/null || true
modprobe usb-serial 2>/dev/null || true
modprobe cdc-acm 2>/dev/null || true
modprobe usbnet 2>/dev/null || true
modprobe usb-core 2>/dev/null || true
modprobe usb-common 2>/dev/null || true
modprobe usb-host 2>/dev/null || true

# Try to trigger udev events for USB devices
echo "run.sh: Triggering udev events..."
udevadm trigger --subsystem-match=usb 2>/dev/null || true
udevadm settle 2>/dev/null || true

# Optimized configuration loading
echo "run.sh: Loading configuration..."

# Function to get config value with fallback
get_config() {
    local key="$1"
    local default="$2"
    
    if command -v bashio &> /dev/null; then
        local value=$(bashio::config "$key" 2>/dev/null || echo "$default")
        [ "$value" = "null" ] && value="$default"
        echo "$value"
    else
        # Fallback to environment variables
        local env_key=$(echo "$key" | tr '[:lower:]' '[:upper:]')
        echo "${!env_key:-$default}"
    fi
}

# Load all configuration values
mode=$(get_config 'GSM_Mode' 'modem')
device=$(get_config 'GSM_Device' '/dev/serial/by-id/usb-HUAWEI_Technology_HUAWEI_Mobile-if00-port0')
pin=$(get_config 'GSM_PIN' '0000')
host=$(get_config 'MQTT_Host' 'homeassistant.local')
port=$(get_config 'MQTT_Port' '1883')
user=$(get_config 'MQTT_User' 'mqtt')
password=$(get_config 'MQTT_Password' 'mqtt')
send=$(get_config 'MQTT_Send' 'send_sms')
recv=$(get_config 'MQTT_Receive' 'sms_received')
status=$(get_config 'MQTT_Status' 'sms_gateway/status')
logging=$(get_config 'ADDON_Logging' 'INFO')
diagnostics=$(get_config 'Run_Diagnostics' 'false')
# PIN functionality removed - not needed for modern modems

# Configuration values are already validated by get_config function

echo "run.sh: launching sms_manager.py"
echo "Configuration values:"
echo "  GSM_Mode: $mode"
echo "  GSM_Device: $device"
echo "  GSM_PIN: $pin"
echo "  MQTT_Host: $host"
echo "  MQTT_Port: $port"
echo "  MQTT_User: $user"
echo "  MQTT_Password: [HIDDEN]"
echo "  MQTT_Send: $send"
echo "  MQTT_Receive: $recv"
echo "  MQTT_Status: $status"
echo "  ADDON_Logging: $logging"
echo "  Run_Diagnostics: $diagnostics"
# PIN functionality removed - not needed for modern modems

# Check if diagnostics mode is requested (from configuration only)
if [ "$diagnostics" = "true" ]; then
    echo "run.sh: Running diagnostics mode..."
    echo "run.sh: Diagnostics enabled in configuration"
    # Build command with conditional flags
    cmd="python3 /sms_manager.py --mode $mode -d $device --pin $pin --host $host --port $port -u $user -s $password --send $send --recv $recv --status $status --log $logging --diagnostics"
    
    # Always test network in diagnostics mode
    cmd="$cmd --test-network"
    
    # PIN functionality removed - not needed for modern modems
    
    echo "run.sh: Executing command: $cmd"
    eval $cmd
else
    echo "run.sh: Starting normal operation..."
    # Build command with conditional skip-pin flag
    cmd="python3 /sms_manager.py --mode $mode -d $device --pin $pin --host $host --port $port -u $user -s $password --send $send --recv $recv --status $status --log $logging"
    
    # PIN functionality removed - not needed for modern modems
    
    eval $cmd
fi
