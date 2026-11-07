"""Bénédictions : à chaque niveau gagné, le joueur choisit 1 bonus parmi 3."""
import math
import random
import pygame
from settings import *

RARITY_COLORS = {
    'commun': (180, 180, 190),
    'rare': (90, 170, 255),
    'épique': (200, 110, 255),
    'légendaire': (255, 190, 60),
}
RARITY_WEIGHT = {'commun': 10, 'rare': 6, 'épique': 3, 'légendaire': 1}

# id : (nom, description, rareté, cumul max, icône)
PERKS = {
    'force':   ("Force brute", "+15 % de dégâts", 'commun', 10, 'sword'),
    'vigor':   ("Vigueur", "+20 PV max et soin complet", 'commun', 10, 'heart'),
    'swift':   ("Pas léger", "+8 % de vitesse de déplacement", 'commun', 5, 'boot'),
    'crit':    ("Œil du faucon", "+8 % de chances de critique", 'rare', 6, 'eye'),
    'shadow':  ("Ombre fugace", "-15 % de recharge d'esquive", 'rare', 4, 'wind'),
    'magnet':  ("Aimant d'avare", "Ramasse le butin de plus loin", 'commun', 4, 'magnet'),
    'greed':   ("Cupidité", "+25 % de butin des monstres", 'rare', 5, 'coin'),
    'vamp':    ("Soif de sang", "Chaque ennemi tué rend 3 PV", 'rare', 5, 'drop'),
    'whirl':   ("Maître du tourbillon", "Tourbillon : -15 % recharge, +25 % dégâts", 'épique', 4, 'spin'),
    'thorns':  ("Épines", "Renvoie 60 % des dégâts subis", 'épique', 3, 'thorn'),
    'fury':    ("Fureur", "Coup final du combo : +40 % dégâts", 'épique', 4, 'fire'),
    'phoenix': ("Seconde chance", "Survit une fois par expédition à un coup fatal", 'légendaire', 1, 'phoenix'),
}


def roll_choices(owned, k=3):
    pool = [pid for pid, p in PERKS.items() if owned.get(pid, 0) < p[3]]
    choices = []
    while pool and len(choices) < k:
        weights = [RARITY_WEIGHT[PERKS[p][2]] for p in pool]
        pick = random.choices(pool, weights=weights, k=1)[0]
        choices.append(pick)
        pool.remove(pick)
    return choices


def apply_perk(player, pid):
    player.perks[pid] = player.perks.get(pid, 0) + 1
    if pid == 'vigor':
        player.max_health += 20
        player.health = player.max_health


