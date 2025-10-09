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
            self.logger.debug(f"📤 AT command details: command='{command}', timeout={timeout}s")
            
            # Use the existing writeCommandAndWaitOK mechanism from gsm_io
            frame = bytes(command, 'ascii')
            self.logger.debug(f"📤 AT command frame: {frame}")
            self.logger.debug(f"📤 AT command frame (hex): {frame.hex()}")
            
            self.gsm.writeCommandAndWaitOK(frame, timeout=timeout)
            self.logger.debug(f"✅ AT command {description} completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error sending AT command {description}: {e}")
            raise
    
    def _execute_at_command_safely(self, command, description="AT command", timeout=None, response_timeout=5):
        """Execute AT command safely - assumes global semaphore is already acquired"""
        try:
            self.logger.debug(f"🔒 Executing AT command: {description}")
            
            # Execute the AT command using existing mechanism
            # Note: Global semaphore should already be acquired by calling operation
            frame = bytes(command, 'ascii')
            result = self.gsm.writeCommandAndWaitOK(frame, timeout=response_timeout)
            
            if result:
                self.logger.debug(f"✅ AT command {description} completed successfully")
            else:
                self.logger.warning(f"⚠️ AT command {description} failed")
            
            return result
                
        except Exception as e:
            self.logger.error(f"❌ Error executing AT command {description}: {e}")
            return False
    
    def _check_at_command_hang(self):
        """Check if AT command is hung and force reset if necessary"""
        try:
            # Check if modem operation is hung using new global semaphore system
            if (self.gsm.ModemOperationInProgress and 
                self.gsm.ModemOperationStartTime and 
                self.gsm.ModemOperationType):
                elapsed_time = time.time() - self.gsm.ModemOperationStartTime
                if elapsed_time > self.gsm.ModemOperationTimeout:
                    self.logger.warning(f"⚠️ Modem operation {self.gsm.ModemOperationType} hung for {elapsed_time:.1f}s - forcing reset")
                    
                    # Force reset modem operation state
                    self.gsm.ModemOperationInProgress = False
                    self.gsm.ModemOperationType = None
                    self.gsm.ModemOperationStartTime = None
                    
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
