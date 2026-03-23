"""
Windows Service Installer - Install/uninstall the security software as a Windows service
"""

import sys
import os
import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import socket
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class PersonalSecurityService(win32serviceutil.ServiceFramework):
    """Windows Service for Personal Security Software"""
    
    _svc_name_ = "PersonalSecurityService"
    _svc_display_name_ = "Personal Security Monitoring Service"
    _svc_description_ = "Monitors system security with face detection and screen protection"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
        self.app = None
        
        # Setup logging for service
        log_dir = Path("C:/ProgramData/PersonalSecurity/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename=str(log_dir / "service.log"),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('SecurityService')
    
    def SvcStop(self):
        """Stop the service"""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        # Signal stop
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        
        # Stop the application
        if self.app:
            try:
                self.app.stop()
            except Exception as e:
                self.logger.error(f"Error stopping application: {e}")
    
    def SvcDoRun(self):
        """Run the service"""
        self.logger.info("Service starting...")
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            self.logger.error(f"Service error: {e}", exc_info=True)
            self.SvcStop()
    
    def main(self):
        """Main service loop"""
        # Import here to avoid issues during service installation
        try:
            # Change to application directory
            app_dir = Path(__file__).parent.parent
            os.chdir(str(app_dir))
            
            # Import application
            from main import SecurityApplication
            
            # Create and start application
            self.logger.info("Initializing security application...")
            self.app = SecurityApplication()
            self.app.start()
            
            self.logger.info("Security application started successfully")
            
            # Keep service running
            while self.is_running:
                # Wait for stop signal or timeout
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop signal received
                    break
            
            self.logger.info("Service stopping...")
            
        except Exception as e:
            self.logger.error(f"Service main error: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"Personal Security Service Error: {e}")

def install_service():
    """Install the Windows service"""
    try:
        # Get the Python executable and script paths
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Service class
        service_class = f"{Path(__file__).stem}.{PersonalSecurityService.__name__}"
        
        # Install command
        win32serviceutil.InstallService(
            None,  # No special options
            PersonalSecurityService._svc_name_,
            PersonalSecurityService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START,
            description=PersonalSecurityService._svc_description_
        )
        
        print(f"Service '{PersonalSecurityService._svc_display_name_}' installed successfully")
        
        # Set service to restart on failure
        set_service_recovery()
        
        # Create necessary directories
        create_service_directories()
        
        print("\nTo start the service, use one of these methods:")
        print(f"1. Command line: net start {PersonalSecurityService._svc_name_}")
        print(f"2. Services app: Start -> Run -> services.msc")
        print(f"3. Python: python {Path(__file__).name} start")
        
    except Exception as e:
        print(f"Failed to install service: {e}")
        if "Access is denied" in str(e):
            print("\nPlease run this script as Administrator")
        sys.exit(1)

def uninstall_service():
    """Uninstall the Windows service"""
    try:
        # Stop service if running
        try:
            win32serviceutil.StopService(PersonalSecurityService._svc_name_)
            print("Service stopped")
        except:
            pass
        
        # Remove service
        win32serviceutil.RemoveService(PersonalSecurityService._svc_name_)
        print(f"Service '{PersonalSecurityService._svc_display_name_}' uninstalled successfully")
        
    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        if "Access is denied" in str(e):
            print("\nPlease run this script as Administrator")
        sys.exit(1)

def set_service_recovery():
    """Configure service to restart on failure"""
    try:
        import subprocess
        
        service_name = PersonalSecurityService._svc_name_
        
        # Set to restart on failure
        commands = [
            f'sc failure {service_name} reset=86400 actions=restart/60000/restart/60000/restart/60000',
            f'sc failureflag {service_name} 1'
        ]
        
        for cmd in commands:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
        
        print("Service recovery options configured")
        
    except Exception as e:
        print(f"Warning: Could not set recovery options: {e}")

def create_service_directories():
    """Create necessary directories for the service"""
    directories = [
        "C:/ProgramData/PersonalSecurity/logs",
        "C:/ProgramData/PersonalSecurity/config",
        "C:/ProgramData/PersonalSecurity/data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("Service directories created")

def check_service_status():
    """Check if service is installed and running"""
    try:
        status = win32serviceutil.QueryServiceStatus(PersonalSecurityService._svc_name_)
        
        state_map = {
            win32service.SERVICE_STOPPED: "Stopped",
            win32service.SERVICE_START_PENDING: "Starting",
            win32service.SERVICE_STOP_PENDING: "Stopping",
            win32service.SERVICE_RUNNING: "Running",
            win32service.SERVICE_CONTINUE_PENDING: "Continue Pending",
            win32service.SERVICE_PAUSE_PENDING: "Pause Pending",
            win32service.SERVICE_PAUSED: "Paused"
        }
        
        current_state = state_map.get(status[1], "Unknown")
        print(f"Service Status: {current_state}")
        
        return status[1]
        
    except Exception as e:
        print(f"Service not installed or error checking status: {e}")
        return None

def main():
    """Main entry point for service management"""
    if len(sys.argv) == 1:
        # If no arguments, run as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PersonalSecurityService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command line arguments
        cmd = sys.argv[1].lower()
        
        if cmd == 'install':
            install_service()
        elif cmd == 'uninstall' or cmd == 'remove':
            uninstall_service()
        elif cmd == 'start':
            win32serviceutil.StartService(PersonalSecurityService._svc_name_)
            print("Service started")
        elif cmd == 'stop':
            win32serviceutil.StopService(PersonalSecurityService._svc_name_)
            print("Service stopped")
        elif cmd == 'restart':
            win32serviceutil.RestartService(PersonalSecurityService._svc_name_)
            print("Service restarted")
        elif cmd == 'status':
            check_service_status()
        else:
            print("Usage: python service_installer.py [install|uninstall|start|stop|restart|status]")
            sys.exit(1)

if __name__ == '__main__':
    main()