"""
GSM Commands Module

Handles AT command execution, synchronization, and communication with GSM modem.
"""

import time
import logging


class GSMCommands:
    """Handles AT command execution and synchronization"""
    
    # AT Command constants
    ATZ = "ATZ"  # reset modem
    ATE0 = "ATE0"  # set echo off
    ATE1 = "ATE1"  # set echo on
    ATCLIP = "AT+CLIP?"  # get calling line identification presentation
    ATCMEE = "AT+CMEE=1"  # set extended error
    ATCSCS = "AT+CSCS=\"GSM\""  # force GSM mode for SMS
    ATCMGF = "AT+CMGF=1"  # enable sms in text mode
    ATCSDH = "AT+CSDH=1"  # enable more fields in sms read
    ATCMGS = "AT+CMGS="  # send message with prompt
    ATCMGD = "AT+CMGD="  # delete messages
    ATCMGL = "AT+CMGL="  # list all messages
    ATCMGR = "AT+CMGR="  # read message by index in storage
    ATCMGW = "AT+CMGW="  # write
    ATCMSS = "AT+CMSS="  # send message by index in storage
    ATCPMS = "AT+CPMS=\"ME\",\"ME\",\"ME\""  # storage is Mobile
    ATCSQ = "AT+CSQ"  # signal strength
    ATCREG = "AT+CREG?"  # registered on network ?
    ATCOPS = "AT+COPS?"  # operator selection
    ATCNMI = "AT+CNMI=2,1,0,0,0"  # when sms arrives CMTI send to pc
    # Huawei E3372 specific commands
    ATCURC = "AT^CURC=0"  # disable periodic status messages
    # ATSYSCFGEX removed - causes timeouts on some modems
    ATCOPS_AUTO = "AT+COPS=0"  # automatic operator selection
    
    def __init__(self, gsm_instance):
        """Initialize with reference to main GSM instance"""
        self.gsm = gsm_instance
        self.logger = logging.getLogger(__name__)
    
    def send_command(self, command, description="AT command", timeout=10):
        """Send AT command and wait for OK response"""
        try:
            if not self.gsm.Opened:
                raise Exception("GSM device not opened")
            
            self.logger.debug(f"📤 Sending AT command: {description} ({command})")
            
            # Use the existing writeCommandAndWaitOK mechanism from gsm_io
            frame = bytes(command, 'ascii')
            self.gsm.writeCommandAndWaitOK(frame, timeout=timeout)
            self.logger.debug(f"✅ AT command {description} completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error sending AT command {description}: {e}")
            raise
    
    def _execute_at_command_safely(self, command, description="AT command", timeout=None, response_timeout=5):
        """Execute AT command safely with synchronization to prevent collisions"""
        if timeout is None:
            timeout = self.gsm.AtCommandTimeout
            
        semaphore_acquired = False
        try:
            # Acquire AT command semaphore
            if not self.gsm.AtCommandSem.acquire(timeout=timeout):
                self.logger.warning(f"⚠️ Timeout waiting for AT command semaphore for: {description}")
                return False
            
            semaphore_acquired = True
            
            # Check if another AT command is already in progress
            if self.gsm.AtCommandInProgress:
                self.logger.warning(f"⚠️ AT command already in progress, skipping: {description}")
                return False
            
            # Mark AT command as in progress
            self.gsm.AtCommandInProgress = True
            self.gsm.AtCommandStartTime = time.time()
            self.logger.debug(f"🔒 AT command semaphore acquired for: {description}")
            
            # Execute the AT command using existing mechanism
            try:
                frame = bytes(command, 'ascii')
                self.gsm.writeCommandAndWaitOK(frame, timeout=response_timeout)
                self.logger.debug(f"✅ AT command {description} completed successfully")
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ AT command {description} failed: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error executing AT command {description}: {e}")
            return False
        finally:
            # Always reset flag
            self.gsm.AtCommandInProgress = False
            self.gsm.AtCommandStartTime = None
            
            # Only release semaphore if it was acquired
            if semaphore_acquired:
                self.gsm.AtCommandSem.release()
                self.logger.debug(f"🔓 AT command semaphore released for: {description}")
    
    def _check_at_command_hang(self):
        """Check if AT command is hung and force reset if necessary"""
        try:
            if self.gsm.AtCommandInProgress and self.gsm.AtCommandStartTime:
                elapsed_time = time.time() - self.gsm.AtCommandStartTime
                if elapsed_time > self.gsm.AtCommandMaxDuration:
                    self.logger.warning(f"⚠️ AT command hung for {elapsed_time:.1f}s - forcing reset")
                    
                    # Force reset AT command state
                    self.gsm.AtCommandInProgress = False
                    self.gsm.AtCommandStartTime = None
                    
                    # Try to clear any pending data
                    if hasattr(self.gsm, 'GsmSerial') and self.gsm.GsmSerial:
                        try:
                            # Clear input buffer
                            if self.gsm.GsmSerial.in_waiting > 0:
                                self.gsm.GsmSerial.read(self.gsm.GsmSerial.in_waiting)
                                self.logger.debug("🧹 Cleared input buffer after AT command hang")
                            
                            # Send break sequence to reset modem
                            self.gsm.GsmSerial.write(b'\x1A')  # Ctrl+Z (break)
                            time.sleep(0.5)
                            
                            # Send AT command to test responsiveness
                            self.gsm.GsmSerial.write(b'AT\r\n')
                            time.sleep(1)
                            
                            if self.gsm.GsmSerial.in_waiting > 0:
                                response = self.gsm.GsmSerial.read(self.gsm.GsmSerial.in_waiting).decode('ascii', errors='ignore')
                                if 'OK' in response:
                                    self.logger.info("✅ Modem responsive after AT command hang recovery")
                                else:
                                    self.logger.warning(f"⚠️ Modem response after hang recovery: {response.strip()}")
                            else:
                                self.logger.warning("⚠️ No response from modem after AT command hang recovery")
                                
                        except Exception as e:
                            self.logger.error(f"❌ Error during AT command hang recovery: {e}")
                    
                    return True  # Hang detected and handled
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking AT command hang: {e}")
            
        return False  # No hang detected
    
    def check_modem_responsiveness(self, timeout=3):
        """Check if modem is responsive by sending AT command"""
        try:
            self.logger.debug("🔄 Checking modem responsiveness...")
            
            if not self.gsm.Opened:
                self.logger.warning("⚠️ GSM device not opened for responsiveness check")
                return False
            
            # Use the existing writeCommandAndWaitOK mechanism
            try:
                frame = bytes("AT", 'ascii')
                self.gsm.writeCommandAndWaitOK(frame, timeout=timeout)
                self.logger.debug("✅ Modem is responsive")
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ Modem not responsive: {e}")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error checking modem responsiveness: {e}")
            return False
