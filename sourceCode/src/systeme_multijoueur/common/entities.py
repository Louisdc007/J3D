import pygame
import math

# Importation relative propre : on prend constants.py qui est dans le même dossier !
from .constants import *

class SharedObstacle:
    def __init__(self, x, y, width, height, color, type="wall"):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.type = type

class SharedPlayer:
    def __init__(self, x, y, player_id):
        self.id = player_id
        self.x = x
        self.y = y
        self.width = PLAYER_SIZE
        self.height = PLAYER_SIZE * PLAYER_HEIGHT_MULT
        self.speed = PLAYER_SPEED
        self.state = "idle"
        self.health = PLAYER_MAX_HEALTH
        self.last_move_direction = (0, -1)
        self.roll_direction = (0, 0)
        self.roll_timer = 0
        self.stun_timer = 0
        self.invincible_timer = 0
        self.recoil_vector = pygame.math.Vector2(0, 0)

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update_logic(self, inputs, obstacles):
        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.stun_timer > 0: self.stun_timer -= 1
        
        dx, dy = 0, 0
        if self.stun_timer == 0:
            if self.state == "rolling":
                self.roll_timer -= 1
                if self.roll_timer <= 0: self.state = "idle"
                dx = self.roll_direction[0] * ROLL_SPEED
                dy = self.roll_direction[1] * ROLL_SPEED
            else:
                if inputs.get('z'): dy = -1
                if inputs.get('s'): dy = 1
                if inputs.get('q'): dx = -1
                if inputs.get('d'): dx = 1
                
                if inputs.get('space'): self.start_roll()

                mag = math.sqrt(dx*dx + dy*dy)
                if mag > 0:
                    self.state = "moving"
                    self.last_move_direction = (dx/mag, dy/mag)
                    dx, dy = (dx/mag)*self.speed, (dy/mag)*self.speed
                else:
                    self.state = "idle"
        else:
            self.state = "stunned"

        total_dx = dx + self.recoil_vector.x
        total_dy = dy + self.recoil_vector.y
        self.recoil_vector *= RECOIL_DRAG

        self.x += total_dx
        self.check_collision(obstacles, total_dx, 0)
        self.y += total_dy
        self.check_collision(obstacles, 0, total_dy)
        
        # On utilise WORLD_WIDTH et WORLD_HEIGHT importés proprement
        self.x = max(0, min(self.x, WORLD_WIDTH - self.width))
        self.y = max(0, min(self.y, WORLD_HEIGHT - self.height))

    def check_collision(self, obstacles, dx, dy):
        rect = self.get_rect()
        for obs in obstacles:
            if rect.colliderect(obs.rect):
                if obs.type == "damage" and self.invincible_timer == 0:
                    self.health -= 1
                    self.invincible_timer = INVINCIBILITY_DURATION
                    self.stun_timer = STUN_DURATION
                    self.recoil_vector = pygame.math.Vector2(-self.last_move_direction[0]*8, -self.last_move_direction[1]*8)
                
                if dx > 0: self.x = obs.rect.left - self.width
                elif dx < 0: self.x = obs.rect.right
                if dy > 0: self.y = obs.rect.top - self.height
                elif dy < 0: self.y = obs.rect.bottom

    def start_roll(self):
        if self.state != "rolling" and self.stun_timer == 0:
            self.state = "rolling"
            self.roll_timer = ROLL_DURATION_FRAMES
            self.roll_direction = self.last_move_direction
