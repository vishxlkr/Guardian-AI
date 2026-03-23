"""
Unit tests for Screen Guard component
"""

import unittest
import tempfile
import time
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.screen_guard import ScreenGuard
from src.core.face_manager import FaceManager
from src.core.camera_manager import CameraManager
from src.core.screen_manager import ScreenManager
from src.core.config_manager import ConfigManager

class TestScreenGuard(unittest.TestCase):
    """Test cases for ScreenGuard class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock dependencies
        self.mock_face_manager = Mock(spec=FaceManager)
        self.mock_camera_manager = Mock(spec=CameraManager)
        self.mock_screen_manager = Mock(spec=ScreenManager)
        self.mock_config_manager = Mock(spec=ConfigManager)
        
        # Configure mock config manager
        self.mock_config_manager.get.side_effect = self._mock_config_get
        
        # Initialize ScreenGuard
        self.screen_guard = ScreenGuard(
            self.mock_face_manager,
            self.mock_camera_manager,
            self.mock_screen_manager,
            self.mock_config_manager
        )
        
        # Create test frame
        self.test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    def _mock_config_get(self, key, default=None):
        """Mock configuration values"""
        config_values = {
            'screen_guard.enabled': True,
            'screen_guard.check_interval': 0.1,  # Faster for testing
            'screen_guard.unknown_face_action': 'blur',
            'security.alert_on_multiple_faces': True
        }
        return config_values.get(key, default)
    
    def test_initialization(self):
        """Test ScreenGuard initialization"""
        self.assertIsInstance(self.screen_guard, ScreenGuard)
        self.assertTrue(self.screen_guard.enabled)
        self.assertEqual(self.screen_guard.check_interval, 0.1)
        self.assertEqual(self.screen_guard.unknown_face_action, 'blur')
        self.assertFalse(self.screen_guard.is_running)
    
    def test_start_stop(self):
        """Test starting and stopping screen guard"""
        # Configure camera as available
        self.mock_camera_manager.is_available.return_value = True
        
        # Start
        self.screen_guard.start()
        self.assertTrue(self.screen_guard.is_running)
        
        # Let it run briefly
        time.sleep(0.2)
        
        # Stop
        self.screen_guard.stop()
        self.assertFalse(self.screen_guard.is_running)
        
        # Should clear overlays on stop
        self.mock_screen_manager.clear_overlays.assert_called()
    
    def test_start_with_disabled(self):
        """Test starting when disabled"""
        self.screen_guard.enabled = False
        self.screen_guard.start()
        self.assertFalse(self.screen_guard.is_running)
    
    def test_start_without_camera(self):
        """Test starting without available camera"""
        self.mock_camera_manager.is_available.return_value = False
        self.screen_guard.start()
        self.assertFalse(self.screen_guard.is_running)
    
    def test_process_frame_no_faces(self):
        """Test processing frame with no faces detected"""
        # Mock no faces detected
        self.mock_face_manager.recognize_faces.return_value = []
        
        # Process frame
        self.screen_guard._process_frame(self.test_frame)
        
        # Should call face recognition
        self.mock_face_manager.recognize_faces.assert_called_once()
        
        # Should not trigger any protective action
        self.mock_screen_manager.blur_face_regions.assert_not_called()
    
    def test_process_frame_authorized_face(self):
        """Test processing frame with authorized face"""
        # Mock authorized face detected
        self.mock_face_manager.recognize_faces.return_value = [
            ("John", (100, 300, 300, 100))
        ]
        
        # Process frame
        self.screen_guard._process_frame(self.test_frame)
        
        # Should not trigger protective action for authorized face
        self.mock_screen_manager.blur_face_regions.assert_not_called()
    
    def test_process_frame_unauthorized_face(self):
        """Test processing frame with unauthorized face"""
        # Mock unauthorized face detected
        self.mock_face_manager.recognize_faces.return_value = [
            ("Unknown", (100, 300, 300, 100))
        ]
        
        # Process frame multiple times to trigger timer
        for _ in range(15):  # More than 1 second worth at 0.1s interval
            self.screen_guard._process_frame(self.test_frame)
            time.sleep(0.1)
        
        # Should trigger protective action
        self.mock_screen_manager.blur_face_regions.assert_called()
    
    def test_multiple_faces_alert(self):
        """Test alert on multiple faces"""
        # Mock multiple faces detected
        self.mock_face_manager.recognize_faces.return_value = [
            ("John", (100, 300, 300, 100)),
            ("Jane", (350, 550, 550, 350))
        ]
        
        # Add known faces
        self.screen_guard.last_known_faces = {"John"}
        
        # Process frame
        self.screen_guard._process_frame(self.test_frame)
        
        # With alert_on_multiple_faces enabled, should detect additional face
        # Check if unauthorized faces were detected (Jane as additional)
        self.assertEqual(len(self.screen_guard._check_unauthorized_faces(
            self.mock_face_manager.recognize_faces.return_value
        )), 1)
    
    def test_protective_actions(self):
        """Test different protective actions"""
        unauthorized_faces = [("Unknown", (100, 300, 300, 100))]
        
        # Test blur action
        self.screen_guard.unknown_face_action = "blur"
        self.screen_guard._take_protective_action(unauthorized_faces, self.test_frame)
        self.mock_screen_manager.blur_face_regions.assert_called_once()
        
        # Test black screen action
        self.mock_screen_manager.reset_mock()
        self.screen_guard.unknown_face_action = "black"
        self.screen_guard._take_protective_action(unauthorized_faces, self.test_frame)
        self.mock_screen_manager.show_black_screen.assert_called_once()
        
        # Test minimize action
        self.mock_screen_manager.reset_mock()
        self.screen_guard.unknown_face_action = "minimize"
        self.screen_guard._take_protective_action(unauthorized_faces, self.test_frame)
        self.mock_screen_manager.minimize_all_windows.assert_called_once()
        
        # Test lock action
        self.mock_screen_manager.reset_mock()
        self.screen_guard.unknown_face_action = "lock"
        self.screen_guard._take_protective_action(unauthorized_faces, self.test_frame)
        self.mock_screen_manager.lock_screen.assert_called_once()
    
    def test_face_history_update(self):
        """Test face history tracking"""
        face_data = [("John", (100, 300, 300, 100))]
        
        # Update history
        self.screen_guard._update_face_history(face_data)
        
        # Check history
        self.assertEqual(len(self.screen_guard.face_history), 1)
        self.assertEqual(self.screen_guard.face_history[0]['faces'], face_data)
        self.assertIn("John", self.screen_guard.last_known_faces)
        
        # Add more history
        for i in range(15):
            self.screen_guard._update_face_history(face_data)
        
        # Should maintain max history size
        self.assertLessEqual(len(self.screen_guard.face_history), 
                           self.screen_guard.max_history)
    
    def test_face_timer_cleanup(self):
        """Test cleanup of face timers"""
        # Add some face timers
        self.screen_guard.unauthorized_face_timer = {
            "unknown_(100, 300, 300, 100)": time.time() - 10,
            "unknown_(200, 400, 400, 200)": time.time()
        }
        
        # Current faces only include one
        current_faces = [("Unknown", (200, 400, 400, 200))]
        
        # Cleanup
        self.screen_guard._cleanup_face_timers(current_faces)
        
        # Should remove old timer
        self.assertNotIn("unknown_(100, 300, 300, 100)", 
                        self.screen_guard.unauthorized_face_timer)
        self.assertIn("unknown_(200, 400, 400, 200)", 
                     self.screen_guard.unauthorized_face_timer)
    
    def test_plugin_manager_integration(self):
        """Test plugin manager notifications"""
        # Set plugin manager
        mock_plugin_manager = Mock()
        self.screen_guard.set_plugin_manager(mock_plugin_manager)
        
        # Mock unauthorized face
        self.mock_face_manager.recognize_faces.return_value = [
            ("Unknown", (100, 300, 300, 100))
        ]
        
        # Process frame to trigger unauthorized detection
        for _ in range(15):
            self.screen_guard._process_frame(self.test_frame)
            time.sleep(0.1)
        
        # Should trigger plugin notification
        mock_plugin_manager.trigger_unauthorized_access.assert_called()
    
    def test_get_status(self):
        """Test getting screen guard status"""
        status = self.screen_guard.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('enabled', status)
        self.assertIn('running', status)
        self.assertIn('check_interval', status)
        self.assertIn('action', status)
        self.assertIn('known_faces', status)
        self.assertIn('unauthorized_count', status)
        self.assertIn('performance', status)
    
    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        # Process some frames
        for _ in range(10):
            self.screen_guard._update_performance_metrics(0.05)
        
        # Check metrics
        self.assertGreater(self.screen_guard.average_processing_time, 0)
        self.assertLess(self.screen_guard.average_processing_time, 1)
    
    @patch('cv2.imwrite')
    def test_save_security_event(self, mock_imwrite):
        """Test saving security events"""
        unauthorized_faces = [("Unknown", (100, 300, 300, 100))]
        
        # Save event
        self.screen_guard._save_security_event(unauthorized_faces, self.test_frame)
        
        # Should save image
        mock_imwrite.assert_called_once()
        
        # Check file path
        args = mock_imwrite.call_args[0]
        self.assertIn('screen_guard', args[0])
        self.assertTrue(args[0].endswith('.jpg'))
    
    def test_monitor_loop_error_handling(self):
        """Test error handling in monitor loop"""
        # Mock camera to raise exception
        self.mock_camera_manager.capture_frame.side_effect = Exception("Camera error")
        self.mock_camera_manager.is_available.return_value = True
        
        # Start guard
        self.screen_guard.start()
        
        # Let it run briefly
        time.sleep(0.3)
        
        # Should handle error and continue running
        self.assertTrue(self.screen_guard.is_running)
        
        # Stop
        self.screen_guard.stop()
    
    def test_has_recent_threats(self):
        """Test recent threat detection"""
        # No threats
        self.assertFalse(self.screen_guard._has_recent_threats())
        
        # Add old threat
        self.screen_guard.unauthorized_face_timer["old_threat"] = time.time() - 10
        self.assertFalse(self.screen_guard._has_recent_threats())
        
        # Add recent threat
        self.screen_guard.unauthorized_face_timer["new_threat"] = time.time() - 1
        self.assertTrue(self.screen_guard._has_recent_threats())

if __name__ == '__main__':
    unittest.main()