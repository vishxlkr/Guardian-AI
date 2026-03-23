"""
Test package for Personal Security Software
"""

import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test configuration
TEST_CONFIG = {
    'camera': {
        'device_id': -1,  # Use mock camera for tests
        'mock_enabled': True
    },
    'face_recognition': {
        'tolerance': 0.6,
        'model': 'hog'
    },
    'logging': {
        'level': 'DEBUG',
        'file': 'test.log'
    }
}