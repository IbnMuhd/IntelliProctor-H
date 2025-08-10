import cv2
import numpy as np
import mediapipe as mp
from insightface.app import FaceAnalysis
from numpy.linalg import norm
from src.utils.image_utils import resize_frame  # ensure this resizes frame to given width
from ultralytics import YOLO  # Add YOLO for heavy phone detection
from src.monitoring.audio_monitor import AudioMonitor  # Import AudioMonitor

class BehaviorMonitor:
    def __init__(self, registered_embedding, frame_skip=3, identity_threshold=0.45):
        self.face_verifier = FaceAnalysis()
        self.face_verifier.prepare(ctx_id=-1)  # Use -1 if you don’t have GPU
        self.frame_count = 0
        self.frame_skip = frame_skip
        self.identity_threshold = identity_threshold
        self.registered_embedding = registered_embedding
        # MediaPipe components
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.last_results = {
            "looking_away": False,
            "multiple_faces": False,
            "eyes_closed": False,
            "phone_detected": False,
            "identity_mismatch": False,
            "noise_detected": False
        }
        # Heavy model: YOLOv8 for phone detection
        self.yolo_model = YOLO('yolov8n.pt')
        # Audio monitor for noise/talking detection
        self.audio_monitor = AudioMonitor()
        self.audio_monitor.start()

    def analyze_frame(self, frame):
        self.frame_count += 1
        if self.frame_count % self.frame_skip != 0:
            self.last_results["noise_detected"] = self.audio_monitor.is_noise()
            return self.last_results
        frame = resize_frame(frame, width=320)  # reduce size for performance
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = {
            "looking_away": False,
            "multiple_faces": False,
            "eyes_closed": False,
            "phone_detected": False,
            "identity_mismatch": False,
            "noise_detected": False
        }
        # Identity verification
        results["identity_mismatch"] = not self._verify_identity(frame)
        # Face behavior
        face_results = self.face_mesh.process(rgb_frame)
        if face_results.multi_face_landmarks:
            if len(face_results.multi_face_landmarks) > 1:
                results["multiple_faces"] = True
            landmarks = face_results.multi_face_landmarks[0]
            results["looking_away"] = self._check_head_pose(landmarks)
            results["eyes_closed"] = self._check_eyes_closed(landmarks)
        # Pose check (lightweight, continuous)
        pose_results = self.pose.process(rgb_frame)
        if pose_results.pose_landmarks:
            results["phone_detected"] = self._check_phone_usage(pose_results.pose_landmarks)
        # Heavy check: YOLO phone detection every 15 frames
        if self.frame_count % 15 == 0:
            if self.detect_phone_yolo(frame):
                results["phone_detected"] = True
        # Audio check: noise/talking detection
        results["noise_detected"] = self.audio_monitor.is_noise()
        self.last_results = results
        return results

    def detect_phone_yolo(self, frame):
        yolo_results = self.yolo_model(frame)
        for result in yolo_results:
            for box in result.boxes:
                cls = int(box.cls[0])
                # COCO class 67 is 'cell phone'
                if cls == 67 and box.conf[0] > 0.4:
                    return True
        return False

    def _verify_identity(self, frame):
        faces = self.face_verifier.get(frame)
        for face in faces:
            live_embedding = face.embedding
            similarity = np.dot(self.registered_embedding, live_embedding) / (
                norm(self.registered_embedding) * norm(live_embedding)
            )
            if similarity > (1 - self.identity_threshold):
                return True
        return False

    def _check_head_pose(self, landmarks):
        nose = landmarks.landmark[1]
        left_temple = landmarks.landmark[234]
        right_temple = landmarks.landmark[454]
        face_width = abs(left_temple.x - right_temple.x)
        nose_offset = abs(nose.x - (left_temple.x + right_temple.x) / 2)
        return nose_offset > face_width * 0.2

    def _check_eyes_closed(self, landmarks):
        def eye_aspect_ratio(eye_points):
            v1 = abs(landmarks.landmark[eye_points[1]].y - landmarks.landmark[eye_points[5]].y)
            v2 = abs(landmarks.landmark[eye_points[2]].y - landmarks.landmark[eye_points[4]].y)
            h = abs(landmarks.landmark[eye_points[0]].x - landmarks.landmark[eye_points[3]].x)
            ear = (v1 + v2) / (2.0 * h)
            return ear
        left_ear = eye_aspect_ratio(self.LEFT_EYE)
        right_ear = eye_aspect_ratio(self.RIGHT_EYE)
        return (left_ear + right_ear) / 2 < 0.2

    def _check_phone_usage(self, landmarks):
        left_wrist = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        wrist_raised = (
            left_wrist.y < left_shoulder.y or
            right_wrist.y < right_shoulder.y
        )
        return wrist_raised

    def draw_results(self, frame, results):
        output = frame.copy()
        y_pos = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        if results.get("looking_away"):
            cv2.putText(output, "Warning: Looking Away", (10, y_pos), font, 0.7, (0, 0, 255), 2)
            y_pos += 30
        if results.get("multiple_faces"):
            cv2.putText(output, "Warning: Multiple Faces Detected", (10, y_pos), font, 0.7, (0, 0, 255), 2)
            y_pos += 30
        if results.get("eyes_closed"):
            cv2.putText(output, "Warning: Eyes Closed", (10, y_pos), font, 0.7, (0, 0, 255), 2)
            y_pos += 30
        if results.get("phone_detected"):
            cv2.putText(output, "Warning: Phone Usage Detected", (10, y_pos), font, 0.7, (0, 0, 255), 2)
            y_pos += 30
        if results.get("identity_mismatch"):
            cv2.putText(output, "Warning: Identity Mismatch!", (10, y_pos), font, 0.7, (0, 0, 255), 2)
            y_pos += 30
        if results.get("noise_detected"):
            cv2.putText(output, "Warning: Noise/Talking Detected!", (10, y_pos), font, 0.7, (0, 0, 255), 2)
        return output
