import numpy as np
import math

class HandDetector:
    def __init__(
        self,
        raise_threshold=50,
        lower_threshold=35,
        ema_alpha=0.3
    ):
        self.raise_threshold = raise_threshold
        self.lower_threshold = lower_threshold
        self.ema_alpha = ema_alpha

        # EMA-smoothed angles
        self.right_angle_ema = None
        self.left_angle_ema = None

        # Arm state
        self.right_up = False
        self.left_up = False

    def calculate_angle(self, a, b, c):
        ba = (a.x - b.x, a.y - b.y)
        bc = (c.x - b.x, c.y - b.y)

        dot = ba[0] * bc[0] + ba[1] * bc[1]
        mag_ba = math.hypot(*ba)
        mag_bc = math.hypot(*bc)

        if mag_ba == 0 or mag_bc == 0:
            return 0

        cos_angle = dot / (mag_ba * mag_bc)
        cos_angle = max(-1, min(1, cos_angle))
        return math.degrees(math.acos(cos_angle))

    def ema(self, prev, current):
        if prev is None:
            return current
        return self.ema_alpha * current + (1 - self.ema_alpha) * prev

    def update(self, pose_landmarks, mp_pose):
        if pose_landmarks is None:
            return None

        lm = pose_landmarks.landmark

        # Right landmarks
        r_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        r_elbow = lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        r_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]

        # Left landmarks
        l_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        l_elbow = lm[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        l_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]

        # Raw angles
        right_angle = self.calculate_angle(r_hip, r_shoulder, r_elbow)
        left_angle = self.calculate_angle(l_hip, l_shoulder, l_elbow)

        # EMA smoothing
        self.right_angle_ema = self.ema(self.right_angle_ema, right_angle)
        self.left_angle_ema = self.ema(self.left_angle_ema, left_angle)

        # Update states
        if self.right_angle_ema > self.raise_threshold:
            self.right_up = True
        elif self.right_angle_ema < self.lower_threshold:
            self.right_up = False

        if self.left_angle_ema > self.raise_threshold:
            self.left_up = True
        elif self.left_angle_ema < self.lower_threshold:
            self.left_up = False

        # Return current move
        if self.right_up:
            return "right"
        elif self.left_up:
            return "left"
        else:
            return None
