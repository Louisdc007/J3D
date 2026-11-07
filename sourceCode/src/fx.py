"""Effets visuels : particules, éclairage dynamique, textes flottants,
secousses d'écran, hit-stop, cadavres, projectiles et zones d'alerte.

Un gestionnaire unique `fx` est partagé par tout le jeu.
"""
import math
import random
import pygame
from settings import *

# ---------------------------------------------------------------------------
# Polices & texte
# ---------------------------------------------------------------------------
_FONT_CACHE = {}


def get_font(size, bold=False):
    key = (size, bold)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = pygame.font.Font(UI_FONT, size)
        f.set_bold(bold)
        _FONT_CACHE[key] = f
    return f


def render_outlined(text, size, color, outline=(0, 0, 0), width=2, bold=False):
    """Texte avec contour (lisible sur n'importe quel fond)."""
    font = get_font(size, bold)
    base = font.render(text, True, color)
    if width <= 0:
        return base
    edge = font.render(text, True, outline)
    w, h = base.get_width() + width * 2, base.get_height() + width * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for dx in (-width, 0, width):
        for dy in (-width, 0, width):
            if dx or dy:
                surf.blit(edge, (dx + width, dy + width))
    surf.blit(base, (width, width))
    return surf


def draw_panel(surface, rect, alpha=225, border=PANEL_BORDER, radius=10, bg=PANEL_BG):
    """Panneau sombre avec liseré doré, style 'grimoire'."""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*bg, alpha), panel.get_rect(), border_radius=radius)
    # léger dégradé interne
    for i in range(0, rect.height // 2, 3):
        a = int(18 * (1 - i / max(1, rect.height / 2)))
        pygame.draw.line(panel, (255, 255, 255, a), (radius, i), (rect.width - radius, i))
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border, rect, 2, border_radius=radius)
    inner = rect.inflate(-6, -6)
    pygame.draw.rect(surface, (*[max(0, c - 60) for c in border],), inner, 1, border_radius=max(0, radius - 3))


# ---------------------------------------------------------------------------
# Textures de lumière (dégradés radiaux)
# ---------------------------------------------------------------------------
_GLOW_CACHE = {}


