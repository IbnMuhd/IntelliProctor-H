import cv2
import numpy as np

def resize_frame(frame, width=None, height=None):
    """
    Resize frame while maintaining aspect ratio
    """
    if width is None and height is None:
        return frame
        
    h, w = frame.shape[:2]
    if width is None:
        aspect = height / float(h)
        dim = (int(w * aspect), height)
    else:
        aspect = width / float(w)
        dim = (width, int(h * aspect))
        
    return cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

def draw_text(frame, text, position, font_scale=0.7, color=(0, 0, 255), thickness=2):
    """
    Draw text on frame with background rectangle
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )
    
    # Calculate background rectangle dimensions
    padding = 5
    rect_height = text_height + 2 * padding
    rect_width = text_width + 2 * padding
    
    # Extract coordinates
    x, y = position
    
    # Draw background rectangle
    cv2.rectangle(
        frame,
        (x, y - rect_height),
        (x + rect_width, y),
        (0, 0, 0),
        -1
    )
    
    # Draw text
    cv2.putText(
        frame,
        text,
        (x + padding, y - padding),
        font,
        font_scale,
        color,
        thickness
    )
    
    return frame

def normalize_frame(frame):
    """
    Normalize frame for better processing
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply histogram equalization
    gray = cv2.equalizeHist(gray)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    return blurred 