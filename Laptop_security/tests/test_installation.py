"""
Installation Test Script - Verify all components are properly installed
"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("Personal Security Software - Installation Test")
print("=" * 60)
print()

# Track test results
tests_passed = 0
tests_failed = 0

def test_import(module_name: str, package_name: str = None) -> bool:
    """Test if a module can be imported"""
    global tests_passed, tests_failed
    
    if package_name is None:
        package_name = module_name
    
    try:
        __import__(package_name)
        print(f"✓ {module_name}")
        tests_passed += 1
        return True
    except ImportError as e:
        print(f"✗ {module_name} - {str(e)}")
        tests_failed += 1
        return False

def test_version(module_name: str, min_version: str = None) -> bool:
    """Test module version"""
    global tests_passed, tests_failed
    
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'Unknown')
        
        version_ok = True
        if min_version and hasattr(module, '__version__'):
            # Simple version comparison
            version_ok = version >= min_version
        
        if version_ok:
            print(f"✓ {module_name} version {version}")
            tests_passed += 1
        else:
            print(f"✗ {module_name} version {version} (need >= {min_version})")
            tests_failed += 1
            
        return version_ok
    except:
        return False

def test_camera() -> bool:
    """Test camera availability"""
    global tests_passed, tests_failed
    
    try:
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✓ Camera access")
                tests_passed += 1
                return True
        
        print("✗ Camera access - No camera detected")
        tests_failed += 1
        return False
    except Exception as e:
        print(f"✗ Camera access - {str(e)}")
        tests_failed += 1
        return False

def test_admin_rights() -> bool:
    """Test administrator privileges"""
    global tests_passed, tests_failed
    
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            print("✓ Administrator privileges")
            tests_passed += 1
        else:
            print("⚠ Administrator privileges - Not running as admin (some features limited)")
        return is_admin
    except:
        print("✗ Administrator privileges check failed")
        tests_failed += 1
        return False

def test_directories() -> bool:
    """Test required directories exist"""
    global tests_passed, tests_failed
    
    required_dirs = [
        "src/core",
        "src/modules", 
        "src/plugins",
        "src/utils",
        "data/logs",
        "data/images/intruders",
        "data/images/authorized",
        "config"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ Directory: {dir_path}")
            tests_passed += 1
        else:
            print(f"✗ Directory: {dir_path} - Not found")
            tests_failed += 1
            all_exist = False
    
    return all_exist

# Run tests
print("1. Testing Python version...")
python_version = sys.version_info
if python_version >= (3, 8):
    print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    tests_passed += 1
else:
    print(f"✗ Python {python_version.major}.{python_version.minor} (need >= 3.8)")
    tests_failed += 1

print("\n2. Testing core dependencies...")
core_deps = [
    ("OpenCV", "cv2"),
    ("NumPy", "numpy"),
    ("PIL/Pillow", "PIL"),
    ("Face Recognition", "face_recognition"),
    ("dlib", "dlib"),
    ("PyYAML", "yaml"),
    ("MSS", "mss"),
    ("PyAutoGUI", "pyautogui"),
    ("PyWin32", "win32api"),
    ("Colorlog", "colorlog"),
    ("Click", "click")
]

for dep_name, import_name in core_deps:
    test_import(dep_name, import_name)

print("\n3. Testing optional dependencies...")
optional_deps = [
    ("Plyer (Notifications)", "plyer"),
    ("Pyttsx3 (Text-to-Speech)", "pyttsx3"),
    ("Pystray (System Tray)", "pystray"),
    ("WMI", "wmi")
]

for dep_name, import_name in optional_deps:
    test_import(dep_name, import_name)

print("\n4. Testing project structure...")
test_directories()

print("\n5. Testing hardware...")
test_camera()

print("\n6. Testing system permissions...")
test_admin_rights()

print("\n7. Testing local modules...")
# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

local_modules = [
    "src.core.config_manager",
    "src.core.camera_manager",
    "src.core.face_manager",
    "src.core.screen_manager",
    "src.core.plugin_manager",
    "src.modules.intruder_monitor",
    "src.modules.screen_guard",
    "src.utils.logger",
    "src.utils.system_utils",
    "src.plugins.base_plugin"
]

for module in local_modules:
    test_import(module)

# Summary
print("\n" + "=" * 60)
print("INSTALLATION TEST SUMMARY")
print("=" * 60)
print(f"Tests Passed: {tests_passed}")
print(f"Tests Failed: {tests_failed}")
print()

if tests_failed == 0:
    print("✓ All tests passed! Your installation is ready.")
    print("\nNext steps:")
    print("1. Run: python main.py add-face --name 'Your Name' --image 'your_photo.jpg'")
    print("2. Run: python main.py run")
else:
    print("✗ Some tests failed. Please fix the issues above.")
    print("\nCommon solutions:")
    print("1. Install missing packages: pip install -r requirements.txt")
    print("2. Run setup script: setup_windows.bat")
    print("3. Install Visual C++ Redistributable")
    print("4. Run as Administrator for full functionality")

print("\nFor detailed help, see README.md")
print("=" * 60)