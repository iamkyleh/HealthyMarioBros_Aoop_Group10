# client.py
import socket
import pygame
from net import send_json, recv_json

HOST = "127.0.0.1"   # change to your server IP
PORT = 65432
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (220, 50, 50)

def draw_cloud(screen, x, y):
    pygame.draw.ellipse(screen, WHITE, (x, y, 100, 40))
    pygame.draw.ellipse(screen, WHITE, (x + 30, y - 10, 120, 50))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Healthy Mario Bros (Client)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)
    big_font = pygame.font.SysFont(None, 64)

    # Networking
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    client_id = None
    name = None
    platforms = []

    # Receive welcome and init
    msg = recv_json(s)
    if msg and msg.get("type") == "welcome":
        client_id = msg.get("client_id")
        name = msg.get("name")
    init_msg = recv_json(s)
    if init_msg and init_msg.get("type") == "init":
        platforms = init_msg.get("platforms", [])

    camera_x = 0
    running = True
    latest_state = None

    while running:
        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        # Map keyboard to movement/attack
        movement = 0
        attack = False
        # Move left/right
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            movement = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            movement = 1
        # Attack key (space)
        if keys[pygame.K_SPACE]:
            attack = True

        # Send input
        try:
            send_json(s, {"movement": movement, "attack": attack})
        except Exception:
            running = False
            break

        # Receive latest state (non-blocking style: one per frame)
        state_msg = recv_json(s)
        if state_msg and state_msg.get("type") == "state":
            latest_state = state_msg["data"]
            camera_x = latest_state.get("camera_x", 0)

        # Draw
        screen.fill(SKY_BLUE)
        # Parallax clouds
        for i in range(10):
            cx = (i * 200 - int(camera_x * 0.5)) % (SCREEN_WIDTH + 100) - 50
            cy = 80 + (i % 3) * 30
            draw_cloud(screen, cx, cy)

        # Platforms
        for p in platforms:
            rect = pygame.Rect(p["x"] - camera_x, p["y"], p["w"], p["h"])
            color = (120, 120, 120) if (p["w"] == 60 and p["h"] == 60) else (160, 100, 60)
            pygame.draw.rect(screen, color, rect)

        # Entities from server state
        if latest_state:
            # Coins
            for c in latest_state["coins"]:
                if not c["collected"]:
                    pygame.draw.circle(screen, (255, 200, 0), (int(c["x"] - camera_x), int(c["y"])), 8)

            # Enemies
            for e in latest_state["enemies"]:
                if e["alive"]:
                    pygame.draw.rect(screen, RED, (e["x"] - camera_x, e["y"], e["w"], e["h"]))

            # Flags
            for f in latest_state["flags"]:
                color = (50, 180, 50) if f["checkpoint_touched"] else (50, 120, 50)
                pygame.draw.rect(screen, color, (f["x"] - camera_x, f["y"], f["w"], f["h"]))
            ff = latest_state["flag_final"]
            pygame.draw.rect(screen, (30, 160, 30), (ff["x"] - camera_x, ff["y"], ff["w"], ff["h"]))

            # Players
            y_ui = 16
            for p in latest_state["players"]:
                pygame.draw.rect(screen, (0, 0, 0), (p["x"] - camera_x, p["y"], p["w"], p["h"]))
                lives_ui = font.render(f"{p['name']} X {p['lives']}", True, BLACK)
                screen.blit(lives_ui, (16, y_ui))
                y_ui += font.get_linesize()

            # Score and win message
            score_ui = font.render(f"Score: {latest_state['score']}", True, BLACK)
            screen.blit(score_ui, (650, 16))
            if latest_state["won"]:
                msg = big_font.render("YOU REACHED THE FLAG!", True, BLACK)
                screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 80))

        # Mouse debug
        mx, my = pygame.mouse.get_pos()
        wx = mx + camera_x
        text = font.render(f"S:({mx},{my})  W:({wx},{my})", True, (0, 0, 0))
        screen.blit(font.render(f"S:({mx},{my})  W:({wx},{my})", True, (255, 255, 255)), (11, SCREEN_HEIGHT - 31))
        screen.blit(text, (10, SCREEN_HEIGHT - 32))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    s.close()

if __name__ == "__main__":
    main()
