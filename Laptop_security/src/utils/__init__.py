"""Utility functions and helpers"""

from .logger import setup_logging, get_logger, security_events
from .system_utils import check_admin_rights, run_as_admin
from .image_utils import resize_image, add_timestamp, highlight_faces
from .tray_icon import TrayIcon

__all__ = [
    'setup_logging',
    'get_logger',
    'security_events',
    'check_admin_rights',
    'run_as_admin',
    'resize_image',
    'add_timestamp',
    'highlight_faces',
    'TrayIcon'
]