def draw_icon(surface, kind, center, size, color):
    cx, cy = center
    s = size
    if kind == 'sword':
        pygame.draw.line(surface, color, (cx - s, cy + s), (cx + s * 0.7, cy - s * 0.7), 5)
        pygame.draw.line(surface, color, (cx - s * 0.6, cy + s * 0.1), (cx - s * 0.1, cy + s * 0.6), 4)
    elif kind == 'heart':
        pygame.draw.circle(surface, color, (cx - s // 2, cy - s // 4), s // 2)
        pygame.draw.circle(surface, color, (cx + s // 2, cy - s // 4), s // 2)
        pygame.draw.polygon(surface, color, [(cx - s, cy - s // 6), (cx + s, cy - s // 6), (cx, cy + s)])
    elif kind == 'boot':
        pygame.draw.polygon(surface, color, [(cx - s * 0.5, cy - s), (cx + s * 0.1, cy - s), (cx + s * 0.1, cy + s * 0.2),
                                             (cx + s, cy + s * 0.45), (cx + s, cy + s * 0.9), (cx - s * 0.5, cy + s * 0.9)])
        for i in range(3):
            pygame.draw.line(surface, (30, 25, 35), (cx + s * (0.15 + i * 0.25), cy - s * 0.3 + i * 4),
                             (cx + s * (0.15 + i * 0.25) + 6, cy + s * 0.9), 2)
    elif kind == 'eye':
        pygame.draw.ellipse(surface, color, (cx - s, cy - s // 2, s * 2, s), 3)
        pygame.draw.circle(surface, color, (cx, cy), s // 3)
    elif kind == 'wind':
        for i in range(3):
            pygame.draw.arc(surface, color, (cx - s, cy - s + i * s * 0.6, s * 2, s), 0, math.pi, 3)
    elif kind == 'magnet':
        pygame.draw.arc(surface, color, (cx - s, cy - s, s * 2, s * 2), math.pi, math.tau, 6)
        pygame.draw.line(surface, color, (cx - s + 3, cy), (cx - s + 3, cy - s * 0.8), 6)
        pygame.draw.line(surface, color, (cx + s - 3, cy), (cx + s - 3, cy - s * 0.8), 6)
    elif kind == 'coin':
        pygame.draw.circle(surface, color, (cx, cy), s)
        pygame.draw.circle(surface, (40, 30, 20), (cx, cy), int(s * 0.6), 2)
    elif kind == 'drop':
        pygame.draw.circle(surface, color, (cx, cy + s // 3), int(s * 0.7))
        pygame.draw.polygon(surface, color, [(cx - s * 0.62, cy + s // 6), (cx + s * 0.62, cy + s // 6), (cx, cy - s)])
    elif kind == 'spin':
        pygame.draw.arc(surface, color, (cx - s, cy - s, s * 2, s * 2), 0.3, 5.2, 4)
        pygame.draw.polygon(surface, color, [(cx + s, cy - 6), (cx + s + 7, cy + 4), (cx + s - 7, cy + 4)])
    elif kind == 'thorn':
        for i in range(6):
            a = i / 6 * math.tau
            pygame.draw.line(surface, color, (cx, cy), (cx + math.cos(a) * s, cy + math.sin(a) * s), 3)
        pygame.draw.circle(surface, color, (cx, cy), s // 3)
    elif kind == 'fire':
        pygame.draw.polygon(surface, color, [(cx, cy - s), (cx + s * 0.7, cy + s * 0.2), (cx + s * 0.4, cy + s),
                                             (cx - s * 0.4, cy + s), (cx - s * 0.7, cy + s * 0.2)])
    elif kind == 'phoenix':
        pygame.draw.polygon(surface, color, [(cx, cy - s * 0.4), (cx - s, cy - s), (cx - s * 0.5, cy + s * 0.2),
                                             (cx, cy + s), (cx + s * 0.5, cy + s * 0.2), (cx + s, cy - s)])


class PerkScreen:
    """Écran de sélection plein écran (le jeu est en pause pendant le choix)."""

    def __init__(self, player):
        self.player = player
        self.choices = roll_choices(player.perks)
        self.t = 0.0
        self.cards = []
        w, h, gap = 270, 340, 36
        total = len(self.choices) * w + (len(self.choices) - 1) * gap
        x0 = (WIDTH - total) // 2
        for i, pid in enumerate(self.choices):
            self.cards.append((pid, pygame.Rect(x0 + i * (w + gap), HEIGHT // 2 - h // 2 + 30, w, h)))
        self.hover = -1

    @property
    def empty(self):
        return not self.choices

    def handle_event(self, event):
        """Retourne l'id de la bénédiction choisie ou None."""
        if self.t < 0.45:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for pid, rect in self.cards:
                if rect.collidepoint(event.pos):
                    return pid
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                                          pygame.K_KP1, pygame.K_KP2, pygame.K_KP3):
            idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2}[event.key]
            if idx < len(self.cards):
                return self.cards[idx][0]
        return None

    def draw(self, surface, dt):
        from fx import render_outlined, get_font
        self.t += dt
        a = min(1.0, self.t / 0.35)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 4, 14, int(225 * a)))
        surface.blit(overlay, (0, 0))

        title = render_outlined("BÉNÉDICTION", 58, GOLD, width=3, bold=True)
        surface.blit(title, title.get_rect(center=(WIDTH // 2, 90 - int((1 - a) * 30))))
        sub = render_outlined(f"Niveau {self.player.level} atteint - choisissez un don (clic ou 1/2/3)", 22, (220, 210, 190))
        surface.blit(sub, sub.get_rect(center=(WIDTH // 2, 140)))

        mouse = pygame.mouse.get_pos()
        for i, (pid, rect) in enumerate(self.cards):
            name, desc, rarity, max_st, icon = PERKS[pid]
            col = RARITY_COLORS[rarity]
            delay = i * 0.08
            k = max(0.0, min(1.0, (self.t - delay) / 0.35))
            k = 1 - (1 - k) ** 3
            r = rect.move(0, int((1 - k) * 120))
            hovered = r.collidepoint(mouse) and self.t > 0.45
            if hovered:
                r = r.inflate(14, 14)
            card = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(card, (22, 18, 30, int(250 * k)), card.get_rect(), border_radius=14)
            for y in range(r.height):
                g = int(40 * (1 - y / r.height))
                pygame.draw.line(card, (*col, int(g * k)), (8, y), (r.width - 8, y))
            surface.blit(card, r.topleft)
            pygame.draw.rect(surface, col, r, 3 if hovered else 2, border_radius=14)
            # pulsation de l'icône
            pul = 1 + 0.06 * math.sin(self.t * 5 + i)
            draw_icon(surface, icon, (r.centerx, r.y + 95), int(32 * pul), col)
            pygame.draw.circle(surface, col, (r.centerx, r.y + 95), int(56 * pul), 2)
            nm = render_outlined(name, 26, (255, 255, 255), bold=True)
            surface.blit(nm, nm.get_rect(center=(r.centerx, r.y + 182)))
            rar = get_font(18).render(rarity.upper(), True, col)
            surface.blit(rar, rar.get_rect(center=(r.centerx, r.y + 210)))
            # description multi-lignes
            words, line, y = desc.split(), "", r.y + 245
            font = get_font(20)
            for w in words:
                test = (line + " " + w).strip()
                if font.size(test)[0] > r.width - 36:
                    surf = font.render(line, True, (220, 215, 205))
                    surface.blit(surf, surf.get_rect(center=(r.centerx, y)))
                    y += 24
                    line = w
                else:
                    line = test
            if line:
                surf = font.render(line, True, (220, 215, 205))
                surface.blit(surf, surf.get_rect(center=(r.centerx, y)))
            owned = self.player.perks.get(pid, 0)
            st = get_font(17).render(f"Possédé : {owned}/{max_st}   [{i + 1}]", True, TEXT_DIM)
            surface.blit(st, st.get_rect(center=(r.centerx, r.bottom - 22)))
