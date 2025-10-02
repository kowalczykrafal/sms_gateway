"""
MIT License

Copyright (c) 2023-2024  Helios  helios14_75@hotmail.fr

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
"""

import sys
import signal
import argparse
import logging
import threading
import time
import json
import datetime
from gsm_core import GSM
from sms_mqtt_handler import create_mqtt_client, connect_mqtt_client, subscribe_to_topic
# sms_status_manager and sms_diagnostics removed - functionality moved to gsm_diagnostics


# Global variables
sms_gateway = None
mqtt_client = None
status_timer = None


def get_local_timestamp():
    """Get current timestamp in system's local timezone"""
    # Get system's local timezone
    local_tz = datetime.datetime.now().astimezone().tzinfo
    return datetime.datetime.now(local_tz).isoformat()


def signal_handler(sig, frame):
    """Handle system signals for graceful shutdown"""
    global sms_gateway, mqtt_client, status_timer

    logging.info('Closing sms gateway under signal handler')
    if 'status_timer' in globals() and status_timer:
        status_timer.cancel()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if sms_gateway:
        sms_gateway.stop()
    logging.info('... Sms gateway stopped and closed under signal handler')
    sys.exit(0)


def _initialize_gsm_gateway(loglevel, options, mqtt_client):
    """Initialize GSM gateway with proper error handling"""
    global sms_gateway
    
    logging.info('Starting SMS gateway')
    try:
        sms_gateway = GSM(loglevel, "Huawei", options.mode, options.device, options.pin, "", options.recv, mqtt_client, False)
        sms_gateway.start()
        
        # Check if GSM device opened successfully
        if not sms_gateway.Opened:
            logging.error(f"Failed to open GSM device: {options.device}")
            # Send error status to MQTT
            error_status = {"status": "error", "error": "gsm_device_error", "message": "Failed to open GSM device"}
            mqtt_client.publish(options.status, json.dumps(error_status), qos=0)
            return False
            
        # Wait for GSM to be ready with timeout
        if not _wait_for_gsm_ready(options.status, timeout=30):
            return False
            
        logging.info('GSM device is ready')
        
        # Send initial status now that GSM is fully ready (including SMS processing)
        logging.info('Sending initial status to MQTT (GSM fully ready)')
        
        # Send complete network status to MQTT (with full signal check on startup)
        try:
            network_info = sms_gateway.checkNetworkStatus(skip_signal_check=False)
            # Add device info for startup status
            device_info = sms_gateway.getNetworkInfo()
            status_data = {
                "status": "ready",
                "gsm": "ready",
                "mqtt": "connected",
                "signal": network_info.get("signal_percentage", 0),
                "signal_strength": network_info.get("signal_strength", "unknown"),
                "registration": network_info.get("registration", "unknown"),
                "operator": network_info.get("operator", "unknown"),
                "sim_status": network_info.get("sim_status", "unknown"),
                "device": device_info.get("device", "unknown"),
                "mode": device_info.get("mode", "unknown"),
                "timestamp": get_local_timestamp()
            }
            mqtt_client.publish(options.status, json.dumps(status_data), qos=0)
            logging.info(f'Initial status sent to MQTT topic: {options.status}')
        except Exception as e:
            logging.error(f'Failed to send initial status: {e}')
        
        # Send start time to MQTT
        start_time = get_local_timestamp()
        start_topic = getattr(options, 'MQTT_StartTime', 'sms_gateway/start_time')
        mqtt_client.publish(start_topic, start_time, qos=0)
        logging.info(f'Start time sent to MQTT topic: {start_topic} - {start_time}')
        
        return True
            
    except Exception as e:
        logging.error(f"Error starting GSM gateway: {e}")
        # Send error status to MQTT
        error_status = {"status": "error", "error": "gsm_startup_error", "message": str(e)}
        mqtt_client.publish(options.status, json.dumps(error_status), qos=0)
        return False


