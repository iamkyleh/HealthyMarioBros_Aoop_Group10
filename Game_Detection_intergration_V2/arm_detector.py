# arm_detector.py
class ArmDetector:
    def __init__(self, target_angle=90, tolerance=15):
        self.target_angle = target_angle
        self.tolerance = tolerance

    def _is_up(self, angle):
        if angle is None:
            return False
        return (self.target_angle - self.tolerance) <= angle <= (self.target_angle + self.tolerance)

    def update(self, angle_left, angle_right):
        return self._is_up(angle_left), self._is_up(angle_right)
