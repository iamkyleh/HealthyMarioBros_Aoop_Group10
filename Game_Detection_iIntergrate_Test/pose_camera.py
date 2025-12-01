# pose_camera.py
import cv2
import mediapipe as mp

class PoseCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def get_frame_and_y(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)

        hip_y_left , hip_y_right= None
        if result.pose_landmarks:
            hip_y_left = result.pose_landmarks.landmark[
                self.mp_pose.PoseLandmark.LEFT_HIP.value
            ].y
            
            hip_y_right = result.pose_landmarks.landmark[
                self.mp_pose.PoseLandmark.LEFT_HIP.value
            ].y

            self.mp_draw.draw_landmarks(
                frame,
                result.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )

        return frame, hip_y_left , hip_y_right

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
