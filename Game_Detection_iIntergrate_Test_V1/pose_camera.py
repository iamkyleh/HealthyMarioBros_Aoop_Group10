# pose_camera.py
import cv2
import mediapipe as mp
import numpy as np

class PoseCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)

        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def get_frame_and_pose(self):
        """
        Returns:
            frame (BGR)
            data {
                "hip_left": float,
                "hip_right": float,
                "shoulder_left": (x, y, z),
                "shoulder_right": (x, y, z),
                "elbow_left": (x, y, z),
                "elbow_right": (x, y, z),
                "wrist_left": (x, y, z),
                "wrist_right": (x, y, z),
                "angle_elbow_left": float,
                "angle_elbow_right": float,
                "angle_shoulder_left": float,
                "angle_shoulder_right": float
            }
        """
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)

        data = {
            "hip_left": None,
            "hip_right": None,
            "shoulder_left": None,
            "shoulder_right": None,
            "elbow_left": None,
            "elbow_right": None,
            "wrist_left": None,
            "wrist_right": None,
            "angle_elbow_left": None,
            "angle_elbow_right": None,
            "angle_shoulder_left": None,
            "angle_shoulder_right": None,
        }

        if result.pose_landmarks:
            lm = result.pose_landmarks.landmark

            # === basic points ===
            SH_L = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            SH_R = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            EL_L = lm[self.mp_pose.PoseLandmark.LEFT_ELBOW.value]
            EL_R = lm[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value]
            WR_L = lm[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
            WR_R = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST.value]
            HIP_L = lm[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            HIP_R = lm[self.mp_pose.PoseLandmark.RIGHT_HIP.value]

            data["hip_left"] = HIP_L.y
            data["hip_right"] = HIP_R.y

            data["shoulder_left"]  = (SH_L.x, SH_L.y, SH_L.z)
            data["shoulder_right"] = (SH_R.x, SH_R.y, SH_R.z)
            data["elbow_left"]     = (EL_L.x, EL_L.y, EL_L.z)
            data["elbow_right"]    = (EL_R.x, EL_R.y, EL_R.z)
            data["wrist_left"]     = (WR_L.x, WR_L.y, WR_L.z)
            data["wrist_right"]    = (WR_R.x, WR_R.y, WR_R.z)

            # === angles helper ===
            def angle(a, b, c):  # angle at b
                a = np.array(a)
                b = np.array(b)
                c = np.array(c)
                ba = a - b
                bc = c - b
                cosang = np.dot(ba, bc) / (np.linalg.norm(ba)*np.linalg.norm(bc) + 1e-6)
                return np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))

            # elbow angles
            data["angle_elbow_left"]  = angle((SH_L.x, SH_L.y, SH_L.z),
                                             (EL_L.x, EL_L.y, EL_L.z),
                                             (WR_L.x, WR_L.y, WR_L.z))

            data["angle_elbow_right"] = angle((SH_R.x, SH_R.y, SH_R.z),
                                              (EL_R.x, EL_R.y, EL_R.z),
                                              (WR_R.x, WR_R.y, WR_R.z))

            # shoulder angles - arm vs vertical
            vertical = (SH_L.x, SH_L.y - 1, SH_L.z)

            data["angle_shoulder_left"] = angle(
                vertical,
                (SH_L.x, SH_L.y, SH_L.z),
                (EL_L.x, EL_L.y, EL_L.z)
            )

            vertical = (SH_R.x, SH_R.y - 1, SH_R.z)

            data["angle_shoulder_right"] = angle(
                vertical,
                (SH_R.x, SH_R.y, SH_R.z),
                (EL_R.x, EL_R.y, EL_R.z)
            )

            # Draw landmarks on frame
            self.mp_draw.draw_landmarks(
                frame,
                result.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )

        return frame, data

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
