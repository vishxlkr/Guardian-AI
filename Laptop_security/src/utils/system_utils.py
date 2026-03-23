"""
System Utilities - Windows-specific system functions
"""

import os
import sys
import ctypes
import subprocess
import winreg
import win32api
import win32con
import win32security
import win32process
import psutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def check_admin_rights() -> bool:
    """Check if the current process has administrator rights"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Restart the current script with administrator privileges"""
    if check_admin_rights():
        return True
    
    try:
        # Get the current script path
        script = os.path.abspath(sys.argv[0])
        params = ' '.join(sys.argv[1:])
        
        # Run as administrator
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable, 
            f'"{script}" {params}', 
            None, 
            1
        )
        return True
    except Exception as e:
        logger.error(f"Failed to elevate privileges: {e}")
        return False

def add_to_startup(app_name: str, app_path: str, args: str = "") -> bool:
    """Add application to Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Set the value
        command = f'"{app_path}"'
        if args:
            command += f' {args}'
            
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        
        logger.info(f"Added {app_name} to Windows startup")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add to startup: {e}")
        return False

def remove_from_startup(app_name: str) -> bool:
    """Remove application from Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Delete the value
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        
        logger.info(f"Removed {app_name} from Windows startup")
        return True
        
    except Exception as e:
        logger.error(f"Failed to remove from startup: {e}")
        return False

def is_in_startup(app_name: str) -> bool:
    """Check if application is in Windows startup"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_READ
        )
        
        # Try to read the value
        try:
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            winreg.CloseKey(key)
            return False
            
    except Exception as e:
        logger.error(f"Failed to check startup status: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information"""
    try:
        info = {
            'os': {
                'name': os.name,
                'platform': sys.platform,
                'version': sys.getwindowsversion().major,
                'build': sys.getwindowsversion().build,
                'release': win32api.GetVersionEx()[4]
            },
            'hardware': {
                'processor': os.environ.get('PROCESSOR_IDENTIFIER', 'Unknown'),
                'architecture': os.environ.get('PROCESSOR_ARCHITECTURE', 'Unknown'),
                'cpu_count': psutil.cpu_count(),
                'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2)
            },
            'user': {
                'username': os.environ.get('USERNAME', 'Unknown'),
                'userdomain': os.environ.get('USERDOMAIN', 'Unknown'),
                'is_admin': check_admin_rights()
            },
            'python': {
                'version': sys.version,
                'executable': sys.executable
            }
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {}

def get_camera_devices() -> List[Dict[str, Any]]:
    """Get list of available camera devices"""
    cameras = []
    
    try:
        # Use DirectShow to enumerate cameras
        import cv2
        
        for i in range(10):  # Check first 10 indexes
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                
                cameras.append({
                    'index': i,
                    'name': f"Camera {i}",
                    'resolution': f"{width}x{height}",
                    'fps': fps,
                    'backend': cap.getBackendName()
                })
                
                cap.release()
                
    except Exception as e:
        logger.error(f"Error enumerating cameras: {e}")
    
    return cameras

def create_shortcut(target_path: str, shortcut_path: str, 
                   args: str = "", icon_path: str = None):
    """Create a Windows shortcut (.lnk file)"""
    try:
        import win32com.client
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        
        shortcut.TargetPath = target_path
        shortcut.Arguments = args
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        
        if icon_path:
            shortcut.IconLocation = icon_path
        
        shortcut.save()
        
        logger.info(f"Created shortcut: {shortcut_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create shortcut: {e}")
        return False

def set_file_hidden(file_path: str):
    """Set file as hidden in Windows"""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(
            file_path,
            win32con.FILE_ATTRIBUTE_HIDDEN
        )
    except Exception as e:
        logger.error(f"Failed to hide file: {e}")

def get_idle_time() -> float:
    """Get system idle time in seconds"""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
        
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
        
        millis = win32api.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0
        
    except Exception as e:
        logger.error(f"Error getting idle time: {e}")
        return 0.0

def is_screen_locked() -> bool:
    """Check if Windows screen is locked"""
    try:
        # Check if the desktop is not visible
        desktop = win32api.OpenDesktop("default", 0, False, win32con.DESKTOP_SWITCHDESKTOP)
        if desktop:
            win32api.CloseDesktop(desktop)
            return False
        return True
        
    except:
        # Alternative method: check foreground window
        try:
            hwnd = win32api.GetForegroundWindow()
            if hwnd == 0:
                return True
            
            # Get window class name
            class_name = win32api.GetClassName(hwnd)
            return class_name == "Windows.UI.Core.CoreWindow"
            
        except:
            return False

def get_active_user_sessions() -> List[str]:
    """Get list of active user sessions"""
    sessions = []
    
    try:
        # Use WMI to get sessions
        import wmi
        c = wmi.WMI()
        
        for session in c.Win32_LogonSession():
            if session.LogonType in [2, 10]:  # Interactive or RemoteInteractive
                sessions.append({
                    'session_id': session.LogonId,
                    'logon_type': session.LogonType,
                    'start_time': session.StartTime
                })
                
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
    
    return sessions

def lock_workstation():
    """Lock the Windows workstation"""
    try:
        ctypes.windll.user32.LockWorkStation()
        logger.info("Workstation locked")
    except Exception as e:
        logger.error(f"Failed to lock workstation: {e}")

def show_system_tray_message(title: str, message: str, duration: int = 5000):
    """Show a system tray balloon message"""
    try:
        # This would require creating a system tray icon first
        # Simplified version using Windows toast notifications
        from plyer import notification
        
        notification.notify(
            title=title,
            message=message,
            app_name="Personal Security Software",
            timeout=duration // 1000
        )
    except Exception as e:
        logger.error(f"Failed to show tray message: {e}")

def get_startup_folder() -> Path:
    """Get the Windows startup folder path"""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        startup = shell.SpecialFolders("Startup")
        return Path(startup)
    except:
        # Fallback to default path
        return Path(os.environ['APPDATA']) / "Microsoft/Windows/Start Menu/Programs/Startup"

def cleanup_temp_files(pattern: str = "security_temp_*"):
    """Clean up temporary files"""
    try:
        temp_dir = Path(os.environ['TEMP'])
        
        for temp_file in temp_dir.glob(pattern):
            try:
                temp_file.unlink()
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")