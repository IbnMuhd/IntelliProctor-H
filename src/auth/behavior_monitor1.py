import cv2
import numpy as np
import mediapipe as mp
from src.utils.image_utils import resize_frame

class BehaviorMonitor:
    def __init__(self):
        """
        Initialize behavior monitoring components
        Using MediaPipe for efficient CPU-based pose and face landmark detection
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize face mesh for eye and head pose tracking
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize pose detection for body movement tracking
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # 0 is fastest, 2 is most accurate
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Define eye indices for MediaPipe face mesh
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
    def analyze_frame(self, frame):
        """
        Analyze frame for suspicious behavior
        Returns dictionary of detected behaviors
        """
        results = {
            "looking_away": False,
            "multiple_faces": False,
            "eyes_closed": False,
            "phone_detected": False
        }
        
        # Convert to RGB (MediaPipe requires RGB input)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process face mesh
        face_results = self.face_mesh.process(rgb_frame)
        if face_results.multi_face_landmarks:
            if len(face_results.multi_face_landmarks) > 1:
                results["multiple_faces"] = True
            
            # Process first face
            face_landmarks = face_results.multi_face_landmarks[0]
            results["looking_away"] = self._check_head_pose(face_landmarks)
            results["eyes_closed"] = self._check_eyes_closed(face_landmarks)
        
        # Process pose for phone detection
        pose_results = self.pose.process(rgb_frame)
        if pose_results.pose_landmarks:
            results["phone_detected"] = self._check_phone_usage(pose_results.pose_landmarks)
        
        return results
    
    def _check_head_pose(self, landmarks):
        """
        Check if person is looking away based on face landmarks
        Simple CPU-efficient implementation
        """
        # Get nose and left/right temple points
        nose = landmarks.landmark[1]
        left_temple = landmarks.landmark[234]
        right_temple = landmarks.landmark[454]
        
        # Calculate horizontal head rotation
        face_width = abs(left_temple.x - right_temple.x)
        nose_offset = abs(nose.x - (left_temple.x + right_temple.x) / 2)
        
        # If nose is too far from center, person is looking away
        return nose_offset > face_width * 0.2
    
    def _check_eyes_closed(self, landmarks):
        """
        Check if eyes are closed using vertical distance between eye landmarks
        """
        def eye_aspect_ratio(eye_points):
            # Calculate vertical distance between eye landmarks
            v1 = abs(landmarks.landmark[eye_points[1]].y - landmarks.landmark[eye_points[5]].y)
            v2 = abs(landmarks.landmark[eye_points[2]].y - landmarks.landmark[eye_points[4]].y)
            # Calculate horizontal distance
            h = abs(landmarks.landmark[eye_points[0]].x - landmarks.landmark[eye_points[3]].x)
            # Calculate eye aspect ratio
            ear = (v1 + v2) / (2.0 * h)
            return ear
        
        left_ear = eye_aspect_ratio(self.LEFT_EYE)
        right_ear = eye_aspect_ratio(self.RIGHT_EYE)
        
        # If eye aspect ratio is below threshold, eyes are closed
        return (left_ear + right_ear) / 2 < 0.2
    
    def _check_phone_usage(self, landmarks):
        """
        Check if person is using phone based on hand position
        """
        # Get wrist and shoulder landmarks
        left_wrist = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        
        # Check if either hand is raised near face
        wrist_raised = (
            left_wrist.y < left_shoulder.y or
            right_wrist.y < right_shoulder.y
        )
        
        return wrist_raised
    
    def draw_results(self, frame, results):
        """
        Draw detection results on frame
        """
        # Create copy of frame
        output = frame.copy()
        
        # Draw warning messages
        y_pos = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if results["looking_away"]:
            cv2.putText(output, "Warning: Looking Away", (10, y_pos), 
                       font, 0.7, (0, 0, 255), 2)
            y_pos += 30
            
        if results["multiple_faces"]:
            cv2.putText(output, "Warning: Multiple Faces Detected", (10, y_pos),
                       font, 0.7, (0, 0, 255), 2)
            y_pos += 30
            
        if results["eyes_closed"]:
            cv2.putText(output, "Warning: Eyes Closed", (10, y_pos),
                       font, 0.7, (0, 0, 255), 2)
            y_pos += 30
            
        if results["phone_detected"]:
            cv2.putText(output, "Warning: Phone Usage Detected", (10, y_pos),
                       font, 0.7, (0, 0, 255), 2)
        
        return output 