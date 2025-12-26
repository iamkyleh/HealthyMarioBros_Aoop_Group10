# client.py
import socket
import pygame
import math
import threading
import cv2
from net import send_json, recv_json
import addpath
import time
from detection.jump_detector import JumpDetector
from detection.pose_camera import PoseCamera
from detection.hand_detector import HandDetector
from detection.attack_detector import AttackDetector

HOST = "192.168.0.128"
PORT = 5000

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (220, 50, 50)

START_TIME = time.time()*1000
def now():
    return time.time()*1000

img_dic = {
    "Brick": (32, 32),
    "Pipe": (60, 60),
    "Coin": (20, 28),
    "Goomba": (32, 32),
    "KoopaTroopa": (32, 46),
    "KoopaTroopaShell": (32, 28),
    "Mario": (24, 32),
    "Luigi": (24, 32),
    "MushroomRetainer": (24, 32),
    "Flag": (48, 144),
    "Flag_Mario": (48, 144),
    "Flag_Luigi": (48, 144),
    "Flag_MushroomRetainer": (48, 144),
    "Flag_final": (48, 256),
    "Flag_final_Mario": (48, 256),
    "Flag_final_Luigi": (48, 256),
    "Flag_final_MushroomRetainer": (48, 256)
}

def load_image(name, size=None):
    """Load an image by name (e.g., 'Brick.png'); optionally scale to size=(w,h)."""
    try:
        img = pygame.image.load(addpath.image_path(name)).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception as e:
        print(f"Failed to load image '{name}': {e}")
        return None

def draw_tiled(surface, image, p, camera_x):
    img_w, img_h = image.get_width(), image.get_height()
    for y in range(p.top, p.bottom, img_h):
        for x in range(p.left, p.right, img_w):
            surface.blit(image, (x - camera_x, y))

