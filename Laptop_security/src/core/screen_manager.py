"""
Screen Manager - Windows screen protection with blur overlays
"""

import tkinter as tk
from tkinter import Canvas
import threading
import time
import mss
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from typing import List, Tuple, Optional
import win32api
import win32con
import win32gui
import win32process
import psutil
from queue import Queue
import logging

logger = logging.getLogger(__name__)

class BlurOverlay:
    """Individual blur overlay window"""
    
    def __init__(self, x: int, y: int, width: int, height: int, 
                 blur_radius: int = 25, opacity: float = 0.8):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.blur_radius = blur_radius
        self.opacity = opacity
        self.window = None
        self.canvas = None
        
    def show(self):
        """Create and show the overlay window"""
        self.window = tk.Toplevel()
        
        # Window configuration
        self.window.attributes('-alpha', self.opacity)
        self.window.attributes('-topmost', True)
        self.window.attributes('-disabled', True)
        self.window.attributes('-transparentcolor', 'black')
        self.window.overrideredirect(True)
        
        # Remove from taskbar
        self.window.wm_attributes('-toolwindow', True)
        
        # Position and size
        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")
        
        # Create canvas
        self.canvas = Canvas(
            self.window, 
            width=self.width, 
            height=self.height,
            highlightthickness=0,
            bg='black'
        )
        self.canvas.pack()
        
        # Capture and blur screen area
        self._apply_blur_effect()
        
        # Make window click-through
        self._make_click_through()
        
    def _apply_blur_effect(self):
        """Capture screen area and apply blur"""
        try:
            # Capture screen area
            with mss.mss() as sct:
                monitor = {
                    "top": self.y,
                    "left": self.x,
                    "width": self.width,
                    "height": self.height
                }
                screenshot = sct.grab(monitor)
                
            # Convert to PIL Image
            img = Image.frombytes(
                "RGB", 
                (screenshot.width, screenshot.height), 
                screenshot.rgb
            )
            
            # Apply Gaussian blur
            blurred = img.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))
            
            # Add dark overlay for privacy
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 100))
            blurred.paste(overlay, (0, 0), overlay)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(blurred)
            
            # Display on canvas
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Add warning text
            self.canvas.create_text(
                self.width // 2,
                self.height // 2,
                text="UNAUTHORIZED\nACCESS\nDETECTED",
                font=("Arial", 24, "bold"),
                fill="red",
                anchor="center"
            )
            
        except Exception as e:
            logger.error(f"Error applying blur effect: {e}")
    
    def _make_click_through(self):
        """Make window click-through on Windows"""
        try:
            hwnd = self.window.winfo_id()
            
            # Get current window style
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # Add click-through style
            style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
            
            # Apply new style
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            
        except Exception as e:
            logger.error(f"Error making window click-through: {e}")
    
    def destroy(self):
        """Destroy the overlay window"""
        if self.window:
            self.window.destroy()
            self.window = None

