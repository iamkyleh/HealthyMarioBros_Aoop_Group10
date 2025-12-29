import cv2
import mediapipe as mp
import math

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles


class AttackDetector:
    def __init__(
        self,
        mar_open_threshold=0.65,
        mar_close_threshold=0.45
    ):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

        # Hysteresis thresholds（很重要）
        self.mar_open_threshold = mar_open_threshold
        self.mar_close_threshold = mar_close_threshold

        self.was_mouth_open = False

        # Mouth landmarks
        self.upper_lip = 13
        self.lower_lip = 14
        self.left_mouth = 61
        self.right_mouth = 291

    def _dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def calculate_mar(self, face_landmarks):
        lm = face_landmarks.landmark
        vertical = self._dist(lm[self.upper_lip], lm[self.lower_lip])
        horizontal = self._dist(lm[self.left_mouth], lm[self.right_mouth])
        return vertical / horizontal if horizontal > 0 else 0

    def detect_attack(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        attack_triggered = False
        mar = 0

        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            mar = self.calculate_mar(face)

            # 嘴巴是否「現在」是開的
            if mar > self.mar_open_threshold:
                is_mouth_open = True
            elif mar < self.mar_close_threshold:
                is_mouth_open = False
            else:
                is_mouth_open = self.was_mouth_open  # 落在遲滯區，維持狀態

            # 🔥 關鍵：只在 CLOSED → OPEN 觸發
            if is_mouth_open and not self.was_mouth_open:
                attack_triggered = True

            self.was_mouth_open = is_mouth_open

            # Visualization
            mp_drawing.draw_landmarks(
                frame,
                face,
                mp_face_mesh.FACEMESH_LIPS,
                None,
                mp_styles.get_default_face_mesh_contours_style()
            )

        cv2.putText(
            frame,
            f"MAR: {mar:.2f} | {'OPEN' if self.was_mouth_open else 'CLOSED'}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255) if self.was_mouth_open else (0, 255, 0),
            2
        )

        return attack_triggered

    def release(self):
        self.face_mesh.close()
