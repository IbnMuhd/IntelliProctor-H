import cv2
import numpy as np
from threading import Thread, Lock
import time

class Camera:
    def __init__(self, src=0, width=640, height=480):
        """
        Initialize the camera with CPU-optimized settings
        """
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.stream.set(cv2.CAP_PROP_FPS, 30)
        
        # Initialize thread and lock
        self.thread = None
        self.lock = Lock()
        self.frame = None
        self.stopped = False
        
        # Start frame grabbing thread
        self.start()
    
    def start(self):
        """Start the thread to read frames from the video stream"""
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self
    
    def update(self):
        """Keep looping infinitely until the thread is stopped"""
        while True:
            if self.stopped:
                return
            
            ret, frame = self.stream.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.01)  # Short sleep to prevent CPU overload
    
    def get_frame(self):
        """Return the current frame"""
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()
    
    def release(self):
        """Stop the thread and release the camera"""
        self.stopped = True
        if self.thread is not None:
            self.thread.join()
        self.stream.release() 

def generate_frames():
    last_empty = False
    while True:
        if not frame_queue.empty():
            if last_empty:
                print("Frame queue filled")
            last_empty = False
            frame = frame_queue.get()
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            if not last_empty:
                print("Frame queue is empty")
            last_empty = True
            time.sleep(0.05)  # Prevents flooding the terminal 

def process_frame():
    while True:
        if camera:
            frame = camera.get_frame()
            if frame is not None:
                # Only process if frame is valid
                print("Processing frame")
                auth_result = face_auth.verify_face(frame)
                behavior_results = behavior_monitor.analyze_frame(frame)
                frame = behavior_monitor.draw_results(frame, behavior_results)
                if not frame_queue.full():
                    frame_queue.put(frame)
            else:
                # Only print once per empty state, or just remove this print
                print("No frame to process")
                time.sleep(0.05)  # Prevents tight loop if camera is not ready
        else:
            time.sleep(0.05) 