class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Healthy Mario Bros (Client)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 64)

        # Player / world state
        self.platforms = {"brick": [], "pipe": []}
        self.flags = []  # Store flag positions from init
        self.flag_final = None  # Store final flag position from init
        self.camera_x = 0
        self.latest_state = None
        self.running = True

        # Networking fields
        self.s = None
        self.client_id = None
        self.name = None
        self.role = None  # "P" for player or "O" for observer

        # Load images
        self._load_img()
        
        self._init_networking()

    # -------------------- Networking ------------------------
    def _init_networking(self):
        # Ask user for role FIRST, before connecting
        while True:
            role_input = input("Enter your role [P (player) / O (observer)]: ").strip().upper()
            if role_input in ["P", "O"]:
                self.role = role_input
                break
            print("Invalid role. Please enter 'P' for player or 'O' for observer.")
        
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Enable TCP_NODELAY for low latency
            self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # For initial connection, use a longer timeout to ensure welcome message is received
            self.s.settimeout(10.0)  # 10 second timeout for initial connection
            
            # Connect to server (same port for both players and observers)
            print(f"Connecting to server on {HOST}:{PORT}...")
            self.s.connect((HOST, PORT))
            print("Connected! Sending role...")
            
            # Send role to server immediately after connecting
            send_json(self.s, {"role": self.role})
            print(f"Role '{self.role}' sent to server. Waiting for welcome message...")

            # Welcome packet with platform data - wait with longer timeout
            # Try multiple times in case of timing issues
            msg = None
            for attempt in range(3):
                msg = recv_json(self.s, timeout=5.0)  # Wait up to 5 seconds for welcome
                if msg:
                    break
                print(f"Attempt {attempt + 1} failed, retrying...")
                import time
                time.sleep(0.1)  # Small delay before retry
            
            if msg and "welcome" in msg:
                if "platform" in msg:
                    self.platforms = msg["platform"]
                if "flag" in msg:
                    self.flags = msg["flag"]  # Store flag positions
                if "flag_final" in msg:
                    self.flag_final = msg["flag_final"]  # Store final flag position
                if "player_name" in msg:
                    self.name = msg["player_name"]
                if "role" in msg:
                    self.role = msg["role"]
                role_name = "player" if self.role == "P" else "observer"
                print(f"Connected as {role_name}" + (f" ({self.name})" if self.name else ""))
            else:
                print(f"Failed to receive welcome message. Received: {msg}")
                if msg:
                    print(f"Message keys: {msg.keys() if isinstance(msg, dict) else 'Not a dict'}")
                self.running = False
                return
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False
            return
        
        # Initialize jump detection (only for players)
        if self.role == "P":
            self.jump_detector = JumpDetector()
            self.hand_detector = HandDetector()
            self.attack_detector = AttackDetector()
            self.pose_camera = PoseCamera()
            self.pose_jump_detected = False
            self.attack_detected = False
            self.jump_count = 0
            self.attack_count = 0
            self.pose_move = 0  # -1 left, 0 none, 1 right
            
            # Start camera thread for jump detection
            self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()

        
        # Now switch to non-blocking mode for game loop
        self.s.settimeout(0.01)  # 10ms timeout for game loop

    def _camera_loop(self):
        """Camera loop for pose detection and jump detection"""
        while self.running:
            frame, hip_y, pose_landmarks = self.pose_camera.get_frame_and_y()
            if frame is None:
                break
            
            # Check for jump detection
            if self.jump_detector.update(hip_y):
                self.pose_jump_detected = True
                self.jump_count += 1
            
            # Check for attack detection
            if self.attack_detector.detect_attack(frame):
                self.attack_detected = True
                self.attack_count += 1
            
            # Check for hand detection
            hand_move = self.hand_detector.update(pose_landmarks, self.pose_camera.mp_pose)
            if hand_move == "right":
                self.pose_move = 1
            elif hand_move == "left":
                self.pose_move = -1
            else:
                self.pose_move = 0
            
            # Add count overlays
            cv2.putText(frame, f"Jumps: {self.jump_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Attacks: {self.attack_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display camera feed
            cv2.imshow("Pose Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.pose_camera.release()
        self.attack_detector.release()

    # -------------------- Game Loop -------------------------
    def run(self):
        while self.running:
            self._handle_events()
            # Receive state first (non-blocking)
            self._receive_state()
            # Then send input
            self._send_input()
            # Draw
            self._draw()
            self.clock.tick(FPS)
        pygame.quit()
        cv2.destroyAllWindows()
        self.s.close()

    # -------------------- Event Handling --------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    # --------------------- Input Send -----------------------
    def _send_input(self):
        # Only send input if this client is a player
        if self.role != "P":
            return
            
        # Check if socket is still valid
        if self.s is None or not self.running:
            return
            
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move = 1
        
        # Override with pose move if detected
        if self.pose_move != 0:
            move = self.pose_move
        
        jump = bool(keys[pygame.K_UP] or keys[pygame.K_w] or self.pose_jump_detected)
        
        # Reset pose jump flag after using it
        if self.pose_jump_detected:
            self.pose_jump_detected = False
            
        attack = bool(keys[pygame.K_SPACE] or self.attack_detected)
        
        # Reset attack flag after using it
        if self.attack_detected:
            self.attack_detected = False
        
        # Only send if input changed or every few frames to reduce network traffic
        current_input = {"move": move, "jump": jump, "attack": attack}
        if not hasattr(self, '_last_input') or self._last_input != current_input:
            try:
                # Format according to format.txt: {"mario": {...}, "luigi": {...}}
                # Send input with player name as key
                if self.name:
                    send_json(self.s, {self.name: current_input})
                else:
                    # Fallback if name not received
                    send_json(self.s, current_input)
                self._last_input = current_input
            except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
                # Connection lost - stop trying to send
                print(f"Connection lost: {e}")
                self.running = False
            except Exception as e:
                # Other errors - log but don't necessarily stop
                print(f"Error sending input: {e}")
                # Only stop on critical errors
                if "10053" in str(e) or "10054" in str(e) or "Connection" in str(type(e).__name__):
                    self.running = False

    # -------------------- RECEIVE STATE ---------------------
    def _receive_state(self):
        """Receive state updates (non-blocking, won't stall game loop)"""
        if self.s is None or not self.running:
            return
            
        try:
            # Try to receive multiple messages if available (catch up on missed frames)
            for _ in range(5):  # Max 5 messages per frame to prevent lag
                msg = recv_json(self.s, timeout=0.001)  # Very short timeout
                if msg is None:
                    break  # No more data available
                if "status" in msg:  # Check if it's a state update
                    self.latest_state = msg
                elif "welcome" in msg:
                    # Handle welcome message if received late
                    if "platform" in msg:
                        self.platforms = msg["platform"]
                    if "flag" in msg:
                        self.flags = msg["flag"]
                    if "flag_final" in msg:
                        self.flag_final = msg["flag_final"]
                    if "player_name" in msg:
                        self.name = msg["player_name"]
        except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
            # Connection lost
            print(f"Connection lost while receiving: {e}")
            self.running = False
        except Exception as e:
            # Only stop on actual connection errors, not timeouts
            err_str = str(e).lower()
            if "timed out" not in err_str and "10060" not in str(e):
                # Check for connection abort errors
                if "10053" in str(e) or "10054" in str(e) or "connection" in err_str:
                    print(f"Connection error: {e}")
                    self.running = False

    # -------------------- DRAW FUNCTIONS --------------------
    def _draw_cloud(self, x, y):
        pygame.draw.ellipse(self.screen, WHITE, (x, y, 100, 40))
        pygame.draw.ellipse(self.screen, WHITE, (x + 30, y - 10, 120, 50))

    def _load_img(self):
        self.image = {}
        for name, s in img_dic.items():
            self.image[name] = load_image(f"{name}.png", s)
        missing = False
        for name, img in self.image.items():
            if not img:
                missing = True
                print(f"ERROR: Failed loading image {name}")
        if missing:
            pygame.quit()

    def _draw(self):
        self.screen.fill(SKY_BLUE)
        # --- CLOUD BACKGROUND ---
        for i in range(10):
            cx = (i * 200 - int(self.camera_x * 0.5)) % (SCREEN_WIDTH + 100) - 50
            cy = 80 + (i % 3) * 30
            self._draw_cloud(cx, cy)

        # Draw platforms (always available from init)
        self._draw_platform_and_pipe()
        
        # check if we have a latest state
        if self.latest_state:
            # Update camera from state
            self.camera_x = self.latest_state.get("camera_x", 0)
            self._draw_entities()
            self._draw_props()
            self._draw_status()
        else:
            # Show waiting message
            waiting_text = self.font.render("Waiting for game state...", True, BLACK)
            self.screen.blit(waiting_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))

        pygame.display.flip()

    def _draw_platform_and_pipe(self):
        # Use stored platform data from init
        for b in self.platforms["brick"]:
            rect = pygame.Rect(b["x"], b["y"], b["w"], b["h"])
            draw_tiled(self.screen, self.image["Brick"], rect, self.camera_x)
        for p in self.platforms["pipe"]:
            rect = pygame.Rect(p["x"], p["y"], p["w"], p["h"])
            self.screen.blit(self.image["Pipe"], (p["x"] - self.camera_x, p["y"]))
        
        # Draw flags - use stored positions, update name from state
        flag_statuses = []
        if self.latest_state and "prop" in self.latest_state:
            flag_statuses = self.latest_state["prop"].get("flag", [])
        
        for i, flag_pos in enumerate(self.flags):
            # Get status from state if available, otherwise use empty string
            flag_name = ""
            if i < len(flag_statuses):
                flag_name = flag_statuses[i].get("name", "")
            
            if flag_name:
                img_name = f"Flag_{flag_name}"
            else:
                img_name = "Flag"
            img = self.image.get(img_name, self.image["Flag"])
            # Use stored position adjusted by camera
            x = flag_pos["x"] - self.camera_x
            y = flag_pos["y"]
            self.screen.blit(img, (x, y))
        
        # Draw final flag - use stored position, update name from state
        if self.flag_final:
            flag_final_status = None
            if self.latest_state and "prop" in self.latest_state:
                flag_final_status = self.latest_state["prop"].get("flag_final")
            
            flag_name = ""
            if flag_final_status:
                flag_name = flag_final_status.get("name", "")
            
            if flag_name:
                img_name = f"Flag_final_{flag_name}"
            else:
                img_name = "Flag_final"
            img = self.image.get(img_name, self.image["Flag_final"])
            # Use stored position adjusted by camera
            x = self.flag_final["x"] - self.camera_x
            y = self.flag_final["y"]
            self.screen.blit(img, (x, y))

    def _draw_entities(self):
        if "entity" not in self.latest_state:
            return
        ent = self.latest_state["entity"]
        for name, parameters in ent.items():
            # Handle goombas with indexed names
            name = name.split("_")[0]
            img = self.image.get(name)
            if img:
                if parameters["dir"] == -1:
                    img = pygame.transform.flip(img, True, False)
                self.screen.blit(img, (parameters["x"], parameters["y"]))
    
    def _draw_props(self):
        if "prop" not in self.latest_state:
            return
        props = self.latest_state["prop"]
        
        # Draw coins
        for c in props.get("coin", []):
            img = self.image["Coin"]
            scale = abs(math.sin(c["rotate"]))
            scaled_w = max(2, int(img.get_width() * scale))
            scaled_img = pygame.transform.scale(img, (scaled_w, img.get_height()))
            x = c["x"] + (img.get_width() - scaled_w) // 2
            y = c["y"]
            self.screen.blit(scaled_img, (x, y))
    
    def _draw_status(self):
        y = 16
        for p_name, p_status in self.latest_state["player_lives"].items():
            test = self.font.render(f"{p_name} X {p_status}", True, BLACK)
            self.screen.blit(test, (16, y))
            y += self.font.get_linesize()

        score_text = self.font.render(f"Score: {self.latest_state['score']}", True, BLACK)
        self.screen.blit(score_text, (650, 16))


if __name__ == "__main__":
    print("!!! NOTICE !!!\nCheck the HOST is on the correct IP address.\nPlace it with IPv4 address of the server.")
    GameClient().run()
