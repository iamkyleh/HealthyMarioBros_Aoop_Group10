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
            if "Flags" in data:
                for f in data["Flags"]:
                    self.flags.append(Flag(f["x"], f["y"]))

            # Load final flag
            if "Flag_final" in data:
                self.flag_final = Flag_final(data["Flag_final"]["x"], data["Flag_final"]["y"])

            # Load coins
            if "Coins" in data:
                for c in data["Coins"]:
                    self.coins.append(Coin(c["x"], c["y"]))

            # Load enemies
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
                # In PVP mode, use individual camera, otherwise use shared camera
                if self.pvp_mode:
                    player_camera_x = self.get_player_camera(player.name)
                    entities[player.name] = {
                        "x": float(player.x - player_camera_x),
                        "y": float(player.y),
                        "dir": player.direction
                    }
                else:
                    entities[player.name] = {
                        "x": float(player.x - self.camera_x),
                        "y": float(player.y),
                        "dir": player.direction
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
    pass
