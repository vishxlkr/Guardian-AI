#!/usr/bin/env python3
"""
Personal Security Software - Main Application
Windows implementation with face detection and screen protection
"""

import sys
import signal
import click
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config_manager import ConfigManager
from src.core.face_manager import FaceManager
from src.core.camera_manager import CameraManager
from src.core.screen_manager import ScreenManager
from src.core.plugin_manager import PluginManager
from src.modules.intruder_monitor import IntruderMonitor
from src.modules.screen_guard import ScreenGuard
from src.modules.system_monitor import SystemMonitor

from src.utils.logger import get_logger, setup_logging
from src.utils.system_utils import check_admin_rights, run_as_admin

logger = get_logger(__name__)

class SecurityApplication:
    """Main security application class"""
    
    def __init__(self, config_path: str = "config\\config.yaml"):
        """Initialize the security application"""
        setup_logging()
        logger.info("=" * 50)
        logger.info("Personal Security Software Starting...")
        logger.info("=" * 50)
        
        # Check for admin rights on Windows
        if not check_admin_rights():
            logger.warning("Application requires administrator privileges")
            if click.confirm("Restart with administrator privileges?"):
                run_as_admin()
                sys.exit(0)
        
        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        self.is_running = False
        
        # Initialize core components
        logger.info("Initializing core components...")
        self.camera_manager = CameraManager(
            device_id=self.config_manager.get('camera.device_id', 0)
        )
        self.face_manager = FaceManager(
            authorized_dir=self.config_manager.get('storage.authorized_faces_dir')
        )
        self.screen_manager = ScreenManager(self.config_manager)
        self.plugin_manager = PluginManager(self.config_manager)
        
        # Initialize security modules
        logger.info("Initializing security modules...")
        self.intruder_monitor = IntruderMonitor(
            self.config_manager, 
            self.camera_manager,
            self.face_manager
        )
        self.screen_guard = ScreenGuard(
            self.face_manager, 
            self.camera_manager, 
            self.screen_manager,
            self.config_manager
        )
        
        # Set up plugin manager callbacks
        self.intruder_monitor.set_plugin_manager(self.plugin_manager)
        self.screen_guard.set_plugin_manager(self.plugin_manager)
        
        # Load plugins
        self.plugin_manager.load_plugins()
        
    def start(self):
        """Start all security services"""
        logger.info("Starting security services...")
        self.is_running = True
        
        # Start screen guard
        if self.config_manager.get('screen_guard.enabled', True):
            self.screen_guard.start()
            logger.info(" Screen Guard started")
        
        # Start intruder monitoring
        if self.config_manager.get('intruder_monitor.enabled', True):
            self.intruder_monitor.start()
            logger.info(" Intruder Monitor started")
        
        # Start system tray icon (Windows)
        if self.config_manager.get('windows.minimize_to_tray', True):
            self._start_tray_icon()
        
        logger.info("All services started successfully!")
        logger.info("Press Ctrl+C to stop...")
        
    def stop(self):
        """Stop all security services"""
        logger.info("Stopping security services...")
        self.is_running = False
        
        # Stop modules
        self.screen_guard.stop()
        self.intruder_monitor.stop()
        
        # Cleanup
        self.plugin_manager.cleanup_all()
        self.camera_manager.release()
        
        logger.info("All services stopped")
        
    def _start_tray_icon(self):
        """Start system tray icon (Windows only)"""
        try:
            from src.utils.tray_icon import TrayIcon
            self.tray_icon = TrayIcon(self)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start tray icon: {e}")

# CLI Commands
@click.group()
def cli():
    """Personal Security Software CLI"""
    pass

@cli.command()
@click.option('--config', default='config\\config.yaml', help='Configuration file path')
def run(config):
    """Run the security application"""
    app = SecurityApplication(config)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("\nShutdown signal received")
        app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app.start()
        # Keep the main thread alive
        while app.is_running:
            time.sleep(1)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        app.stop()
        sys.exit(1)

@cli.command()
@click.option('--name', required=True, help='Name of the person')
@click.option('--image', required=True, type=click.Path(exists=True), help='Path to face image')
def add_face(name, image):
    """Add authorized face to the system"""
    setup_logging()
    face_manager = FaceManager()
    success = face_manager.add_authorized_face(name, image)
    if success:
        click.echo(f" Successfully added {name} to authorized faces")
    else:
        click.echo(f" Failed to add {name}. Please check the image and try again")

@cli.command()
def test_camera():
    """Test camera functionality"""
    setup_logging()
    click.echo("Testing camera...")
    camera = CameraManager()
    
    # Test capture
    frame = camera.capture_frame()
    if frame is not None:
        click.echo(" Camera test successful")
        click.echo(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
        
        # Show preview window
        import cv2
        cv2.imshow("Camera Test - Press Q to exit", frame)
        while True:
            frame = camera.capture_frame()
            if frame is not None:
                cv2.imshow("Camera Test - Press Q to exit", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
    else:
        click.echo(" Camera test failed - no frame captured")
    
    camera.release()

@cli.command()
def list_faces():
    """List all authorized faces"""
    setup_logging()
    face_manager = FaceManager()
    faces = face_manager.list_authorized_faces()
    
    if faces:
        click.echo("Authorized faces:")
        for name in faces:
            click.echo(f"  • {name}")
    else:
        click.echo("No authorized faces found")

@cli.command()
@click.option('--name', required=True, help='Name of the person to remove')
def remove_face(name):
    """Remove authorized face"""
    setup_logging()
    face_manager = FaceManager()
    if face_manager.remove_authorized_face(name):
        click.echo(f" Successfully removed {name}")
    else:
        click.echo(f" Face {name} not found")

@cli.command()
def install_service():
    """Install as Windows service"""
    from scripts.install_service import install_service
    install_service()

@cli.command()
def uninstall_service():
    """Uninstall Windows service"""
    from src.utils.service_installer import uninstall_service
    uninstall_service()

if __name__ == '__main__':
    cli()