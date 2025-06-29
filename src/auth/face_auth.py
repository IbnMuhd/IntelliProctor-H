import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

class FaceAuthenticator:
    def __init__(self):
        """
        Initialize face detection and recognition models optimized for CPU
        Using InsightFace which provides robust face recognition capabilities
        """
        self.face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        self.face_app.prepare(ctx_id=0, det_size=(320, 320))

        # Store registered face embeddings
        self.registered_embeddings = {}
    
    def embedding_to_blob(self, embedding):
        """
        Convert a numpy embedding to bytes for BLOB storage.
        """
        if embedding is None:
            return None
        return embedding.astype(np.float32).tobytes()

    def blob_to_embedding(self, blob):
        """
        Convert bytes (BLOB) back to numpy embedding.
        """
        if blob is None:
            return None
        return np.frombuffer(blob, dtype=np.float32)

    def get_face_encoding(self, frame):
        """
        Extract a face embedding using InsightFace.
        Returns a numpy array or None if no face detected.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.face_app.get(rgb)
        if not faces:
            return None
        # Use the face with the largest bounding box area
        face = max(faces, key=lambda f: f.bbox[2]*f.bbox[3])
        return face.embedding

    def compare_encodings(self, encoding1, encoding2, tolerance=0.4):
        """
        Compare two face encodings using cosine similarity.
        Accepts numpy arrays or BLOBs (bytes).
        Returns True if similarity is above (1-tolerance).
        """
        if encoding1 is None or encoding2 is None:
            return False
        # Convert BLOBs to numpy arrays if needed
        if isinstance(encoding1, bytes):
            encoding1 = self.blob_to_embedding(encoding1)
        if isinstance(encoding2, bytes):
            encoding2 = self.blob_to_embedding(encoding2)
        # Normalize vectors
        encoding1 = encoding1 / np.linalg.norm(encoding1)
        encoding2 = encoding2 / np.linalg.norm(encoding2)
        similarity = np.dot(encoding1, encoding2)
        return similarity > (1 - tolerance)

    def verify_face(self, frame, stored_encoding=None, tolerance=0.4):
        """
        Verify if the detected face matches the registered face encoding.
        Accepts stored_encoding as numpy array or BLOB.
        Returns dict with verification result and message.
        """
        encoding = self.get_face_encoding(frame)
        if encoding is None:
            return {"verified": False, "message": "No face detected"}
        if stored_encoding is not None:
            if self.compare_encodings(encoding, stored_encoding, tolerance):
                return {"verified": True, "message": "Face verified"}
            else:
                return {"verified": False, "message": "Face does not match"}
        # If no stored_encoding provided, just return the encoding for registration (as BLOB)
        return {"verified": True, "encoding": self.embedding_to_blob(encoding), "message": "Face encoding captured"}