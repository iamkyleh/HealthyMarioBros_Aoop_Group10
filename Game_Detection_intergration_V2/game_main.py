# game_main.py
import pygame
import cv2
from pose_camera import PoseCamera
from integrated_detector import IntegratedDetector
from game_controller import GameController
from mario_sprite import Mario

def main():
    # --- Pygame setup ---
    pygame.init()
    screen = pygame.display.set_mode((800, 450))
    pygame.display.set_caption("Pose-Controlled Mario")

    clock = pygame.time.Clock()

    mario = Mario(100, 350)
    all_sprites = pygame.sprite.Group(mario)

    # --- Pose modules ---
    cam = PoseCamera()
    detector = IntegratedDetector()
    controller = GameController()

    running = True
    while running:
        # ======== 1. Pygame events ========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ======== 2. Get pose data ========
        frame, pose = cam.get_frame_and_pose()
        if frame is None:
            break

        detection = detector.update(pose)
        cmds = controller.update(detection)

        # ======== 3. Apply to Mario ========
        mario.apply_input(cmds["left"], cmds["right"], cmds["jump"])
        all_sprites.update()

        # ======== 4. Draw game ========
        screen.fill((135, 206, 235))  # sky blue
        pygame.draw.rect(screen, (100, 180, 100), (0, 400, 800, 50))  # ground
        all_sprites.draw(screen)
        pygame.display.flip()

        # ======== 5. Show webcam window ========

        cv2.imshow("Webcam Pose", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        clock.tick(30)

    cam.release()
    pygame.quit()

if __name__ == "__main__":
    main()