class ScreenManager:
    """Manages screen protection and blur overlays"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.overlays: List[BlurOverlay] = []
        self.overlay_queue = Queue()
        self._lock = threading.Lock()
        self.tk_root = None
        self.tk_thread = None
        
        # Blur settings
        self.blur_radius = self.config.get('screen_guard.blur_settings.radius', 25)
        self.blur_duration = self.config.get('screen_guard.blur_settings.duration', 2)
        self.blur_opacity = self.config.get('screen_guard.blur_settings.opacity', 0.8)
        self.blur_padding = self.config.get('screen_guard.blur_settings.padding', 60)
        
        # Start Tkinter in separate thread
        self._start_tk_thread()
    
    def _start_tk_thread(self):
        """Start Tkinter main loop in separate thread"""
        self.tk_thread = threading.Thread(target=self._tk_main_loop, daemon=True)
        self.tk_thread.start()
        
        # Wait for initialization
        time.sleep(0.5)
    
    def _tk_main_loop(self):
        """Tkinter main loop"""
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()  # Hide main window
            
            # Process overlay queue
            self.tk_root.after(100, self._process_overlay_queue)
            
            # Start main loop
            self.tk_root.mainloop()
            
        except Exception as e:
            logger.error(f"Tkinter thread error: {e}")
    
    def _process_overlay_queue(self):
        """Process pending overlay requests"""
        try:
            while not self.overlay_queue.empty():
                action, data = self.overlay_queue.get_nowait()
                
                if action == "create":
                    self._create_overlay_internal(*data)
                elif action == "clear":
                    self._clear_overlays_internal()
                    
        except Exception as e:
            logger.error(f"Error processing overlay queue: {e}")
        
        # Schedule next check
        if self.tk_root:
            self.tk_root.after(100, self._process_overlay_queue)
    
    def blur_face_regions(self, face_locations: List[Tuple[int, int, int, int]]):
        """Create blur overlays for detected face regions"""
        for top, right, bottom, left in face_locations:
            # Add padding
            left = max(0, left - self.blur_padding)
            top = max(0, top - self.blur_padding)
            right = right + self.blur_padding
            bottom = bottom + self.blur_padding
            
            # Calculate dimensions
            width = right - left
            height = bottom - top
            
            # Queue overlay creation
            self.overlay_queue.put(("create", (left, top, width, height)))
    
    def _create_overlay_internal(self, x: int, y: int, width: int, height: int):
        """Create overlay in Tkinter thread"""
        try:
            overlay = BlurOverlay(x, y, width, height, self.blur_radius, self.blur_opacity)
            overlay.show()
            
            with self._lock:
                self.overlays.append(overlay)
            
            # Schedule removal
            if self.blur_duration > 0:
                self.tk_root.after(
                    int(self.blur_duration * 1000),
                    lambda: self._remove_overlay(overlay)
                )
                
        except Exception as e:
            logger.error(f"Error creating overlay: {e}")
    
    def _remove_overlay(self, overlay: BlurOverlay):
        """Remove specific overlay"""
        try:
            overlay.destroy()
            
            with self._lock:
                if overlay in self.overlays:
                    self.overlays.remove(overlay)
                    
        except Exception as e:
            logger.error(f"Error removing overlay: {e}")
    
    def clear_overlays(self):
        """Clear all overlays"""
        self.overlay_queue.put(("clear", None))
    
    def _clear_overlays_internal(self):
        """Clear overlays in Tkinter thread"""
        with self._lock:
            for overlay in self.overlays:
                try:
                    overlay.destroy()
                except:
                    pass
            self.overlays.clear()
    
    def minimize_all_windows(self):
        """Minimize all windows (Windows + M)"""
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
        win32api.keybd_event(ord('M'), 0, 0, 0)
        win32api.keybd_event(ord('M'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    def lock_screen(self):
        """Lock Windows screen"""
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
        win32api.keybd_event(ord('L'), 0, 0, 0)
        win32api.keybd_event(ord('L'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    def show_black_screen(self, duration: float = 2.0):
        """Show full black screen overlay"""
        # Get screen dimensions
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        
        # Create full screen overlay
        self.overlay_queue.put(("create", (0, 0, screen_width, screen_height)))
        
        # Auto-remove after duration
        if duration > 0:
            threading.Timer(duration, self.clear_overlays).start()
    
    def get_active_window_info(self) -> Optional[dict]:
        """Get information about the active window"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            
            if hwnd:
                # Get window title
                window_title = win32gui.GetWindowText(hwnd)
                
                # Get process info
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                
                # Get window position
                rect = win32gui.GetWindowRect(hwnd)
                
                return {
                    'title': window_title,
                    'process': process.name(),
                    'pid': pid,
                    'position': {
                        'left': rect[0],
                        'top': rect[1],
                        'right': rect[2],
                        'bottom': rect[3]
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting active window info: {e}")
            
        return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.clear_overlays()
        
        if self.tk_root:
            self.tk_root.quit()
            
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()