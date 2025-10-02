"""
GSM I/O Main Module
Main interface for GSM modem I/O operations
"""

import time
import logging
import threading
from gsm_serial import GsmSerial
from gsm_io_thread import GsmIoThread

class GsmIo:
    """Main GSM I/O interface"""
    
    def __init__(self, loglevel, device):
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.opened = False
        
        # Initialize serial connection and I/O thread
        self.serial = GsmSerial(device)
        self.io_thread = GsmIoThread(self.serial)
        
        # Command synchronization
        self.semaphore = threading.Semaphore(1)  # Allow only one AT command at a time
        self.command_lock = None
        self.waiting_ok = False
        self.ready_to_send = True
        
        # SMS related
        self.record_sms_text = False
        self.sms_list = []
        
    def open_device(self):
        """Open GSM device connection"""
        try:
            if self.serial.open_connection():
                self.opened = True
                self.io_thread.start()
                self.logger.info(f"GSM device opened: {self.device}")
                return True
            else:
                self.logger.error(f"Failed to open GSM device: {self.device}")
                return False
        except Exception as e:
            self.logger.error(f"Error opening GSM device: {e}")
            return False
    
    def close_device(self):
        """Close GSM device connection"""
        try:
            if self.opened:
                self.io_thread.stop()
                self.serial.close_connection()
                self.opened = False
                self.logger.info("GSM device closed")
        except Exception as e:
            self.logger.error(f"Error closing GSM device: {e}")
    
    def write_command(self, command, description="", timeout=10):
        """Write command to modem and wait for OK response"""
        if not self.opened:
            self.logger.error("Device not opened")
            return False
        
        # Acquire semaphore to prevent AT command conflicts
        if not self.semaphore.acquire(timeout=timeout):
            self.logger.warning(f"⚠️ Timeout waiting for AT command semaphore for: {description}")
            return False
        
        try:
            self.logger.debug(f"📤 Sending AT command: {description} ({command})")
            
            # Reset flags and send command
            self.io_thread.reset_flags()
            # Ensure command is string and add line ending
            if isinstance(command, bytes):
                command_str = command.decode('ascii', errors='ignore')
            else:
                command_str = str(command)
            
            if not self.serial.write_data(command_str + '\r\n'):
                return False
            
            # Wait for OK response
            if self.io_thread.wait_for_ok(timeout):
                self.logger.debug(f"✅ AT command {description} completed successfully")
                return True
            else:
                # Log timeout as debug to reduce spam, but still log as error for critical operations
                if "CPMS" in str(command) or "CMGR" in str(command) or "CMGL" in str(command):
                    self.logger.debug(f"⚠️ AT command {description} timeout after {timeout}s for command: {command}")
                else:
                    self.logger.error(f"❌ Error sending AT command {description}: Timeout waiting for OK response after {timeout}s for command: {command}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error sending AT command {description}: {e}")
            return False
        finally:
            # Always release semaphore
            self.semaphore.release()
    
    def write_data(self, data):
        """Write data to modem"""
        if not self.opened:
            self.logger.error("Device not opened")
            return False
        
        return self.serial.write_data(data)
    
    def wait_for_response(self, response_type, timeout=10):
        """Wait for specific response type"""
        if not self.opened:
            return False
        
        start_time = time.time()
        self.io_thread.reset_flags()
        
        while time.time() - start_time < timeout:
            if response_type == "OK" and self.io_thread.ok_received:
                return True
            elif response_type == "CMSS" and self.io_thread.cmss_received:
                return True
            elif response_type == "CPMS" and self.io_thread.cpms_received:
                return True
            elif response_type == "CMGL" and self.io_thread.cmgl_received:
                return True
            elif response_type == "CMGR" and self.io_thread.cmgr_received:
                return True
            elif response_type == "CMTI" and self.io_thread.cmti_received:
                return True
            time.sleep(0.01)
        
        elapsed = time.time() - start_time
        # Log timeout as debug to reduce spam, but still log as error for critical operations
        if response_type in ["CPMS", "CMGR", "CMGL"]:
            self.logger.debug(f"⚠️ Timeout after {elapsed:.1f}s waiting for {response_type} response")
        else:
            self.logger.error(f"❌ Timeout after {elapsed:.1f}s waiting for {response_type} response")
        return False
    
    def get_response_data(self, response_type):
        """Get data from specific response type"""
        if response_type == "CMGL":
            return self.io_thread.cmgl_data
        elif response_type == "CMGR":
            return self.io_thread.cmgr_data
        return ""
    
    def get_sms_list(self):
        """Get parsed SMS list from I/O thread"""
        return self.io_thread.sms_list.copy()
    
    def start_sms_recording(self):
        """Start recording SMS text"""
        self.record_sms_text = True
        self.io_thread.sms_text = b''
    
    def stop_sms_recording(self):
        """Stop recording SMS text"""
        self.record_sms_text = False
        self.io_thread.last_sms_text = self.io_thread.sms_text
        return self.io_thread.last_sms_text
    
    def get_sms_text(self):
        """Get recorded SMS text"""
        return self.io_thread.sms_text
    
    def get_last_sms_text(self):
        """Get last recorded SMS text"""
        return self.io_thread.last_sms_text
    
    def flush_buffers(self):
        """Flush serial buffers"""
        if self.opened:
            self.serial.flush_buffers()
            self.io_thread.reset_flags()
    
    def is_opened(self):
        """Check if device is opened"""
        return self.opened
