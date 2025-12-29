import json
import time
import os
import glob
import pygame

from .net import send_json, recv_json
from .player import *
from .enemy import *
from .props import *
from .weapon import FireFlower, FireballProjectile
import addpath

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

enemy_classes = {
    "Goomba": Goomba,
    "KoopaTroopa": KoopaTroopa,
}

class GAME:
    """Base GAME class (copied from server.Game)."""
    def __init__(self, filename="world1", pvp_mode=False):
        self.respawn_point = (80, 400)
        self.filename = filename
        self.platforms, self.flags, self.flag_final, self.coins, self.enemies = [], [], None, [], []
        self._load_level(self.filename)
        self.players = []
        self.score = 0
        self.won = False
        self.loose = False
        self.camera_x = 0
        self.pvp_mode = pvp_mode
        self.fireballs = []  # Store all active fireballs

    def reload_level(self, filename):
        """Reload level with new filename"""
        try:
            self.filename = filename
            self.platforms, self.flags, self.flag_final, self.coins, self.enemies = [], [], None, [], []
            self._load_level(self.filename)
            # Reset respawn point
            self.respawn_point = (80, 400)
        except Exception as e:
            print(f"Error reloading level {filename}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _load_level(self, filename):
        with open(addpath.world_path(f"{filename}.json")) as f:
            data = json.load(f)

            # Load platforms
            for p in data["Platforms"]:
                self.platforms.append(pygame.Rect(p["x"], p["y"], p["w"], p["h"]))

            # Load flags
            if "Flags" in data and data["Flags"]:
                for f in data["Flags"]:
                    self.flags.append(Flag(f["x"], f["y"]))

            # Load final flag
            if "Flag_final" in data and data["Flag_final"]:
                self.flag_final = Flag_final(data["Flag_final"]["x"], data["Flag_final"]["y"])

            # Load coins
            if "Coins" in data and data["Coins"]:
                for c in data["Coins"]:
                    self.coins.append(Coin(c["x"], c["y"]))

            # Load enemies
            if "Enemies" in data and data["Enemies"]:
                for e in data["Enemies"]:
                    cls = enemy_classes[e["type"]]
                    enemy = cls(e["x"], e["y"])
                    self.enemies.append(enemy)
        # After loading platforms, compute camera bounds
        self._compute_camera_bounds()

    def _compute_camera_bounds(self):
        """Compute camera min/max values based on platform extents."""
        if not self.platforms:
            self.camera_min = 0
            self.camera_max = 0
            return
        lefts = [p.left for p in self.platforms]
        rights = [p.right for p in self.platforms]
        # Minimum camera_x: don't scroll left past the smallest platform left (usually 0)
        self.camera_min = min(0, min(lefts))
        # Maximum camera_x: rightmost platform edge minus screen width
        level_right = max(rights)
        self.camera_max = max(0, int(level_right - SCREEN_WIDTH))

    def add_player(self, name, pvp_mode=False):
        """Add a new player to the game"""
        player = Player(name, self.respawn_point)
        # Set faction based on PVP mode
        if pvp_mode:
            # Assign unique faction for each player in PVP mode
            player.faction = f"p{len(self.players) + 1}"
        else:
            player.faction = 'P'  # All players same faction in co-op
        # Give player a FireFlower weapon
        player.weapon = FireFlower(owner=player)
        self.players.append(player)
        return player

    def update_camera(self):
        """Update camera position based on players"""
        if not self.players:
            return
        # In PVP mode, camera is handled per-player on client side
        if self.pvp_mode:
            # Just set a default camera for server state (not used in PVP)
            self.camera_x = 0
            return
        # Co-op mode: calculate mean position
        mid = 0
        alive_count = 0
        for player in self.players:
            if player.is_alive:
                mid += player.x
                alive_count += 1
        if alive_count > 0:
            mid //= alive_count
            self.camera_x = int(mid) - SCREEN_WIDTH // 2
            # clamp to computed bounds
            if hasattr(self, 'camera_min'):
                if self.camera_x < self.camera_min:
                    self.camera_x = self.camera_min
            else:
                if self.camera_x < 0:
                    self.camera_x = 0
            if hasattr(self, 'camera_max') and self.camera_x > self.camera_max:
                self.camera_x = self.camera_max

    def get_player_camera(self, player_name):
        """Get individual camera position for a player (used in PVP mode)"""
        for player in self.players:
            if player.name == player_name and player.is_alive:
                camera_x = int(player.x) - SCREEN_WIDTH // 2
                # clamp per-player camera to bounds if available
                if hasattr(self, 'camera_min') and camera_x < self.camera_min:
                    camera_x = self.camera_min
                elif camera_x < 0:
                    camera_x = 0
                if hasattr(self, 'camera_max') and camera_x > self.camera_max:
                    camera_x = self.camera_max
                return camera_x
        return 0

    def handle_collisions_and_rules(self):
        """Handle all game rules and collisions"""
        if self.won or self.loose:
            return

        for player in self.players:
            if not player.is_alive:
                continue
            mrect = player.rect

            # Coins
            for c in self.coins:
                if not c.collected and mrect.colliderect(c.rect):
                    c.collected = True
                    self.score += 100

            # Goombas
            for e in self.enemies:
                if not e.is_alive:
                    continue
                if mrect.colliderect(e.rect):
                    if player.vel_y > 0 and (mrect.bottom - e.rect.top) < 20:
                        # Kill enemy
                        if e.take_damage(his_status=player.status):
                            self.score += e.points
                        player.vel_y = -8
                        player.y -= 5
                    else:
                        # Kill player
                        if e.can_deal_damage:
                            player.take_damage(his_status=e.status, respawn_point=self.respawn_point)

            # Player-to-player collisions
            for p in self.players:
                # Skip self-collision
                if p == player or not p.is_alive:
                    continue
                # Use the player's collision handling method
                player.handle_player_collision(p, self.respawn_point)

            # Flags
            for f in self.flags:
                if not f.is_checkpoint and mrect.colliderect(f.rect):
                    f.update(player.name)
                    self.respawn_point = (f.x, f.y)

            # Final flag
            if self.flag_final and mrect.colliderect(self.flag_final.rect):
                self.won = True
                self.flag_final.update(player.name)

            # Fell off world
            if player.y > 800:
                player.take_damage(from_faction='W', respawn_point=self.respawn_point)
        # Check lose condition: no players alive
        if not any(p.is_alive for p in self.players):
            self.loose = True

    def update(self, player_inputs):
        """Update game state. player_inputs is a dict mapping player names to input dicts"""
        if self.won:
            return

        # Update players and handle fireball attacks
        for player in self.players:
            if player.name in player_inputs:
                inp = player_inputs[player.name]
                player.update(self.platforms, inp)
                # Handle fireball attack
                if inp.get("attack", False) and hasattr(player, 'weapon'):
                    fireball = player.weapon.attack()
                    if fireball:
                        self.fireballs.append(fireball)

        # Update fireballs
        all_entities = list(self.players) + list(self.enemies)
        for fb in self.fireballs[:]:  # Use slice to avoid modification during iteration
            if fb.is_alive:
                fb.update(self.platforms, all_entities)
            if not fb.is_alive:
                self.fireballs.remove(fb)

        # Update enemies
        for e in self.enemies:
            e.update(self.platforms)

        # Update coins
        for c in self.coins:
            c.update()

        # Handle collisions
        self.handle_collisions_and_rules()

        # Update camera
        self.update_camera()

        # Score to lives conversion
        if self.score / 1000 >= 1:
            for p in self.players:
                p.lives += self.score // 1000
            self.score = self.score % 1000

    def get_state_dict(self):
        """Get current game state as a dict matching format.txt"""
        # Note: platform data is sent once in init, not in every update

        # Build entity data
        entities = {}
        for player in self.players:
            if player.is_alive:
                # Check invincibility status
                is_invincible = getattr(player, 'is_invincible', False)
                # In PVP mode, use individual camera, otherwise use shared camera
                if self.pvp_mode:
                    player_camera_x = self.get_player_camera(player.name)
                    entities[player.name] = {
                        "x": float(player.x - player_camera_x),
                        "y": float(player.y),
                        "dir": player.direction,
                        "invincible": is_invincible
                    }
                else:
                    entities[player.name] = {
                        "x": float(player.x - self.camera_x),
                        "y": float(player.y),
                        "dir": player.direction,
                        "invincible": is_invincible
                    }

        # Handle enemies - format.txt shows multiple, so we'll use a list approach
        # But since JSON doesn't allow duplicate keys, we'll send them as goomba_0, goomba_1, etc.
        # Or we can send as a list in a different structure. Let's use indexed keys for now.
        for i, enemy in enumerate(self.enemies):
            if enemy.is_alive:
                entities[f"{enemy.name}_{i}"] = {
                    "x": float(enemy.x - self.camera_x),
                    "y": float(enemy.y),
                    "dir": enemy.direction
                }

        # Handle fireballs
        for i, fb in enumerate(self.fireballs):
            if fb.is_alive:
                entities[f"Fireball_{i}"] = {
                    "x": float(fb.x - self.camera_x),
                    "y": float(fb.y),
                    "dir": fb.direction
                }

        # Build prop data
        coins_data = []
        for c in self.coins:
            if not c.collected:
                coins_data.append({
                    "x": float(c.x - self.camera_x),
                    "y": float(c.y),
                    "rotate": c.rotation
                })

        # Only send flag names/status, not positions (positions sent in init)
        flags_data = []
        for f in self.flags:
            flags_data.append({
                "name": f.touched_by if f.touched_by else ""
            })

        flag_final_data = None
        if self.flag_final:
            flag_final_data = {
                "name": self.flag_final.touched_by if self.flag_final.touched_by else ""
            }

        # Build status
        player_lives_data = {}
        for p in self.players:
            player_lives_data[f"{p.name}"] = p.lives

        # In PVP mode, send individual camera positions for each player
        player_cameras = {}
        if self.pvp_mode:
            for player in self.players:
                if player.is_alive:
                    player_cameras[player.name] = self.get_player_camera(player.name)

        return {
            "status": 1,
            "won": self.won,
            "loose": self.loose,
            "player_lives": player_lives_data,
            "score": self.score,
            "entity": entities,
            "prop": {
                "coin": coins_data,
                "flag": flags_data,
                "flag_final": flag_final_data
            },
            "camera_x": self.camera_x,
            "pvp_mode": self.pvp_mode,
            "player_cameras": player_cameras if self.pvp_mode else {}
        }

    def get_init_dict(self):
        """Get initial state dict for format.txt"""
        brick_platforms = []
        pipe_platforms = []
        for p in self.platforms:
            if p.width == 60 and p.height == 60:
                pipe_platforms.append({"x": p.left, "y": p.top, "w": p.width, "h": p.height})
            else:
                brick_platforms.append({"x": p.left, "y": p.top, "w": p.width, "h": p.height})

        # Include flag positions in initial data
        flags_data = []
        for f in self.flags:
            flags_data.append({
                "x": float(f.x),
                "y": float(f.y)
            })

        flag_final_data = None
        if self.flag_final:
            flag_final_data = {
                "x": float(self.flag_final.x),
                "y": float(self.flag_final.y)
            }

        return {
            "welcome": "Welcome to HealthyMarioBros",
            "platform": {
                "brick": brick_platforms,
                "pipe": pipe_platforms
            },
            "flag": flags_data,
            "flag_final": flag_final_data
        }


# Child classes for modes - currently identical, provided for future overrides
class GameAdventure(GAME):
    pass

class GamePVP(GAME):
    pass

class GamePVE(GAME):
    """
    PVE Game Mode: Mario (human player) vs Luigi (RL AI controlled)
    Luigi is an AI opponent that fights against the human player.
    """
    def __init__(self, filename="world_PVE/PVE1", pvp_mode=False):
        super().__init__(filename, pvp_mode=False)
        # PvE: Mario (human) vs Luigi (AI)
        self.players = []
        self.score = 0
        self.won = False
        self.loose = False
        self.camera_x = 0
        self.fireballs = []
        
        # Game constants for observation normalization
        self.max_x = 800
        self.max_y = 600
        self.max_vel = 20
        self.max_lives = 5
        
        # Separate spawn points for each player
        self.mario_spawn = (100, 450)
        self.luigi_spawn = (650, 450)
        
        # Add Mario (human) - spawns on left side
        mario = Player("Mario", self.mario_spawn)
        mario.faction = "P"
        mario.weapon = FireFlower(owner=mario)
        mario.lives = 5
        self.players.append(mario)
        
        # Add Luigi (AI) - spawns on right side
        luigi = Player("Luigi", self.luigi_spawn)
        luigi.faction = "E"  # Enemy faction for PvE
        luigi.weapon = FireFlower(owner=luigi)
        luigi.lives = 5
        self.players.append(luigi)
        
        # RL agent setup
        self._init_rl_agent()
        
        # Fallback AI state
        self.fallback_ai_timer = 0
        self.fallback_ai_action = 0
        
        print(f"[GamePVE] Initialized - Mario (human) vs Luigi (AI)")

    def _init_rl_agent(self):
        """Try to load the trained RL agent for Luigi"""
        import os
        self.rl_model = None
        self.np = None
        
        # Try to load RL agent if available
        try:
            from stable_baselines3 import PPO
            import numpy as np
            self.np = np
            
            # Try multiple possible model paths
            model_paths = [
                os.path.join(os.path.dirname(__file__), "..", "luigi_pve_ai.zip"),
                os.path.join(os.path.dirname(__file__), "..", "best_model.zip"),
                os.path.join(os.path.dirname(__file__), "rl_training", "luigi_pve_ai.zip"),
                "luigi_pve_ai.zip",
                "best_model.zip",
            ]
            
            for model_path in model_paths:
                abs_path = os.path.abspath(model_path)
                if os.path.exists(abs_path):
                    print(f"[GamePVE] Loading RL model from: {abs_path}")
                    self.rl_model = PPO.load(abs_path)
                    print(f"[GamePVE] RL Luigi AI loaded successfully!")
                    return
            
            print("[GamePVE] No trained RL model found. Using fallback AI.")
            print("[GamePVE] Train the AI with: python game/rl_training/train_luigi_pve.py --train")
            
        except ImportError as e:
            print(f"[GamePVE] stable_baselines3 not installed: {e}")
            print("[GamePVE] Install with: pip install stable-baselines3[extra]")
        except Exception as e:
            print(f"[GamePVE] Error loading RL agent: {e}")
            import traceback
            traceback.print_exc()

    def _get_rl_observation(self, mario, luigi):
        """
        Get normalized observation vector matching the training environment.
        Observation space: 16 dimensions
        """
        if mario is None or luigi is None:
            return self.np.zeros(16, dtype=self.np.float32)
        
        # Normalize positions to [-1, 1]
        luigi_x = (luigi.x / self.max_x) * 2 - 1
        luigi_y = (luigi.y / self.max_y) * 2 - 1
        luigi_vel_x = self.np.clip(luigi.vel_x / self.max_vel, -1, 1)
        luigi_vel_y = self.np.clip(luigi.vel_y / self.max_vel, -1, 1)
        luigi_lives = luigi.lives / self.max_lives
        luigi_on_ground = 1.0 if luigi.on_ground else 0.0
        
        mario_x = (mario.x / self.max_x) * 2 - 1
        mario_y = (mario.y / self.max_y) * 2 - 1
        mario_vel_x = self.np.clip(mario.vel_x / self.max_vel, -1, 1)
        mario_vel_y = self.np.clip(mario.vel_y / self.max_vel, -1, 1)
        mario_lives = mario.lives / self.max_lives
        mario_on_ground = 1.0 if mario.on_ground else 0.0
        
        # Relative position and velocity
        distance_x = (mario.x - luigi.x) / self.max_x
        distance_y = (mario.y - luigi.y) / self.max_y
        relative_vel_x = self.np.clip((mario.vel_x - luigi.vel_x) / self.max_vel, -1, 1)
        relative_vel_y = self.np.clip((mario.vel_y - luigi.vel_y) / self.max_vel, -1, 1)
        
        return self.np.array([
            luigi_x, luigi_y, luigi_vel_x, luigi_vel_y, luigi_lives, luigi_on_ground,
            mario_x, mario_y, mario_vel_x, mario_vel_y, mario_lives, mario_on_ground,
            distance_x, distance_y, relative_vel_x, relative_vel_y
        ], dtype=self.np.float32)

    def _action_to_input(self, action):
        """
        Convert discrete action to game input dict.
        Must match the training environment action space.
        Actions: 0=idle, 1=left, 2=right, 3=jump, 4=attack,
                 5=left+jump, 6=right+jump, 7=left+attack, 8=right+attack
        """
        if self.np is not None and isinstance(action, (list, self.np.ndarray)):
            action = int(action[0]) if hasattr(action, '__len__') else int(action)
        else:
            action = int(action)
        
        actions_map = {
            0: {"move": 0, "jump": False, "attack": False},   # idle
            1: {"move": -1, "jump": False, "attack": False},  # left
            2: {"move": 1, "jump": False, "attack": False},   # right
            3: {"move": 0, "jump": True, "attack": False},    # jump
            4: {"move": 0, "jump": False, "attack": True},    # attack
            5: {"move": -1, "jump": True, "attack": False},   # left + jump
            6: {"move": 1, "jump": True, "attack": False},    # right + jump
            7: {"move": -1, "jump": False, "attack": True},   # left + attack
            8: {"move": 1, "jump": False, "attack": True},    # right + attack
        }
        return actions_map.get(action, actions_map[0])

    def _get_fallback_ai_input(self, mario, luigi):
        """
        Simple fallback AI when RL model is not available.
        Implements basic chase and attack behavior.
        """
        import random
        
        if mario is None or luigi is None:
            return {"move": 0, "jump": False, "attack": False}
        
        dx = mario.x - luigi.x
        dy = mario.y - luigi.y
        distance = (dx**2 + dy**2) ** 0.5
        
        # Change action periodically for variety
        self.fallback_ai_timer += 1
        if self.fallback_ai_timer % 30 == 0:
            self.fallback_ai_action = random.randint(0, 8)
        
        # Chase Mario
        move = 0
        if abs(dx) > 30:
            move = 1 if dx > 0 else -1
        
        # Jump when Mario is above or randomly
        jump = False
        if luigi.on_ground:
            if dy < -40:  # Mario is above
                jump = True
            elif random.random() < 0.05:  # Random jump
                jump = True
        
        # Attack when close
        attack = False
        if distance < 120 and random.random() < 0.15:
            attack = True
        
        # Occasionally use combo moves
        if random.random() < 0.1:
            action_id = random.choice([5, 6, 7, 8])  # Combo actions
            return self._action_to_input(action_id)
        
        return {"move": move, "jump": jump, "attack": attack}

    def update(self, player_inputs):
        """Update game state. player_inputs is a dict mapping player names to input dicts"""
        if self.won or self.loose:
            return

        # Get player references
        mario = next((p for p in self.players if p.name == "Mario"), None)
        luigi = next((p for p in self.players if p.name == "Luigi"), None)
        
        # Human Mario input
        if mario and mario.is_alive:
            if mario.name in player_inputs:
                inp = player_inputs[mario.name]
                mario.update(self.platforms, inp)
                if inp.get("attack", False) and hasattr(mario, 'weapon'):
                    fireball = mario.weapon.attack()
                    if fireball:
                        self.fireballs.append(fireball)
            else:
                # No input received - just apply physics
                mario.update(self.platforms, {"move": 0, "jump": False, "attack": False})

        # RL Luigi input (AI)
        if luigi and luigi.is_alive:
            if self.rl_model is not None and self.np is not None:
                # Use trained RL model
                obs = self._get_rl_observation(mario, luigi)
                action, _ = self.rl_model.predict(obs, deterministic=True)
                ai_inp = self._action_to_input(action)
            else:
                # Use fallback AI
                ai_inp = self._get_fallback_ai_input(mario, luigi)
            
            luigi.update(self.platforms, ai_inp)
            if ai_inp.get("attack", False) and hasattr(luigi, 'weapon'):
                fireball = luigi.weapon.attack()
                if fireball:
                    self.fireballs.append(fireball)

        # Update fireballs
        all_entities = list(self.players) + list(self.enemies)
        for fb in self.fireballs[:]:
            if fb.is_alive:
                fb.update(self.platforms, all_entities)
            if not fb.is_alive:
                self.fireballs.remove(fb)

        # Update enemies (if any)
        for e in self.enemies:
            e.update(self.platforms)

        # Update coins
        for c in self.coins:
            c.update()

        # Handle collisions
        self.handle_collisions_and_rules()

        # Update camera (follow Mario)
        self.update_camera()

        # Check win/lose conditions for PVE
        if mario and not mario.is_alive:
            self.loose = True
            print("[GamePVE] Game Over - Mario lost!")
        elif luigi and not luigi.is_alive:
            self.won = True
            print("[GamePVE] Victory - Luigi defeated!")

        # Score to lives conversion
        if self.score / 1000 >= 1:
            for p in self.players:
                if p.is_alive:
                    p.lives += self.score // 1000
            self.score = self.score % 1000
    
    def _get_spawn_point(self, player):
        """Get the appropriate spawn point for a player"""
        if player.name == "Mario":
            return self.mario_spawn
        elif player.name == "Luigi":
            return self.luigi_spawn
        return self.respawn_point
    
    def handle_collisions_and_rules(self):
        """Override to handle PVE-specific collision rules"""
        if self.won or self.loose:
            return

        for player in self.players:
            if not player.is_alive:
                continue
            mrect = player.rect
            spawn_point = self._get_spawn_point(player)

            # Coins
            for c in self.coins:
                if not c.collected and mrect.colliderect(c.rect):
                    c.collected = True
                    self.score += 100

            # Enemies
            for e in self.enemies:
                if not e.is_alive:
                    continue
                if mrect.colliderect(e.rect):
                    if player.vel_y > 0 and (mrect.bottom - e.rect.top) < 20:
                        if e.take_damage(his_status=player.status):
                            self.score += e.points
                        player.vel_y = -8
                        player.y -= 5
                    else:
                        if e.can_deal_damage:
                            player.take_damage(his_status=e.status, respawn_point=spawn_point)

            # Player-to-player collisions (Mario vs Luigi)
            for p in self.players:
                if p == player or not p.is_alive:
                    continue
                player.handle_player_collision(p, spawn_point)

            # Fell off world
            if player.y > 800:
                player.take_damage(from_faction='W', respawn_point=spawn_point)
