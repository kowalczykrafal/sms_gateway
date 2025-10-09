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

import time
import json
import logging
from threading import Thread, Lock
from queue import Queue

from gsm_io import gsm_io
from gsm_commands import GSMCommands
from gsm_sms import GSMSMS
from gsm_reset import GSMReset
from gsm_diagnostics import GSMDiagnostics



class GSM(gsm_io):
    """Main GSM modem class - orchestrates all GSM operations"""
    
    def __init__(self, loglevel, name: str, mode: str, device: str, pin: str, auth: str, recv: str, mqtt_client, skip_pin=False):
        super().__init__(loglevel, device)
        
        # Basic configuration
        self.GsmMode = mode
        self.MQTTClient = mqtt_client
        self.GsmPIN = pin  # Keep PIN for fallback support
        self.Auth = auth
        self.Recv = recv
        self.Ready = False
        self.Name = name
        
        # Threading and synchronization
        self.GsmReaderThread = None
        self.SMSQueue = Queue()
        
        # Global modem communication semaphore - only one operation at a time
        self.ModemSemaphore = Lock()
        self.ModemOperationInProgress = False
        self.ModemOperationType = None  # 'startup', 'sms_receive', 'status_check', 'sms_send'
        self.ModemOperationStartTime = None
        self.ModemOperationTimeout = 120  # 2 minutes max per operation
        
        # State flags (inherited from gsm_io, but set defaults)
        self.Opened = False
        self.SmsList = []
        
        # Set up logging first
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=loglevel)
        self.logger = logging.getLogger(__name__)
        
        # Initialize sub-modules after logger is set up
        self.commands = GSMCommands(self)
        self.sms = GSMSMS(self)
        self.reset = GSMReset(self)
        self.diagnostics = GSMDiagnostics(self)
    
    def acquire_modem_semaphore(self, operation_type, timeout=None):
        """Acquire global modem semaphore for specific operation"""
        if timeout is None:
            timeout = self.ModemOperationTimeout
            
        try:
            if not self.ModemSemaphore.acquire(timeout=timeout):
                self.logger.warning(f"⚠️ Timeout waiting for modem semaphore for {operation_type} operation")
                return False
            
            # Check if another operation is already in progress
            if self.ModemOperationInProgress:
                self.logger.warning(f"⚠️ Modem operation {self.ModemOperationType} already in progress, skipping {operation_type}")
                self.ModemSemaphore.release()
                return False
            
            # Mark operation as in progress
            self.ModemOperationInProgress = True
            self.ModemOperationType = operation_type
            self.ModemOperationStartTime = time.time()
            
            # Start I/O thread when semaphore is acquired
            if hasattr(self, 'gsm_io_main') and hasattr(self.gsm_io_main, 'io_thread'):
                if not self.gsm_io_main.io_thread.is_running:
                    self.logger.debug("🔄 Starting I/O thread for modem communication")
                    self.gsm_io_main.io_thread.start()
            
            self.logger.debug(f"🔒 Modem semaphore acquired for {operation_type} operation")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error acquiring modem semaphore for {operation_type}: {e}")
            return False
    
    def release_modem_semaphore(self, operation_type):
        """Release global modem semaphore after operation completion"""
        try:
            if self.ModemOperationInProgress and self.ModemOperationType == operation_type:
                elapsed = time.time() - self.ModemOperationStartTime
                self.logger.debug(f"🔓 Modem semaphore released for {operation_type} operation (took {elapsed:.1f}s)")
                
                # Stop I/O thread when semaphore is released
                if hasattr(self, 'gsm_io_main') and hasattr(self.gsm_io_main, 'io_thread'):
                    if self.gsm_io_main.io_thread.is_running:
                        self.logger.debug("🔄 Stopping I/O thread - no modem operations in progress")
                        self.gsm_io_main.io_thread.stop()
                
                self.ModemOperationInProgress = False
                self.ModemOperationType = None
                self.ModemOperationStartTime = None
                self.ModemSemaphore.release()
                return True
            else:
                self.logger.warning(f"⚠️ Attempted to release semaphore for {operation_type} but operation is {self.ModemOperationType}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error releasing modem semaphore for {operation_type}: {e}")
            return False
    
    def is_modem_busy(self):
        """Check if modem is currently busy with an operation"""
        return self.ModemOperationInProgress
    
    def get_current_operation(self):
        """Get current modem operation type"""
        return self.ModemOperationType if self.ModemOperationInProgress else None
    
    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            if hasattr(self, 'logger'):
                self.stop()
        except:
            pass  # Ignore errors during cleanup
    
    def start(self):
        """Start GSM modem operations"""
        try:
            self.logger.info("🔄 Starting GSM modem...")
            
            # Try USB reset first
            self.reset._try_usb_reset()
            time.sleep(3)
            
            # Open device
            self.Opened = self.openGsmDevice()
            if not self.Opened:
                raise Exception(f"Failed to open GSM device: {self.GsmDevice}")
            
            # Start I/O activity
            self.startGsmIoActivity()
            
            # Initialize device with semaphore
            if self.acquire_modem_semaphore("startup", timeout=180):
                try:
                    self.initGsmDevice()
                    self.processStartupSms()
                finally:
                    self.release_modem_semaphore("startup")
            else:
                raise Exception("Failed to acquire modem semaphore for startup")
            
            # Start SMS reader thread
            self.startGsmReader()
            
            self.Ready = True
            self.logger.info("✅ GSM modem started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start GSM modem: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop GSM modem operations"""
        try:
            self.logger.info("🔄 Stopping GSM modem...")
            self.Ready = False
            
            # Stop SMS reader
            self.stopGsmReader()
            
            # Close device
            if self.Opened:
                self.closeGsmDevice()
                self.Opened = False
            
            self.logger.info("✅ GSM modem stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping GSM modem: {e}")
    
    def initGsmDevice(self):
        """Initialize GSM device with AT commands"""
        try:
            self.logger.info("🔄 Initializing GSM device...")
            
            # Basic AT commands
            # Skip ATZ (reset) as it may cause issues with some modems
            self.logger.info("... Skipping ATZ (reset) command to avoid modem issues")
            
            self.commands.send_command("ATE0", "Disable echo", timeout=15)
            self.commands.send_command("AT+CMEE=1", "Enable extended error reporting", timeout=15)
            self.commands.send_command("AT+CSCS=\"GSM\"", "Set GSM character set", timeout=15)
            
            # Huawei E3372 specific commands to prevent periodic status messages and timeouts
            try:
                self.logger.info("... Applying Huawei E3372 specific optimizations...")
                self.commands.send_command("AT^CURC=0", "Disable periodic status messages", timeout=10)
                # AT^SYSCFGEX removed - causes timeouts on some modems
                self.commands.send_command("AT+COPS=0", "Automatic operator selection", timeout=10)
                self.logger.info("... Huawei E3372 optimizations applied successfully")
            except Exception as e:
                self.logger.warning(f"... Huawei E3372 optimizations failed (may not be Huawei modem): {e}")
            
            # PIN handling - try to send PIN if needed (fallback for older modems)
            try:
                # Check if PIN is needed by trying to get network status
                self.commands.send_command("AT+CREG?", "Check network registration", timeout=10)
                # If we get here, modem is working without PIN
                self.logger.info("... Modem working without PIN (modern modem)")
            except Exception as e:
                # If network check fails, try sending PIN as fallback
                if pin and pin.strip():
                    self.logger.info(f"... Trying PIN fallback for older modem: {pin[:2]}**")
                    try:
                        pin_cmd = f"AT+CPIN=\"{pin}\""
                        self.commands.send_command(pin_cmd, "Send PIN (fallback)", timeout=20)
                        self.logger.info("... PIN sent successfully (fallback)")
                    except Exception as pin_error:
                        self.logger.warning(f"... PIN fallback failed: {pin_error}")
                else:
                    self.logger.warning("... No PIN provided for fallback")
            
            # SMS configuration
            self.commands.send_command("AT+CMGF=1", "Enable text mode SMS", timeout=15)
            self.commands.send_command("AT+CSDH=1", "Enable detailed SMS headers", timeout=15)
            self.commands.send_command("AT+CNMI=2,1,0,0,0", "Configure SMS notifications", timeout=15)
            
            # Set SMS storage after basic initialization but before SMS processing
            try:
                self.logger.info("📤 Setting SMS storage after initialization...")
                
                # First check if modem is responsive with a simple command
                self.commands.send_command("AT", "Test modem responsiveness", timeout=5)
                
                # Wait a bit for modem to be fully ready
                time.sleep(2)
                
                self.commands.send_command("AT+CPMS?", "Check SMS storage status", timeout=30)
                self.logger.info("✅ SMS storage status checked successfully")
            except Exception as e:
                # Log timeout errors as warnings, others as errors
                if "Timeout" in str(e):
                    self.logger.warning(f"⚠️ SMS storage setup timeout: {e} - continuing with initialization")
                else:
                    self.logger.error(f"❌ Failed to set SMS storage: {e} - continuing with initialization")
            
            self.logger.info("✅ GSM device initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize GSM device: {e}")
            raise
    
    def processStartupSms(self):
        """Process existing SMS messages at startup"""
        try:
            self.logger.info("📱 Processing startup SMS messages...")
            
            # Check for existing SMS messages using the same mechanism as readNewSms
            # Note: Global semaphore should already be acquired by calling operation
            self.SmsList = []
            self.GsmIoCMGLReceived = False
            
            # Send AT+CMGL="ALL" command to get all SMS
            # Set flag to expect CMGL response
            if hasattr(self, 'gsm_io_main') and hasattr(self.gsm_io_main, 'io_thread'):
                self.gsm_io_main.io_thread.set_expecting_cmgl(True)
            
            frame = bytes(self.commands.ATCMGL + "\"ALL\"", 'ascii')
            self.writeData(frame + b'\r')
            
            # Wait for response with timeout
            timeout = 10  # 10 seconds timeout
            start_time = time.time()
            while not self.GsmIoCMGLReceived and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            sms_list = self.SmsList if self.GsmIoCMGLReceived else []
            
            # Also check if we have CMGL data from the new I/O thread
            if not sms_list and hasattr(self, 'gsm_io_main') and self.gsm_io_main.io_thread.cmgl_received:
                cmgl_data = self.gsm_io_main.io_thread.cmgl_data
                if cmgl_data:
                    self.logger.info(f"📨 Found CMGL data: {cmgl_data}")
                    # Parse CMGL response manually
                    sms_list = self._parse_cmgl_response(cmgl_data)
                    # Reset CMGL flags after processing
                    self.gsm_io_main.io_thread.cmgl_received = False
                    self.gsm_io_main.io_thread.cmgl_data = ""
            
            if sms_list:
                self.logger.info(f"📨 Found {len(sms_list)} existing SMS message(s) in inbox")
                
                # Clear only READ messages, preserve UNREAD
                read_messages = [sms for sms in sms_list if sms['Status'] == 'REC READ']
                unread_messages = [sms for sms in sms_list if sms['Status'] == 'REC UNREAD']
                
                if read_messages:
                    self.logger.info(f"🗑️ Clearing {len(read_messages)} READ message(s) at startup")
                    for sms in read_messages:
                        self.logger.info(f"🗑️ Deleting READ SMS ID: {sms['Id']}")
                        self.sms.delete_sms(sms['Id'])
                    
                    if unread_messages:
                        self.logger.info(f"📱 Preserving {len(unread_messages)} UNREAD message(s) for processing")
                else:
                    self.logger.debug("📭 No READ messages found to clear")
            else:
                self.logger.debug("📭 No existing SMS messages found in inbox")
            
            self.logger.info("📱 Startup SMS processing completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing startup SMS: {e}")
            # Try modem restart on error
            try:
                self.logger.warning("🔄 Attempting modem restart due to startup SMS error...")
                self.reset._try_at_command_reset()
                time.sleep(3)
                self.reset._try_usb_reset()
                time.sleep(3)
                
                # Reopen device
                if self.Opened:
                    self.closeGsmDevice()
                
                self.Opened = self.openGsmDevice()
                if self.Opened:
                    self.startGsmIoActivity()
                    self.initGsmDevice()
                    self.logger.info("✅ Modem restart successful after startup SMS error")
                else:
                    self.logger.error("❌ Failed to reopen GSM device after reset")
                    
            except Exception as restart_error:
                self.logger.error(f"❌ Error during modem restart: {restart_error}")
    
    def _parse_cmgl_response(self, cmgl_data):
        """Parse CMGL response data into SMS list"""
        try:
            sms_list = []
            lines = cmgl_data.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('+CMGL:'):
                    # Parse CMGL line: +CMGL: 5,"REC READ","+48509073123",,"25/10/07,18:52:14+08",145
                    parts = line.split(',')
                    if len(parts) >= 6:
                        try:
                            sms_id = parts[0].split(':')[1].strip()
                            status = parts[1].strip().strip('"')
                            number = parts[2].strip().strip('"')
                            # Skip parts[3] (empty)
                            timestamp = parts[4].strip().strip('"')
                            # Skip parts[5] (length)
                            
                            sms_data = {
                                'Id': sms_id,
                                'Status': status,
                                'Number': number,
                                'Timestamp': timestamp,
                                'Msg': ''  # No message content in CMGL
                            }
                            sms_list.append(sms_data)
                            self.logger.debug(f"📨 Parsed SMS: ID={sms_id}, Status={status}, Number={number}")
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"⚠️ Error parsing CMGL line: {line} - {e}")
                            continue
            
            return sms_list
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing CMGL response: {e}")
            return []
    
    def startGsmReader(self):
        """Start SMS reader thread"""
        if self.GsmReaderThread is None or not self.GsmReaderThread.is_alive():
            self.GsmReaderThread = Thread(target=self.runGsmReaderThread, daemon=True)
            self.GsmReaderThread.isRunning = True
            self.GsmReaderThread.start()
            self.logger.info("🔄 SMS Reader Thread started")
    
    def stopGsmReader(self):
        """Stop SMS reader thread"""
        if self.GsmReaderThread and self.GsmReaderThread.is_alive():
            self.GsmReaderThread.isRunning = False
            self.GsmReaderThread.join(timeout=5)
            self.logger.info("🔄 SMS Reader Thread stopped")
    
    def runGsmReaderThread(self):
        """Main SMS reader thread with error handling"""
        self.logger.info("🔄 SMS Reader Thread started - checking for SMS every 30 seconds")
        last_successful_operation = time.time()
        modem_health_check_interval = 300  # 5 minutes
        
        while getattr(self.GsmReaderThread, "isRunning", True):
            try:
                self.logger.debug("🔄 SMS Reader Thread - checking for new SMS...")
                
                # Check for hung AT commands
                if self.commands._check_at_command_hang():
                    self.logger.warning("⚠️ AT command hang detected and recovered - continuing...")
                    continue
                
                # Periodic modem health check
                current_time = time.time()
                if current_time - last_successful_operation > modem_health_check_interval:
                    self.logger.info("🔄 Performing periodic modem health check...")
                    if not self.diagnostics._check_modem_health():
                        self.logger.critical("💀 Modem health check failed - stopping SMS reader thread")
                        self.logger.critical("🔄 Main loop will exit program for system restart")
                        self.GsmReaderThread.isRunning = False
                        break
                
                # Check for new SMS
                self.sms.readNewSms()
                
                # Process SMS from queue
                sms_count = 0
                while True:
                    try:
                        message = self.SMSQueue.get(False)
                        if message['Status'] in ["REC UNREAD", "REC READ"]:
                            self.sms._processSmsForMqtt(message)
                            sms_count += 1
                    except:
                        break
                
                if sms_count > 0:
                    self.logger.info(f"📨 Processed {sms_count} SMS message(s) from queue")
                
                last_successful_operation = time.time()
                
                # Wait before next check
                self.logger.debug("⏳ SMS Reader Thread - waiting 30 seconds before next check...")
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ Error in SMS reader thread: {e}")
                
                # Check if it's a modem hang/responsiveness error - stop thread and let main loop handle exit
                error_str = str(e).lower()
                if "hang" in error_str or "not responsive" in error_str or "timeout" in error_str:
                    self.logger.critical(f"💀 Modem hang/responsiveness error detected: {e}")
                    self.logger.critical("🔄 Stopping I/O thread and SMS reader thread - main loop will exit program")
                    self.logger.critical("💡 This will allow system restart (Docker/Home Assistant will restart the container)")
                    
                    # Stop I/O thread first
                    if hasattr(self, 'gsm_io_main') and hasattr(self.gsm_io_main, 'io_thread'):
                        self.logger.critical("🔄 Stopping I/O thread...")
                        self.gsm_io_main.stop()
                    
                    self.GsmReaderThread.isRunning = False
                    break
                
                # Check if it's a connection error - stop thread and let main loop handle exit
                elif self.reset._is_connection_error(e):
                    self.logger.critical(f"💀 I/O error detected: {e}")
                    self.logger.critical("🔄 Stopping I/O thread and SMS reader thread - main loop will exit program")
                    self.logger.critical("💡 This will allow system restart (Docker/Home Assistant will restart the container)")
                    
                    # Stop I/O thread first
                    if hasattr(self, 'gsm_io_main') and hasattr(self.gsm_io_main, 'io_thread'):
                        self.logger.critical("🔄 Stopping I/O thread...")
                        self.gsm_io_main.stop()
                    
                    self.GsmReaderThread.isRunning = False
                    break
                else:
                    time.sleep(30)
    
    def sendSmsToNumber(self, number, message):
        """Send SMS to specified number"""
        return self.sms.sendSmsToNumber(number, message)
    
    def checkNetworkStatus(self, skip_signal_check=False):
        """Check network status and return info"""
        return self.diagnostics.checkNetworkStatus(skip_signal_check)
    
    def getNetworkInfo(self):
        """Get detailed network information"""
        return self.diagnostics.getNetworkInfo()
    
    @staticmethod
    def encodeUTF8toJSON(bytes_message):
        """Encode UTF-8 message for JSON transmission"""
        try:
            if isinstance(bytes_message, bytes):
                return bytes_message.decode('utf-8', errors='ignore')
            return str(bytes_message)
        except Exception as e:
            logging.error(f"❌ Error encoding UTF-8 to JSON: {e}")
            return str(bytes_message)
    
