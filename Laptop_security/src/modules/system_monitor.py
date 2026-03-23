"""
System Monitor - Monitors various system events for security
"""

import psutil
import threading
import time
import logging
from typing import Dict, Any, List, Callable
from datetime import datetime
import win32api
import win32con
import win32security
import win32evtlog

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system events and triggers security actions"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.is_monitoring = False
        self.monitor_threads = []
        self.event_handlers = {}
        
        # Monitoring settings
        self.check_interval = self.config.get('system_monitor.check_interval', 5)
        self.monitor_processes = self.config.get('system_monitor.monitor_processes', True)
        self.monitor_network = self.config.get('system_monitor.monitor_network', True)
        self.monitor_usb = self.config.get('system_monitor.monitor_usb', True)
        
        # State tracking
        self.known_processes = set()
        self.known_connections = set()
        self.known_usb_devices = set()
        
    def start(self):
        """Start all system monitors"""
        logger.info("Starting system monitor")
        self.is_monitoring = True
        
        # Initialize current state
        self._initialize_baseline()
        
        # Start monitoring threads
        if self.monitor_processes:
            thread = threading.Thread(target=self._monitor_processes, daemon=True)
            thread.start()
            self.monitor_threads.append(thread)
        
        if self.monitor_network:
            thread = threading.Thread(target=self._monitor_network, daemon=True)
            thread.start()
            self.monitor_threads.append(thread)
        
        if self.monitor_usb:
            thread = threading.Thread(target=self._monitor_usb, daemon=True)
            thread.start()
            self.monitor_threads.append(thread)
    
    def stop(self):
        """Stop all monitors"""
        logger.info("Stopping system monitor")
        self.is_monitoring = False
        
        # Wait for threads to finish
        for thread in self.monitor_threads:
            thread.join(timeout=5)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific event types"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger handlers for an event"""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def _initialize_baseline(self):
        """Initialize baseline state for monitoring"""
        # Get current processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                self.known_processes.add((proc.info['pid'], proc.info['name']))
            except:
                pass
        
        # Get current network connections
        for conn in psutil.net_connections():
            if conn.status == 'ESTABLISHED':
                self.known_connections.add((conn.raddr.ip if conn.raddr else None, 
                                           conn.raddr.port if conn.raddr else None))
        
        # Get current USB devices
        self.known_usb_devices = self._get_usb_devices()
        
        logger.info("System baseline initialized")
    
    def _monitor_processes(self):
        """Monitor for new suspicious processes"""
        suspicious_processes = [
            'keylogger', 'mimikatz', 'pwdump', 'procdump',
            'lazagne', 'wirelesskey', 'netpass'
        ]
        
        while self.is_monitoring:
            try:
                current_processes = set()
                
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name']
                        current_processes.add((pid, name))
                        
                        # Check for suspicious processes
                        if any(susp in name.lower() for susp in suspicious_processes):
                            self._trigger_event('suspicious_process', {
                                'pid': pid,
                                'name': name,
                                'exe': proc.info.get('exe', ''),
                                'timestamp': datetime.now().isoformat()
                            })
                            logger.warning(f"Suspicious process detected: {name}")
                        
                        # Check for new processes
                        if (pid, name) not in self.known_processes:
                            # Check if it's accessing camera
                            if self._is_process_accessing_camera(proc):
                                self._trigger_event('camera_access', {
                                    'pid': pid,
                                    'name': name,
                                    'timestamp': datetime.now().isoformat()
                                })
                                logger.warning(f"Process accessing camera: {name}")
                    
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Update known processes
                self.known_processes = current_processes
                
            except Exception as e:
                logger.error(f"Error monitoring processes: {e}")
            
            time.sleep(self.check_interval)
    
    def _monitor_network(self):
        """Monitor network connections"""
        while self.is_monitoring:
            try:
                current_connections = set()
                suspicious_ports = [22, 23, 3389, 5900, 5800]  # SSH, Telnet, RDP, VNC
                
                for conn in psutil.net_connections():
                    if conn.status == 'ESTABLISHED' and conn.raddr:
                        connection = (conn.raddr.ip, conn.raddr.port)
                        current_connections.add(connection)
                        
                        # Check for new connections
                        if connection not in self.known_connections:
                            # Check for suspicious ports
                            if conn.laddr.port in suspicious_ports:
                                self._trigger_event('suspicious_connection', {
                                    'local_port': conn.laddr.port,
                                    'remote_ip': conn.raddr.ip,
                                    'remote_port': conn.raddr.port,
                                    'timestamp': datetime.now().isoformat()
                                })
                                logger.warning(f"Suspicious connection on port {conn.laddr.port}")
                
                # Update known connections
                self.known_connections = current_connections
                
            except Exception as e:
                logger.error(f"Error monitoring network: {e}")
            
            time.sleep(self.check_interval)
    
    def _monitor_usb(self):
        """Monitor USB device changes"""
        while self.is_monitoring:
            try:
                current_devices = self._get_usb_devices()
                
                # Check for new devices
                new_devices = current_devices - self.known_usb_devices
                if new_devices:
                    for device in new_devices:
                        self._trigger_event('usb_connected', {
                            'device': device,
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info(f"USB device connected: {device}")
                
                # Check for removed devices
                removed_devices = self.known_usb_devices - current_devices
                if removed_devices:
                    for device in removed_devices:
                        self._trigger_event('usb_disconnected', {
                            'device': device,
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info(f"USB device disconnected: {device}")
                
                # Update known devices
                self.known_usb_devices = current_devices
                
            except Exception as e:
                logger.error(f"Error monitoring USB: {e}")
            
            time.sleep(self.check_interval)
    
    def _get_usb_devices(self) -> set:
        """Get list of USB devices"""
        devices = set()
        try:
            import wmi
            c = wmi.WMI()
            for usb in c.Win32_USBControllerDevice():
                devices.add(usb.Dependent.DeviceID)
        except Exception as e:
            logger.error(f"Error getting USB devices: {e}")
        return devices
    
    def _is_process_accessing_camera(self, process) -> bool:
        """Check if a process is accessing the camera"""
        try:
            # Check for common camera access patterns
            camera_indicators = [
                'camera', 'webcam', 'video', 'capture',
                'obs', 'zoom', 'teams', 'skype'
            ]
            
            proc_name = process.info['name'].lower()
            
            # Skip our own process
            if 'python' in proc_name:
                return False
            
            # Check process name
            if any(indicator in proc_name for indicator in camera_indicators):
                return True
            
            # Check open handles (more complex, Windows-specific)
            # This would require additional Windows API calls
            
        except:
            pass
        
        return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'process_count': len(psutil.pids()),
                'network_connections': len(list(psutil.net_connections())),
                'logged_in_users': [user.name for user in psutil.users()]
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}
    
    def check_system_integrity(self) -> List[str]:
        """Run basic system integrity checks"""
        issues = []
        
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent}%")
            
            # Check memory usage
            mem_percent = psutil.virtual_memory().percent
            if mem_percent > 90:
                issues.append(f"High memory usage: {mem_percent}%")
            
            # Check disk space
            disk_percent = psutil.disk_usage('/').percent
            if disk_percent > 90:
                issues.append(f"Low disk space: {disk_percent}% used")
            
            # Check for multiple login sessions
            users = psutil.users()
            if len(users) > 1:
                issues.append(f"Multiple users logged in: {len(users)}")
            
        except Exception as e:
            logger.error(f"Error checking system integrity: {e}")
            issues.append(f"Integrity check error: {str(e)}")
        
        return issues