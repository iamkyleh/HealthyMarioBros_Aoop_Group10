# jump_detector.py
import numpy as np
from collections import deque

class JumpDetector:
    def __init__(self, up_threshold=0.12, down_threshold=0.06):
        self.baseline_window = deque(maxlen=5)
        self.prev_y = None
        self.jumping = False
        self.jump_count = 0
        self.cooldown = 0
        self.up_threshold = up_threshold
        self.down_threshold = down_threshold

    def update(self, current_y):
        if current_y is None or np.isnan(current_y):
            return False

        self.baseline_window.append(current_y)
        baseline_y = np.mean(self.baseline_window)

        if self.prev_y is None:
            self.prev_y = current_y
            return False

        velocity = self.prev_y - current_y
        self.prev_y = current_y

        if self.cooldown > 0:
            self.cooldown -= 1
            return False

        jump_triggered = False

        if velocity > self.up_threshold and not self.jumping:
            self.jumping = True
            jump_triggered = True
            print("🟢 Jump UP detected!")

        if velocity < -self.down_threshold and self.jumping:
            self.jumping = False
            self.jump_count += 1
            self.cooldown = 5
            print(f"✅ Jump LAND → Total: {self.jump_count}")

        return jump_triggered
