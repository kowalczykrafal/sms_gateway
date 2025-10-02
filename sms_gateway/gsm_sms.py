"""
GSM SMS Module

Handles SMS operations: reading, sending, processing, and MQTT integration.
"""

import time
import json
import logging


class GSMSMS:
    """Handles SMS operations and MQTT integration"""
    
    def __init__(self, gsm_instance):
        """Initialize with reference to main GSM instance"""
        self.gsm = gsm_instance
        self.logger = logging.getLogger(__name__)
    
    def sendSmsToNumber(self, number, message):
        """Send SMS to specified number"""
        try:
            self.logger.info(f"📤 Sending SMS to {number}: {message[:50]}...")
            
            if not self.gsm.Opened:
                raise Exception("GSM device not opened")
            
            # Check if AT command semaphore is available
            if not self.gsm.AtCommandSem.acquire(blocking=False):
                self.logger.warning("⚠️ AT command semaphore busy - waiting for SMS send...")
                # Wait for semaphore with timeout (2 minutes)
                if not self.gsm.AtCommandSem.acquire(blocking=True, timeout=120):
                    raise Exception("Timeout waiting for AT command semaphore (2 minutes)")
            
            try:
                self.logger.debug("🔒 AT command semaphore acquired for SMS sending")
                # Set text mode
                self.gsm.commands.send_command("AT+CMGF=1", "Set text mode")
                
                # Set character set
                self.gsm.commands.send_command("AT+CSCS=\"GSM\"", "Set GSM character set")
                
                # Send SMS
                sms_command = f"AT+CMGS=\"{number}\""
                self.gsm.GsmIoPromptReceived = False
                self.gsm.GsmIoCMSSReceived = False
                
                # Send command and wait for prompt
                self.gsm.writeData((sms_command + '\r').encode('ascii'))
                
                # Wait for prompt
                timeout = 0
                while not self.gsm.GsmIoPromptReceived and timeout < 1000:
                    time.sleep(0.001)
                    timeout += 1
                
                if not self.gsm.GsmIoPromptReceived:
                    raise Exception("Timeout waiting for SMS prompt")
                
                # Send message
                message_bytes = message.encode('utf-8')
                self.gsm.writeData(message_bytes + b'\x1A')  # Ctrl+Z to send
                self.logger.debug(f"📤 SMS message sent: '{message}' + Ctrl+Z")
                
                # Wait for confirmation
                timeout = 0
                self.logger.debug(f"⏳ Waiting for SMS confirmation from modem...")
                while not self.gsm.GsmIoCMSSReceived and timeout < 30000:  # 30 seconds timeout
                    time.sleep(0.001)
                    timeout += 1
                
                if self.gsm.GsmIoCMSSReceived:
                    self.logger.info(f"✅ SMS sent successfully to {number}")
                    return True
                else:
                    self.logger.error(f"❌ Timeout waiting for SMS confirmation after {timeout/1000:.1f}s")
                    raise Exception("Timeout waiting for SMS confirmation")
                    
            finally:
                # Always release AT command semaphore
                self.gsm.AtCommandSem.release()
                self.logger.debug("🔓 AT command semaphore released after SMS sending")
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to send SMS to {number}: {e}")
            return False
    
    def readNewSms(self):
        """Read new SMS messages from modem"""
        try:
            if not self.gsm.Opened:
                self.logger.error("... readNewSMS, device not opened")
                return None
                
            self.logger.debug("📱 Checking for new SMS messages...")
            
            # Check if AT command semaphore is available before SMS operations
            if not self.gsm.AtCommandSem.acquire(blocking=False):
                self.logger.warning("⚠️ AT command semaphore busy - skipping SMS check")
                return None
            
            try:
                # First check if there are any SMS messages
                self.logger.debug("🔄 Checking SMS message count...")
                sms_count = self._check_sms_count()
                
                if sms_count == 0:
                    self.logger.info("📭 No SMS messages found in modem")
                    return None
                elif sms_count is None:
                    # SMS count check couldn't determine count - try to read SMS directly
                    self.logger.info("📊 SMS count check couldn't determine count - trying to read SMS directly...")
                    sms_count = 1  # Assume there might be SMS and try to read
                else:
                    self.logger.debug(f"📨 Found {sms_count} SMS message(s) - reading details...")
                
                # Process SMS iteratively - read and process one by one
                self.logger.debug(f"📨 Found {sms_count} SMS message(s) - processing iteratively")
                
                # Process each SMS iteratively
                for sms_id in range(sms_count):
                    self.logger.debug(f"📩 Processing SMS ID: {sms_id}")
                    
                    # Read individual SMS using AT+CMGR
                    sms_data = self._read_single_sms(sms_id)
                    if not sms_data:
                        self.logger.warning(f"⚠️ Failed to read SMS ID: {sms_id}")
                        continue
                    
                    message_id = sms_data['Id']
                    number = sms_data['Number']
                    status = sms_data['Status']
                    message_text = sms_data['Msg']
                    
                    self.logger.info(f"📩 SMS ID: {message_id}, From: {number}, Status: {status}")
                    self.logger.debug(f"📨 SMS content: '{message_text}' (length: {len(message_text)})")
                    
                    # Add to queue for processing
                    self.gsm.SMSQueue.put(sms_data)
                    self.logger.info(f"📨 SMS added to queue: ID {message_id}, From: {number}")
                    
                    # Delete the SMS after processing (WITHIN semaphore)
                    try:
                        self.logger.debug(f"🗑️ Attempting to delete SMS ID: {message_id}")
                        self._delete_sms_without_semaphore(message_id)
                        self.logger.debug(f"🗑️ Successfully deleted SMS ID: {message_id}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to delete SMS ID {message_id}: {e}")
                
                return None  # SMS are processed in runGsmReaderThread
                
            finally:
                # Always release AT command semaphore AFTER all SMS processing is complete
                self.gsm.AtCommandSem.release()
            
        except Exception as e:
            self.logger.error(f"❌ Error in readNewSms: {e}")
            # Store the error to re-raise after cleanup
            error_str = str(e).lower()
            connection_error = e if self.gsm.reset._is_connection_error(e) else None
            hang_error = e if ("hang" in error_str or "timeout" in error_str or "not responsive" in error_str) else None
            
            if connection_error or hang_error:
                self.logger.warning("🔄 Connection/hang error in readNewSms - propagating to main thread")
            else:
                self.logger.warning("⚠️ Non-connection error in readNewSms - continuing")
            
            # Re-raise connection and hang errors after cleanup
            if connection_error:
                raise connection_error
            if hang_error:
                raise hang_error
    
    def _check_sms_count(self):
        """Check the number of SMS messages in the modem without reading them"""
        try:
            self.logger.debug("🔄 Checking SMS message count with AT+CPMS...")
            
            # Execute AT command directly (semaphore already acquired in readNewSms)
            if not self.gsm.Opened:
                self.logger.warning("⚠️ GSM device not opened for SMS count check")
                return None
            
            self.logger.debug(f"📤 Executing AT command: SMS count check (AT+CPMS?)")
            
            # Send CPMS command
            self.gsm.writeData(b'AT+CPMS?\r\n')
            
            # Wait for CPMS response with timeout
            timeout = 10
            if not self.gsm.waitForGsmIoCPMSReceived(timeout):
                self.logger.warning("⚠️ No CPMS response received - modem may be unresponsive")
                return None
            
            if self.gsm.CPMSResponse:
                # Parse +CPMS response: +CPMS: "ME",0,23,"ME",0,23,"ME",0,23
                # Format: +CPMS: <mem1>,<used1>,<total1>,<mem2>,<used2>,<total2>,<mem3>,<used3>,<total3>
                try:
                    # Extract the first "used" count (messages in SIM memory)
                    parts = self.gsm.CPMSResponse.split(',')
                    if len(parts) >= 2:
                        used_count = int(parts[1].strip())
                        self.logger.debug(f"📊 SMS count: {used_count} messages in SIM memory")
                        return used_count
                    else:
                        self.logger.warning("⚠️ Could not parse CPMS response")
                        return None
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"⚠️ Error parsing CPMS response: {e}")
                    return None
            else:
                self.logger.warning("⚠️ No CPMS response received")
                return None
                
        except Exception as e:
            self.logger.warning(f"⚠️ SMS count check failed with error: {e}")
            # Check if it's a connection error and propagate it
            if self.gsm.reset._is_connection_error(e):
                self.logger.warning("🔄 Connection error in SMS count check - propagating to main thread")
                raise e
            return 0
    
    
    def _read_single_sms(self, sms_id):
        """Read a single SMS using AT+CMGR command"""
        try:
            self.logger.debug(f"📖 Reading SMS ID: {sms_id}")
            
            # Reset CMGR flags
            self.gsm.GsmIoCMGRReceived = False
            self.gsm.GsmIoCMGRData = ""
            
            # Send AT+CMGR command to read specific SMS
            frame = bytes(self.gsm.commands.ATCMGR + str(sms_id), 'ascii')
            self.gsm.writeData(frame + b'\r')
            
            # Wait for response with timeout
            timeout = 10  # 10 seconds timeout for single SMS read
            if not self.gsm.waitForGsmIoCMGRReceived(timeout):
                self.logger.warning(f"⚠️ Timeout waiting for SMS read response for ID: {sms_id} - modem may be unresponsive")
                return None
            
            # Parse CMGR response
            cmgr_data = self.gsm.GsmIoCMGRData
            if not cmgr_data:
                self.logger.warning(f"⚠️ No CMGR data received for SMS ID: {sms_id}")
                return None
            
            # Parse CMGR response format: +CMGR: "REC UNREAD","+1234567890",,"25/09/26,11:26:10+02"
            # Followed by SMS content
            lines = cmgr_data.split('\n')
            if len(lines) < 2:
                self.logger.warning(f"⚠️ Invalid CMGR response format for SMS ID: {sms_id}")
                return None
            
            # Parse header line
            header_line = lines[0].strip()
            if not header_line.startswith('+CMGR:'):
                self.logger.warning(f"⚠️ Invalid CMGR header for SMS ID: {sms_id}: {header_line}")
                return None
            
            # Extract fields from header
            # Format: +CMGR: "REC UNREAD","+1234567890",,"25/09/26,11:26:10+02"
            header_content = header_line[7:].strip()  # Remove '+CMGR: '
            fields = []
            current_field = ""
            in_quotes = False
            
            for char in header_content:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    fields.append(current_field.strip('"'))
                    current_field = ""
                    continue
                current_field += char
            
            if current_field:
                fields.append(current_field.strip('"'))
            
            if len(fields) < 4:
                self.logger.warning(f"⚠️ Insufficient fields in CMGR response for SMS ID: {sms_id}: {fields}")
                return None
            
            self.logger.debug(f"📖 CMGR fields for SMS ID {sms_id}: {fields}")
            
            # Extract SMS content (everything after the header)
            sms_content = '\n'.join(lines[1:]).strip()
            
            # Clean SMS content - remove PDU headers and trailing OK
            if sms_content:
                # Split by newlines and find the actual message content
                content_lines = sms_content.split('\n')
                message_lines = []
                
                for line in content_lines:
                    line = line.strip()
                    # Skip PDU header lines (contain commas and quotes)
                    if ',' in line and '"' in line and not line.startswith('+'):
                        continue
                    # Skip standalone OK
                    if line == 'OK':
                        continue
                    # This should be the actual message content
                    if line:
                        message_lines.append(line)
                
                # Join the message lines
                clean_content = '\n'.join(message_lines).strip()
                if clean_content:
                    sms_content = clean_content
            
            # Create SMS data
            sms_data = {
                'Id': sms_id,
                'Number': fields[1] if len(fields) > 1 else "",
                'Status': fields[0] if len(fields) > 0 else "",
                'Msg': sms_content
            }
            
            self.logger.debug(f"📖 Successfully read SMS ID: {sms_id}, From: {sms_data['Number']}, Content: '{sms_content}'")
            return sms_data
            
        except Exception as e:
            self.logger.error(f"❌ Error reading SMS ID {sms_id}: {e}")
            return None

    def _delete_sms_without_semaphore(self, sms_id):
        """Delete SMS by ID without acquiring semaphore (assumes semaphore is already held)"""
        try:
            self.logger.debug(f"🗑️ Sending delete command for SMS ID: {sms_id}")
            frame = bytes(self.gsm.commands.ATCMGD + str(sms_id) + ",0", 'ascii')
            # Use writeData directly instead of writeCommandAndWaitOK to avoid semaphore conflict
            self.gsm.writeData(frame + b'\r')
            # Wait for OK response
            if not self.gsm.waitForGsmIoOKReceived(timeout=10):
                raise Exception(f"Timeout waiting for OK response for SMS delete command")
            self.logger.debug(f"🗑️ Delete command completed for SMS ID: {sms_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error deleting SMS ID {sms_id}: {e}")
            raise e
    
    def delete_sms(self, sms_id):
        """Delete SMS by ID (public method that acquires semaphore)"""
        try:
            self.logger.debug(f"🗑️ Sending delete command for SMS ID: {sms_id}")
            frame = bytes(self.gsm.commands.ATCMGD + str(sms_id) + ",0", 'ascii')
            self.gsm.writeCommandAndWaitOK(frame)
            self.logger.debug(f"🗑️ Delete command completed for SMS ID: {sms_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error deleting SMS ID {sms_id}: {e}")
            # Check if it's a connection error and propagate it
            if self.gsm.reset._is_connection_error(e):
                self.logger.warning("🔄 Connection error in SMS deletion - propagating to main thread")
                raise e
            raise
    
    def _processSmsForMqtt(self, sms_data):
        """Process SMS data and send to MQTT"""
        try:
            self.logger.info("")
            self.logger.info("📨 Returning SMS to MQTT: From %s, Status: %s", sms_data['Number'], sms_data['Status'])
            self.logger.info("")
            self.logger.debug("Receiving SMS as UTF-8 string")
            self.logger.debug(f"... SMS content before strip: %s", repr(sms_data['Msg']))
            
            # Clean up SMS text - remove leading/trailing whitespace and \r\n
            sms_data['Msg'] = sms_data['Msg'].strip()
            
            # Encode message for JSON
            sms_data['Msg'] = self.gsm.encodeUTF8toJSON(sms_data['Msg'])
            json_message = {"from": sms_data['Number'], "txt": sms_data['Msg']}
            
            self.logger.debug("...... Publishing it to mqtt as JSON on topic sms_received")
            self.logger.debug(json_message)
            
            # Publish to MQTT
            self.gsm.MQTTClient.publish(self.gsm.Recv, json.dumps(json_message))
            
        except Exception as e:
            self.logger.error(f"❌ Error processing SMS for MQTT: {e}")
