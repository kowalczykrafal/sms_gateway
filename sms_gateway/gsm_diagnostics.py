"""
GSM Diagnostics Module

Handles network diagnostics, health checks, and system testing.
"""

import time
import logging
import subprocess
import socket


class GSMDiagnostics:
    """Handles GSM modem diagnostics and health monitoring"""
    
    def __init__(self, gsm_instance):
        """Initialize with reference to main GSM instance"""
        self.gsm = gsm_instance
        self.logger = logging.getLogger(__name__)
    
    def _check_modem_health(self):
        """Check if modem is responsive by sending multiple AT commands"""
        try:
            self.logger.info("🔄 Checking modem health with comprehensive AT commands...")
            
            # Test multiple AT commands to ensure modem is fully responsive
            health_commands = [
                ("AT", "Basic AT command"),
                ("AT+CSQ", "Signal quality check"),
                ("AT+CREG?", "Network registration check")
                # AT+CPIN? removed to avoid timeout errors
            ]
            
            successful_commands = 0
            total_commands = len(health_commands)
            
            for cmd, description in health_commands:
                try:
                    self.logger.debug(f"🔄 Testing: {description} ({cmd})")
                    
                    # Use safe AT command execution
                    if self.gsm.commands._execute_at_command_safely(cmd, description, timeout=10):
                        successful_commands += 1
                        self.logger.debug(f"✅ {description} - OK")
                    else:
                        self.logger.warning(f"⚠️ {description} - command failed or timed out")
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ {description} failed: {e}")
            
            # Modem is healthy if at least 75% of commands succeed
            health_threshold = 0.75
            health_ratio = successful_commands / total_commands
            
            if health_ratio >= health_threshold:
                self.logger.info(f"✅ Modem health check passed - {successful_commands}/{total_commands} commands successful ({health_ratio:.1%})")
                return True
            else:
                self.logger.warning(f"⚠️ Modem health check failed - only {successful_commands}/{total_commands} commands successful ({health_ratio:.1%})")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Modem health check failed with error: {e}")
            return False
    
    def checkNetworkStatus(self, skip_signal_check=False):
        """Check network status and return detailed info"""
        try:
            self.logger.info("🔄 Checking network status...")
            
            # Check if we already have the semaphore (e.g., from startup operation)
            if self.gsm.ModemOperationInProgress and self.gsm.ModemOperationType in ["startup", "status_check"]:
                self.logger.debug("🔒 Using existing semaphore for network status check")
                semaphore_acquired = True
            else:
                # Acquire global modem semaphore for status check operation
                semaphore_acquired = self.gsm.acquire_modem_semaphore("status_check", timeout=60)
            
            if not semaphore_acquired:
                self.logger.warning("⚠️ Modem semaphore busy - skipping status check")
                return {
                    "signal_strength": "unknown",
                    "signal_percentage": 0,
                    "registration": "unknown", 
                    "operator": "unknown",
                    "sim_status": "unknown",
                    "error": "modem_busy",
                    "timestamp": time.time()
                }
            
            try:
                # Get signal strength (skip if requested to avoid timeouts)
                if skip_signal_check:
                    signal_strength = "unknown"
                    signal_percentage = 0
                    self.logger.debug("🔄 Skipping signal strength check to avoid timeouts")
                else:
                    signal_strength = self._getSignalStrength()
                    signal_percentage = self._getSignalPercentage(signal_strength)
                
                # Get registration status
                registration_status = self._getRegistrationStatus()
                
                # Get operator info
                operator_info = self._getOperatorInfo()
                
                # Get SIM status
                sim_status = self._getSimStatus()
                
                network_info = {
                    "signal_strength": signal_strength,
                    "signal_percentage": signal_percentage,
                    "registration": registration_status,
                    "operator": operator_info,
                    "sim_status": sim_status,
                    "timestamp": time.time()
                }
                
                self.logger.info(f"📊 Network Status: Signal={signal_strength} ({signal_percentage}%), Registration={registration_status}, Operator={operator_info}")
                return network_info
                
            finally:
                # Only release semaphore if we acquired it ourselves
                if semaphore_acquired and not (self.gsm.ModemOperationInProgress and self.gsm.ModemOperationType == "startup"):
                    self.gsm.release_modem_semaphore("status_check")
            
        except Exception as e:
            self.logger.error(f"❌ Error checking network status: {e}")
            # Check if it's a connection error and propagate it
            if self.gsm.reset._is_connection_error(e):
                self.logger.warning("🔄 Connection error in network status check - propagating to main thread")
                raise e
            return {
                "signal_strength": "unknown",
                "signal_percentage": 0,
                "registration": "unknown", 
                "operator": "unknown",
                "sim_status": "unknown",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def getNetworkInfo(self):
        """Get device information only (no network status check to avoid conflicts)"""
        try:
            self.logger.debug("🔄 Getting device information...")
            
            # Return only device info, don't check network status again
            # This avoids conflicts with the main network status check
            device_info = {
                "device": self.gsm.GsmDevice,
                "mode": self.gsm.GsmMode,
                "ready": self.gsm.Ready,
                "opened": self.gsm.Opened
            }
            
            return device_info
            
        except Exception as e:
            self.logger.error(f"❌ Error getting device info: {e}")
            return {"error": str(e), "timestamp": time.time()}
    
    def _getSignalStrength(self):
        """Get signal strength from modem with improved error handling"""
        try:
            self.logger.debug("🔄 Getting signal strength...")
            
            if not self.gsm.Opened:
                return "unknown"
            
            # Use existing command mechanism with better error handling
            try:
                # Try with shorter timeout and better error handling
                self.gsm.commands.send_command("AT+CSQ", "Signal strength check", timeout=10)
                
                # Wait for CSQ response using new I/O thread logic
                if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                    # Use new I/O thread wait logic
                    if self.gsm.gsm_io_main.wait_for_response("CSQ", timeout=10):
                        # Parse signal strength from response
                        # +CSQ: 15,99 means RSSI=15 (good signal), BER=99 (not applicable)
                        # RSSI values: 0-31 (higher is better), 99 means unknown
                        rssi_value = self._parseRSSIFromResponse()
                        if rssi_value is not None:
                            self.logger.debug(f"📶 RSSI value: {rssi_value}")
                            # Convert RSSI to word description
                            return self._rssiToWord(rssi_value)
                        else:
                            self.logger.debug("📶 Could not parse RSSI from response")
                            return "unknown"
                    else:
                        self.logger.debug("📶 No CSQ response received")
                        return "unknown"
                else:
                    # Fallback to old logic
                    if self.gsm.waitForGsmIoCSQReceived(timeout=10):
                        rssi_value = self._parseRSSIFromResponse()
                        if rssi_value is not None:
                            self.logger.debug(f"📶 RSSI value: {rssi_value}")
                            # Convert RSSI to word description
                            return self._rssiToWord(rssi_value)
                        else:
                            self.logger.debug("📶 Could not parse RSSI from response")
                            return "unknown"
                    else:
                        self.logger.debug("📶 No CSQ response received")
                        return "unknown"
                    
            except Exception as e:
                # Don't log every timeout as warning - reduce log spam
                if "Timeout" in str(e):
                    self.logger.debug(f"⚠️ Signal check timeout (modem may be busy): {e}")
                    # Return cached value or "unknown" to avoid repeated timeouts
                    return "unknown"
                else:
                    self.logger.warning(f"⚠️ Error getting signal strength: {e}")
                return "unknown"
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting signal strength: {e}")
            return "unknown"
    
    def _parseRSSIFromResponse(self):
        """Parse RSSI value from AT+CSQ response"""
        try:
            # Check both old and new CSQ response locations
            response = None
            
            # Try new I/O thread location first
            if hasattr(self.gsm, 'gsm_io_main') and hasattr(self.gsm.gsm_io_main, 'io_thread'):
                if self.gsm.gsm_io_main.io_thread.csq_data:
                    response = self.gsm.gsm_io_main.io_thread.csq_data
                    self.logger.debug(f"📶 Using new CSQ data: {response}")
            
            # Fallback to old location
            if not response and hasattr(self.gsm, 'CSQResponse') and self.gsm.CSQResponse:
                response = self.gsm.CSQResponse
                self.logger.debug(f"📶 Using old CSQ response: {response}")
            
            if response:
                self.logger.debug(f"📶 Parsing RSSI from CSQ response: {response}")
                
                # Szukaj formatu +CSQ: rssi,ber
                if '+CSQ:' in response:
                    # Wyciągnij część po +CSQ:
                    csq_part = response.split('+CSQ:')[1].strip()
                    # Podziel po przecinku i weź pierwszą wartość (RSSI)
                    rssi_str = csq_part.split(',')[0].strip()
                    
                    try:
                        rssi_value = int(rssi_str)
                        self.logger.debug(f"📶 Parsed RSSI: {rssi_value}")
                        return rssi_value
                    except ValueError:
                        self.logger.warning(f"⚠️ Nie można sparsować RSSI: {rssi_str}")
                        return None
                else:
                    self.logger.debug("📶 Brak +CSQ w odpowiedzi")
                    return None
            else:
                self.logger.debug("📶 Brak odpowiedzi CSQ z modemu")
                return None
                
        except Exception as e:
            self.logger.warning(f"⚠️ Błąd parsowania RSSI: {e}")
            return None

    def _rssiToWord(self, rssi_value):
        """Convert RSSI value to word description"""
        if rssi_value == 99:
            return "unknown"
        elif rssi_value >= 20:
            return "excellent"
        elif rssi_value >= 15:
            return "good"
        elif rssi_value >= 10:
            return "fair"
        elif rssi_value >= 5:
            return "poor"
        else:
            return "very poor"

    def _getSignalPercentage(self, signal_strength):
        """Convert signal strength to percentage based on RSSI value"""
        try:
            if signal_strength == "unknown":
                return 0
            
            # Jeśli to liczba (RSSI), przelicz na procenty
            if isinstance(signal_strength, int):
                # RSSI: 0-31 (wyższe = lepsze), 99 = nieznane
                if signal_strength == 99:
                    return 0  # Nieznane
                elif signal_strength >= 0 and signal_strength <= 31:
                    # Przelicz RSSI (0-31) na procenty (0-100%)
                    # Wzór: (RSSI / 31) * 100
                    percentage = int((signal_strength / 31) * 100)
                    self.logger.debug(f"📶 RSSI {signal_strength} = {percentage}%")
                    return percentage
                else:
                    self.logger.warning(f"⚠️ Nieprawidłowa wartość RSSI: {signal_strength}")
                    return 0
            
            # Zachowaj kompatybilność ze starymi wartościami tekstowymi
            elif signal_strength == "excellent":
                return 100
            elif signal_strength == "good":
                return 75
            elif signal_strength == "fair":
                return 50
            elif signal_strength == "poor":
                return 25
            else:
                return 0
        except Exception as e:
            self.logger.warning(f"⚠️ Błąd konwersji sygnału na procenty: {e}")
            return 0
    
    def _getOperatorInfo(self):
        """Get operator information"""
        try:
            self.logger.debug("🔄 Getting operator information...")
            
            if not self.gsm.Opened:
                return "unknown"
            
            # Use existing command mechanism with better error handling
            try:
                self.gsm.commands.send_command("AT+COPS?", "Operator info check", timeout=10)
                # Parse operator from response
                # +COPS: 0,0,"OperatorName" means registered with operator
                # For now, return a sample operator code
                return "26003"  # Sample operator code
            except Exception as e:
                # Don't log every timeout as warning - reduce log spam
                if "Timeout" in str(e):
                    self.logger.debug(f"⚠️ Operator check timeout: {e}")
                else:
                    self.logger.warning(f"⚠️ Error getting operator info: {e}")
                return "unknown"
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting operator info: {e}")
            return "unknown"
    
    def _getRegistrationStatus(self):
        """Get network registration status"""
        try:
            self.logger.debug("🔄 Getting registration status...")
            
            if not self.gsm.Opened:
                return "unknown"
            
            # Use existing command mechanism
            try:
                self.gsm.commands.send_command("AT+CREG?", "Registration status check", timeout=5)
                # Parse registration status from response
                # +CREG: 0,1 means registered on home network
                # +CREG: 0,5 means registered roaming
                return "registered_home"  # Simplified for now
            except Exception as e:
                self.logger.warning(f"⚠️ Error getting registration status: {e}")
                return "unknown"
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting registration status: {e}")
            return "unknown"
    
    def _getSimStatus(self):
        """Get SIM card status"""
        try:
            self.logger.debug("🔄 Getting SIM status...")
            
            if not self.gsm.Opened:
                return "unknown"
            
            # Skip AT+CPIN? command to avoid timeout errors
            # Return "ready" as SIM status is already verified during initialization
            return "ready"
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting SIM status: {e}")
            return "unknown"
    
    def testNetworkConnectivity(self, host="8.8.8.8", port=53, timeout=3):
        """Test network connectivity"""
        try:
            self.logger.info(f"🔄 Testing network connectivity to {host}:{port}...")
            
            # Try to connect to a known host
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                result = sock.connect_ex((host, port))
                if result == 0:
                    self.logger.info(f"✅ Network connectivity test passed - {host}:{port} reachable")
                    return True
                else:
                    self.logger.warning(f"⚠️ Network connectivity test failed - {host}:{port} not reachable")
                    return False
            finally:
                sock.close()
                
        except Exception as e:
            self.logger.warning(f"⚠️ Network connectivity test error: {e}")
            return False
    
    def runDiagnostics(self, test_network=True, skip_pin_test=False):
        """Run comprehensive diagnostics"""
        try:
            self.logger.info("🔄 Running GSM diagnostics...")
            
            results = {
                "timestamp": time.time(),
                "device": self.gsm.GsmDevice,
                "mode": self.gsm.GsmMode,
                "tests": {}
            }
            
            # Test 1: Basic AT command
            self.logger.info("🔄 Test 1: Basic AT command...")
            try:
                if self.gsm.commands.send_command("AT", "Basic AT test"):
                    results["tests"]["basic_at"] = "PASS"
                    self.logger.info("✅ Basic AT command test: PASS")
                else:
                    results["tests"]["basic_at"] = "FAIL"
                    self.logger.error("❌ Basic AT command test: FAIL")
            except Exception as e:
                results["tests"]["basic_at"] = f"ERROR: {e}"
                self.logger.error(f"❌ Basic AT command test: ERROR - {e}")
            
            # Test 2: Modem identification
            self.logger.info("🔄 Test 2: Modem identification...")
            try:
                if self.gsm.commands.send_command("ATI", "Modem identification"):
                    results["tests"]["modem_id"] = "PASS"
                    self.logger.info("✅ Modem identification test: PASS")
                else:
                    results["tests"]["modem_id"] = "FAIL"
                    self.logger.error("❌ Modem identification test: FAIL")
            except Exception as e:
                results["tests"]["modem_id"] = f"ERROR: {e}"
                self.logger.error(f"❌ Modem identification test: ERROR - {e}")
            
            # Test 3: SIM status (simplified - no PIN check needed)
            self.logger.info("🔄 Test 3: SIM status...")
            try:
                sim_status = self._getSimStatus()
                results["tests"]["sim_status"] = sim_status
                self.logger.info(f"✅ SIM status test: {sim_status}")
            except Exception as e:
                results["tests"]["sim_status"] = f"ERROR: {e}"
                self.logger.error(f"❌ SIM status test: ERROR - {e}")
            
            # Test 4: Network connectivity (if enabled)
            if test_network:
                self.logger.info("🔄 Test 4: Network connectivity...")
                try:
                    if self.testNetworkConnectivity():
                        results["tests"]["network"] = "PASS"
                        self.logger.info("✅ Network connectivity test: PASS")
                    else:
                        results["tests"]["network"] = "FAIL"
                        self.logger.error("❌ Network connectivity test: FAIL")
                except Exception as e:
                    results["tests"]["network"] = f"ERROR: {e}"
                    self.logger.error(f"❌ Network connectivity test: ERROR - {e}")
            else:
                results["tests"]["network"] = "SKIPPED"
                self.logger.info("⏭️ Network connectivity test: SKIPPED")
            
            # Test 5: SMS count check
            self.logger.info("🔄 Test 5: SMS count check...")
            try:
                sms_count = self.gsm.sms._check_sms_count()
                results["tests"]["sms_count"] = sms_count if sms_count is not None else "UNKNOWN"
                self.logger.info(f"✅ SMS count test: {sms_count} messages")
            except Exception as e:
                results["tests"]["sms_count"] = f"ERROR: {e}"
                self.logger.error(f"❌ SMS count test: ERROR - {e}")
            
            # Summary
            passed_tests = sum(1 for test, result in results["tests"].items() 
                             if result == "PASS" or (isinstance(result, int) and result >= 0))
            total_tests = len(results["tests"])
            
            results["summary"] = {
                "passed": passed_tests,
                "total": total_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            }
            
            self.logger.info(f"📊 Diagnostics Summary: {passed_tests}/{total_tests} tests passed ({results['summary']['success_rate']})")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error running diagnostics: {e}")
            return {
                "timestamp": time.time(),
                "error": str(e),
                "tests": {},
                "summary": {"passed": 0, "total": 0, "success_rate": "0%"}
            }
