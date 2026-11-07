"""Arrière-plan animé des menus et boutons stylisés."""
import math
import os
import random
import pygame
from settings import *
from fx import ParticleSystem, render_outlined, get_font, vignette, additive_glow


class MenuBackground:
    def __init__(self):
        self.t = 0.0
        self.particles = ParticleSystem()
        self.image = None
        path = resource_path(os.path.join('assets', 'intro', '9.png'))
        try:
            img = pygame.image.load(path).convert()
            w = int(WIDTH * 1.15)
            h = int(img.get_height() * w / img.get_width())
            h = max(h, int(HEIGHT * 1.15))
            img = pygame.transform.smoothscale(img, (w, h))
            dark = pygame.Surface(img.get_size())
            dark.fill((95, 80, 90))
            img.blit(dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            self.image = img
        except Exception:
            self.image = None
        # brume procédurale
        self.fog = pygame.Surface((WIDTH * 2, 260), pygame.SRCALPHA)
        rnd = random.Random(7)
        for _ in range(70):
            x = rnd.randint(0, WIDTH * 2)
            y = rnd.randint(60, 200)
            r = rnd.randint(60, 140)
            pygame.draw.circle(self.fog, (120, 110, 140, 10), (x, y), r)
        self.title_cache = None

    def draw(self, surface, dt):
        self.t += dt
        if self.image:
            ox = (self.image.get_width() - WIDTH) / 2 + math.sin(self.t * 0.07) * 40
            oy = (self.image.get_height() - HEIGHT) / 2 + math.cos(self.t * 0.05) * 15
            surface.blit(self.image, (-ox, -oy))
        else:
            surface.fill((20, 14, 22))
        fx_off = (self.t * 25) % WIDTH
        surface.blit(self.fog, (-fx_off, HEIGHT - 240))
        surface.blit(self.fog, (-fx_off + WIDTH * 2 - 2, HEIGHT - 240))
        # braises qui montent
        if random.random() < 0.7:
            self.particles.embers(random.randint(0, WIDTH), HEIGHT + 10, 1, spread_x=0)
            self.particles.particles[-1].vy = -random.uniform(40, 110)
            self.particles.particles[-1].life = self.particles.particles[-1].max_life = random.uniform(3, 6)
            self.particles.particles[-1].drag = 0.05
        self.particles.update(dt)
        self.particles.draw(surface, 0, 0, glow_pass=True)
        surface.blit(vignette(200), (0, 0))

    def draw_title(self, surface, y=150, subtitle="Le prix de la cupidité"):
        glow = 0.5 + 0.5 * math.sin(self.t * 1.5)
        additive_glow(surface, WIDTH // 2, y, int(260 + 30 * glow), (70, 40, 10))
        if self.title_cache is None:
            self.title_cache = self._make_title()
        surface.blit(self.title_cache, self.title_cache.get_rect(center=(WIDTH // 2, y)))
        sub = render_outlined(subtitle.upper(), 22, (200, 170, 130), width=2)
        surface.blit(sub, sub.get_rect(center=(WIDTH // 2, y + 70)))

    @staticmethod
    def _make_title():
        font = get_font(150, bold=True)
        text = "GREED"
        base = font.render(text, True, (255, 255, 255))
        w, h = base.get_size()
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            k = y / h
            col = (int(255 - 40 * k), int(225 - 120 * k), int(130 - 110 * k))
            grad.fill((*col, 255), (0, y, w, 1))
        grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        shadow = font.render(text, True, (20, 5, 5))
        edge = font.render(text, True, (60, 30, 10))
        out = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
        out.blit(shadow, (14, 14))
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                out.blit(edge, (8 + dx, 8 + dy))
        out.blit(grad, (8, 8))
        return out


def draw_button(surface, rect, text, hovered, accent=GOLD, danger=False, size=30, t=0.0):
    """Bouton 'gravé' avec survol animé."""
    r = rect.inflate(10, 4) if hovered else rect
    bg = pygame.Surface(r.size, pygame.SRCALPHA)
    base = (60, 14, 18) if danger else (24, 20, 30)
    for y in range(r.height):
        k = y / r.height
        col = tuple(int(c * (1.25 - 0.5 * k)) for c in base)
        bg.fill((*col, 225), (0, y, r.width, 1))
    surface.blit(bg, r.topleft)
    border = (255, 120, 110) if danger and hovered else (accent if hovered else PANEL_BORDER)
    pygame.draw.rect(surface, border, r, 2, border_radius=4)
    # coins ornés
    for (cx, cy) in (r.topleft, r.topright, r.bottomleft, r.bottomright):
        pygame.draw.circle(surface, border, (cx, cy), 4 if hovered else 3)
    if hovered:
        additive_glow(surface, r.centerx, r.centery, r.width // 2, (40, 28, 10))
        # flèches latérales
        off = 8 + 3 * math.sin(t * 8)
        pygame.draw.polygon(surface, accent, [(r.left - off - 10, r.centery - 7), (r.left - off, r.centery),
                                              (r.left - off - 10, r.centery + 7)])
        pygame.draw.polygon(surface, accent, [(r.right + off + 10, r.centery - 7), (r.right + off, r.centery),
                                              (r.right + off + 10, r.centery + 7)])
    col = (255, 245, 225) if hovered else (215, 200, 180)
    label = render_outlined(text, size, col, width=2, bold=True)
    surface.blit(label, label.get_rect(center=r.center))
