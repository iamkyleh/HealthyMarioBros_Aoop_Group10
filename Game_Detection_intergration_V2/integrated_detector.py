# integrated_detector.py
from jump_detector import JumpDetector
from arm_detector import ArmDetector

class IntegratedDetector:
    def __init__(self):
        self.jump = JumpDetector()
        self.arm = ArmDetector()

    def update(self, pose):
        hip_left = pose["hip_left"]
        hip_right = pose["hip_right"]

        if hip_left is not None and hip_right is not None:
            hip_y = (hip_left + hip_right) / 2
        else:
            hip_y = hip_left or hip_right

        jump_now = self.jump.update(hip_y)

        left_up, right_up = self.arm.update(
            pose["angle_shoulder_left"],
            pose["angle_shoulder_right"]
        )

        return {
            "jump": jump_now,
            "left_arm": left_up,
            "right_arm": right_up
        }
