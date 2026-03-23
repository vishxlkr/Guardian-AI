"""
Screen Guard - Real-time face detection and screen protection
"""

import threading
import time
import logging
from typing import List, Dict, Tuple
from datetime import datetime
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class ScreenGuard:
    """Monitors for unauthorized faces and protects screen content"""
    
    def __init__(self, face_manager, camera_manager, screen_manager, config_manager):
        self.face_manager = face_manager
        self.camera = camera_manager
        self.screen = screen_manager
        self.config = config_manager
        
        # Settings
        self.enabled = self.config.get('screen_guard.enabled', True)
        self.check_interval = self.config.get('screen_guard.check_interval', 0.5)
        self.unknown_face_action = self.config.get('screen_guard.unknown_face_action', 'blur')
        
        # Thread control
        self.is_running = False
        self.monitor_thread = None
        
        # Plugin manager (set later)
        self.plugin_manager = None
        
        # Face tracking
        self.face_history = []
        self.max_history = 10
        self.last_known_faces = set()
        self.unauthorized_face_timer = {}
        
        # Performance metrics
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.average_processing_time = 0
    
    def set_plugin_manager(self, plugin_manager):
        """Set the plugin manager for notifications"""
        self.plugin_manager = plugin_manager
    
    def start(self):
        """Start screen monitoring"""
        if not self.enabled:
            logger.info("Screen guard is disabled")
            return
        
        if not self.camera.is_available():
            logger.error("Camera not available for screen guard")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ScreenGuard"
        )
        self.monitor_thread.start()
        logger.info("Screen guard started")
    
    def stop(self):
        """Stop screen monitoring"""
        self.is_running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # Clear any active overlays
        self.screen.clear_overlays()
        
        logger.info("Screen guard stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Screen guard monitoring active")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Capture frame
                frame = self.camera.capture_frame(timeout=0.5)
                
                if frame is not None:
                    # Process frame
                    self._process_frame(frame)
                    consecutive_errors = 0
                else:
                    logger.warning("No frame captured")
                    consecutive_errors += 1
                
                # Calculate processing time
                processing_time = time.time() - start_time
                self._update_performance_metrics(processing_time)
                
                # Dynamic sleep to maintain target FPS
                sleep_time = max(0, self.check_interval - processing_time)
                time.sleep(sleep_time)
                
                # Check for too many errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, restarting camera")
                    self.camera.restart()
                    consecutive_errors = 0
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def _process_frame(self, frame: np.ndarray):
        """Process a single frame for face detection"""
        # Detect faces
        face_data = self.face_manager.recognize_faces(frame)
        
        # Update face history
        self._update_face_history(face_data)
        
        # Check for unauthorized faces
        unauthorized_faces = self._check_unauthorized_faces(face_data)
        
        if unauthorized_faces:
            # Log warning
            logger.warning(f"Detected {len(unauthorized_faces)} unauthorized face(s)")
            
            # Take protective action
            self._take_protective_action(unauthorized_faces, frame)
            
            # Notify plugins
            if self.plugin_manager:
                for name, location in unauthorized_faces:
                    self.plugin_manager.trigger_unauthorized_access({
                        'name': name,
                        'location': location,
                        'timestamp': datetime.now().isoformat(),
                        'action_taken': self.unknown_face_action
                    })
        else:
            # Clear overlays if no threats
            if not self._has_recent_threats():
                self.screen.clear_overlays()
    
    def _update_face_history(self, face_data: List[Tuple[str, Tuple]]):
        """Update face detection history"""
        # Add current detection to history
        self.face_history.append({
            'timestamp': time.time(),
            'faces': face_data
        })
        
        # Keep only recent history
        if len(self.face_history) > self.max_history:
            self.face_history.pop(0)
        
        # Update known faces set
        current_known = {name for name, _ in face_data if name != "Unknown"}
        self.last_known_faces = current_known
    
    def _check_unauthorized_faces(self, face_data: List[Tuple[str, Tuple]]) -> List[Tuple[str, Tuple]]:
        """Check for unauthorized faces in the frame"""
        unauthorized = []
        current_time = time.time()
        
        for name, location in face_data:
            if name == "Unknown":
                # Track how long unknown face has been present
                face_key = f"unknown_{location}"
                
                if face_key not in self.unauthorized_face_timer:
                    self.unauthorized_face_timer[face_key] = current_time
                
                # Consider unauthorized if present for more than 1 second
                if current_time - self.unauthorized_face_timer[face_key] > 1.0:
                    unauthorized.append((name, location))
            else:
                # Known face - could still check if multiple people
                if self.config.get('security.alert_on_multiple_faces', True):
                    if len(self.last_known_faces) > 1 and name not in self.last_known_faces:
                        unauthorized.append((f"Additional:{name}", location))
        
        # Clean up old timers
        self._cleanup_face_timers(face_data)
        
        return unauthorized
    
    def _cleanup_face_timers(self, current_faces: List[Tuple[str, Tuple]]):
        """Clean up face timers for faces no longer present"""
        current_keys = {f"unknown_{location}" for name, location in current_faces if name == "Unknown"}
        
        # Remove timers for faces no longer detected
        for key in list(self.unauthorized_face_timer.keys()):
            if key not in current_keys:
                del self.unauthorized_face_timer[key]
    
    def _take_protective_action(self, unauthorized_faces: List[Tuple[str, Tuple]], frame: np.ndarray):
        """Take protective action based on configuration"""
        action = self.unknown_face_action
        
        if action == "blur":
            # Blur screen areas around unauthorized faces
            face_locations = [location for _, location in unauthorized_faces]
            self.screen.blur_face_regions(face_locations)
            
        elif action == "black":
            # Show black screen
            self.screen.show_black_screen(duration=2.0)
            
        elif action == "minimize":
            # Minimize all windows
            self.screen.minimize_all_windows()
            
        elif action == "lock":
            # Lock the screen
            self.screen.lock_screen()
            
        # Save evidence
        self._save_security_event(unauthorized_faces, frame)
    
    def _save_security_event(self, unauthorized_faces: List[Tuple[str, Tuple]], frame: np.ndarray):
        """Save security event for later review"""
        try:
            timestamp = datetime.now()
            event_dir = self.config.get('storage.intruder_images_dir', 'data\\images\\intruders')
            
            # Annotate frame
            annotated = frame.copy()
            for name, (top, right, bottom, left) in unauthorized_faces:
                # Draw red rectangle
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 0, 255), 3)
                
                # Add label
                label = f"UNAUTHORIZED: {name}"
                cv2.putText(annotated, label,
                           (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.7, (0, 0, 255), 2)
            
            # Save image
            filename = f"screen_guard_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = Path(event_dir) / filename
            cv2.imwrite(str(filepath), annotated)
            
            logger.info(f"Security event saved: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving security event: {e}")
    
    def _has_recent_threats(self) -> bool:
        """Check if there have been recent unauthorized faces"""
        if not self.unauthorized_face_timer:
            return False
        
        current_time = time.time()
        
        # Check if any unauthorized face was seen in last 5 seconds
        for last_seen in self.unauthorized_face_timer.values():
            if current_time - last_seen < 5.0:
                return True
        
        return False
    
    def _update_performance_metrics(self, processing_time: float):
        """Update performance metrics"""
        # Update FPS counter
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.last_fps_time >= 1.0:
            fps = self.fps_counter / (current_time - self.last_fps_time)
            self.fps_counter = 0
            self.last_fps_time = current_time
            
            # Update average processing time
            alpha = 0.1  # Smoothing factor
            self.average_processing_time = (alpha * processing_time + 
                                          (1 - alpha) * self.average_processing_time)
            
            # Log performance metrics periodically
            if int(current_time) % 30 == 0:  # Every 30 seconds
                logger.debug(f"Screen Guard Performance - FPS: {fps:.1f}, "
                           f"Avg Processing: {self.average_processing_time*1000:.1f}ms")
    
    def get_status(self) -> Dict:
        """Get current status of screen guard"""
        return {
            'enabled': self.enabled,
            'running': self.is_running,
            'check_interval': self.check_interval,
            'action': self.unknown_face_action,
            'known_faces': list(self.last_known_faces),
            'unauthorized_count': len(self.unauthorized_face_timer),
            'performance': {
                'average_processing_ms': round(self.average_processing_time * 1000, 1),
                'face_history_size': len(self.face_history)
            }
        }
    
    def test_protection(self):
        """Test protection mechanisms"""
        logger.info("Testing screen protection...")
        
        # Test blur
        self.screen.blur_face_regions([(100, 300, 300, 100)])
        time.sleep(2)
        
        # Test black screen
        self.screen.show_black_screen(1)
        time.sleep(1.5)
        
        logger.info("Protection test complete")