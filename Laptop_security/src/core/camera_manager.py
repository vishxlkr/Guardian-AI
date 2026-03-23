"""
Camera Manager - Handles webcam operations with Windows optimizations
"""

import cv2
import threading
import queue
import time
import numpy as np
from typing import Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CameraManager:
    """Manages camera operations with thread-safe capture"""
    
    def __init__(self, device_id: int = 0, buffer_size: int = 2):
        self.device_id = device_id
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.is_running = False
        self.capture_thread = None
        self._lock = threading.Lock()
        
        # Camera settings
        self.resolution = (640, 480)
        self.fps = 30
        
        # Performance metrics
        self.fps_actual = 0
        self.frame_count = 0
        self.last_fps_update = time.time()
        
        # Initialize camera
        self._init_camera()
    
    def _init_camera(self):
        """Initialize camera with Windows-specific optimizations"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Initializing camera (attempt {attempt + 1}/{max_retries})...")
                
                # Use DirectShow on Windows for better performance
                self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW)
                
                if not self.cap.isOpened():
                    # Fallback to default backend
                    self.cap = cv2.VideoCapture(self.device_id)
                
                if self.cap.isOpened():
                    # Configure camera properties
                    self._configure_camera()
                    
                    # Start capture thread
                    self.is_running = True
                    self.capture_thread = threading.Thread(
                        target=self._capture_loop, 
                        daemon=True,
                        name="CameraCapture"
                    )
                    self.capture_thread.start()
                    
                    logger.info("Camera initialized successfully")
                    return
                    
            except Exception as e:
                logger.error(f"Camera initialization error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        raise RuntimeError("Failed to initialize camera after all retries")
    
    def _configure_camera(self):
        """Configure camera settings for optimal performance"""
        if not self.cap:
            return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        # Set FPS
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Windows-specific optimizations
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer latency
        
        # Log actual camera settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        logger.info(f"Camera settings: {actual_width}x{actual_height} @ {actual_fps} FPS")
    
    def _capture_loop(self):
        """Continuous capture loop running in separate thread"""
        logger.info("Camera capture thread started")
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Update FPS metrics
                    self._update_fps()
                    
                    # Clear old frames from queue
                    while not self.frame_queue.empty():
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            break
                    
                    # Add new frame
                    self.frame_queue.put(frame)
                else:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)  # Brief pause on error
                    
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                time.sleep(0.1)
        
        logger.info("Camera capture thread stopped")
    
    def capture_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get the latest captured frame"""
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return frame.copy()  # Return copy to avoid modifications
        except queue.Empty:
            logger.warning("No frame available in queue")
            return None
    
    def capture_multiple_frames(self, count: int = 5, 
                              interval: float = 0.1) -> List[np.ndarray]:
        """Capture multiple frames with specified interval"""
        frames = []
        
        for i in range(count):
            frame = self.capture_frame()
            if frame is not None:
                frames.append(frame)
            
            if i < count - 1:
                time.sleep(interval)
        
        return frames
    
    def save_frame(self, frame: np.ndarray, filepath: str) -> bool:
        """Save frame to file"""
        try:
            cv2.imwrite(filepath, frame)
            return True
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return False
    
    def get_camera_info(self) -> dict:
        """Get camera information and status"""
        if not self.cap or not self.cap.isOpened():
            return {"status": "disconnected"}
        
        return {
            "status": "connected",
            "device_id": self.device_id,
            "resolution": {
                "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            },
            "fps_configured": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "fps_actual": round(self.fps_actual, 1),
            "backend": self.cap.getBackendName(),
            "frame_count": self.frame_count
        }
    
    def _update_fps(self):
        """Update FPS calculation"""
        self.frame_count += 1
        
        current_time = time.time()
        elapsed = current_time - self.last_fps_update
        
        if elapsed >= 1.0:  # Update FPS every second
            self.fps_actual = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_update = current_time
    
    def release(self):
        """Release camera resources"""
        logger.info("Releasing camera resources...")
        
        # Stop capture thread
        self.is_running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        # Release camera
        with self._lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        
        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()   # get_nowait() to remove items without blocking
            except queue.Empty:
                break          # queue.Empty exception that might occur if the queue becomes empty between the check and the get operation (race condition)
        
        logger.info("Camera resources released")
    
    def restart(self):
        """Restart camera connection"""
        logger.info("Restarting camera...")
        self.release()
        time.sleep(0.5)
        self._init_camera()
    
    def is_available(self) -> bool:
        """Check if camera is available and working"""
        return self.cap is not None and self.cap.isOpened() and self.is_running
    
    def adjust_brightness(self, frame: np.ndarray, value: int = 30) -> np.ndarray:
        """Adjust frame brightness"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + value, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    def detect_motion(self, frame1: np.ndarray, frame2: np.ndarray, 
                     threshold: int = 25) -> Tuple[bool, np.ndarray]:
        """Detect motion between two frames"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) #Why grayscale? Motion detection focuses on brightness changes, not color changes
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        #  A grayscale image where brighter pixels indicate more change
        # Frame1 pixel: 100    Frame2 pixel: 150    Difference: |100-150| = 50
        # Frame1 pixel: 200    Frame2 pixel: 195    Difference: |200-195| = 5
        
        # Calculate difference
        diff = cv2.absdiff(gray1, gray2)
        
        # Threshold
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

        '''
           What is Threshold and Its Role?
            The threshold is a crucial parameter that determines the sensitivity of motion detection:
              Threshold Value Explanation:

               Low threshold (e.g., 10-20): Very sensitive

                   Detects even small movements
                     May trigger on noise, shadows, or lighting changes
                        More false positives


                      High threshold (e.g., 50-100): Less sensitive

                         Only detects significant movements
                            Ignores minor changes and noise
                          May miss subtle movements


                       Default threshold (25): Balanced sensitivity

                       Good for typical indoor/outdoor scenarios
                       Filters out most noise while detecting real motion


                       Difference Image:    After Threshold (25):
                       [5, 10, 30, 60] →   [0, 0, 255, 255]
                       [15, 45, 8, 70] →   [0, 255, 0, 255]

                        White areas = Motion detected
                        Black areas = No significant motion
        '''
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        '''
           Finds connected white regions in the binary image
           Each contour represents a potential moving object
           RETR_EXTERNAL: Only finds outer contours (ignores holes)
           CHAIN_APPROX_SIMPLE: Compresses contours to save memory
        '''
        
        # Check for significant motion
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Minimum area threshold
                motion_detected = True
                break
        
        return motion_detected, thresh
    
    @staticmethod
    def list_available_cameras() -> List[int]:
        """List all available camera devices"""
        available_cameras = []
        
        # Check first 10 indexes
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        
        return available_cameras
    
    def __del__(self):
        """Cleanup on deletion"""
        self.release()