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

import paho.mqtt.client as mqtt
import json
import logging
import sys


def check_mqtt_connection(mqtt_client):
    """Check if MQTT connection is active and working"""
    try:
        if not mqtt_client or not mqtt_client.is_connected():
            logging.error("MQTT client is not connected")
            return False
            
        # Try to publish a test message to verify connection
        result = mqtt_client.publish("test/connection", "test", qos=0)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logging.error(f"Failed to publish test message. Return code: {result.rc}")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error checking MQTT connection: {e}")
        return False


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback for when the client receives a CONNACK response from the server."""
    if rc == 0:
        logging.info("Successfully connected to MQTT broker")
    else:
        logging.error(f"Failed to connect to MQTT broker. Return code: {rc}")
        sys.exit(1)


def on_disconnect(client, userdata, flags, rc, properties=None):
    """Callback for when the client disconnects from the broker."""
    if rc != 0:
        logging.error(f"Unexpected MQTT disconnection. Return code: {rc}")
        logging.error("Stopping SMS Gateway due to MQTT connection loss")
        sys.exit(1)
    else:
        logging.info("MQTT broker disconnected")


def on_message(client, userdata, msg, sms_gateway):
    """Handle incoming MQTT messages for SMS sending"""
    logging.info("")
    logging.info(f"📨 MQTT SMS send request received")
    logging.debug(f"... JSON UTF-8 Message")
    logging.debug(msg.payload)
    
    try:
        message = json.loads(msg.payload)
        to_number = message["to"]
        txt_message = message["txt"]
        
        logging.info(f"📤 Sending SMS to: {to_number}")
        logging.info(f"💬 Message: {txt_message[:100]}{'...' if len(txt_message) > 100 else ''}")
        
        sms_gateway.sendSmsToNumber(to_number, txt_message)
        logging.info(f"✅ SMS send request processed for {to_number}")
        
    except KeyError as e:
        logging.error(f"❌ Missing field in SMS request: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"❌ Invalid JSON in SMS request: {e}")
    except Exception as e:
        logging.error(f"❌ Error processing SMS request: {e}")


def create_mqtt_client(host, port, user, password, sms_gateway):
    """Create and configure MQTT client"""
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = lambda client, userdata, msg: on_message(client, userdata, msg, sms_gateway)
    mqtt_client.username_pw_set(user, password)
    
    return mqtt_client


def connect_mqtt_client(mqtt_client, host, port):
    """Connect MQTT client to broker"""
    try:
        logging.info('Attempting to connect to MQTT broker: '+host+':'+str(port))
        mqtt_client.connect(host, port, 60)  # 60 second timeout
        
        # Start the loop in a separate thread to handle callbacks
        mqtt_client.loop_start()
        
        # Wait a moment for connection to establish
        import time
        time.sleep(3)
        
        # Check if connection was successful
        if not mqtt_client.is_connected():
            logging.error("Failed to establish MQTT connection")
            logging.error("Stopping SMS Gateway due to MQTT connection failure")
            mqtt_client.loop_stop()
            sys.exit(1)
            
        logging.info('Successfully connected to MQTT broker: '+host+':'+str(port))
        return True
        
    except Exception as e:
        logging.error(f"Error connecting to MQTT broker: {e}")
        logging.error("Stopping SMS Gateway due to MQTT connection error")
        if mqtt_client:
            mqtt_client.loop_stop()
        sys.exit(1)


def subscribe_to_topic(mqtt_client, topic):
    """Subscribe to MQTT topic for SMS sending"""
    logging.info(f'Subscribing on topic: {topic}')
    mqtt_client.subscribe(topic)
    logging.info('... Subscribing done')
    logging.info('')
    logging.info('SMS Gateway is running - waiting for messages')