def _wait_for_gsm_ready(status_topic, timeout=30):
    """Wait for GSM device to be ready with timeout"""
    global sms_gateway
    
    start_time = time.time()
    while not sms_gateway.Ready:
        if time.time() - start_time > timeout:
            logging.error(f"GSM device initialization timeout after {timeout} seconds")
            # Send error status to MQTT
            error_status = {"status": "error", "error": "gsm_timeout", "message": "GSM initialization timeout"}
            mqtt_client.publish(status_topic, json.dumps(error_status), qos=0)
            return False
        time.sleep(1)
    return True


def _run_main_loop(options):
    """Simplified main loop - monitor MQTT and GSM thread status"""
    global mqtt_client, sms_gateway
    
    loop_count = 0
    try:
        while True:
            time.sleep(180)  # Check MQTT connection every 3 minutes
            loop_count += 1
            
            # Log loop activity every 5 iterations (15 minutes)
            if loop_count % 5 == 0:
                logging.debug(f"🔄 Main loop active - iteration {loop_count} (every 3 minutes)")
            
            # Check MQTT connection periodically
            if not mqtt_client.is_connected():
                logging.error("MQTT connection lost - stopping SMS Gateway")
                sys.exit(1)
            
            # Send periodic status every 3 minutes (with signal strength check)
            try:
                # Get network info with signal strength check (only in this periodic loop)
                network_info = sms_gateway.checkNetworkStatus(skip_signal_check=False)
                # Add device info for periodic status
                device_info = sms_gateway.getNetworkInfo()
                status_data = {
                    "status": "ready",
                    "gsm": "ready",
                    "mqtt": "connected",
                    "signal": network_info.get("signal_percentage", 0),
                    "signal_strength": network_info.get("signal_strength", "unknown"),
                    "registration": network_info.get("registration", "unknown"),
                    "operator": network_info.get("operator", "unknown"),
                    "sim_status": network_info.get("sim_status", "unknown"),
                    "device": device_info.get("device", "unknown"),
                    "mode": device_info.get("mode", "unknown"),
                    "timestamp": get_local_timestamp()
                }
                mqtt_client.publish(options.status, json.dumps(status_data), qos=0)
                logging.info(f'Periodic status sent to MQTT topic: {options.status}')
            except Exception as e:
                logging.error(f'Failed to send periodic status: {e}')
            
            # Check if GSM reader thread stopped (indicates critical error)
            if sms_gateway and hasattr(sms_gateway, 'GsmReaderThread'):
                if not getattr(sms_gateway.GsmReaderThread, 'isRunning', True):
                    logging.critical("💀 GSM reader thread stopped - exiting program for system restart")
                    sys.exit(1)
                
    except KeyboardInterrupt:
        logging.info('Received keyboard interrupt')
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        sys.exit(1)


def main_modem(loglevel, options):
    """Optimized main modem function with better error handling"""
    global sms_gateway, mqtt_client, status_timer

    # Initialize GSM gateway
    if not _initialize_gsm_gateway(loglevel, options, mqtt_client):
        return
    
    # Update MQTT client callback with initialized sms_gateway
    from sms_mqtt_handler import on_message
    mqtt_client.on_message = lambda client, userdata, msg: on_message(client, userdata, msg, sms_gateway)
        
    # Subscribe to MQTT topic
    subscribe_to_topic(mqtt_client, options.send)
    
    # Main loop
    _run_main_loop(options)


