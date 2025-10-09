"""
GSM Serial Communication Module
Handles basic serial port operations for GSM modem communication
"""

import serial
import serial.tools.list_ports
import logging
import time
from threading import Lock

class GsmSerial:
    """Handles basic serial port operations for GSM modem"""
    
    def __init__(self, device_path):
        self.device_path = device_path
        self.serial_connection = serial.Serial()
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        self.last_error_log_time = 0
        
    def open_connection(self):
        """Open serial connection to GSM device"""
        try:
            with self.lock:
                self.serial_connection.port = self.device_path
                self.serial_connection.baudrate = 115200
                self.serial_connection.timeout = 1
                self.serial_connection.open()
                self.logger.info(f"Serial connection opened to {self.device_path}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to open serial connection: {e}")
            return False
    
    def close_connection(self):
        """Close serial connection"""
        try:
            with self.lock:
                if self.serial_connection.is_open:
                    self.serial_connection.close()
                    self.logger.info("Serial connection closed")
        except Exception as e:
            self.logger.error(f"Error closing serial connection: {e}")
    
    def is_open(self):
        """Check if connection is open"""
        return self.serial_connection.is_open
    
    def write_data(self, data):
        """Write data to serial port"""
        try:
            with self.lock:
                if isinstance(data, str):
                    data = data.encode('ascii')
                self.serial_connection.write(data)
                # Enhanced logging for DEBUG mode
                self.logger.debug(f"Data written to modem: {data.decode('ascii', errors='ignore')}")
                self.logger.debug(f"Data written (hex): {data.hex()}")
                self.logger.debug(f"Data written (bytes): {data}")
                return True
        except Exception as e:
            self.logger.error(f"Error writing to modem: {e}")
            # If it's an I/O error, the modem connection is broken - raise exception
            if "I/O error" in str(e) or "Errno 5" in str(e):
                self.logger.error("❌ FATAL: Modem I/O error - connection lost. Raising exception.")
                # Raise a specific exception that will be caught by GsmReaderThread
                raise ConnectionError(f"Modem I/O error: {e}")
            return False
    
    def read_data(self, size=64):
        """Read data from serial port"""
        try:
            with self.lock:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(size)
                    return data
                return b''
        except Exception as e:
            self.logger.error(f"Error reading from modem: {e}")
            # If it's an I/O error, the modem connection is broken - raise exception
            if "I/O error" in str(e) or "Errno 5" in str(e):
                self.logger.error("❌ FATAL: Modem I/O error during read - connection lost. Raising exception.")
                raise ConnectionError(f"Modem I/O error during read: {e}")
            return b''
    
    def has_data_available(self):
        """Check if data is available for reading"""
        try:
            with self.lock:
                available = self.serial_connection.in_waiting >= 1
                return available
        except Exception as e:
            # Log error only once every 10 seconds to avoid spam
            current_time = time.time()
            if current_time - self.last_error_log_time > 10:
                self.logger.error(f"Error checking data availability: {e}")
                self.last_error_log_time = current_time
            # If it's an I/O error, the modem connection is broken - raise exception
            if "I/O error" in str(e) or "Errno 5" in str(e):
                self.logger.error("❌ FATAL: Modem I/O error during availability check - connection lost. Raising exception.")
                raise ConnectionError(f"Modem I/O error during availability check: {e}")
            return False
    
    def flush_buffers(self):
        """Flush input and output buffers"""
        try:
            with self.lock:
                self.serial_connection.flushInput()
                self.serial_connection.flushOutput()
        except Exception as e:
            self.logger.error(f"Error flushing buffers: {e}")
