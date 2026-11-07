"""Illustrations procédurales des bâtiments sans texture (auberge, arbre, fleurs)
et fabrique d'images partagée par les bâtiments, le fantôme de placement et
les vignettes du menu de construction."""
import math
import os
import random
import pygame
from settings import *

# Textures fournies par le projet
BUILDING_TEXTURES = {
    'bank': 'bank.jpg',
    'forge': 'forge.jpg',
    'library': 'bibli.jpg',
    'shop': 'marche.jpg',
    'path': ('floor_assets', 'dirt_path.jpg'),  # Tuple = dossier différent
}
BUILDING_CROP_MODE = {'library'}
BUILDING_PATTERN_MODE = {'path': (320, 320)}  # 5x5 tiles de 64px

_CACHE = {}
_TEX_CACHE = {}


def _load_texture(entry):
    if entry in _TEX_CACHE:
        return _TEX_CACHE[entry]
    if isinstance(entry, tuple):
        path = resource_path(os.path.join('assets', entry[0], entry[1]))
    else:
        path = resource_path(os.path.join('assets', 'building', entry))
    try:
        tex = pygame.image.load(path).convert()
    except Exception:
        tex = None
    _TEX_CACHE[entry] = tex
    return tex


# ---------------------------------------------------------------------------
# Dessins procéduraux
# ---------------------------------------------------------------------------
def draw_inn(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    rnd = random.Random(3)
    wall_top = int(h * 0.42)
    # murs à colombages
    pygame.draw.rect(s, (214, 190, 150), (4, wall_top, w - 8, h - wall_top - 2))
    for x in range(4, w - 4, 18):
        pygame.draw.rect(s, (95, 58, 30), (x, wall_top, 4, h - wall_top - 2))
    pygame.draw.rect(s, (95, 58, 30), (4, wall_top, w - 8, 4))
    pygame.draw.line(s, (95, 58, 30), (4, (wall_top + h) // 2), (w - 5, (wall_top + h) // 2), 3)
    # toit de tuiles
    roof = [(0, wall_top + 2), (w * 0.18, 2), (w * 0.82, 2), (w, wall_top + 2)]
    pygame.draw.polygon(s, (140, 45, 35), roof)
    for i in range(1, 5):
        y = 2 + i * (wall_top / 5)
        k = i / 5
        pygame.draw.line(s, (105, 30, 25), (w * 0.18 * (1 - k), y), (w - w * 0.18 * (1 - k), y), 2)
    for x in range(int(w * 0.2), int(w * 0.8), 9):
        pygame.draw.line(s, (165, 60, 45), (x, 4), (x + rnd.randint(-2, 2), wall_top - 2), 1)
    pygame.draw.polygon(s, (70, 25, 20), roof, 2)
    # cheminée fumante
    pygame.draw.rect(s, (110, 100, 100), (int(w * 0.68), 0, 10, 14))
    # porte et fenêtres éclairées
    door = pygame.Rect(0, 0, 16, h - wall_top - 8)
    door.midbottom = (w // 2, h - 2)
    pygame.draw.rect(s, (80, 45, 20), door, border_top_left_radius=8, border_top_right_radius=8)
    pygame.draw.circle(s, (230, 190, 80), (door.right - 4, door.centery + 2), 2)
    for cx in (int(w * 0.22), int(w * 0.78)):
        win = pygame.Rect(0, 0, 16, 12)
        win.center = (cx, (wall_top + h) // 2 + 2)
        pygame.draw.rect(s, (255, 205, 110), win)
        pygame.draw.rect(s, (95, 58, 30), win, 2)
        pygame.draw.line(s, (95, 58, 30), win.midtop, win.midbottom, 1)
    # enseigne
    pygame.draw.line(s, (60, 40, 20), (door.left - 6, wall_top + 8), (door.left - 6, wall_top + 16), 2)
    pygame.draw.rect(s, (170, 120, 50), (door.left - 16, wall_top + 14, 14, 9))
    pygame.draw.circle(s, (230, 200, 120), (door.left - 9, wall_top + 18), 2)
    return s


def draw_tree(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    rnd = random.Random(11)
    pygame.draw.ellipse(s, (0, 0, 0, 70), (6, h - 14, w - 12, 12))
    pygame.draw.rect(s, (95, 60, 30), (w // 2 - 5, h // 2, 10, h // 2 - 6))
    pygame.draw.line(s, (70, 45, 20), (w // 2 - 2, h // 2 + 4), (w // 2 - 2, h - 8), 2)
    blobs = [(w * 0.5, h * 0.36, w * 0.34), (w * 0.3, h * 0.5, w * 0.24), (w * 0.7, h * 0.5, w * 0.24),
             (w * 0.42, h * 0.24, w * 0.22), (w * 0.62, h * 0.26, w * 0.2)]
    for (x, y, r) in blobs:
        pygame.draw.circle(s, (28, 85, 35), (int(x), int(y) + 3), int(r))
    for (x, y, r) in blobs:
        pygame.draw.circle(s, (45, 125, 50), (int(x), int(y)), int(r))
    for (x, y, r) in blobs:
        pygame.draw.circle(s, (75, 160, 70), (int(x - r * 0.3), int(y - r * 0.3)), int(r * 0.45))
    for _ in range(5):
        pygame.draw.circle(s, (200, 40, 40), (rnd.randint(14, w - 14), rnd.randint(8, h // 2 + 4)), 2)
    return s


def draw_flower(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    rnd = random.Random(5)
    for _ in range(6):
        x, y = rnd.randint(5, w - 5), rnd.randint(10, h - 4)
        pygame.draw.line(s, (50, 120, 45), (x, y), (x, y - 7), 2)
        pygame.draw.ellipse(s, (60, 140, 55), (x - 5, y - 4, 5, 3))
        col = rnd.choice([(255, 105, 180), (255, 220, 80), (190, 120, 255), (255, 255, 255), (255, 120, 90)])
        for a in range(5):
            ang = a / 5 * math.tau
            pygame.draw.circle(s, col, (int(x + math.cos(ang) * 3), int(y - 8 + math.sin(ang) * 3)), 2)
        pygame.draw.circle(s, (250, 210, 60), (x, y - 8), 1)
    return s


PROCEDURAL = {'inn': draw_inn, 'tree': draw_tree, 'flower': draw_flower}


def _fallback(b_type):
    data = BUILDING_DATA[b_type]
    w, h = data['size']
    s = pygame.Surface((w, h))
    s.fill(data['color'])
    pygame.draw.rect(s, (30, 30, 30), (0, 0, w, h), 3)
    return s


def building_image(b_type, pos=(0, 0)):
    """Image d'un bâtiment (texture du projet, dessin procédural ou couleur)."""
    data = BUILDING_DATA[b_type]
    target_w, target_h = data['size']
    if b_type in BUILDING_PATTERN_MODE:
        tex = _load_texture(BUILDING_TEXTURES[b_type])
        if tex is None:
            return _fallback(b_type)
        pat_w, pat_h = BUILDING_PATTERN_MODE[b_type]
        key = ('pattern', b_type)
        if key not in _CACHE:
            _CACHE[key] = pygame.transform.scale(tex, (pat_w, pat_h))
        tex_scaled = _CACHE[key]
        img = pygame.Surface((target_w, target_h))
        img.blit(tex_scaled, (0, 0), (int(pos[0] % pat_w), int(pos[1] % pat_h), target_w, target_h))
        return img
    if b_type in _CACHE:
        return _CACHE[b_type]
    if b_type in PROCEDURAL:
        img = PROCEDURAL[b_type](target_w, target_h)
    elif b_type in BUILDING_TEXTURES:
        tex = _load_texture(BUILDING_TEXTURES[b_type])
        if tex is None:
            img = _fallback(b_type)
        elif b_type in BUILDING_CROP_MODE:
            orig_w, orig_h = tex.get_size()
            scaled_w = int(orig_w * target_h / orig_h)
            tex_scaled = pygame.transform.scale(tex, (scaled_w, target_h))
            crop_x = (scaled_w - target_w) // 2
            img = tex_scaled.subsurface(pygame.Rect(crop_x, 0, target_w, target_h)).copy()
        else:
            img = pygame.transform.scale(tex, (target_w, target_h))
    else:
        img = _fallback(b_type)
    _CACHE[b_type] = img
    return img


def thumbnail(b_type, size):
    """Vignette carrée (menu de construction)."""
    key = ('thumb', b_type, size)
    if key in _CACHE:
        return _CACHE[key]
    img = building_image(b_type, (0, 0))
    w, h = img.get_size()
    k = min((size - 6) / w, (size - 6) / h)
    th = pygame.transform.smoothscale(img.convert_alpha() if img.get_alpha() is None else img,
                                      (max(1, int(w * k)), max(1, int(h * k))))
    _CACHE[key] = th
    return th


def ghost_image(b_type, pos, valid):
    """Fantôme de placement : la vraie image, translucide, teintée selon la validité."""
    img = building_image(b_type, pos).copy().convert_alpha()
    tint = (0, 60, 0, 0) if valid else (110, 0, 0, 0)
    img.fill(tint, special_flags=pygame.BLEND_RGBA_ADD)
    img.set_alpha(175)
    return img
