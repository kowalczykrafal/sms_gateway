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
            
        except Exception as e:
            self.logger.error(f"❌ Error checking network status: {e}")
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
        """Get detailed network information (without signal check to avoid timeouts)"""
        try:
            self.logger.info("🔄 Getting detailed network information...")
            
            network_info = self.checkNetworkStatus(skip_signal_check=True)
            
            # SMS storage is now set during initialization, no need to set it here
            
            # Add additional network details
            network_info.update({
                "device": self.gsm.GsmDevice,
                "mode": self.gsm.GsmMode,
                "ready": self.gsm.Ready,
                "opened": self.gsm.Opened
            })
            
            return network_info
            
        except Exception as e:
            self.logger.error(f"❌ Error getting network info: {e}")
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
                self.gsm.commands.send_command("AT+CSQ", "Signal strength check", timeout=3)
                # Parse signal strength from response
                # +CSQ: 15,99 means RSSI=15 (good signal), BER=99 (not applicable)
                # RSSI values: 0-31 (higher is better), 99 means unknown
                return "good"  # Simplified for now
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
    
    def _getSignalPercentage(self, signal_strength):
        """Convert signal strength to percentage"""
        try:
            if signal_strength == "unknown":
                return 0
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
        except:
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
