"""
Performance configuration for Intel Core i3 with 8GB RAM
Optimized settings for smooth operation on modest hardware
"""

# Camera and Video Settings
CAMERA_SETTINGS = {
    'width': 640,
    'height': 480,
    'fps': 15,  # Reduced from default 30
    'buffer_size': 5  # Reduced buffer for memory efficiency
}

# Processing Intervals (in seconds)
PROCESSING_INTERVALS = {
    'face_check': 1.5,      # Check face every 1.5 seconds
    'behavior_check': 2.0,   # Check behavior every 2 seconds
    'audio_check': 2.0,      # Check audio every 2 seconds
    'system_monitor': 5.0    # Monitor system every 5 seconds
}

# Model Settings
MODEL_SETTINGS = {
    'face_model': 'buffalo_s',        # Smaller model
    'detection_size': (160, 160),     # Smaller detection area
    'confidence_threshold': 0.3,       # Lower confidence for speed
    'frame_skip': 10,                 # Process every 10th frame
    'cache_size': 5                   # Small cache size
}

# Memory Management
MEMORY_SETTINGS = {
    'max_queue_size': 5,              # Reduced queue size
    'max_cache_size': 10,             # Small cache
    'cleanup_interval': 30,           # Cleanup every 30 seconds
    'max_memory_usage': 70            # Alert if memory > 70%
}

# Audio Settings
AUDIO_SETTINGS = {
    'sample_rate': 8000,              # Reduced from 16000
    'channels': 1,                    # Mono audio
    'chunk_size': 1024,               # Smaller chunks
    'threshold': 0.02                 # Audio threshold
}

# Performance Thresholds
PERFORMANCE_THRESHOLDS = {
    'cpu_warning': 70,                # Warn if CPU > 70%
    'cpu_critical': 85,               # Critical if CPU > 85%
    'memory_warning': 75,             # Warn if memory > 75%
    'memory_critical': 90             # Critical if memory > 90%
}

# Optimization Flags
OPTIMIZATIONS = {
    'enable_caching': True,
    'enable_frame_skipping': True,
    'enable_dynamic_adjustment': True,
    'enable_memory_monitoring': True,
    'reduce_resolution': True,
    'use_headless_opencv': True
}

def get_optimized_settings():
    """Return all optimized settings for the system"""
    return {
        'camera': CAMERA_SETTINGS,
        'intervals': PROCESSING_INTERVALS,
        'models': MODEL_SETTINGS,
        'memory': MEMORY_SETTINGS,
        'audio': AUDIO_SETTINGS,
        'thresholds': PERFORMANCE_THRESHOLDS,
        'optimizations': OPTIMIZATIONS
    } 