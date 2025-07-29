"""
Accuracy configuration for maintaining high accuracy while optimizing performance
Balanced settings for Intel Core i3 with 8GB RAM
"""

# Accuracy vs Performance Trade-offs
ACCURACY_LEVELS = {
    "high": {
        "description": "Maximum accuracy, higher CPU usage",
        "face_model": "buffalo_l",           # Large model
        "detection_size": (320, 320),        # Full resolution
        "confidence_threshold": 0.5,          # Standard confidence
        "frame_skip": 5,                     # Process more frames
        "retry_attempts": 3,                 # More retry attempts
        "multi_resolution": True,             # Use multiple resolutions
        "adaptive_thresholds": True,          # Adaptive thresholds
        "cache_size": 15                     # Larger cache
    },
    "balanced": {
        "description": "Balanced accuracy and performance (RECOMMENDED)",
        "face_model": "buffalo_s",           # Small model
        "detection_size": (160, 160),        # Reduced resolution
        "confidence_threshold": 0.4,          # Slightly lower confidence
        "frame_skip": 10,                    # Process fewer frames
        "retry_attempts": 2,                 # Fewer retry attempts
        "multi_resolution": True,             # Use multiple resolutions
        "adaptive_thresholds": True,          # Adaptive thresholds
        "cache_size": 10                     # Medium cache
    },
    "performance": {
        "description": "Maximum performance, lower accuracy",
        "face_model": "buffalo_s",           # Small model
        "detection_size": (128, 128),        # Very small resolution
        "confidence_threshold": 0.3,          # Lower confidence
        "frame_skip": 15,                    # Process very few frames
        "retry_attempts": 1,                 # No retries
        "multi_resolution": False,            # Single resolution
        "adaptive_thresholds": False,         # Fixed thresholds
        "cache_size": 5                      # Small cache
    }
}

# Current accuracy level (change this to adjust accuracy vs performance)
CURRENT_ACCURACY_LEVEL = "balanced"

# Confidence thresholds for different detection types
DETECTION_THRESHOLDS = {
    "face_verification": 0.6,        # Higher threshold for face verification
    "multiple_faces": 0.7,           # Very high threshold for multiple faces
    "looking_away": 0.6,             # Higher threshold for looking away
    "eyes_closed": 0.65,             # Higher threshold for eyes closed
    "phone_detection": 0.7,          # High threshold for phone detection
    "audio_detection": 0.5            # Standard threshold for audio
}

# Adaptive threshold settings
ADAPTIVE_SETTINGS = {
    "enabled": True,
    "history_size": 10,              # Number of recent results to consider
    "adjustment_factor": 0.2,        # How much to adjust thresholds
    "min_threshold": 0.3,            # Minimum threshold value
    "max_threshold": 0.5             # Maximum threshold value
}

# Multi-resolution settings
MULTI_RESOLUTION_SETTINGS = {
    "enabled": True,
    "resolutions": [
        (640, 480),                  # Original resolution
        (320, 240),                  # Medium resolution
        (160, 120)                   # Small resolution (fallback)
    ],
    "confidence_weights": [0.6, 0.3, 0.1]  # Weights for each resolution
}

# Retry settings for improved accuracy
RETRY_SETTINGS = {
    "enabled": True,
    "max_attempts": 2,               # Maximum retry attempts
    "delay_between_attempts": [0.1, 0.2],  # Delays in seconds
    "backoff_factor": 1.5            # Exponential backoff factor
}

# Cache settings for accuracy preservation
CACHE_SETTINGS = {
    "enabled": True,
    "max_size": 10,                  # Maximum cache size
    "ttl_seconds": 30,               # Time to live for cache entries
    "accuracy_boost": True           # Use cache to improve accuracy
}

# Performance monitoring for accuracy
ACCURACY_MONITORING = {
    "enabled": True,
    "track_false_positives": True,   # Track false positive rate
    "track_false_negatives": True,   # Track false negative rate
    "track_detection_rate": True,    # Track overall detection rate
    "alert_threshold": 0.8           # Alert if accuracy drops below 80%
}

def get_accuracy_settings(level=CURRENT_ACCURACY_LEVEL):
    """Get accuracy settings for the specified level"""
    if level not in ACCURACY_LEVELS:
        level = "balanced"  # Default to balanced
    return ACCURACY_LEVELS[level]

def get_current_settings():
    """Get current accuracy settings"""
    return get_accuracy_settings(CURRENT_ACCURACY_LEVEL)

def get_accuracy_trade_offs():
    """Get information about accuracy vs performance trade-offs"""
    return {
        "current_level": CURRENT_ACCURACY_LEVEL,
        "available_levels": list(ACCURACY_LEVELS.keys()),
        "recommendations": {
            "high": "Use for critical exams where accuracy is paramount",
            "balanced": "Use for most exams (recommended for your hardware)",
            "performance": "Use only if system is struggling with performance"
        }
    }

def adjust_accuracy_level(new_level):
    """Change the accuracy level (call this function to adjust accuracy vs performance)"""
    global CURRENT_ACCURACY_LEVEL
    if new_level in ACCURACY_LEVELS:
        CURRENT_ACCURACY_LEVEL = new_level
        return True
    return False 