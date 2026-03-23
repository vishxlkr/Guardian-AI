"""
Intruder Monitor - Monitors Windows for failed login attempts and captures intruders
"""

import cv2
import datetime
from pathlib import Path
import platform
import threading
import time
import win32evtlog
import win32evtlogutil
import win32con
import win32security
import pywintypes
from typing import Optional, Dict, Any,List,Tuple
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

class IntruderMonitor:
    """Monitors system for security breaches and captures intruder images"""
    
    def __init__(self, config_manager, camera_manager, face_manager):
        self.config = config_manager
        self.camera = camera_manager
        self.face_manager = face_manager
        
        # Directories
        self.intruder_dir = Path(self.config.get('storage.intruder_images_dir', 
                                                'data\\images\\intruders'))
        self.intruder_dir.mkdir(parents=True, exist_ok=True)
        
        # Monitoring settings
        self.monitor_enabled = self.config.get('intruder_monitor.enabled', True)
        self.capture_on_failed = self.config.get('intruder_monitor.capture_on_failed_login', True)
        self.check_interval = self.config.get('windows.event_log_monitoring.check_interval', 5)
        
        # Thread control
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_event_time = datetime.datetime.now()
        
        # Plugin manager (set later)
        self.plugin_manager = None
        
        # Failed login tracking
        self.failed_attempts = {}
        self.max_attempts = self.config.get('intruder_monitor.max_failed_attempts', 3)
        self.lockout_duration = self.config.get('intruder_monitor.lockout_duration', 300)
    
    def set_plugin_manager(self, plugin_manager):
        """Set the plugin manager for notifications"""
        self.plugin_manager = plugin_manager
    
    def start(self):
        """Start monitoring for intrusions"""
        if not self.monitor_enabled:
            logger.info("Intruder monitoring is disabled")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="IntruderMonitor"
        )
        self.monitor_thread.start()
        logger.info("Intruder monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Intruder monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop for Windows events"""
        logger.info("Starting Windows event log monitoring...")
        
        while self.is_monitoring:
            try:
                # Monitor Windows Security Event Log
                self._check_windows_events()
                
                # Clean up old failed attempts
                self._cleanup_failed_attempts()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(10)  # Longer pause on error
    
    def _check_windows_events(self):
        """Check Windows Event Log for security events"""
        try:
            server = 'localhost'
            log_type = 'Security'
            
            # Open event log
            hand = win32evtlog.OpenEventLog(server, log_type)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            # Read recent events
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            for event in events:
                # Check if event is newer than last check
                event_time = event.TimeGenerated
                if event_time <= self.last_event_time:
                    continue
                
                # Event ID 4625: Failed login attempt
                if event.EventID == 4625:
                    self._handle_failed_login(event)
                
                # Event ID 4800: Workstation locked
                elif event.EventID == 4800:
                    logger.info("Workstation locked")
                
                # Event ID 4801: Workstation unlocked
                elif event.EventID == 4801:
                    logger.info("Workstation unlocked")
            
            # Update last check time
            self.last_event_time = datetime.datetime.now()
            
            # Close event log
            win32evtlog.CloseEventLog(hand)
            
        except Exception as e:
            logger.error(f"Error reading Windows events: {e}")
    
    def _handle_failed_login(self, event):
        """Handle failed login attempt"""
        try:
            # Extract event details
            event_data = self._parse_event_data(event)
            username = event_data.get('username', 'Unknown')
            ip_address = event_data.get('ip_address', 'Local')
            
            logger.warning(f"Failed login attempt - User: {username}, IP: {ip_address}")
            
            # Track failed attempts
            key = f"{username}_{ip_address}"
            current_time = time.time()
            
            if key not in self.failed_attempts:
                self.failed_attempts[key] = []
            
            self.failed_attempts[key].append(current_time)
            
            # Check if threshold exceeded
            recent_attempts = [t for t in self.failed_attempts[key] 
                             if current_time - t < self.lockout_duration]
            
            if len(recent_attempts) >= self.max_attempts:
                logger.error(f"Multiple failed login attempts from {username} at {ip_address}")
                
                # Capture intruder with enhanced info
                self.capture_intruder(
                    reason="multiple_failed_logins",
                    metadata={
                        'username': username,
                        'ip_address': ip_address,
                        'attempt_count': len(recent_attempts),
                        'event_time': event.TimeGenerated.isoformat()
                    }
                )
            else:
                # Single failed attempt
                self.capture_intruder(
                    reason="failed_login",
                    metadata={
                        'username': username,
                        'ip_address': ip_address,
                        'event_time': event.TimeGenerated.isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error handling failed login: {e}")
    
    def _parse_event_data(self, event) -> Dict[str, Any]:
        """Parse Windows event data"""
        data = {}
        
        try:
            # Get string inserts from event
            strings = event.StringInserts
            
            if strings and len(strings) >= 10:
                data['username'] = strings[5] if strings[5] else 'Unknown'
                data['domain'] = strings[6] if strings[6] else 'Local'
                data['logon_type'] = strings[10] if len(strings) > 10 else 'Unknown'
                data['ip_address'] = strings[19] if len(strings) > 19 else 'Local'
            
        except Exception as e:
            logger.error(f"Error parsing event data: {e}")
        
        return data
    
    def capture_intruder(self, reason: str = "security_breach", 
                        metadata: Optional[Dict] = None) -> Optional[str]:
        """Capture image of potential intruder with metadata"""
        try:
            # Capture frame from camera
            frame = self.camera.capture_frame()
            if frame is None:
                logger.error("Failed to capture frame from camera")
                return None
            
            # Detect faces in frame
            face_data = self.face_manager.recognize_faces(frame)
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now()
            filename = f"intruder_{reason}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.intruder_dir / filename
            
            # Draw face rectangles and labels
            annotated_frame = self._annotate_frame(frame, face_data)
            
            # Save image
            cv2.imwrite(str(filepath), annotated_frame)
            logger.warning(f"Intruder image captured: {filepath}")
            
            # Save metadata
            metadata_file = filepath.with_suffix('.json')
            full_metadata = {
                'timestamp': timestamp.isoformat(),
                'reason': reason,
                'faces_detected': len(face_data),
                'face_identities': [name for name, _ in face_data],
                'camera_info': self.camera.get_camera_info(),
                **(metadata or {})
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(full_metadata, f, indent=2)
            
            # Log intrusion
            self._log_intrusion_attempt(reason, str(filepath), full_metadata)
            
            # Trigger plugin notifications
            if self.plugin_manager:
                self.plugin_manager.trigger_intruder_detected(
                    str(filepath), 
                    timestamp.isoformat()
                )
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to capture intruder: {e}")
            return None
    
    def _annotate_frame(self, frame: np.ndarray, face_data: List) -> np.ndarray:
        """Annotate frame with face detection results"""
        annotated = frame.copy()
        
        for name, (top, right, bottom, left) in face_data:
            # Draw rectangle
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
            
            # Draw label with background
            label = f"{name}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            
            # Background for text
            cv2.rectangle(annotated, 
                         (left, bottom - label_size[1] - 10),
                         (left + label_size[0] + 10, bottom),
                         color, cv2.FILLED)
            
            # Text
            cv2.putText(annotated, label,
                       (left + 5, bottom - 5),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 255), 1)
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, timestamp,
                   (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (255, 255, 255), 2)
        
        return annotated
    
    def _log_intrusion_attempt(self, reason: str, image_path: str, metadata: Dict):
        """Log intrusion attempt to file"""
        log_file = Path(self.config.get('storage.log_dir', 'data\\logs')) / "intrusions.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'reason': reason,
            'image_path': image_path,
            'metadata': metadata
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _cleanup_failed_attempts(self):
        """Clean up old failed login attempts"""
        current_time = time.time()
        
        # Remove old entries
        for key in list(self.failed_attempts.keys()):
            self.failed_attempts[key] = [
                t for t in self.failed_attempts[key]
                if current_time - t < self.lockout_duration
            ]
            
            # Remove empty entries
            if not self.failed_attempts[key]:
                del self.failed_attempts[key]
    
    def get_intrusion_history(self, days: int = 7) -> List[Dict]:
        """Get recent intrusion history"""
        history = []
        log_file = Path(self.config.get('storage.log_dir', 'data\\logs')) / "intrusions.log"
        
        if not log_file.exists():
            return history
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            history.append(entry)
                            
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading intrusion history: {e}")
        
        return history
    
    def cleanup_old_images(self, days: int = None):
        """Clean up old intruder images"""
        if days is None:
            days = self.config.get('storage.retention_days', 30)
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cleaned_count = 0
        
        for image_file in self.intruder_dir.glob("intruder_*.jpg"):
            try:
                # Check file modification time
                mtime = datetime.datetime.fromtimestamp(image_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    # Remove image and metadata
                    image_file.unlink()
                    
                    metadata_file = image_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning up {image_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old intruder images")