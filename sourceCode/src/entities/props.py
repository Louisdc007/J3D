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


class Breakable(pygame.sprite.Sprite):
    """Tonneau ou jarre : bloque le passage, se brise d'un coup et lâche parfois du butin."""
    _imgs = {}

    def __init__(self, pos, groups, kind=None):
        super().__init__(groups)
        self.kind = kind or random.choice(('barrel', 'barrel', 'jar'))
        if not Breakable._imgs:
            Breakable._imgs = {'barrel': self._draw_barrel(), 'jar': self._draw_jar()}
        self.image = Breakable._imgs[self.kind]
        self.rect = self.image.get_rect(center=pos)
        # le rect sert aussi d'obstacle : on le réduit à la base de l'objet
        self.hitbox = pygame.Rect(0, 0, 34, 26)
        self.hitbox.midbottom = self.rect.midbottom
        self.rect = self.hitbox.copy()
        self.draw_rect = self.image.get_rect(midbottom=self.hitbox.midbottom)
        self.is_prop = True

    @staticmethod
    def _draw_barrel():
        s = pygame.Surface((40, 46), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 80), (2, 38, 36, 8))
        pygame.draw.rect(s, (110, 66, 34), (5, 6, 30, 36), border_radius=8)
        for x in (11, 19, 27):
            pygame.draw.line(s, (85, 50, 25), (x, 8), (x, 40), 1)
        for y in (12, 34):
            pygame.draw.rect(s, (80, 80, 90), (4, y, 32, 4))
        pygame.draw.ellipse(s, (135, 85, 45), (6, 2, 28, 10))
        pygame.draw.ellipse(s, (90, 55, 28), (6, 2, 28, 10), 2)
        return s

    @staticmethod
    def _draw_jar():
        s = pygame.Surface((40, 46), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 80), (4, 38, 32, 8))
        pygame.draw.ellipse(s, (150, 90, 60), (5, 12, 30, 32))
        pygame.draw.rect(s, (150, 90, 60), (13, 4, 14, 12))
        pygame.draw.ellipse(s, (120, 70, 45), (11, 2, 18, 6))
        pygame.draw.arc(s, (200, 140, 90), (9, 16, 14, 20), 1.8, 3.4, 2)
        pygame.draw.line(s, (110, 60, 40), (8, 28), (32, 28), 2)
        return s


class SpikeTrap(pygame.sprite.Sprite):
    """Piège à pointes : s'arme (pointes visibles), sort, puis se rétracte.
    Blesse aussi les monstres !"""
    _frames = None
    CYCLE = (('down', 1.7), ('warn', 0.55), ('up', 0.6))

    def __init__(self, pos, groups):
        super().__init__(groups)
        if SpikeTrap._frames is None:
            SpikeTrap._frames = {k: self._draw(k) for k in ('down', 'warn', 'up')}
        self.phase_i = random.randrange(3)
        self.t = random.uniform(0, self.CYCLE[self.phase_i][1])
        self.image = SpikeTrap._frames[self.phase]
        self.rect = self.image.get_rect(topleft=pos)
        self.is_ground = True
        self.hit_ids = set()

    @property
    def phase(self):
        return self.CYCLE[self.phase_i][0]

    @staticmethod
    def _draw(state):
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 56, 62), (4, 4, 56, 56), border_radius=4)
        pygame.draw.rect(s, (40, 36, 42), (4, 4, 56, 56), 2, border_radius=4)
        for i in range(3):
            for j in range(3):
                cx, cy = 14 + i * 18, 14 + j * 18
                pygame.draw.circle(s, (20, 18, 22), (cx, cy), 4)
                if state == 'warn':
                    pygame.draw.polygon(s, (170, 170, 180), [(cx - 3, cy + 2), (cx + 3, cy + 2), (cx, cy - 4)])
                elif state == 'up':
                    pygame.draw.polygon(s, (215, 215, 225), [(cx - 5, cy + 4), (cx + 5, cy + 4), (cx, cy - 14)])
                    pygame.draw.line(s, (255, 255, 255), (cx, cy - 13), (cx - 2, cy + 2), 1)
        return s

    def update(self, dt=0.016):
        if dt <= 0:
            return
        self.t += dt
        if self.t >= self.CYCLE[self.phase_i][1]:
            self.t = 0.0
            self.phase_i = (self.phase_i + 1) % 3
            self.image = SpikeTrap._frames[self.phase]
            if self.phase == 'up':
                self.hit_ids.clear()
                self.just_sprung = True

    def hurts(self, rect):
        return self.phase == 'up' and self.rect.inflate(-14, -14).colliderect(rect)


SHRINE_BUFFS = {
    'rage': ("Autel de Rage", "+50 % de dégâts", (255, 90, 60)),
    'haste': ("Autel de Célérité", "+30 % de vitesse, esquive rechargée", (120, 220, 255)),
    'vitality': ("Autel de Vitalité", "Régénère vos PV", (110, 255, 130)),
    'fortune': ("Autel de Fortune", "Butin des monstres doublé", (255, 215, 80)),
}


class Shrine(pygame.sprite.Sprite):
    """Autel : touche E pour recevoir une bénédiction temporaire."""

    def __init__(self, pos, groups):
        super().__init__(groups)
        self.buff = random.choice(list(SHRINE_BUFFS))
        self.color = SHRINE_BUFFS[self.buff][2]
        self.used = False
        self.t = random.random() * 6
        self.image = self._draw(False)
        self.hitbox = pygame.Rect(0, 0, 44, 30)
        self.hitbox.center = pos
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)
        self.light_pos = (self.rect.centerx, self.rect.top + 14)
        self.light_color = tuple(int(c * 0.8) for c in self.color)
        self.light_radius = 200
        self.is_prop = True

    def _draw(self, used):
        s = pygame.Surface((56, 76), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 90), (4, 64, 48, 12))
        pygame.draw.polygon(s, (80, 76, 90), [(8, 70), (48, 70), (42, 58), (14, 58)])
        pygame.draw.rect(s, (110, 104, 122), (18, 24, 20, 36))
        pygame.draw.rect(s, (70, 66, 80), (18, 24, 20, 36), 2)
        pygame.draw.rect(s, (130, 124, 140), (12, 18, 32, 8))
        col = (70, 70, 80) if used else self.color
        pygame.draw.polygon(s, col, [(28, 0), (38, 12), (28, 20), (18, 12)])
        if not used:
            pygame.draw.polygon(s, (255, 255, 255), [(28, 3), (32, 9), (28, 12), (24, 9)])
            for i in range(3):
                pygame.draw.line(s, col, (24 + i * 4, 32), (24 + i * 4, 52), 1)
        return s

    def use(self):
        self.used = True
        self.image = self._draw(True)
        self.light_radius = 0

    def flicker(self, t):
        return 0.0 if self.used else 1 + 0.12 * math.sin(t * 3 + self.t)

    def update(self, dt=0.016):
        if self.used:
            return
        self.t += dt
        if random.random() < 0.15:
            from fx import fx
            fx.particles.emit(self.rect.centerx, self.rect.top + 10, 1, self.color, speed=(10, 40),
                              life=(0.6, 1.2), size=(1.5, 3), gravity=-60, glow=True, jitter=10)