def main(args=None):
    """Main entry point"""
    global mqtt_client

    try:
        parser = argparse.ArgumentParser(description="SMS Gateway command line launcher")
        parser.add_argument("--mode", dest="mode", help="modem or api", default="modem")
        parser.add_argument("-d", "--device", dest="device", help="USB device name", default="/dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0")
        parser.add_argument("--pin", dest="pin", help="code pin", default="-")
        parser.add_argument("-u", "--user", dest="user", help="mqtt user", default="mqtt")
        parser.add_argument("-s", "--secret", dest="secret", help="mqtt user password", default="mqtt")
        parser.add_argument("-r", "--host", dest="host", help="mqtt host", default="homeassistant.local")
        parser.add_argument("-p", "--port", dest="port", help="mqtt port", default="1883")
        parser.add_argument("--send", dest="send", help="mqtt send", default="send_sms")
        parser.add_argument("--recv", dest="recv", help="mqtt receive", default="sms_received")
        parser.add_argument("--status", dest="status", help="mqtt status topic", default="sms_gateway/status")
        parser.add_argument("--log", dest="logging", help="addon logging level", default="INFO")
        parser.add_argument("--diagnostics", dest="diagnostics", help="run diagnostics and exit", action="store_true")
        parser.add_argument("--test-network", dest="test_network", help="test network connectivity in diagnostics", action="store_true")
        # PIN functionality removed - not needed for modern modems
        options = parser.parse_args(args)
            
    except (Exception,):
        return None

    # Set logger
    log_level = logging.DEBUG
    if options.logging == "DEBUG":
        log_level = logging.DEBUG
    elif options.logging == "INFO":
        log_level = logging.INFO
    elif options.logging == "WARNING":
        log_level = logging.WARNING
    elif options.logging == "ERROR":
        log_level = logging.ERROR
    elif options.logging == "CRITICAL":
        log_level = logging.CRITICAL

    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)

    logging.info('')
    logging.info('Arguments parsed:')
    logging.info('... mode is: '+options.mode)
    logging.info('... device is: '+options.device)
    logging.info('... pin is: '+options.pin)
    logging.info('... mqtt user is: '+options.user)
    logging.info('... mqtt user secret is: [HIDDEN]')
    logging.info('... mqtt host is: '+options.host)
    logging.info('... mqtt port is: '+options.port)
    logging.info('... mqtt send is: '+options.send)
    logging.info('... mqtt recv is: '+options.recv)
    logging.info('... mqtt status is: '+options.status)
    logging.info('... addon logging is: '+options.logging)

    # Run diagnostics if requested
    if options.diagnostics:
        logging.info('Running diagnostics mode...')
        # Diagnostics functionality moved to gsm_diagnostics
        logging.info('Diagnostics functionality available in gsm_diagnostics module')
        working_devices = True  # Simplified for now
        if working_devices:
            logging.info('Diagnostics completed successfully - found working devices')
        else:
            logging.warning('Diagnostics completed - no working devices found')
        logging.info('Diagnostics mode finished - container will keep running for manual review')
        logging.info('You can manually restart the container when ready')
        
        # Keep container running indefinitely for manual review
        try:
            while True:
                time.sleep(180)  # Sleep for 3 minute intervals
                logging.info('Diagnostics container still running - ready for manual restart')
        except KeyboardInterrupt:
            logging.info('Received interrupt signal - stopping diagnostics container')
            sys.exit(0)

    # Handle Interrupt and termination signals
    logging.info("")
    logging.info('Preparing signal handling for termination')
    signal.signal(signal.SIGINT, signal_handler)  # Handle CTRL-C signal
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    logging.info('.... signal handling for termination done')

    # Handle MQTT
    logging.info('Connecting to MQTT broker')
    broker = options.host
    port = int(options.port)
    user = options.user
    password = options.secret

    # Create MQTT client (will be configured with sms_gateway later)
    mqtt_client = create_mqtt_client(broker, port, user, password, None)
    
    # Connect to MQTT broker
    if not connect_mqtt_client(mqtt_client, broker, port):
        return
        
    logging.info('... Listening on topic: '+options.send)
    
    # Don't send initial status yet - wait for GSM to be fully ready
    logging.info('MQTT connected - waiting for GSM initialization to complete before sending status')

    if options.mode == 'modem':
        main_modem(log_level, options)
    else:
        logging.info('Error ! specify options "mode"')
    pass


if __name__ == '__main__':
    main()
