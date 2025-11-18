import cv2
import mediapipe as mp
import numpy as np
from collections import deque

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(0)

baseline_window = deque(maxlen=5)
prev_y = None
jumping = False
jump_count = 0
cooldown = 0 

def jump_detection(current_y, up_threshold=0.12, down_threshold=0.06):
    global prev_y, jumping, jump_count, cooldown

    # 1. Handle missing / invalid pose values
    if current_y is None or np.isnan(current_y):
        return None
    # 2. Update moving baseline (average of last valid values)
    baseline_window.append(current_y)
    baseline_y = np.mean(baseline_window)
    # 3. Compute velocity (frame-to-frame movement)
    if prev_y is None:
        prev_y = current_y
        return None
    velocity = prev_y - current_y  # positive = going upp
    prev_y = current_y
    # 4. Cooldown to avoid double count or camera re-enter glitches
    if cooldown > 0:
        cooldown -= 1
        return None
    # 5. Detect jump start
    if velocity > up_threshold and not jumping:
        jumping = True
        print("🟢 Jump UP detected!")
    # 6. Detect jump landing
    if velocity < -down_threshold and jumping:
        jumping = False
        jump_count += 1
        cooldown = 5   # ignore the next few frames
        print(f"✅ Jump LAND detected → Count = {jump_count}")
    return baseline_y


def move_right():

    return

def move_left():

    return 

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Recolor image to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Make detection
        results = pose.process(image)

        # Recolor back to BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # Extract landmarks
        try:
            landmarks = results.pose_landmarks.landmark
            left_hip_y = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y
            jump_detection(left_hip_y)
        except:
            pass

   
        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        # Display jump count
        cv2.putText(image, f'Jumps: {jump_count}', (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow('Mediapipe Feed', image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
