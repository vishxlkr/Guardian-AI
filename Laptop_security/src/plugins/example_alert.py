"""
Example Alert Plugin - Demonstrates various alert mechanisms
"""

from src.plugins.base_plugin import BasePlugin
import winsound
import threading
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import json

# Windows-specific imports
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

class ExampleAlertPlugin(BasePlugin):
    """Example plugin that provides various alert mechanisms for security events"""
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Alert settings
        self.sound_alert = config.get('sound_alert', True)
        self.desktop_notification = config.get('desktop_notification', True)
        self.voice_alert = config.get('voice_alert', False)
        self.log_events = config.get('log_events', True)
        
        # Sound settings
        self.beep_frequency = config.get('beep_frequency', 1000)
        self.beep_duration = config.get('beep_duration', 500)
        
        # Initialize TTS engine if available and enabled
        self.tts_engine = None
        if TTS_AVAILABLE and self.voice_alert:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS: {e}")
                self.voice_alert = False
        
        # Event log file
        self.event_log = Path("data/logs/plugin_events.json")
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
    
    def on_intruder_detected(self, image_path: str, timestamp: str):
        """Handle intruder detection event"""
        if not self.enabled:
            return
        
        self.logger.warning(f"Intruder detected! Image: {image_path}")
        
        # Sound alert
        if self.sound_alert:
            self._play_alert_sound(pattern="intruder")
        
        # Desktop notification
        if self.desktop_notification and PLYER_AVAILABLE:
            self._show_notification(
                title="🚨 Security Alert: Intruder Detected",
                message=f"An intruder was captured at {timestamp}\nImage saved: {Path(image_path).name}",
                timeout=10
            )
        
        # Voice alert
        if self.voice_alert and self.tts_engine:
            self._speak("Warning! Intruder detected. Security breach recorded.")
        
        # Log event
        if self.log_events:
            self._log_event({
                'type': 'intruder_detected',
                'timestamp': timestamp,
                'image_path': image_path,
                'alert_methods': self._get_active_alerts()
            })
    
    def on_unauthorized_access(self, face_data: Dict[str, Any]):
        """Handle unauthorized screen access event"""
        if not self.enabled:
            return
        
        self.logger.warning(f"Unauthorized access detected: {face_data.get('name', 'Unknown')}")
        
        # Sound alert (different pattern)
        if self.sound_alert:
            self._play_alert_sound(pattern="unauthorized")
        
        # Desktop notification
        if self.desktop_notification and PLYER_AVAILABLE:
            self._show_notification(
                title="⚠️ Screen Security Alert",
                message=f"Unauthorized person detected looking at screen\nAction taken: {face_data.get('action_taken', 'Unknown')}",
                timeout=5
            )
        
        # Voice alert
        if self.voice_alert and self.tts_engine:
            self._speak("Unauthorized access detected. Screen protection activated.")
        
        # Log event
        if self.log_events:
            self._log_event({
                'type': 'unauthorized_access',
                'timestamp': face_data.get('timestamp', datetime.now().isoformat()),
                'face_name': face_data.get('name', 'Unknown'),
                'location': face_data.get('location'),
                'action_taken': face_data.get('action_taken'),
                'alert_methods': self._get_active_alerts()
            })
    
    def on_system_event(self, event_type: str, data: Dict[str, Any]):
        """Handle generic system events"""
        if not self.enabled:
            return
        
        # Only alert on specific events
        alert_events = ['failed_login', 'system_locked', 'multiple_faces_detected']
        
        if event_type in alert_events:
            self.logger.info(f"System event: {event_type}")
            
            if self.sound_alert:
                self._play_alert_sound(pattern="system")
            
            if self.log_events:
                self._log_event({
                    'type': 'system_event',
                    'event_type': event_type,
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                })
    
    def _play_alert_sound(self, pattern: str = "default"):
        """Play alert sound based on pattern"""
        def play():
            try:
                if pattern == "intruder":
                    # Urgent pattern: 3 beeps
                    for _ in range(3):
                        winsound.Beep(self.beep_frequency, self.beep_duration)
                        winsound.Beep(int(self.beep_frequency * 1.5), self.beep_duration // 2)
                
                elif pattern == "unauthorized":
                    # Warning pattern: 2 beeps
                    winsound.Beep(self.beep_frequency * 2, self.beep_duration // 2)
                    winsound.Beep(self.beep_frequency * 2, self.beep_duration // 2)
                
                elif pattern == "system":
                    # Simple beep
                    winsound.Beep(self.beep_frequency, self.beep_duration // 3)
                
                else:
                    # Default beep
                    winsound.Beep(self.beep_frequency, self.beep_duration)
                    
            except Exception as e:
                self.logger.error(f"Error playing sound: {e}")
        
        # Play in separate thread to avoid blocking
        threading.Thread(target=play, daemon=True).start()
    
    def _show_notification(self, title: str, message: str, timeout: int = 10):
        """Show desktop notification"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Personal Security Software",
                timeout=timeout,
                app_icon=None  # Can add icon path here
            )
        except Exception as e:
            self.logger.error(f"Error showing notification: {e}")
    
    def _speak(self, text: str):
        """Speak text using TTS"""
        if not self.tts_engine:
            return
        
        def speak():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                self.logger.error(f"Error in TTS: {e}")
        
        # Speak in separate thread
        threading.Thread(target=speak, daemon=True).start()
    
    def _log_event(self, event_data: Dict[str, Any]):
        """Log event to file"""
        try:
            # Read existing events
            events = []
            if self.event_log.exists():
                try:
                    with open(self.event_log, 'r') as f:
                        events = json.load(f)
                except:
                    events = []
            
            # Add new event
            events.append(event_data)
            
            # Keep only last 1000 events
            if len(events) > 1000:
                events = events[-1000:]
            
            # Write back
            with open(self.event_log, 'w') as f:
                json.dump(events, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def _get_active_alerts(self) -> list:
        """Get list of active alert methods"""
        active = []
        if self.sound_alert:
            active.append("sound")
        if self.desktop_notification and PLYER_AVAILABLE:
            active.append("desktop_notification")
        if self.voice_alert and self.tts_engine:
            active.append("voice")
        return active
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        info = super().get_info()
        info.update({
            'alert_methods': {
                'sound': self.sound_alert,
                'desktop_notification': self.desktop_notification and PLYER_AVAILABLE,
                'voice': self.voice_alert and TTS_AVAILABLE,
                'logging': self.log_events
            },
            'capabilities': {
                'plyer_available': PLYER_AVAILABLE,
                'tts_available': TTS_AVAILABLE
            }
        })
        return info
    
    def test_alerts(self):
        """Test all alert methods"""
        self.logger.info("Testing all alert methods...")
        
        # Test sound
        if self.sound_alert:
            self._play_alert_sound("intruder")
        
        # Test notification
        if self.desktop_notification and PLYER_AVAILABLE:
            self._show_notification(
                "Test Alert",
                "This is a test of the alert system",
                5
            )
        
        # Test voice
        if self.voice_alert and self.tts_engine:
            self._speak("This is a test of the voice alert system")
        
        self.logger.info("Alert test complete")