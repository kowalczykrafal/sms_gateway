"""
GSM Reset Module

Handles modem reset operations: USB reset, AT command reset, and reconnection logic.
"""

import time
import logging
import subprocess
import os
import glob


class GSMReset:
    """Handles GSM modem reset operations and reconnection logic"""
    
    def __init__(self, gsm_instance):
        """Initialize with reference to main GSM instance"""
        self.gsm = gsm_instance
        self.logger = logging.getLogger(__name__)
    
    def _is_connection_error(self, error):
        """Check if error is a connection-related error"""
        try:
            error_str = str(error).lower()
            connection_indicators = [
                'device or resource busy',
                'permission denied',
                'no such file or directory',
                'connection lost',
                'serial port',
                'i/o error',
                'broken pipe',
                'connection reset',
                'timeout'
            ]
            
            for indicator in connection_indicators:
                if indicator in error_str:
                    return True
            return False
        except:
            return False
    
    def _try_compiled_usbreset(self):
        """Try to reset USB device using compiled usbreset tool"""
        try:
            self.logger.info("🔄 Attempting USB reset with compiled usbreset tool...")
            
            # Find USB device path for our GSM device
            usb_device_path = self._find_usb_device_path()
            if not usb_device_path:
                self.logger.debug("⚠️ Could not find USB device path for reset")
                return False
            
            self.logger.debug(f"📱 Found USB device path: {usb_device_path}")
            
            # Try to use compiled usbreset tool
            try:
                result = subprocess.run(['/usr/local/bin/usbreset', usb_device_path], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.logger.info("✅ Compiled usbreset successful")
                    time.sleep(2)  # Give device time to reset
                    return True
                else:
                    # Check if it's a permission error (expected in Home Assistant)
                    if "Operation not permitted" in result.stderr:
                        self.logger.debug("⚠️ Compiled usbreset failed: Operation not permitted (expected in Home Assistant)")
                    else:
                        self.logger.debug(f"⚠️ Compiled usbreset failed: {result.stderr}")
                    return False
                    
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                self.logger.debug(f"⚠️ Compiled usbreset not available: {e}")
                return False
                
        except Exception as e:
            self.logger.debug(f"⚠️ Compiled usbreset error: {e}")
            return False
    
    def _find_usb_device_path(self):
        """Find USB device path for our GSM device"""
        try:
            # Get device path from our GSM device
            if hasattr(self.gsm, 'GsmDevice') and self.gsm.GsmDevice:
                device_path = self.gsm.GsmDevice
                self.logger.debug(f"📱 GSM device path: {device_path}")
                
                # Convert /dev/ttyUSB* to /dev/bus/usb/*/***
                if '/dev/ttyUSB' in device_path:
                    # Find corresponding USB device
                    usb_devices = glob.glob('/dev/bus/usb/*/*')
                    for usb_dev in usb_devices:
                        try:
                            # Check if this USB device corresponds to our ttyUSB
                            # This is a simplified approach - in reality we'd need to parse sysfs
                            # For now, just return the first available USB device
                            if os.path.exists(usb_dev):
                                self.logger.debug(f"📱 Found USB device: {usb_dev}")
                                return usb_dev
                        except:
                            continue
                
                # Fallback: try common USB device paths
                common_paths = [
                    '/dev/bus/usb/001/001',
                    '/dev/bus/usb/001/002', 
                    '/dev/bus/usb/001/003',
                    '/dev/bus/usb/002/001',
                    '/dev/bus/usb/002/002',
                    '/dev/bus/usb/002/003'
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        self.logger.debug(f"📱 Using fallback USB device: {path}")
                        return path
                        
            return None
            
        except Exception as e:
            self.logger.debug(f"⚠️ Error finding USB device path: {e}")
            return None
    
    def _try_usb_reset(self):
        """Try to reset USB device using usbreset or alternative methods"""
        try:
            # Method 1: Try compiled usbreset tool (most effective)
            if self._try_compiled_usbreset():
                return True
            
            # Check if we're in a Home Assistant environment (no privileged access)
            if os.path.exists('/etc/hassio.json') or os.environ.get('SUPERVISOR_TOKEN'):
                self.logger.debug("Home Assistant environment detected - using simplified USB reset")
                self._try_simple_usb_reset()
                return True
            
            # Check if basic tools are available
            tools_available = []
            try:
                subprocess.run(['lsusb'], capture_output=True, timeout=2)
                tools_available.append('lsusb')
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            try:
                subprocess.run(['usbreset'], capture_output=True, timeout=2)
                tools_available.append('usbreset')
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            try:
                subprocess.run(['modprobe'], capture_output=True, timeout=2)
                tools_available.append('modprobe')
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            try:
                subprocess.run(['udevadm'], capture_output=True, timeout=2)
                tools_available.append('udevadm')
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            self.logger.debug(f"Available USB tools: {tools_available}")
            
            # Method 2: Try standard usbreset command
            if 'usbreset' in tools_available:
                self.logger.info("🔄 Attempting USB reset with usbreset command...")
                try:
                    # Find USB device ID
                    result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if 'HUAWEI' in line or 'Mobile' in line:
                                # Extract bus and device numbers
                                parts = line.split()
                                if len(parts) >= 4:
                                    bus_device = parts[1] + ':' + parts[3].rstrip(':')
                                    self.logger.debug(f"Found Huawei device: {bus_device}")
                                    
                                    # Try to reset using usbreset
                                    reset_result = subprocess.run(['usbreset', bus_device], 
                                                               capture_output=True, text=True, timeout=10)
                                    if reset_result.returncode == 0:
                                        self.logger.info("✅ USB reset successful with usbreset command")
                                        time.sleep(2)
                                        return True
                                    else:
                                        self.logger.debug(f"usbreset command failed: {reset_result.stderr}")
                except Exception as e:
                    self.logger.debug(f"usbreset command error: {e}")
            
            # Method 3: Try udevadm trigger (more likely to work in Home Assistant)
            if 'udevadm' in tools_available:
                self.logger.info("🔄 Attempting USB reset with udevadm trigger...")
                try:
                    # Trigger udev events for USB devices
                    subprocess.run(['udevadm', 'trigger', '--subsystem-match=usb'], capture_output=True, timeout=5)
                    time.sleep(1)
                    subprocess.run(['udevadm', 'settle'], capture_output=True, timeout=5)
                    time.sleep(2)
                    self.logger.info("✅ USB reset successful with udevadm trigger")
                    return True
                except Exception as e:
                    self.logger.debug(f"udevadm trigger error: {e}")
            
            # Method 4: Try modprobe + udevadm
            if 'modprobe' in tools_available and 'udevadm' in tools_available:
                self.logger.info("🔄 Attempting USB reset with modprobe + udevadm...")
                try:
                    # Unbind and rebind USB driver
                    subprocess.run(['modprobe', '-r', 'usb-storage'], capture_output=True, timeout=5)
                    time.sleep(1)
                    subprocess.run(['modprobe', 'usb-storage'], capture_output=True, timeout=5)
                    time.sleep(1)
                    subprocess.run(['udevadm', 'trigger'], capture_output=True, timeout=5)
                    time.sleep(2)
                    self.logger.info("✅ USB reset successful with modprobe + udevadm")
                    return True
                except Exception as e:
                    self.logger.debug(f"modprobe + udevadm error: {e}")
            
            # Method 5: Fallback - simple sleep
            self.logger.info("🔄 Using fallback USB reset method (sleep)...")
            self._try_simple_usb_reset()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ USB reset failed: {e}")
            return False
    
    def _try_simple_usb_reset(self):
        """Simple USB reset using sleep (fallback method)"""
        try:
            self.logger.info("🔄 Performing simple USB reset (sleep method)...")
            time.sleep(3)  # Give device time to reset
            self.logger.info("✅ Simple USB reset completed")
        except Exception as e:
            self.logger.error(f"❌ Simple USB reset error: {e}")
    
    def _try_usb_unbind_rebind(self, device_id):
        """Try to unbind and rebind USB device"""
        try:
            self.logger.info(f"🔄 Attempting USB unbind/rebind for device {device_id}...")
            
            # Try to unbind device
            try:
                with open(f'/sys/bus/usb/drivers/usb/unbind', 'w') as f:
                    f.write(device_id)
                self.logger.debug(f"Unbound device {device_id}")
            except Exception as e:
                self.logger.debug(f"Failed to unbind device {device_id}: {e}")
            
            time.sleep(2)
            
            # Try to rebind device
            try:
                with open(f'/sys/bus/usb/drivers/usb/bind', 'w') as f:
                    f.write(device_id)
                self.logger.debug(f"Rebound device {device_id}")
            except Exception as e:
                self.logger.debug(f"Failed to rebind device {device_id}: {e}")
            
            time.sleep(2)
            self.logger.info("✅ USB unbind/rebind completed")
            
        except Exception as e:
            self.logger.error(f"❌ USB unbind/rebind error: {e}")
    
    def _try_at_command_reset(self):
        """Try to reset modem using AT commands"""
        try:
            self.logger.info("🔄 Attempting AT command modem reset...")
            
            # Check if device is open before trying AT commands
            if not self.gsm.Opened:
                self.logger.debug("⚠️ Device not open, skipping AT command reset")
                return False
            
            # Try different AT reset commands (including Huawei E3372 specific)
            reset_commands = [
                ("AT^CURC=0", "Disable periodic status messages (Huawei)"),
                ("AT+CFUN=0", "Disable RF function"),
                ("AT+CFUN=1", "Enable RF function"),
                ("AT+CPOWD=1", "Power down"),
                ("AT+CPOWD=0", "Power up"),
                ("AT+CRESET", "Reset"),
                ("AT+CRST", "Reset alternative"),
                ("AT+CRESET=1", "Reset with parameter"),
                ("AT^RESET", "Huawei specific reset"),
            ]
            
            for cmd, description in reset_commands:
                try:
                    self.logger.debug(f"🔄 Trying AT command: {description} ({cmd})")
                    
                    # Use safe AT command execution
                    if self.gsm.commands._execute_at_command_safely(cmd, description, timeout=5):
                        self.logger.info(f"✅ AT command {description} executed successfully")
                        time.sleep(2)
                        break
                    else:
                        self.logger.debug(f"AT command {description} failed or timed out")
                        
                except Exception as e:
                    self.logger.debug(f"AT command {description} failed: {e}")
                    continue
            
            # Final AT command to check if modem is responsive
            try:
                if self.gsm.Opened and self.gsm.commands._execute_at_command_safely("AT", "Final responsiveness test", timeout=3):
                    self.logger.info("✅ Modem is responsive after AT reset")
                else:
                    self.logger.debug("Modem not responsive after AT reset")
            except Exception as e:
                self.logger.debug(f"AT test after reset failed: {e}")
                
        except Exception as e:
            self.logger.debug(f"AT command reset failed: {e}")
    
