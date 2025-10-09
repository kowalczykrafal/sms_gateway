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
            
            # Acquire global modem semaphore for SMS sending operation
            if not self.gsm.acquire_modem_semaphore("sms_send", timeout=120):
                raise Exception("Timeout waiting for modem semaphore (2 minutes)")
            
            try:
                self.logger.debug("🔒 Modem semaphore acquired for SMS sending")
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
                # Always release global modem semaphore
                self.gsm.release_modem_semaphore("sms_send")
                    
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
            
            # Acquire global modem semaphore for SMS receiving operation
            # Increased timeout to 120 seconds to handle large SMS volumes
            if not self.gsm.acquire_modem_semaphore("sms_receive", timeout=120):
                self.logger.warning("⚠️ Modem semaphore busy - skipping SMS check")
                return None
            
            try:
                # Record start time for SMS processing
                sms_processing_start = time.time()
                self.logger.debug("🔄 Starting SMS processing...")
                
                # Get actual SMS list using CMGL to get real SMS IDs
                self.logger.debug("🔄 Getting SMS list with actual IDs...")
                sms_list = self._get_sms_list()
                
                if not sms_list:
                    self.logger.info("📭 No SMS messages found in modem")
                    return None
                
                self.logger.debug(f"📨 Found {len(sms_list)} SMS message(s) - processing with real IDs")
                
                # Process each SMS using real IDs from CMGL
                for sms_data in sms_list:
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
                        # Small delay to allow modem to process the deletion
                        time.sleep(0.5)
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to delete SMS ID {message_id}: {e}")
                
                # Log SMS processing time
                sms_processing_time = time.time() - sms_processing_start
                if sms_processing_time > 60:
                    self.logger.warning(f"⚠️ SMS processing took {sms_processing_time:.1f} seconds - consider optimizing")
                else:
                    self.logger.info(f"📊 SMS processing completed in {sms_processing_time:.1f} seconds")
                
                return None  # SMS are processed in runGsmReaderThread
                
            finally:
                # Always release global modem semaphore AFTER all SMS processing is complete
                self.gsm.release_modem_semaphore("sms_receive")
            
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
    
    def _get_sms_list(self):
        """Get list of SMS messages with their actual IDs using AT+CMGL"""
        try:
            self.logger.debug("🔄 Getting SMS list with AT+CMGL...")
            
            # Reset CMGL flags
            self.gsm.GsmIoCMGLReceived = False
            self.gsm.GsmIoCMGLData = ""
            if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                self.gsm.gsm_io_main.io_thread.cmgl_received = False
                self.gsm.gsm_io_main.io_thread.cmgl_data = ""
                self.gsm.gsm_io_main.io_thread.set_expecting_cmgl(True)
            
            # Send AT+CMGL command to list all SMS
            frame = bytes(self.gsm.commands.ATCMGL + "\"ALL\"", 'ascii')
            cmgl_cmd = frame + b'\r'
            self.logger.debug(f"📤 Sending CMGL command: {cmgl_cmd}")
            self.gsm.writeData(frame + b'\r')
            
            # Wait for response with timeout
            timeout = 30
            if not self.gsm.waitForGsmIoCMGLReceived(timeout):
                self.logger.warning(f"⚠️ Timeout waiting for CMGL response after {timeout}s")
                return []
            
            # Get CMGL data from new I/O thread location first, fallback to old location
            cmgl_data = None
            if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                if self.gsm.gsm_io_main.io_thread.cmgl_data:
                    cmgl_data = self.gsm.gsm_io_main.io_thread.cmgl_data
                    self.logger.debug(f"📨 Using new CMGL data: {cmgl_data}")
            
            if not cmgl_data and hasattr(self.gsm, 'GsmIoCMGLData') and self.gsm.GsmIoCMGLData:
                cmgl_data = self.gsm.GsmIoCMGLData
                self.logger.debug(f"📨 Using old CMGL data: {cmgl_data}")
            
            # Check if CMGL response was received but no data (means no SMS)
            if not cmgl_data:
                # Check if CMGL response was received (indicates successful command execution)
                cmgl_received = False
                if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                    cmgl_received = self.gsm.gsm_io_main.io_thread.cmgl_received
                elif hasattr(self.gsm, 'GsmIoCMGLReceived'):
                    cmgl_received = self.gsm.GsmIoCMGLReceived
                
                if cmgl_received:
                    self.logger.debug("📨 CMGL response received but no data - no SMS found")
                    return []  # No SMS found
                else:
                    self.logger.warning("⚠️ No CMGL response received")
                    return []
            
            # Parse CMGL response into SMS list
            sms_list = self._parse_cmgl_response(cmgl_data)
            self.logger.debug(f"📨 Parsed {len(sms_list)} SMS from CMGL response")
            
            return sms_list
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting SMS list: {e}")
            # Check if it's a connection error and propagate it
            if self.gsm.reset._is_connection_error(e):
                self.logger.warning("🔄 Connection error in SMS list - propagating to main thread")
                raise e
            return []
    
    def _parse_cmgl_response(self, cmgl_data):
        """Parse CMGL response data into SMS list"""
        try:
            sms_list = []
            lines = cmgl_data.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('+CMGL:'):
                    # Parse CMGL line: +CMGL: 0,"REC READ","+48509073123",,"25/10/08,13:10:00+08",145,2
                    parts = line.split(',')
                    if len(parts) >= 6:
                        try:
                            sms_id = parts[0].split(':')[1].strip()
                            status = parts[1].strip().strip('"')
                            number = parts[2].strip().strip('"')
                            # Skip parts[3] (empty)
                            timestamp = parts[4].strip().strip('"')
                            # Skip parts[5] (length)
                            
                            # Find the message content (next line after CMGL header)
                            message_content = ""
                            if i + 1 < len(lines):
                                message_content = lines[i + 1].strip()
                            
                            sms_data = {
                                'Id': sms_id,
                                'Status': status,
                                'Number': number,
                                'Timestamp': timestamp,
                                'Msg': message_content
                            }
                            sms_list.append(sms_data)
                            self.logger.debug(f"📨 Parsed SMS: ID={sms_id}, Status={status}, Number={number}, Content='{message_content}'")
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"⚠️ Error parsing CMGL line: {line} - {e}")
                            continue
            
            return sms_list
        except Exception as e:
            self.logger.error(f"❌ Error parsing CMGL response: {e}")
            return []

    def _check_sms_count(self):
        """Check the number of SMS messages in the modem without reading them"""
        try:
            self.logger.debug("🔄 Checking SMS message count with AT+CPMS...")
            
            # Execute AT command directly (semaphore already acquired in readNewSms)
            if not self.gsm.Opened:
                self.logger.warning("⚠️ GSM device not opened for SMS count check")
                return None
            
            self.logger.debug(f"📤 Executing AT command: SMS count check (AT+CPMS?)")
            
            # Use send_command instead of direct writeData for better reliability
            # This ensures proper timeout handling and error recovery
            result = self.gsm.commands.send_command("AT+CPMS?", "SMS count check", timeout=30)
            
            if not result:
                self.logger.warning("⚠️ No CPMS response received - modem may be unresponsive")
                self.logger.debug("🔍 CPMS timeout may indicate modem is busy or slow - will retry in next cycle")
                return None
            
            if self.gsm.CPMSResponse:
                # Parse +CPMS response from AT+CPMS? command:
                # Format: +CPMS: "SM",0,25,"SM",0,25,"SM",0,25
                # Structure: <mem1>,<used1>,<total1>,<mem2>,<used2>,<total2>,<mem3>,<used3>,<total3>
                # For SIM storage: mem1="SM", used1=messages in received box, total1=max capacity
                try:
                    # Remove "+CPMS: " prefix and split by comma
                    response_clean = self.gsm.CPMSResponse.replace('+CPMS:', '').strip()
                    parts = response_clean.split(',')
                    
                    self.logger.debug(f"📊 CPMS response parsing: '{self.gsm.CPMSResponse}'")
                    self.logger.debug(f"📊 CPMS parts: {parts}")
                    
                    if len(parts) >= 2:
                        # Get the second part (used count for received messages)
                        used_count = int(parts[1].strip())
                        self.logger.debug(f"📊 SMS count: {used_count} messages in SIM memory (from parts[1]='{parts[1].strip()}')")
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
    
    

    def _delete_sms_without_semaphore(self, sms_id):
        """Delete SMS by ID without acquiring semaphore (assumes semaphore is already held)"""
        try:
            self.logger.debug(f"🗑️ Sending delete command for SMS ID: {sms_id}")
            
            # Reset OK flag before sending command
            self.gsm.GsmIoOKReceived = False
            if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                self.gsm.gsm_io_main.io_thread.ok_received = False
            
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
            
            # Add delay after SMS deletion to allow modem to update its internal state
            time.sleep(1)
            self.logger.debug(f"🗑️ Successfully deleted SMS ID: {sms_id}")
            
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
