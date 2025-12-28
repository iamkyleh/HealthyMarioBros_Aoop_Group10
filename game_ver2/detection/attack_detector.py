import cv2

from mediapipe.python.solutions.hands import Hands, HandLandmark, HAND_CONNECTIONS
from mediapipe.python.solutions.drawing_utils import draw_landmarks


class AttackDetector:
    def __init__(self):
        # Initialize MediaPipe Hands
        self.hands = Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

    def is_pointing(self, hand_landmarks):
        """
        Detect if the hand is making a pointing gesture
        (index finger extended, other fingers curled).
        """
        if hand_landmarks is None:
            return False

        # Index finger
        index_tip = hand_landmarks.landmark[HandLandmark.INDEX_FINGER_TIP]
        index_dip = hand_landmarks.landmark[HandLandmark.INDEX_FINGER_DIP]
        index_pip = hand_landmarks.landmark[HandLandmark.INDEX_FINGER_PIP]

        # Other fingers
        middle_tip = hand_landmarks.landmark[HandLandmark.MIDDLE_FINGER_TIP]
        middle_pip = hand_landmarks.landmark[HandLandmark.MIDDLE_FINGER_PIP]

        ring_tip = hand_landmarks.landmark[HandLandmark.RING_FINGER_TIP]
        ring_pip = hand_landmarks.landmark[HandLandmark.RING_FINGER_PIP]

        pinky_tip = hand_landmarks.landmark[HandLandmark.PINKY_TIP]
        pinky_pip = hand_landmarks.landmark[HandLandmark.PINKY_PIP]

        thumb_tip = hand_landmarks.landmark[HandLandmark.THUMB_TIP]
        thumb_ip = hand_landmarks.landmark[HandLandmark.THUMB_IP]

        # Index finger extended (tip above DIP and PIP)
        index_extended = (
            index_tip.y < index_dip.y and
            index_dip.y < index_pip.y
        )

        # Other fingers curled
        middle_curled = middle_tip.y > middle_pip.y
        ring_curled = ring_tip.y > ring_pip.y
        pinky_curled = pinky_tip.y > pinky_pip.y
        thumb_curled = thumb_tip.y > thumb_ip.y

        return (
            index_extended and
            middle_curled and
            ring_curled and
            pinky_curled
        )

    def detect_attack(self, frame):
        """
        Process a frame and return True if a pointing gesture is detected.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                if self.is_pointing(hand_landmarks):
                    # Draw landmarks for visualization
                    draw_landmarks(
                        frame,
                        hand_landmarks,
                        HAND_CONNECTIONS
                    )
                    return True

        return False

    def release(self):
        self.hands.close()
