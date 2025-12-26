# main.py
import threading
import cv2
from pose_camera import PoseCamera
from jump_detector import JumpDetector
from mario_game import MarioGame

def camera_loop(detector, mario):
    cam = PoseCamera()

    while True:
        frame, hip_y = cam.get_frame_and_y()

        if frame is None:
            break

        # Jump detection
        if detector.update(hip_y):
            mario.apply_jump()

        cv2.putText(frame, f"Jumps: {detector.jump_count}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.imshow("Camera Window", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()


def game_loop(mario):
    while mario.running:
        mario.game_loop_step()


if __name__ == "__main__":
    detector = JumpDetector()
    mario = MarioGame()

    # Start camera in a separate thread
    t1 = threading.Thread(target=camera_loop, args=(detector, mario))
    t1.start()

    # Game loop runs on main thread or another thread
    game_loop(mario)

    print("Exiting...")