def glow_texture(radius, color=(255, 255, 255), falloff=2.0):
    """Dégradé radial RGB (noir sur les bords) destiné au mélange additif."""
    radius = max(4, int(radius))
    # quantification : limite le nombre de textures différentes (cache efficace)
    radius = (radius // 8) * 8 if radius > 64 else (radius // 2) * 2
    radius = max(4, radius)
    key = (radius, color, falloff)
    tex = _GLOW_CACHE.get(key)
    if tex is not None:
        return tex
    small = 64
    base = pygame.Surface((small, small))
    base.fill((0, 0, 0))
    half = small // 2
    for r in range(half, 0, -1):
        t = 1 - r / half
        k = t ** falloff
        pygame.draw.circle(base, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (half, half), r)
    tex = pygame.transform.smoothscale(base, (radius * 2, radius * 2))
    if len(_GLOW_CACHE) > 900:
        _GLOW_CACHE.clear()
    _GLOW_CACHE[key] = tex
    return tex


class Lighting:
    """Calque d'obscurité multiplié sur l'écran ; les lumières y sont ajoutées."""

    def __init__(self):
        self.dark = pygame.Surface((WIDTH, HEIGHT))
        self.ambient = (40, 34, 52)

    def begin(self, ambient):
        self.ambient = ambient
        self.dark.fill(ambient)

    def add(self, x, y, radius, color=(255, 220, 170)):
        if x + radius < 0 or y + radius < 0 or x - radius > WIDTH or y - radius > HEIGHT:
            return
        tex = glow_texture(int(radius) // 4 * 4, color)
        self.dark.blit(tex, (x - tex.get_width() // 2, y - tex.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)

    def apply(self, screen):
        screen.blit(self.dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def additive_glow(surface, x, y, radius, color):
    tex = glow_texture(int(radius), color)
    surface.blit(tex, (x - tex.get_width() // 2, y - tex.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# Vignette
# ---------------------------------------------------------------------------
_VIGNETTE = {}


def vignette(strength=170, color=(0, 0, 0)):
    key = (strength, color)
    if key in _VIGNETTE:
        return _VIGNETTE[key]
    small = pygame.Surface((64, 36), pygame.SRCALPHA)
    for y in range(36):
        for x in range(64):
            dx = (x - 31.5) / 32
            dy = (y - 17.5) / 18
            d = min(1.0, math.sqrt(dx * dx + dy * dy))
            a = int(strength * max(0.0, (d - 0.45) / 0.55) ** 1.6)
            small.set_at((x, y), (*color, a))
    surf = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    _VIGNETTE[key] = surf
    return surf


# ---------------------------------------------------------------------------
# Particules
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color',
                 'drag', 'gravity', 'glow', 'shrink', 'square')

    def __init__(self, x, y, vx, vy, life, size, color, drag, gravity, glow, shrink, square):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size, self.color = size, color
        self.drag, self.gravity = drag, gravity
        self.glow, self.shrink, self.square = glow, shrink, square


class ParticleSystem:
    MAX = 1800

    def __init__(self):
        self.particles = []

    def clear(self):
        self.particles.clear()

    def emit(self, x, y, count=10, color=(255, 255, 255), speed=(60, 220), life=(0.3, 0.7),
             size=(2, 5), angle=None, spread=math.tau, drag=4.0, gravity=0.0, glow=False,
             shrink=True, square=True, jitter=0):
        if len(self.particles) > self.MAX:
            return
        for _ in range(count):
            a = (angle if angle is not None else random.uniform(0, math.tau)) + random.uniform(-spread / 2, spread / 2)
            s = random.uniform(*speed)
            c = color if not callable(color) else color()
            px = x + (random.uniform(-jitter, jitter) if jitter else 0)
            py = y + (random.uniform(-jitter, jitter) if jitter else 0)
            self.particles.append(Particle(px, py, math.cos(a) * s, math.sin(a) * s,
                                           random.uniform(*life), random.uniform(*size), c,
                                           drag, gravity, glow, shrink, square))

    def update(self, dt):
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            f = max(0.0, 1 - p.drag * dt)
            p.vx *= f
            p.vy = p.vy * f + p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.particles = alive

    def draw(self, surface, ox, oy, glow_pass=False):
        for p in self.particles:
            if p.glow != glow_pass:
                continue
            t = p.life / p.max_life
            size = p.size * (t if p.shrink else 1)
            if size < 0.6:
                continue
            x, y = p.x - ox, p.y - oy
            if x < -20 or y < -20 or x > WIDTH + 20 or y > HEIGHT + 20:
                continue
            if glow_pass:
                r = int(size * 3)
                if r >= 4:
                    c = p.color
                    q = math.ceil(t * 6) / 6
                    additive_glow(surface, int(x), int(y), r, (int(c[0] * q), int(c[1] * q), int(c[2] * q)))
                else:
                    pygame.draw.circle(surface, p.color, (int(x), int(y)), max(1, int(size)))
            elif p.square:
                s = max(1, int(size))
                surface.fill(p.color, (int(x) - s // 2, int(y) - s // 2, s, s))
            else:
                pygame.draw.circle(surface, p.color, (int(x), int(y)), max(1, int(size)))

    # --- recettes -------------------------------------------------------
    def blood(self, x, y, direction=None, amount=14):
        ang = math.atan2(direction[1], direction[0]) if direction else None
        self.emit(x, y, amount, lambda: (random.randint(120, 190), random.randint(0, 20), random.randint(10, 30)),
                  speed=(80, 320), life=(0.25, 0.6), size=(2, 5), angle=ang,
                  spread=1.4 if ang is not None else math.tau, drag=5, gravity=380)

    def sparks(self, x, y, color=(255, 220, 140), amount=10, direction=None):
        ang = math.atan2(direction[1], direction[0]) if direction else None
        self.emit(x, y, amount, color, speed=(180, 480), life=(0.12, 0.35), size=(1.5, 3),
                  angle=ang, spread=1.8 if ang is not None else math.tau, drag=6, glow=True)

    def dust(self, x, y, amount=6, color=(140, 130, 120)):
        self.emit(x, y, amount, color, speed=(20, 80), life=(0.3, 0.6), size=(3, 6), drag=3,
                  gravity=-30, square=False)

    def death(self, x, y, color=(150, 30, 40)):
        self.emit(x, y, 26, lambda: (random.randint(90, 170), random.randint(0, 25), random.randint(20, 45)),
                  speed=(60, 360), life=(0.35, 0.9), size=(3, 7), drag=4, gravity=260)
        self.emit(x, y, 14, (110, 90, 130), speed=(20, 120), life=(0.6, 1.2), size=(5, 10), drag=2,
                  gravity=-50, square=False)

    def soul(self, x, y, color=(120, 255, 200)):
        self.emit(x, y, 10, color, speed=(20, 90), life=(0.6, 1.3), size=(2, 4), drag=1.5,
                  gravity=-120, glow=True, jitter=12)

    def ring(self, x, y, color=(255, 200, 120), amount=36, speed=420, glow=True):
        for i in range(amount):
            a = i / amount * math.tau
            self.particles.append(Particle(x, y, math.cos(a) * speed, math.sin(a) * speed,
                                           random.uniform(0.3, 0.5), random.uniform(2, 4), color,
                                           3.0, 0.0, glow, True, True))

    def embers(self, x, y, amount=1, spread_x=20):
        self.emit(x, y, amount, lambda: random.choice([(255, 170, 60), (255, 120, 40), (255, 210, 120)]),
                  speed=(20, 60), life=(0.6, 1.4), size=(1.5, 3), angle=-math.pi / 2, spread=0.9,
                  drag=0.6, gravity=-40, glow=True, jitter=spread_x)


# ---------------------------------------------------------------------------
# Textes flottants (dégâts, butin...)
# ---------------------------------------------------------------------------
class FloatingText:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'surf', 'pop')

    def __init__(self, x, y, text, color, size=22, life=0.9, rise=70, pop=1.0):
        self.x, self.y = x, y
        self.vx = random.uniform(-25, 25)
        self.vy = -rise
        self.life = self.max_life = life
        self.surf = render_outlined(text, size, color, width=2, bold=True)
        self.pop = pop


# ---------------------------------------------------------------------------
# Cadavres (animation de mort qui reste au sol puis s'estompe)
# ---------------------------------------------------------------------------
class Corpse:
    def __init__(self, frames, rect, facing_right, tint=None):
        self.frames = frames or []
        self.rect = rect.copy()
        self.facing_right = facing_right
        self.index = 0.0
        self.timer = 0.0
        self.alpha = 255
        self.tint = tint
        self.done = not self.frames

    def update(self, dt):
        if self.done:
            return
        if self.index < len(self.frames) - 1:
            self.index = min(len(self.frames) - 1, self.index + dt * 9)
        else:
            self.timer += dt
            if self.timer > 1.2:
                self.alpha -= 300 * dt
                if self.alpha <= 0:
                    self.done = True

    def draw(self, surface, ox, oy):
        if self.done:
            return
        img = self.frames[int(self.index)]
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
        if self.alpha < 255:
            img = img.copy()
            img.set_alpha(max(0, int(self.alpha)))
        surface.blit(img, (self.rect.x - ox, self.rect.y - oy))


# ---------------------------------------------------------------------------
# Zones d'alerte (attaques télégraphiées)
# ---------------------------------------------------------------------------
class Telegraph:
    """Cercle ou ligne rouge qui se remplit avant une attaque."""

    def __init__(self, kind, x, y, duration, radius=0, end=None, width=60, color=(255, 40, 40)):
        self.kind = kind
        self.x, self.y = x, y
        self.duration = duration
        self.t = 0.0
        self.radius = radius
        self.end = end
        self.width = width
        self.color = color

    @property
    def progress(self):
        return min(1.0, self.t / self.duration)

    def update(self, dt):
        self.t += dt
        return self.t < self.duration

    def draw(self, surface, ox, oy):
        p = self.progress
        pulse = 0.5 + 0.5 * math.sin(self.t * 18)
        if self.kind == 'circle':
            r = int(self.radius)
            size = r * 2 + 4
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 40 + int(30 * pulse)), (size // 2, size // 2), r)
            pygame.draw.circle(s, (*self.color, 110), (size // 2, size // 2), max(2, int(r * p)))
            pygame.draw.circle(s, (*self.color, 220), (size // 2, size // 2), r, 3)
            surface.blit(s, (self.x - ox - size // 2, self.y - oy - size // 2))
        elif self.kind == 'line' and self.end:
            sx, sy = self.x - ox, self.y - oy
            ex, ey = self.end[0] - ox, self.end[1] - oy
            minx, miny = min(sx, ex) - self.width, min(sy, ey) - self.width
            w = int(abs(ex - sx) + self.width * 2) + 2
            h = int(abs(ey - sy) + self.width * 2) + 2
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            a = (sx - minx, sy - miny)
            b = (ex - minx, ey - miny)
            pygame.draw.line(s, (*self.color, 50 + int(40 * pulse)), a, b, self.width)
            mid = (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)
            pygame.draw.line(s, (*self.color, 140), a, mid, self.width)
            surface.blit(s, (minx, miny))


# ---------------------------------------------------------------------------
# Projectiles
# ---------------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, vx, vy, damage, color=(160, 255, 80), radius=9, life=4.0, owner='enemy'):
        self.pos = pygame.math.Vector2(x, y)
        self.vel = pygame.math.Vector2(vx, vy)
        self.damage = damage
        self.color = color
        self.radius = radius
        self.life = life
        self.owner = owner
        self.alive = True
        self.trail_t = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.pos.x - self.radius), int(self.pos.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt, obstacles, particles):
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        self.pos += self.vel * dt
        self.trail_t += dt
        if self.trail_t > 0.03:
            self.trail_t = 0
            particles.emit(self.pos.x, self.pos.y, 1, self.color, speed=(5, 30), life=(0.15, 0.3),
                           size=(2, 4), glow=True)
        from spatial import nearby_obstacles
        r = self.rect
        for o in nearby_obstacles(obstacles, r):
            if o.rect.colliderect(r):
                self.alive = False
                particles.sparks(self.pos.x, self.pos.y, self.color, 8)
                return

    def draw(self, surface, ox, oy):
        x, y = int(self.pos.x - ox), int(self.pos.y - oy)
        additive_glow(surface, x, y, self.radius * 3, tuple(int(c * 0.8) for c in self.color))
        pygame.draw.circle(surface, self.color, (x, y), self.radius)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), max(2, self.radius // 2))


# ---------------------------------------------------------------------------
# Traînées d'esquive & arcs d'épée
# ---------------------------------------------------------------------------
class Afterimage:
    __slots__ = ('surf', 'x', 'y', 'life', 'max_life')

    def __init__(self, image, x, y, color=(90, 200, 255), life=0.25):
        sil = image.copy()
        sil.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        sil.fill((*color, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.surf = sil
        self.x, self.y = x, y
        self.life = self.max_life = life


_SLASH_CACHE = {}


def slash_surface(radius, thickness, color, arc_deg=150):
    key = (radius, thickness, color, arc_deg)
    if key in _SLASH_CACHE:
        return _SLASH_CACHE[key]
    size = radius * 2 + 8
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    arc = math.radians(arc_deg)
    steps = 40
    for i in range(steps):
        t0 = i / steps
        t1 = (i + 1) / steps
        a0 = -arc / 2 + arc * t0
        a1 = -arc / 2 + arc * t1
        # épaisseur maximale au centre de l'arc (forme de croissant)
        w0 = thickness * math.sin(math.pi * t0)
        w1 = thickness * math.sin(math.pi * t1)
        alpha = int(230 * math.sin(math.pi * t0) ** 0.6)
        pts = [
            (c + math.cos(a0) * radius, c + math.sin(a0) * radius),
            (c + math.cos(a1) * radius, c + math.sin(a1) * radius),
            (c + math.cos(a1) * (radius - w1), c + math.sin(a1) * (radius - w1)),
            (c + math.cos(a0) * (radius - w0), c + math.sin(a0) * (radius - w0)),
        ]
        pygame.draw.polygon(s, (*color, alpha), pts)
    # liseré blanc sur le bord extérieur
    for i in range(steps):
        t0 = i / steps
        a0 = -arc / 2 + arc * t0
        a1 = -arc / 2 + arc * (i + 1) / steps
        alpha = int(255 * math.sin(math.pi * t0))
        pygame.draw.line(s, (255, 255, 255, alpha),
                         (c + math.cos(a0) * radius, c + math.sin(a0) * radius),
                         (c + math.cos(a1) * radius, c + math.sin(a1) * radius), 2)
    _SLASH_CACHE[key] = s
    return s


class Slash:
    def __init__(self, x, y, angle_deg, radius=78, thickness=26, color=(210, 230, 255), life=0.16,
                 arc=150, full_circle=False):
        self.x, self.y = x, y
        self.angle = angle_deg
        self.life = self.max_life = life
        self.full = full_circle
        base = slash_surface(radius, thickness, color, 340 if full_circle else arc)
        self.surf = pygame.transform.rotate(base, -angle_deg)

    def draw(self, surface, ox, oy):
        t = self.life / self.max_life
        img = self.surf
        if self.full:
            img = pygame.transform.rotate(self.surf, (1 - t) * -540)
        img.set_alpha(int(255 * min(1.0, t * 1.6)))
        surface.blit(img, (self.x - ox - img.get_width() // 2, self.y - oy - img.get_height() // 2))


# ---------------------------------------------------------------------------
# Gestionnaire global
# ---------------------------------------------------------------------------
class FXManager:
    def __init__(self):
        self.particles = ParticleSystem()
        self.texts = []
        self.corpses = []
        self.telegraphs = []
        self.projectiles = []
        self.afterimages = []
        self.slashes = []
        self.decals = []
        self.trauma = 0.0
        self.shake_enabled = True
        self.hitstop_timer = 0.0
        self.flash_color = None
        self.flash_alpha = 0.0
        self.banner = None
        self.time = 0.0
        self.time_scale = 1.0
        self.slowmo_timer = 0.0

    def reset(self):
        self.particles.clear()
        self.texts.clear()
        self.corpses.clear()
        self.telegraphs.clear()
        self.projectiles.clear()
        self.afterimages.clear()
        self.slashes.clear()
        self.decals.clear()
        self.trauma = 0.0
        self.hitstop_timer = 0.0
        self.flash_alpha = 0.0
        self.slowmo_timer = 0.0
        self.time_scale = 1.0

    # --- déclencheurs ---------------------------------------------------
    def shake(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def hitstop(self, seconds):
        self.hitstop_timer = max(self.hitstop_timer, seconds)

    def slowmo(self, seconds, scale=0.3):
        self.slowmo_timer = seconds
        self.time_scale = scale

    def flash(self, color, alpha=120):
        self.flash_color = color
        self.flash_alpha = alpha

    def text(self, x, y, text, color=(255, 255, 255), size=22, life=0.9, rise=70, pop=1.0):
        if len(self.texts) < 80:
            self.texts.append(FloatingText(x, y, text, color, size, life, rise, pop))

    def show_banner(self, title, subtitle='', color=GOLD, duration=2.6):
        self.banner = {'title': title, 'sub': subtitle, 'color': color, 't': 0.0, 'dur': duration}

    def decal_blood(self, x, y, size=None):
        size = size or random.randint(10, 26)
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        for _ in range(random.randint(3, 6)):
            r = random.randint(size // 3, size)
            cx = size + random.randint(-size // 2, size // 2)
            cy = size + random.randint(-size // 3, size // 3)
            pygame.draw.ellipse(s, (random.randint(70, 110), 0, 8, random.randint(110, 170)),
                                (cx - r, cy - r // 2, r * 2, r))
        self.decals.append((s, x - size, y - size))
        if len(self.decals) > 140:
            self.decals.pop(0)

    def add_corpse(self, enemy):
        frames = []
        anims = getattr(enemy, 'animations', None)
        if anims:
            frames = anims.get('ded') or []
        tint = getattr(enemy, 'tint', None)
        if tint and frames:
            frames = [_tinted(f, tint) for f in frames]
        self.corpses.append(Corpse(frames, enemy.rect, getattr(enemy, 'facing_right', True)))
        if len(self.corpses) > 40:
            self.corpses.pop(0)

    # --- mise à jour ----------------------------------------------------
    def update(self, dt):
        """dt réel ; retourne le dt 'de jeu' (ralenti / figé)."""
        self.time += dt
        self.trauma = max(0.0, self.trauma - dt * 1.6)
        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - dt * 500)
        if self.banner:
            self.banner['t'] += dt
            if self.banner['t'] > self.banner['dur']:
                self.banner = None
        if self.slowmo_timer > 0:
            self.slowmo_timer -= dt
            if self.slowmo_timer <= 0:
                self.time_scale = 1.0
        game_dt = dt * self.time_scale
        if self.hitstop_timer > 0:
            self.hitstop_timer -= dt
            game_dt = 0.0

        self.particles.update(dt)
        for t in self.texts:
            t.life -= dt
            t.x += t.vx * dt
            t.y += t.vy * dt
            t.vy *= max(0.0, 1 - 3 * dt)
        self.texts = [t for t in self.texts if t.life > 0]
        for c in self.corpses:
            c.update(dt)
        self.corpses = [c for c in self.corpses if not c.done]
        self.telegraphs = [t for t in self.telegraphs if t.update(game_dt)]
        for a in self.afterimages:
            a.life -= dt
        self.afterimages = [a for a in self.afterimages if a.life > 0]
        for s in self.slashes:
            s.life -= dt
        self.slashes = [s for s in self.slashes if s.life > 0]
        return game_dt

    def shake_offset(self):
        if not self.shake_enabled or self.trauma <= 0:
            return 0, 0
        amt = self.trauma * self.trauma * 22
        t = self.time * 60
        return (math.sin(t * 1.7) + random.uniform(-0.5, 0.5)) * amt, (math.cos(t * 2.3) + random.uniform(-0.5, 0.5)) * amt

    # --- rendu ----------------------------------------------------------
    def draw_ground(self, surface, ox, oy):
        for s, x, y in self.decals:
            if -60 < x - ox < WIDTH + 60 and -60 < y - oy < HEIGHT + 60:
                surface.blit(s, (x - ox, y - oy))
        for t in self.telegraphs:
            t.draw(surface, ox, oy)
        for c in self.corpses:
            c.draw(surface, ox, oy)

    def draw_world(self, surface, ox, oy):
        for a in self.afterimages:
            img = a.surf
            img.set_alpha(int(170 * a.life / a.max_life))
            surface.blit(img, (a.x - ox, a.y - oy))
        self.particles.draw(surface, ox, oy, glow_pass=False)

    def draw_glow(self, surface, ox, oy):
        for s in self.slashes:
            s.draw(surface, ox, oy)
        for p in self.projectiles:
            p.draw(surface, ox, oy)
        self.particles.draw(surface, ox, oy, glow_pass=True)

    def draw_texts(self, surface, ox, oy):
        for t in self.texts:
            k = t.life / t.max_life
            img = t.surf
            age = t.max_life - t.life
            if age < 0.12 and t.pop > 1.0:
                scale = 1 + (t.pop - 1) * (1 - age / 0.12)
                img = pygame.transform.rotozoom(img, 0, scale)
            if k < 0.35:
                img = img.copy() if img is t.surf else img
                img.set_alpha(int(255 * k / 0.35))
            surface.blit(img, (t.x - ox - img.get_width() // 2, t.y - oy - img.get_height() // 2))

    def draw_screen(self, surface):
        if self.flash_alpha > 0 and self.flash_color:
            s = pygame.Surface((WIDTH, HEIGHT))
            s.fill(self.flash_color)
            s.set_alpha(int(self.flash_alpha))
            surface.blit(s, (0, 0))
        if self.banner:
            b = self.banner
            t, dur = b['t'], b['dur']
            a = min(1.0, t / 0.3, (dur - t) / 0.5)
            a = max(0.0, a)
            band = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
            for y in range(120):
                k = 1 - abs(y - 60) / 60
                band.fill((0, 0, 0, int(170 * k * a)), (0, y, WIDTH, 1))
            surface.blit(band, (0, HEIGHT // 3 - 60))
            title = render_outlined(b['title'], 64, b['color'], width=3, bold=True)
            scale = 1 + max(0.0, 0.25 - t) * 1.2
            if scale != 1:
                title = pygame.transform.rotozoom(title, 0, scale)
            title.set_alpha(int(255 * a))
            surface.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3 - 12)))
            if b['sub']:
                sub = render_outlined(b['sub'], 26, (230, 220, 200), width=2)
                sub.set_alpha(int(255 * a))
                surface.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 34)))


_TINT_CACHE = {}


def _tinted(surf, tint):
    key = (id(surf), tint)
    t = _TINT_CACHE.get(key)
    if t is None:
        t = surf.copy()
        t.fill((*tint, 0), special_flags=pygame.BLEND_RGBA_ADD)
        _TINT_CACHE[key] = t
    return t


def tint_surface(surf, tint):
    return _tinted(surf, tint)


fx = FXManager()
