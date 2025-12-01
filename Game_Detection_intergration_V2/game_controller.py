# game_controller.py
class GameController:
    def __init__(self):
        self.left = False
        self.right = False
        self.jump = False

    def update(self, detection):
        self.left = detection["left_arm"]
        self.right = detection["right_arm"]
        self.jump = detection["jump"]

        return {
            "left": self.left,
            "right": self.right,
            "jump": self.jump
        }
