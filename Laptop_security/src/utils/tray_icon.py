"""
Tray Icon Manager - Windows system tray integration
"""

import sys
import threading
from pathlib import Path
import logging
from PIL import Image

# Windows tray icon imports
try:
    import pystray
    from PIL import Image, ImageDraw
    import win32api
    import win32gui
    import win32con
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

logger = logging.getLogger(__name__)

class TrayIcon:
    """Manages Windows system tray icon for the security application"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.icon = None
        self.running = False
        
        if not TRAY_AVAILABLE:
            logger.error("System tray dependencies not available")
            return
        
        # Create icon image
        self.icon_image = self._create_icon_image()
        
        # Menu items
        self.menu_items = self._create_menu()
    
    def _create_icon_image(self) -> Image.Image:
        """Create a simple icon image"""
        # Create a 64x64 image with a shield icon
        width = 64
        height = 64
        
        # Create image
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw shield shape
        shield_color = (0, 120, 215, 255)  # Windows blue
        
        # Shield points
        shield_points = [
            (width//2, height//8),      # Top center
            (width*7//8, height//4),     # Top right
            (width*7//8, height*5//8),   # Right side
            (width//2, height*7//8),     # Bottom point
            (width//8, height*5//8),     # Left side
            (width//8, height//4),       # Top left
            (width//2, height//8)        # Back to top
        ]
        
        # Draw shield
        draw.polygon(shield_points, fill=shield_color, outline=(0, 0, 0, 255))
        
        # Draw lock symbol in center
        lock_color = (255, 255, 255, 255)
        
        # Lock body
        draw.rectangle(
            [width*3//8, height*3//8, width*5//8, height*5//8],
            fill=lock_color
        )
        
        # Lock shackle
        draw.arc(
            [width*3//8, height*2//8, width*5//8, height*4//8],
            start=180, end=0,
            fill=lock_color, width=3
        )
        
        return image
    
    def _create_menu(self):
        """Create tray icon menu"""
        return pystray.Menu(
            pystray.MenuItem("Personal Security", self._show_status, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Status", self._show_status),
            pystray.MenuItem("Test Camera", self._test_camera),
            pystray.MenuItem("Test Protection", self._test_protection),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Screen Guard",
                pystray.Menu(
                    pystray.MenuItem("Enable", self._enable_screen_guard, 
                                   checked=lambda item: self._is_screen_guard_enabled()),
                    pystray.MenuItem("Disable", self._disable_screen_guard,
                                   checked=lambda item: not self._is_screen_guard_enabled()),
                )
            ),
            pystray.MenuItem(
                "Intruder Monitor", 
                pystray.Menu(
                    pystray.MenuItem("Enable", self._enable_intruder_monitor,
                                   checked=lambda item: self._is_intruder_monitor_enabled()),
                    pystray.MenuItem("Disable", self._disable_intruder_monitor,
                                   checked=lambda item: not self._is_intruder_monitor_enabled()),
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View Logs", self._open_logs),
            pystray.MenuItem("Settings", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._quit_app)
        )
    
    def run(self):
        """Start the system tray icon"""
        if not TRAY_AVAILABLE:
            return
        
        try:
            # Create icon
            self.icon = pystray.Icon(
                "PersonalSecurity",
                self.icon_image,
                "Personal Security - Active",
                self.menu_items
            )
            
            # Run icon
            self.running = True
            self.icon.run()
            
        except Exception as e:
            logger.error(f"Error running tray icon: {e}")
    
    def stop(self):
        """Stop the system tray icon"""
        self.running = False
        if self.icon:
            self.icon.stop()
    
    def _show_status(self, icon, item):
        """Show application status"""
        try:
            # Get status from modules
            screen_status = self.app.screen_guard.get_status()
            camera_info = self.app.camera_manager.get_camera_info()
            
            status_msg = (
                f"Personal Security Status\n"
                f"========================\n"
                f"Camera: {camera_info.get('status', 'Unknown')}\n"
                f"Screen Guard: {'Active' if screen_status['running'] else 'Inactive'}\n"
                f"Known Faces: {len(screen_status['known_faces'])}\n"
                f"Unauthorized Detections: {screen_status['unauthorized_count']}\n"
            )
            
            self._show_notification("Security Status", status_msg)
            
        except Exception as e:
            logger.error(f"Error showing status: {e}")
    
    def _test_camera(self, icon, item):
        """Test camera functionality"""
        self._show_notification("Camera Test", "Testing camera...")
        
        def test():
            frame = self.app.camera_manager.capture_frame()
            if frame is not None:
                self._show_notification("Camera Test", "✓ Camera working properly")
            else:
                self._show_notification("Camera Test", "✗ Camera test failed")
        
        threading.Thread(target=test, daemon=True).start()
    
    def _test_protection(self, icon, item):
        """Test protection mechanisms"""
        self._show_notification("Protection Test", "Testing screen protection...")
        
        def test():
            self.app.screen_guard.test_protection()
            self._show_notification("Protection Test", "Protection test completed")
        
        threading.Thread(target=test, daemon=True).start()
    
    def _is_screen_guard_enabled(self) -> bool:
        """Check if screen guard is enabled"""
        try:
            return self.app.screen_guard.enabled and self.app.screen_guard.is_running
        except:
            return False
    
    def _enable_screen_guard(self, icon, item):
        """Enable screen guard"""
        self.app.screen_guard.enabled = True
        if not self.app.screen_guard.is_running:
            self.app.screen_guard.start()
        self._show_notification("Screen Guard", "Screen Guard enabled")
        
        # Update icon menu
        icon.update_menu()
    
    def _disable_screen_guard(self, icon, item):
        """Disable screen guard"""
        self.app.screen_guard.stop()
        self.app.screen_guard.enabled = False
        self._show_notification("Screen Guard", "Screen Guard disabled")
        
        # Update icon menu
        icon.update_menu()
    
    def _is_intruder_monitor_enabled(self) -> bool:
        """Check if intruder monitor is enabled"""
        try:
            return self.app.intruder_monitor.monitor_enabled and self.app.intruder_monitor.is_monitoring
        except:
            return False
    
    def _enable_intruder_monitor(self, icon, item):
        """Enable intruder monitor"""
        self.app.intruder_monitor.monitor_enabled = True
        if not self.app.intruder_monitor.is_monitoring:
            self.app.intruder_monitor.start()
        self._show_notification("Intruder Monitor", "Intruder Monitor enabled")
        
        # Update icon menu
        icon.update_menu()
    
    def _disable_intruder_monitor(self, icon, item):
        """Disable intruder monitor"""
        self.app.intruder_monitor.stop()
        self.app.intruder_monitor.monitor_enabled = False
        self._show_notification("Intruder Monitor", "Intruder Monitor disabled")
        
        # Update icon menu
        icon.update_menu()
    
    def _open_logs(self, icon, item):
        """Open logs folder"""
        import os
        log_dir = Path("data/logs").absolute()
        os.startfile(str(log_dir))
    
    def _open_settings(self, icon, item):
        """Open settings file"""
        import os
        config_file = Path("config/config.yaml").absolute()
        os.startfile(str(config_file))
    
    def _quit_app(self, icon, item):
        """Quit the application"""
        self._show_notification("Personal Security", "Shutting down...")
        
        # Stop the app
        self.app.stop()
        
        # Stop the icon
        self.stop()
        
        # Exit
        sys.exit(0)
    
    def _show_notification(self, title: str, message: str):
        """Show Windows notification"""
        try:
            if self.icon:
                self.icon.notify(message, title)
            else:
                # Fallback to Windows API
                win32api.MessageBox(0, message, title, win32con.MB_OK | win32con.MB_ICONINFORMATION)
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def update_tooltip(self, text: str):
        """Update icon tooltip"""
        if self.icon:
            self.icon.title = text