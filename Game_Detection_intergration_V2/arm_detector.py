# arm_detector.py

class ArmDetector:
    def __init__(self,
                 shoulder_target=90,
                 shoulder_tol=15,
                 elbow_target=180,
                 elbow_tol=25):
        """
        shoulder_target = angle for raised arms
        elbow_target    = angle for straight arms
        """
        self.shoulder_target = shoulder_target
        self.shoulder_tol = shoulder_tol
        self.elbow_target = elbow_target
        self.elbow_tol = elbow_tol

    def _in_range(self, angle, target, tol):
        if angle is None:
            return False
        return (target - tol) <= angle <= (target + tol)

    def update(self,
               shoulder_left, shoulder_right,
               elbow_left, elbow_right):
        """
        Returns:
            left_up  (bool)
            right_up (bool)
        """

        # LEFT ARM CHECK
        left_horizontal = self._in_range(shoulder_left, self.shoulder_target, self.shoulder_tol)
        left_straight   = self._in_range(elbow_left, self.elbow_target, self.elbow_tol)
        left_up = left_horizontal and left_straight

        # RIGHT ARM CHECK
        right_horizontal = self._in_range(shoulder_right, self.shoulder_target, self.shoulder_tol)
        right_straight   = self._in_range(elbow_right, self.elbow_target, self.elbow_tol)
        right_up = right_horizontal and right_straight

        return left_up, right_up
