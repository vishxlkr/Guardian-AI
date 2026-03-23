"""
Image Utilities - Helper functions for image processing and manipulation
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path
from typing import Tuple, List, Optional, Union
import datetime
import logging

logger = logging.getLogger(__name__)

def resize_image(image: np.ndarray, max_width: int = 800, 
                 max_height: int = 600) -> np.ndarray:
    """Resize image while maintaining aspect ratio"""
    height, width = image.shape[:2]
    
    # Calculate scaling factor
    scale = min(max_width / width, max_height / height)
    
    if scale < 1:
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    return image

def add_timestamp(image: np.ndarray, timestamp: Optional[datetime.datetime] = None,
                 position: str = "bottom-right") -> np.ndarray:
    """Add timestamp overlay to image"""
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    img_copy = image.copy()
    height, width = img_copy.shape[:2]
    
    # Format timestamp
    text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Text properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    color = (255, 255, 255)  # White
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Calculate position
    padding = 10
    if position == "bottom-right":
        x = width - text_width - padding
        y = height - padding
    elif position == "bottom-left":
        x = padding
        y = height - padding
    elif position == "top-right":
        x = width - text_width - padding
        y = text_height + padding
    else:  # top-left
        x = padding
        y = text_height + padding
    
    # Add background rectangle
    cv2.rectangle(img_copy, 
                 (x - 5, y - text_height - 5),
                 (x + text_width + 5, y + 5),
                 (0, 0, 0), cv2.FILLED)
    
    # Add text
    cv2.putText(img_copy, text, (x, y), font, font_scale, color, thickness)
    
    return img_copy

def add_watermark(image: np.ndarray, text: str = "SECURITY", 
                 opacity: float = 0.3) -> np.ndarray:
    """Add semi-transparent watermark to image"""
    # Convert to PIL Image
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    # Create watermark layer
    watermark = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    
    # Try to use a better font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Get text size
    text_width, text_height = draw.textsize(text, font)
    
    # Calculate position (center)
    x = (pil_image.width - text_width) // 2
    y = (pil_image.height - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, font=font, fill=(255, 0, 0, int(255 * opacity)))
    
    # Composite images
    pil_image = pil_image.convert('RGBA')
    watermarked = Image.alpha_composite(pil_image, watermark)
    
    # Convert back to OpenCV format
    return cv2.cvtColor(np.array(watermarked.convert('RGB')), cv2.COLOR_RGB2BGR)

def create_image_grid(images: List[np.ndarray], grid_size: Tuple[int, int] = None,
                     cell_size: Tuple[int, int] = (200, 200)) -> np.ndarray:
    """Create a grid of images"""
    if not images:
        return np.zeros((cell_size[1], cell_size[0], 3), dtype=np.uint8)
    
    # Auto-calculate grid size if not provided
    if grid_size is None:
        n = len(images)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        grid_size = (rows, cols)
    
    rows, cols = grid_size
    
    # Create blank canvas
    grid_image = np.zeros((rows * cell_size[1], cols * cell_size[0], 3), dtype=np.uint8)
    
    # Place images
    for idx, img in enumerate(images[:rows * cols]):
        row = idx // cols
        col = idx % cols
        
        # Resize image to cell size
        resized = cv2.resize(img, cell_size)
        
        # Calculate position
        y1 = row * cell_size[1]
        y2 = y1 + cell_size[1]
        x1 = col * cell_size[0]
        x2 = x1 + cell_size[0]
        
        # Place image
        grid_image[y1:y2, x1:x2] = resized
    
    return grid_image

def highlight_faces(image: np.ndarray, face_locations: List[Tuple[int, int, int, int]],
                   labels: Optional[List[str]] = None, 
                   authorized_color: Tuple[int, int, int] = (0, 255, 0),
                   unauthorized_color: Tuple[int, int, int] = (0, 0, 255)) -> np.ndarray:
    """Draw rectangles around faces with labels"""
    img_copy = image.copy()
    
    for i, (top, right, bottom, left) in enumerate(face_locations):
        # Determine color based on label
        if labels and i < len(labels):
            label = labels[i]
            color = authorized_color if label != "Unknown" else unauthorized_color
        else:
            label = "Unknown"
            color = unauthorized_color
        
        # Draw rectangle
        cv2.rectangle(img_copy, (left, top), (right, bottom), color, 2)
        
        # Add label with background
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        
        # Background
        cv2.rectangle(img_copy,
                     (left, top - label_size[1] - 10),
                     (left + label_size[0] + 10, top),
                     color, cv2.FILLED)
        
        # Text
        cv2.putText(img_copy, label,
                   (left + 5, top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.6, (255, 255, 255), 1)
    
    return img_copy

def apply_privacy_blur(image: np.ndarray, regions: List[Tuple[int, int, int, int]],
                      blur_strength: int = 25) -> np.ndarray:
    """Apply blur to specific regions of an image"""
    img_copy = image.copy()
    
    for top, right, bottom, left in regions:
        # Extract region
        region = img_copy[top:bottom, left:right]
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(region, (blur_strength, blur_strength), 0)
        
        # Replace region
        img_copy[top:bottom, left:right] = blurred
    
    return img_copy

def enhance_image(image: np.ndarray, brightness: float = 1.0,
                 contrast: float = 1.0, saturation: float = 1.0) -> np.ndarray:
    """Enhance image properties"""
    # Convert to PIL
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    # Apply enhancements
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(pil_image)
        pil_image = enhancer.enhance(brightness)
    
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(contrast)
    
    if saturation != 1.0:
        enhancer = ImageEnhance.Color(pil_image)
        pil_image = enhancer.enhance(saturation)
    
    # Convert back
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def detect_motion_regions(frame1: np.ndarray, frame2: np.ndarray,
                         threshold: int = 25, min_area: int = 500) -> List[Tuple[int, int, int, int]]:
    """Detect regions with motion between two frames"""
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Calculate difference
    diff = cv2.absdiff(gray1, gray2)
    
    # Threshold
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and convert to regions
    motion_regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(contour)
            motion_regions.append((y, x + w, y + h, x))  # top, right, bottom, left
    
    return motion_regions

def save_image_securely(image: np.ndarray, filepath: Union[str, Path],
                       add_metadata: bool = True) -> bool:
    """Save image with security metadata"""
    try:
        filepath = Path(filepath)
        
        # Add timestamp if requested
        if add_metadata:
            image = add_timestamp(image)
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save image
        cv2.imwrite(str(filepath), image)
        
        # Save metadata file
        if add_metadata:
            metadata = {
                'timestamp': datetime.datetime.now().isoformat(),
                'dimensions': f"{image.shape[1]}x{image.shape[0]}",
                'file_size': filepath.stat().st_size if filepath.exists() else 0,
                'security_software_version': '1.0.0'
            }
            
            import json
            metadata_path = filepath.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return False

def create_alert_overlay(image: np.ndarray, alert_text: str = "ALERT",
                        alert_type: str = "warning") -> np.ndarray:
    """Add alert overlay to image"""
    img_copy = image.copy()
    height, width = img_copy.shape[:2]
    
    # Colors based on alert type
    colors = {
        'warning': (0, 165, 255),  # Orange
        'danger': (0, 0, 255),     # Red
        'info': (255, 255, 0)      # Cyan
    }
    color = colors.get(alert_type, colors['warning'])
    
    # Add semi-transparent overlay
    overlay = img_copy.copy()
    cv2.rectangle(overlay, (0, 0), (width, 60), color, -1)
    cv2.addWeighted(overlay, 0.3, img_copy, 0.7, 0, img_copy)
    
    # Add text
    font = cv2.FONT_HERSHEY_BOLD
    font_scale = 1.5
    thickness = 3
    
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(alert_text, font, font_scale, thickness)
    
    # Center text
    x = (width - text_width) // 2
    y = 40
    
    # Add text with outline
    cv2.putText(img_copy, alert_text, (x, y), font, font_scale, (0, 0, 0), thickness + 2)
    cv2.putText(img_copy, alert_text, (x, y), font, font_scale, (255, 255, 255), thickness)
    
    return img_copy

def compare_faces(image1: np.ndarray, image2: np.ndarray) -> float:
    """Compare similarity between two face images (0-1, higher is more similar)"""
    try:
        # Resize to same size
        size = (160, 160)
        img1_resized = cv2.resize(image1, size)
        img2_resized = cv2.resize(image2, size)
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
        
        # Calculate structural similarity
        from skimage.metrics import structural_similarity as ssim
        score = ssim(gray1, gray2)
        
        return score
        
    except Exception as e:
        logger.error(f"Error comparing faces: {e}")
        return 0.0