"""
GSM I/O Compatibility Module
Provides backward compatibility with the original gsm_io interface
"""

import logging
from gsm_io_main import GsmIo as GsmIoMain
# gsm_text_decoder removed - no longer needed

class gsm_io:
    """Backward compatible GSM I/O interface"""

    def __init__(self, loglevel, device):
        self.logger = logging.getLogger(__name__)
        self.device = device
        
        # Initialize main GSM I/O
        self.gsm_io_main = GsmIoMain(loglevel, device)
        # text_decoder removed - no longer needed
        
        # Backward compatibility attributes
        self.GsmSerial = self.gsm_io_main.serial.serial_connection
        self.GsmDevice = device
        self.GsmIoProtocolSem = None  # Not used in new implementation
        self.GsmIoReadyToSend = True
        self.CommandSem = None  # Not used in new implementation
        self.WaitingOk = False
        self.RecordSmsText = False
        self.GsmIoCMSSId = -1
        self.GsmIoCMSSReceived = False
        self.GsmIoOKReceived = False
        self.GsmIoPromptReceived = False
        self.SmsText = b''
        self.LastSmsText = b''
        self.GsmIoMessageId = b''
        self.GsmIoActivityThread = None
        self.SmsList = []
        self.GsmIoCMGLReceived = False
        self.GsmIoCMGRReceived = False
        self.GsmIoCMGRData = ""
        self.GsmIoCMGLData = ""
        self.GsmIoCMTIReceived = False
        self.GsmIoCPMSReceived = False
        self.CPMSResponse = ""
        self.Opened = False
        
    def openGsmDevice(self):
        """Open GSM device (backward compatibility)"""
        result = self.gsm_io_main.open_device()
        self.Opened = result
        return result
    
    def closeGsmDevice(self):
        """Close GSM device (backward compatibility)"""
        self.gsm_io_main.close_device()
        self.Opened = False
    
    def startGsmIoActivity(self):
        """Start I/O activity (backward compatibility)"""
        # Already started in openGsmDevice
        pass
    
    def stopGsmIoActivity(self):
        """Stop I/O activity (backward compatibility)"""
        # Already stopped in closeGsmDevice
        pass
    
    def writeCommandAndWaitOK(self, command, description="", timeout=10):
        """Write command and wait for OK (backward compatibility)"""
        result = self.gsm_io_main.write_command(command, description, timeout)
        
        # Update backward compatibility flags
        self.GsmIoOKReceived = self.gsm_io_main.io_thread.ok_received
        self.GsmIoPromptReceived = self.gsm_io_main.io_thread.prompt_received
        
        return result
    
    def writeData(self, data):
        """Write data (backward compatibility)"""
        return self.gsm_io_main.write_data(data)
    
    def waitForGsmIoCMSSReceived(self, timeout=10):
        """Wait for CMSS response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("CMSS", timeout)
        self.GsmIoCMSSReceived = self.gsm_io_main.io_thread.cmss_received
        return result
    
    def waitForGsmIoCMGLReceived(self, timeout=10):
        """Wait for CMGL response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("CMGL", timeout)
        self.GsmIoCMGLReceived = self.gsm_io_main.io_thread.cmgl_received
        self.GsmIoCMGLData = self.gsm_io_main.io_thread.cmgl_data
        
        # Update SmsList with parsed SMS from I/O thread
        if result:
            self.SmsList = self.gsm_io_main.get_sms_list()
            self.logger.debug(f"📨 Updated SmsList with {len(self.SmsList)} SMS messages")
        
        return result
    
    def waitForGsmIoCMGRReceived(self, timeout=10):
        """Wait for CMGR response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("CMGR", timeout)
        self.GsmIoCMGRReceived = self.gsm_io_main.io_thread.cmgr_received
        self.GsmIoCMGRData = self.gsm_io_main.io_thread.cmgr_data
        return result
    
    def waitForGsmIoOKReceived(self, timeout=10):
        """Wait for OK response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("OK", timeout)
        self.GsmIoOKReceived = self.gsm_io_main.io_thread.ok_received
        return result
    
    def waitForGsmIoCPMSReceived(self, timeout=10):
        """Wait for CPMS response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("CPMS", timeout)
        self.GsmIoCPMSReceived = self.gsm_io_main.io_thread.cpms_received
        self.CPMSResponse = self.gsm_io_main.io_thread.cpms_data
        return result
    
    def waitForGsmIoCMTIReceived(self, timeout=10):
        """Wait for CMTI response (backward compatibility)"""
        result = self.gsm_io_main.wait_for_response("CMTI", timeout)
        self.GsmIoCMTIReceived = self.gsm_io_main.io_thread.cmti_received
        return result
    
    def startSmsTextRecording(self):
        """Start SMS text recording (backward compatibility)"""
        self.gsm_io_main.start_sms_recording()
        self.RecordSmsText = True
    
    def stopSmsTextRecording(self):
        """Stop SMS text recording (backward compatibility)"""
        result = self.gsm_io_main.stop_sms_recording()
        self.RecordSmsText = False
        self.LastSmsText = result
        return result
    
    def getSmsText(self):
        """Get SMS text (backward compatibility)"""
        return self.gsm_io_main.get_sms_text()
    
    def getLastSmsText(self):
        """Get last SMS text (backward compatibility)"""
        return self.gsm_io_main.get_last_sms_text()
    
    def flushGsmIoBuffers(self):
        """Flush I/O buffers (backward compatibility)"""
        self.gsm_io_main.flush_buffers()
    
    def _decode_sms_text(self, sms_bytes):
        """Decode SMS text (backward compatibility)"""
        # Return raw SMS bytes - no hex decoding needed
        return sms_bytes

    def runGsmIoActivityThread(self):
        """Run I/O activity thread (backward compatibility)"""
        # This is handled by the new implementation
        pass
    
    def _has_data_available(self):
        """Check if data is available (backward compatibility)"""
        return self.gsm_io_main.serial.has_data_available()
    
    # Properties for backward compatibility
    @property
    def GsmIoOKReceived(self):
        return self.gsm_io_main.io_thread.ok_received
    
    @GsmIoOKReceived.setter
    def GsmIoOKReceived(self, value):
        self.gsm_io_main.io_thread.ok_received = value
    
    @property
    def GsmIoPromptReceived(self):
        return self.gsm_io_main.io_thread.prompt_received
    
    @GsmIoPromptReceived.setter
    def GsmIoPromptReceived(self, value):
        self.gsm_io_main.io_thread.prompt_received = value
    
    @property
    def GsmIoCMSSReceived(self):
        return self.gsm_io_main.io_thread.cmss_received
    
    @GsmIoCMSSReceived.setter
    def GsmIoCMSSReceived(self, value):
        self.gsm_io_main.io_thread.cmss_received = value
    
    @property
    def GsmIoCMGLReceived(self):
        return self.gsm_io_main.io_thread.cmgl_received
    
    @GsmIoCMGLReceived.setter
    def GsmIoCMGLReceived(self, value):
        self.gsm_io_main.io_thread.cmgl_received = value
    
    @property
    def GsmIoCMGRReceived(self):
        return self.gsm_io_main.io_thread.cmgr_received
    
    @GsmIoCMGRReceived.setter
    def GsmIoCMGRReceived(self, value):
        self.gsm_io_main.io_thread.cmgr_received = value
    
    @property
    def GsmIoCMTIReceived(self):
        return self.gsm_io_main.io_thread.cmti_received
    
    @GsmIoCMTIReceived.setter
    def GsmIoCMTIReceived(self, value):
        self.gsm_io_main.io_thread.cmti_received = value
