"""
Logger Configuration - Setup colored logging with file rotation
"""

import logging
import colorlog
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import sys

def setup_logging(log_level: str = "INFO", log_dir: str = "data\\logs"):
    """Setup application-wide logging configuration"""
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with color
    console_handler = colorlog.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Color formatter for console
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    
    # Plain formatter for file
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        log_path / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Security events handler
    security_handler = TimedRotatingFileHandler(
        log_path / "security.log",
        when='midnight',
        interval=1,
        backupCount=30  # Keep 30 days
    )
    security_handler.setLevel(logging.WARNING)
    security_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    security_handler.setFormatter(security_formatter)
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure security logger
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    # Set third-party library log levels
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup
    root_logger.info("=" * 50)
    root_logger.info("Logging system initialized")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Log directory: {log_path.absolute()}")
    root_logger.info("=" * 50)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)

def get_security_logger() -> logging.Logger:
    """Get the security-specific logger"""
    return logging.getLogger('security')

class SecurityEventLogger:
    """Specialized logger for security events"""
    
    def __init__(self):
        self.logger = get_security_logger()
    
    def log_intrusion(self, event_type: str, details: dict):
        """Log an intrusion event"""
        self.logger.warning(f"INTRUSION: {event_type} - {details}")
    
    def log_failed_auth(self, username: str, source: str):
        """Log failed authentication"""
        self.logger.warning(f"FAILED_AUTH: User={username}, Source={source}")
    
    def log_unauthorized_access(self, face_id: str, location: str):
        """Log unauthorized screen access"""
        self.logger.warning(f"UNAUTHORIZED_ACCESS: Face={face_id}, Location={location}")
    
    def log_system_event(self, event: str, details: dict):
        """Log system security event"""
        self.logger.info(f"SYSTEM_EVENT: {event} - {details}")

# Create global security event logger
security_events = SecurityEventLogger()

def log_exception(logger: logging.Logger, msg: str = "Exception occurred"):
    """Helper to log exceptions with traceback"""
    logger.exception(msg)

def create_module_logger(module_name: str) -> logging.Logger:
    """Create a logger for a specific module with custom settings"""
    logger = logging.getLogger(module_name)
    
    # Module-specific configuration can be added here
    
    return logger