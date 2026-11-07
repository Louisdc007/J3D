"""Décors interactifs du donjon : torches murales et coffres."""
import math
import random
import pygame
from settings import *


class Torch(pygame.sprite.Sprite):
    """Torche murale : source de lumière vacillante + braises."""
    _frames = None

    def __init__(self, pos, groups):
        super().__init__(groups)
        if Torch._frames is None:
            Torch._frames = [self._make_frame(i) for i in range(6)]
        self.frame = random.random() * 6
        self.image = Torch._frames[0]
        # La torche est posée sur la face basse du mur
        self.rect = self.image.get_rect(midbottom=(pos[0] + TILE_SIZE // 2, pos[1] + TILE_SIZE - 6))
        self.light_pos = (self.rect.centerx, self.rect.top + 8)
        self.seed = random.random() * 100
        self.ember_t = random.random()
        self.is_prop = True

    @staticmethod
    def _make_frame(i):
        s = pygame.Surface((20, 40), pygame.SRCALPHA)
        # support
        pygame.draw.rect(s, (60, 40, 25), (8, 18, 4, 20))
        pygame.draw.rect(s, (90, 90, 100), (5, 16, 10, 4))
        # flamme
        h = 14 + (i % 3) * 2
        w = 10 - (i % 2) * 2
        sway = [-1, 0, 1, 0, -1, 1][i]
        pygame.draw.ellipse(s, (255, 120, 30), (5 + sway, 16 - h, w, h + 2))
        pygame.draw.ellipse(s, (255, 210, 90), (7 + sway, 18 - h + 4, w - 4, h - 4))
        pygame.draw.ellipse(s, (255, 255, 220), (8 + sway, 18 - h + 8, 3, max(2, h - 10)))
        return s

    def flicker(self, t):
        return 1 + 0.08 * math.sin(t * 9 + self.seed) + 0.05 * math.sin(t * 23 + self.seed * 2)

    def update(self, dt=0.016):
        self.frame = (self.frame + dt * 10) % 6
        self.image = Torch._frames[int(self.frame)]
        self.ember_t += dt
        if self.ember_t > 0.25:
            self.ember_t = 0
            from fx import fx
            fx.particles.embers(self.light_pos[0], self.light_pos[1] - 6, 1, spread_x=3)


class Chest(pygame.sprite.Sprite):
    """Coffre au trésor ; s'ouvre avec la touche E. Peut être une mimique !"""
    _closed = None
    _open = None

    def __init__(self, pos, groups, tier_bonus=0, mimic=False):
        super().__init__(groups)
        if Chest._closed is None:
            Chest._closed = self._draw(False)
            Chest._open = self._draw(True)
        self.image = Chest._closed
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-6, -10)
        self.opened = False
        self.mimic = mimic
        self.tier_bonus = tier_bonus
        self.wobble = 0.0
        self.is_prop = True

    @staticmethod
    def _draw(opened):
        s = pygame.Surface((48, 44), pygame.SRCALPHA)
        wood, wood_d, metal, gold = (120, 72, 36), (78, 44, 22), (70, 70, 80), (230, 190, 70)
        pygame.draw.rect(s, wood_d, (2, 18, 44, 24), border_radius=4)
        pygame.draw.rect(s, wood, (4, 20, 40, 20), border_radius=3)
        for x in (4, 40):
            pygame.draw.rect(s, metal, (x, 18, 4, 24))
        if opened:
            pygame.draw.rect(s, (20, 10, 5), (6, 14, 36, 8))
            pygame.draw.ellipse(s, gold, (10, 12, 28, 10))
            pygame.draw.rect(s, wood_d, (2, 0, 44, 12), border_radius=4)
            pygame.draw.rect(s, wood, (4, 2, 40, 8), border_radius=3)
        else:
            pygame.draw.rect(s, wood_d, (2, 8, 44, 14), border_radius=6)
            pygame.draw.rect(s, wood, (4, 10, 40, 10), border_radius=5)
            pygame.draw.rect(s, metal, (2, 18, 44, 3))
            pygame.draw.rect(s, gold, (20, 16, 8, 9), border_radius=2)
            pygame.draw.rect(s, (60, 40, 10), (23, 20, 2, 3))
        return s

    def open(self):
        self.opened = True
        self.image = Chest._open

    def update(self, dt=0.016):
        if not self.opened:
            self.wobble += dt
            if self.mimic and int(self.wobble * 2) % 5 == 0:
                # une mimique tremble légèrement... aux plus attentifs de le voir
                self.rect.centerx = self.hitbox.centerx + random.choice((-1, 0, 1))
            else:
                self.rect.centerx = self.hitbox.centerx
