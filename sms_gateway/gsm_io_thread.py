"""
GSM I/O Thread Module
Handles the background thread for reading modem responses
"""

import time
import logging
from threading import Thread

class GsmIoThread:
    """Background thread for handling GSM modem I/O operations"""
    
    def __init__(self, serial_connection):
        self.serial = serial_connection
        self.logger = logging.getLogger(__name__)
        self.thread = None
        self.is_running = False
        
        # Response flags
        self.ok_received = False
        self.prompt_received = False
        self.cmss_received = False
        self.cmti_received = False
        self.cpms_received = False
        self.cmgr_received = False
        self.cmgl_received = False
        self.csq_received = False
        
        # Response data
        self.cpms_data = ""
        self.cmgr_data = ""
        self.cmgl_data = ""
        self.csq_data = ""
        
        # Frame buffer
        self.frame_buffer = b''
        
        # SMS parsing state (for new iterative logic)
        self.sms_list = []
        
        # Loop protection
        self.last_response = ""
        self.response_count = 0
        self.max_duplicate_responses = 10
        
        # Command expectation flags
        self._expecting_cmgl = False
    
    def set_expecting_cmgl(self, expecting=True):
        """Set flag indicating we're expecting a CMGL response"""
        self._expecting_cmgl = expecting
        if expecting:
            self.logger.debug("📨 Set expecting CMGL response flag")
        
    def start(self):
        """Start the I/O thread"""
        if not self.is_running:
            self.logger.debug("🔄 Starting GSM I/O Activity Thread...")
            self.is_running = True
            self.thread = Thread(target=self._run_thread, daemon=True)
            self.thread.start()
            self.logger.debug("✅ GSM I/O Activity Thread started successfully")
        else:
            self.logger.warning("GSM I/O Thread is already running")
    
    def stop(self):
        """Stop the I/O thread"""
        if self.is_running:
            self.logger.debug("🔄 Stopping GSM I/O Activity Thread...")
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=5)
            self.logger.debug("✅ GSM I/O Activity Thread stopped")
    
    def _run_thread(self):
        """Main thread loop"""
        self.logger.debug("🔄 GSM I/O Activity Thread started")
        loop_count = 0
        
        try:
            while self.is_running:
                time.sleep(0.001)
                loop_count += 1
                
                # Thread activity logging removed to reduce spam
                
                try:
                    self._process_available_data()
                    self._check_for_prompts()
                    self._process_frame_buffer()
                    
                    
                except Exception as e:
                    self.logger.error(f"Error in GSM I/O thread: {e}")
                    # Check if it's a connection error - if so, exit the thread
                    if hasattr(self.gsm, 'reset') and self.gsm.reset._is_connection_error(e):
                        self.logger.critical("💀 Connection error in I/O thread - exiting thread")
                        self.logger.critical("🔄 Main thread will handle the connection error")
                        self.stop()  # Stop the I/O thread properly
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            self.logger.error(f"❌ FATAL ERROR in GSM I/O thread: {e}")
            self.logger.error(f"❌ GSM I/O thread crashed and will exit")
        finally:
            self.logger.debug("🔄 GSM I/O Activity Thread ended")
    
    def _process_available_data(self):
        """Process data available from modem"""
        if self.serial.has_data_available():
            # Read more data at once to get complete responses
            data = self.serial.read_data(256)
            
            if data:
                try:
                    data_str = data.decode('ascii', errors='ignore')
                    # Log raw data in DEBUG mode
                    self.logger.debug(f"📥 Raw data received: {data}")
                    self.logger.debug(f"📥 Raw data (hex): {data.hex()}")
                    self.logger.debug(f"📥 Raw data (decoded): {data_str}")
                except Exception as e:
                    self.logger.error(f"❌ Error decoding data: {e}")
                
                self.frame_buffer += data
            else:
                self.logger.warning("⚠️ No data read despite availability")
    
    def _check_for_prompts(self):
        """Check for command prompts in frame buffer"""
        try:
            if '> ' in self.frame_buffer.decode("ascii", errors='ignore'):
                self.ok_received = True
                self.prompt_received = True
                self.frame_buffer = b''
        except Exception as e:
            self.logger.error(f"❌ Error checking for prompt: {e}")
    
    def _process_frame_buffer(self):
        """Process complete frames in buffer"""
        try:
            frame_str = self.frame_buffer.decode("ascii", errors='ignore')
        except Exception as e:
            self.logger.error(f"❌ Error decoding frame: {e}")
            frame_str = str(self.frame_buffer)
        
        if '\r\n' in frame_str:
            # Complete response received
            response_text = frame_str.strip()
            # Log ALL modem responses in DEBUG mode
            self.logger.debug(f"📥 Modem response: {response_text}")
            
            # Also log important responses with special markers
            if any(keyword in response_text for keyword in ['+CMGL:', '+CMGS:', '+CMSS:', '+CMTI:', '+CMGR:', '+CPMS:', '+CSQ:', 'ERROR']):
                self.logger.debug(f"🔍 Important response: {response_text}")
            
            # Process command responses
            if '+CMGR:' in response_text:
                # This is a CMGR response (single SMS read)
                self.logger.debug(f"📨 Found +CMGR: in response, processing it")
                self.logger.debug(f"📨 SMS READ RESPONSE: {response_text}")
                # Reset loop protection for new SMS read
                self.last_response = ""
                self.response_count = 0
                
                # Check if this is a complete CMGR response with SMS content and OK
                if '+CMGR:' in response_text and 'OK' in response_text and '\n' in response_text:
                    # This is a complete CMGR response with SMS content and OK
                    self.cmgr_received = True
                    self.cmgr_data = response_text
                    self.logger.debug(f"📨 Complete CMGR response detected with SMS content and OK")
                    self.logger.debug(f"📨 SMS READ COMPLETED: {response_text}")
                    # Clear frame buffer to prevent reprocessing
                    self.frame_buffer = b''
                    return  # Don't process as regular response
            elif self.cmgr_data and not self.cmgr_received and not any(keyword in response_text for keyword in ['+CMGR:', 'ERROR']):
                # This is SMS content between +CMGR: and final OK
                # Check for infinite loop protection FIRST
                if response_text == self.last_response:
                    self.response_count += 1
                    self.logger.warning(f"⚠️ Duplicate response detected ({self.response_count}/{self.max_duplicate_responses}): {response_text}")
                    if self.response_count >= self.max_duplicate_responses:
                        self.logger.error(f"❌ INFINITE LOOP DETECTED! Stopping after {self.max_duplicate_responses} duplicate responses")
                        self.cmgr_received = True  # Force completion to break the loop
                        return
                    else:
                        # Skip adding duplicate content
                        self.logger.debug(f"📨 Skipping duplicate SMS content")
                        return
                else:
                    self.last_response = response_text
                    self.response_count = 0
                
                # Check if this is a standalone OK (final response)
                if response_text.strip() == 'OK':
                    # This is the final OK - don't add to content, let _process_response handle it
                    self.logger.debug(f"📨 Found final OK for CMGR response")
                elif response_text.strip().endswith('OK'):
                    # This is SMS content that ends with OK - finalize the response
                    self.cmgr_data += '\n' + response_text
                    self.logger.debug(f"📨 Added SMS content ending with OK to CMGR: {response_text}")
                    self.logger.debug(f"📨 SMS CONTENT: {response_text}")
                    # Finalize the CMGR response since content ends with OK
                    self.cmgr_received = True
                    self.logger.debug(f"📨 SMS READ COMPLETED (content ends with OK): {self.cmgr_data}")
                else:
                    # This is SMS content (may contain OK as part of message)
                    self.cmgr_data += '\n' + response_text
                    self.logger.debug(f"📨 Added SMS content to CMGR: {response_text}")
                    self.logger.debug(f"📨 SMS CONTENT: {response_text}")
                return  # Don't process as regular response
            
            self._process_response(response_text, frame_str)
            
            self.frame_buffer = b''
            
        elif len(self.frame_buffer) > 0:
            # Partial frame - check if it's a CMGR response that needs to be completed
            frame_str = self.frame_buffer.decode('ascii', errors='ignore')
            if '+CMGR:' in frame_str and not self.cmgr_received:
                # This is a partial CMGR response - keep collecting
                self.logger.debug(f"📨 Collecting partial CMGR response: {frame_str}")
                return  # Don't clear buffer, keep collecting
            
            # Only log if it's getting too long
            if len(self.frame_buffer) > 100:
                self.logger.warning(f"⚠️ Frame getting long ({len(self.frame_buffer)} bytes), clearing buffer")
                self.frame_buffer = b''
            
    
    def _process_response(self, response_text, frame_str):
        """Process different types of modem responses"""
        if '+CPMS:' in response_text:
            self.cpms_received = True
            self.cpms_data = response_text
            self.logger.debug(f"📊 CPMS response received: {response_text}")
            
            # If this response also contains OK, we have a complete response
            if 'OK' in response_text:
                self.ok_received = True
                self.logger.debug(f"📊 CPMS response with OK - complete response received")
        elif '+CSQ:' in response_text:
            self.csq_received = True
            self.csq_data = response_text
            self.logger.debug(f"📶 Signal strength response: {response_text}")
            
            # If this response also contains OK, we have a complete response
            if 'OK' in response_text:
                self.ok_received = True
                self.logger.debug(f"📶 CSQ response with OK - complete response received")
        elif '+CMGS:' in response_text:
            self.cmss_received = True
            self.logger.info(f"✅ SMS sent: {response_text}")
        elif '+CMSS:' in response_text:
            self.cmss_received = True
            self.logger.info(f"✅ SMS sent: {response_text}")
        elif '+CMTI:' in response_text:
            self.cmti_received = True
        elif '+CMGL:' in response_text:
            # CMGL response - mark as received
            self.cmgl_received = True
            self.cmgl_data = response_text
            self.logger.debug(f"📨 CMGL response received: {response_text}")
            
            # Check if this is a complete CMGL response with SMS content and OK
            if '+CMGL:' in response_text and 'OK' in response_text and '\n' in response_text:
                # This is a complete CMGL response with SMS content and OK
                self.logger.debug(f"📨 Complete CMGL response detected with SMS content and OK")
                self.logger.debug(f"📨 CMGL READ COMPLETED: {response_text}")
        elif '+CME ERROR' in response_text:
            self.logger.warning(f"⚠️ CME ERROR: {response_text}")
        elif 'ERROR' in response_text or 'ERROR\r\n' in frame_str:
            self.logger.warning(f"⚠️ ERROR: {response_text}")
        elif 'OK\r\n' in frame_str or 'OK' in response_text:
            self.ok_received = True
            # Only log OK if it's not a simple OK response
            if response_text.strip() != 'OK':
                self.logger.debug(f"✅ OK response: {response_text}")
            
            # If we're collecting CMGR response, finalize it only if this is a standalone OK
            if self.cmgr_data and not self.cmgr_received and response_text.strip() == 'OK':
                self.cmgr_received = True
                self.logger.debug(f"📨 Completed CMGR response with final OK: {self.cmgr_data}")
                self.logger.debug(f"📨 SMS READ COMPLETED: {self.cmgr_data}")
                # Keep cmgr_data for parsing, don't reset it yet
            
            # If we got OK without CMGL, it means no SMS (old logic - just log for debugging)
            # Only log this if we're actually expecting a CMGL response (not for every OK)
            if not self.cmgl_received and not self.sms_list and hasattr(self, '_expecting_cmgl') and self._expecting_cmgl:
                self.cmgl_received = True
                # Only log if this is a standalone OK (not part of a larger response)
                if response_text.strip() == 'OK':
                    self.logger.debug("📨 No SMS found - CMGL response completed")
                self._expecting_cmgl = False  # Reset flag
        elif '+CMGR:' in response_text:
            # Start collecting CMGR response
            self.cmgr_received = False  # Don't set to True yet, wait for complete response
            self.cmgr_data = response_text
            self.logger.debug(f"📨 Started CMGR response: {response_text}")
            self.logger.debug(f"📨 SMS READ STARTED: {response_text}")
            
            # Check if this is a complete CMGR response (contains all fields)
            # Format: +CMGR: "REC READ","+48509073123",,"25/10/08,09:58:46+08",145,3
            if response_text.count(',') >= 5:  # Complete CMGR header
                self.logger.debug(f"📨 Complete CMGR header detected: {response_text}")
                # Don't set cmgr_received yet, wait for SMS content and final OK
                
            # Check if this response contains both CMGR header and OK (complete response)
            if '+CMGR:' in response_text and 'OK' in response_text and '\n' in response_text:
                # This is a complete CMGR response with SMS content and OK
                self.cmgr_received = True
                self.logger.debug(f"📨 Complete CMGR response detected with SMS content and OK")
                self.logger.debug(f"📨 SMS READ COMPLETED: {response_text}")
        elif '+CMGS:' in response_text:
            self.cmss_received = True
            self.logger.info(f"✅ SMS sent: {response_text}")
        elif '+CMSS:' in response_text:
            self.cmss_received = True
            self.logger.info(f"✅ SMS sent: {response_text}")
    
    
    def reset_flags(self):
        """Reset all response flags"""
        self.ok_received = False
        self.prompt_received = False
        self.cmss_received = False
        self.cmti_received = False
        self.cpms_received = False
        self.cmgr_received = False
        self.cmgl_received = False
        self.csq_received = False
        self.cpms_data = ""
        self.cmgr_data = ""
        self.cmgl_data = ""
        self.csq_data = ""
        self.frame_buffer = b''
        
        # Reset SMS parsing state
        self.sms_list = []
        
        # Reset loop protection
        self.last_response = ""
        self.response_count = 0
    
    def wait_for_ok(self, timeout=10):
        """Wait for OK response with timeout"""
        start_time = time.time()
        self.reset_flags()
        
        while time.time() - start_time < timeout:
            if self.ok_received:
                return True
            time.sleep(0.01)
        
        elapsed = time.time() - start_time
        # Log timeout as debug to reduce spam
        self.logger.debug(f"⚠️ Timeout after {elapsed:.1f}s waiting for OK response")
        return False
