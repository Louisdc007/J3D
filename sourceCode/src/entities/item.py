import math
import random
import pygame

# ---------------------------------------------------------------------------
# Icônes procédurales (aucun asset requis)
# ---------------------------------------------------------------------------
_ICONS = {}

ITEM_GLOW = {
    'gold': (120, 90, 20),
    'iron': (60, 70, 90),
    'xp': (14, 60, 44),
    'health': (130, 20, 30),
    'artifact': (200, 20, 60),
    'potion': (140, 20, 60),
}


def _coin_frames():
    frames = []
    for i in range(8):
        w = max(2, int(18 * abs(math.cos(i / 8 * math.pi))))
        s = pygame.Surface((20, 20), pygame.SRCALPHA)
        r = pygame.Rect(0, 0, w, 18)
        r.center = (10, 10)
        pygame.draw.ellipse(s, (150, 100, 10), r)
        pygame.draw.ellipse(s, (255, 205, 50), r.inflate(-2, -2))
        if w > 8:
            pygame.draw.ellipse(s, (255, 240, 150), r.inflate(-w // 2, -10).move(-1, -2))
            pygame.draw.line(s, (190, 140, 20), (10, 6), (10, 14), 2)
        frames.append(s)
    return frames


def _iron_icon():
    s = pygame.Surface((22, 16), pygame.SRCALPHA)
    pygame.draw.polygon(s, (70, 72, 80), [(3, 14), (19, 14), (16, 3), (6, 3)])
    pygame.draw.polygon(s, (170, 172, 180), [(5, 12), (17, 12), (15, 5), (7, 5)])
    pygame.draw.line(s, (230, 232, 240), (7, 5), (15, 5), 1)
    return s


def _xp_icon():
    s = pygame.Surface((14, 14), pygame.SRCALPHA)
    pygame.draw.circle(s, (40, 160, 110), (7, 7), 6)
    pygame.draw.circle(s, (120, 255, 190), (7, 7), 4)
    pygame.draw.circle(s, (230, 255, 240), (5, 5), 2)
    return s


def _health_icon():
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    pygame.draw.circle(s, (200, 30, 40), (5, 5), 5)
    pygame.draw.circle(s, (200, 30, 40), (13, 5), 5)
    pygame.draw.polygon(s, (200, 30, 40), [(0, 6), (18, 6), (9, 16)])
    pygame.draw.circle(s, (255, 140, 140), (4, 4), 2)
    return s


def _artifact_icon():
    s = pygame.Surface((26, 30), pygame.SRCALPHA)
    pts = [(13, 0), (25, 10), (13, 30), (1, 10)]
    pygame.draw.polygon(s, (120, 0, 20), pts)
    pygame.draw.polygon(s, (230, 30, 60), [(13, 3), (22, 10), (13, 25), (4, 10)])
    pygame.draw.polygon(s, (255, 150, 170), [(13, 3), (17, 9), (9, 9)])
    return s


def _potion_icon():
    s = pygame.Surface((18, 24), pygame.SRCALPHA)
    pygame.draw.rect(s, (120, 80, 40), (6, 0, 6, 4))
    pygame.draw.rect(s, (200, 200, 215), (6, 4, 6, 6))
    pygame.draw.circle(s, (210, 30, 60), (9, 15), 8)
    pygame.draw.circle(s, (255, 150, 170), (6, 12), 2)
    return s


def get_icon(kind):
    if not _ICONS:
        _ICONS['gold'] = _coin_frames()
        _ICONS['iron'] = [_iron_icon()]
        _ICONS['xp'] = [_xp_icon()]
        _ICONS['health'] = [_health_icon()]
        _ICONS['artifact'] = [_artifact_icon()]
        _ICONS['potion'] = [_potion_icon()]
    return _ICONS.get(kind, _ICONS['xp'])


class Item(pygame.sprite.Sprite):
    def __init__(self, pos, groups, type, burst=False):
        super().__init__(groups)

        self.type = type
        self.multiplayer_id = None  # Set when synced

        self.frames = get_icon(type)
        self.frame_index = random.random() * len(self.frames)
        self.image = self.frames[0]
        self.base_pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=pos)
        # Hitbox widened to 40x40 for easy pickup in multiplayer
        self.hitbox = self.rect.inflate(24, 24)
        self.bob = random.uniform(0, math.tau)
        self.glow_color = ITEM_GLOW.get(type, (60, 60, 60))

        # petit "pop" à l'apparition : l'objet est projeté puis retombe
        self.vel = pygame.math.Vector2(0, 0)
        self.height = 0.0
        self.vz = 0.0
        if burst:
            ang = random.uniform(0, math.tau)
            spd = random.uniform(60, 200)
            self.vel = pygame.math.Vector2(math.cos(ang) * spd, math.sin(ang) * spd)
            self.vz = random.uniform(180, 320)
        self.spawn_time = pygame.time.get_ticks()
        self.magnet_speed = 0.0

    @property
    def pickup_ready(self):
        return pygame.time.get_ticks() - self.spawn_time > 250

    def attract(self, target, dt, radius):
        """Attire l'objet vers le joueur (effet aimant)."""
        if not self.pickup_ready:
            return
        to = pygame.math.Vector2(target) - self.base_pos
        d = to.length()
        if 0 < d < radius:
            self.magnet_speed = min(900, self.magnet_speed + 1800 * dt)
            step = min(d, self.magnet_speed * dt)
            self.base_pos += to.normalize() * step
        else:
            self.magnet_speed = 0.0

    def update(self, dt=0.016):
        if self.vz or self.height > 0:
            self.vz -= 900 * dt
            self.height = max(0.0, self.height + self.vz * dt)
            if self.height == 0.0:
                self.vz = 0.0
        if self.vel.length_squared() > 1:
            self.base_pos += self.vel * dt
            self.vel *= max(0.0, 1 - 5 * dt)
        self.frame_index = (self.frame_index + dt * 10) % len(self.frames)
        self.image = self.frames[int(self.frame_index)]
        self.bob += dt * 4
        y_off = -self.height - abs(math.sin(self.bob)) * 4
        self.rect = self.image.get_rect(center=(self.base_pos.x, self.base_pos.y + y_off))
        self.hitbox.center = (int(self.base_pos.x), int(self.base_pos.y))
