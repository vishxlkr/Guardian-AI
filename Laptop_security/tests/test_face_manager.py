"""
Unit tests for Face Manager component
"""

import unittest
import tempfile
import shutil
import numpy as np
import cv2
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.face_manager import FaceManager

class TestFaceManager(unittest.TestCase):
    """Test cases for FaceManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.authorized_dir = Path(self.test_dir) / "authorized"
        self.authorized_dir.mkdir()
        
        # Initialize FaceManager with test directory
        self.face_manager = FaceManager(str(self.authorized_dir))
        
        # Create test image with a face (simple rectangle for testing)
        self.test_image = self._create_test_face_image()
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def _create_test_face_image(self) -> np.ndarray:
        """Create a simple test image"""
        # Create a blank image
        image = np.ones((480, 640, 3), dtype=np.uint8) * 255
        
        # Draw a simple face-like rectangle
        # This won't be detected as a real face, but good for testing image handling
        cv2.rectangle(image, (200, 150), (440, 350), (100, 100, 100), -1)
        cv2.circle(image, (270, 220), 20, (50, 50, 50), -1)  # Left eye
        cv2.circle(image, (370, 220), 20, (50, 50, 50), -1)  # Right eye
        cv2.ellipse(image, (320, 300), (60, 30), 0, 0, 180, (50, 50, 50), 2)  # Mouth
        
        return image
    
    def test_initialization(self):
        """Test FaceManager initialization"""
        self.assertIsInstance(self.face_manager, FaceManager)
        self.assertEqual(self.face_manager.authorized_faces_dir, self.authorized_dir)
        self.assertIsInstance(self.face_manager.known_face_encodings, list)
        self.assertIsInstance(self.face_manager.known_face_names, list)
    
    def test_load_authorized_faces_empty(self):
        """Test loading when no authorized faces exist"""
        self.face_manager.load_authorized_faces()
        self.assertEqual(len(self.face_manager.known_face_encodings), 0)
        self.assertEqual(len(self.face_manager.known_face_names), 0)
    
    def test_add_authorized_face_invalid_image(self):
        """Test adding face with invalid image path"""
        result = self.face_manager.add_authorized_face("test_user", "nonexistent.jpg")
        self.assertFalse(result)
    
    def test_list_authorized_faces(self):
        """Test listing authorized faces"""
        # Initially empty
        faces = self.face_manager.list_authorized_faces()
        self.assertEqual(len(faces), 0)
        
        # Add a test face manually
        self.face_manager.known_face_names.append("test_user")
        self.face_manager.known_face_encodings.append(np.zeros(128))  # Dummy encoding
        
        faces = self.face_manager.list_authorized_faces()
        self.assertEqual(len(faces), 1)
        self.assertIn("test_user", faces)
    
    def test_remove_authorized_face(self):
        """Test removing authorized face"""
        # Add a test face
        self.face_manager.known_face_names.append("test_user")
        self.face_manager.known_face_encodings.append(np.zeros(128))
        
        # Remove it
        result = self.face_manager.remove_authorized_face("test_user")
        self.assertTrue(result)
        self.assertEqual(len(self.face_manager.known_face_names), 0)
        
        # Try removing non-existent face
        result = self.face_manager.remove_authorized_face("nonexistent")
        self.assertFalse(result)
    
    def test_get_face_info(self):
        """Test getting face metadata"""
        # Add metadata
        self.face_manager.face_metadata["test_user"] = {
            'file': 'test_user.jpg',
            'added': '2024-01-01T10:00:00'
        }
        
        info = self.face_manager.get_face_info("test_user")
        self.assertIsNotNone(info)
        self.assertEqual(info['file'], 'test_user.jpg')
        
        # Non-existent user
        info = self.face_manager.get_face_info("nonexistent")
        self.assertIsNone(info)
    
    def test_recognize_faces_no_faces(self):
        """Test face recognition with no known faces"""
        # Create a simple test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        faces = self.face_manager.recognize_faces(frame)
        self.assertIsInstance(faces, list)
        # Should detect no faces in blank image
        self.assertEqual(len(faces), 0)
    
    def test_cache_operations(self):
        """Test cache save and load operations"""
        # Add test data
        self.face_manager.known_face_names = ["user1", "user2"]
        self.face_manager.known_face_encodings = [np.zeros(128), np.ones(128)]
        
        # Save to cache
        self.face_manager._save_to_cache()
        self.assertTrue(self.face_manager._encodings_cache_file.exists())
        
        # Clear data
        self.face_manager.known_face_names = []
        self.face_manager.known_face_encodings = []
        
        # Load from cache
        result = self.face_manager._load_from_cache()
        self.assertTrue(result)
        self.assertEqual(len(self.face_manager.known_face_names), 2)
        self.assertIn("user1", self.face_manager.known_face_names)
        self.assertIn("user2", self.face_manager.known_face_names)
    
    def test_verify_face(self):
        """Test face verification"""
        # Add a known face
        test_encoding = np.random.rand(128)
        self.face_manager.known_face_names.append("test_user")
        self.face_manager.known_face_encodings.append(test_encoding)
        
        # Verify with same encoding (should match)
        is_match, distance = self.face_manager.verify_face(test_encoding, "test_user")
        self.assertTrue(is_match)
        self.assertLess(distance, 0.1)  # Should be very close
        
        # Verify with different encoding (should not match)
        different_encoding = np.random.rand(128)
        is_match, distance = self.face_manager.verify_face(different_encoding, "test_user")
        self.assertFalse(is_match)
        self.assertGreater(distance, 0.6)
        
        # Verify non-existent user
        is_match, distance = self.face_manager.verify_face(test_encoding, "nonexistent")
        self.assertFalse(is_match)
        self.assertEqual(distance, 1.0)
    
    def test_find_similar_faces(self):
        """Test finding similar faces"""
        # Add multiple known faces
        base_encoding = np.random.rand(128)
        similar_encoding = base_encoding + np.random.rand(128) * 0.1  # Small variation
        different_encoding = np.random.rand(128)
        
        self.face_manager.known_face_names = ["user1", "user2", "user3"]
        self.face_manager.known_face_encodings = [
            base_encoding, similar_encoding, different_encoding
        ]
        
        # Find similar faces
        similar_faces = self.face_manager.find_similar_faces(base_encoding, threshold=0.6)
        
        self.assertGreaterEqual(len(similar_faces), 2)  # Should find user1 and user2
        self.assertEqual(similar_faces[0][0], "user1")  # First should be exact match
        self.assertLess(similar_faces[0][1], 0.1)  # Very small distance
    
    def test_thread_safety(self):
        """Test thread safety of face manager operations"""
        import threading
        
        def add_faces():
            for i in range(10):
                self.face_manager.known_face_names.append(f"user_{i}")
                self.face_manager.known_face_encodings.append(np.random.rand(128))
        
        def remove_faces():
            for i in range(5):
                if f"user_{i}" in self.face_manager.known_face_names:
                    self.face_manager.remove_authorized_face(f"user_{i}")
        
        # Run operations in parallel
        threads = []
        for _ in range(3):
            t1 = threading.Thread(target=add_faces)
            t2 = threading.Thread(target=remove_faces)
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        self.assertIsInstance(self.face_manager.known_face_names, list)

if __name__ == '__main__':
    unittest.main()