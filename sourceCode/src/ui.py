import math
import pygame
from settings import *
from fx import render_outlined, get_font, draw_panel
from entities.item import get_icon


class UI():
    """Interface en jeu : vie (avec traînée de dégâts), XP, compétences,
    ressources, horloge, barre de boss, notifications."""

    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.font = get_font(UI_FONT_SIZE)
        self.clock_font = get_font(30, bold=True)
        self.ghost_health = None
        self.shown_health = None
        self.boss_ghost = None
        self.toasts = []
        self.t = 0.0
        self.coin_icon = get_icon('gold')[0]
        self.iron_icon = get_icon('iron')[0]
        self.heart_icon = get_icon('health')[0]
        self.artifact_icon = get_icon('artifact')[0]
        self.res_display = {'gold': 0, 'iron': 0}
        self.res_bump = {'gold': 0.0, 'iron': 0.0}
        self.low_hp_overlay = None

    # ------------------------------------------------------------------
    def toast(self, text, color=(240, 230, 210), icon=None, duration=2.8):
        self.toasts.append({'text': text, 'color': color, 't': 0.0, 'dur': duration, 'icon': icon})
        if len(self.toasts) > 5:
            self.toasts.pop(0)

    # ------------------------------------------------------------------
    def show_bar(self, current, max_amount, bg_rect, color):
        """Compatibilité : barre simple."""
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        ratio = max(0.0, min(1.0, current / max(1, max_amount)))
        cur = bg_rect.copy()
        cur.width = int(bg_rect.width * ratio)
        pygame.draw.rect(self.display_surface, color, cur)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

    def _fancy_bar(self, rect, ratio, ghost_ratio, color, dark, label=None):
        s = self.display_surface
        pygame.draw.rect(s, (8, 6, 10), rect.inflate(6, 6), border_radius=6)
        pygame.draw.rect(s, dark, rect, border_radius=4)
        if ghost_ratio > ratio:
            g = rect.copy()
            g.width = int(rect.width * ghost_ratio)
            pygame.draw.rect(s, (240, 230, 200), g, border_radius=4)
        f = rect.copy()
        f.width = int(rect.width * ratio)
        if f.width > 0:
            pygame.draw.rect(s, color, f, border_radius=4)
            hl = pygame.Rect(f.x + 2, f.y + 2, max(0, f.width - 4), max(1, rect.height // 3))
            light = tuple(min(255, c + 70) for c in color)
            pygame.draw.rect(s, light, hl, border_radius=3)
        pygame.draw.rect(s, PANEL_BORDER, rect.inflate(4, 4), 2, border_radius=6)
        if label:
            txt = render_outlined(label, 17, (255, 255, 255), width=1, bold=True)
            s.blit(txt, txt.get_rect(center=rect.center))

    def _skill_slot(self, center, key, ratio, icon_fn, count=None, active=True):
        s = self.display_surface
        r = pygame.Rect(0, 0, 54, 54)
        r.center = center
        pygame.draw.rect(s, (14, 12, 18), r, border_radius=10)
        icon_fn(s, r.center, active and ratio >= 1)
        if ratio < 1:
            # balayage de recharge
            cover = pygame.Surface(r.size, pygame.SRCALPHA)
            h = int(r.height * (1 - ratio))
            cover.fill((0, 0, 0, 170), (0, 0, r.width, h))
            s.blit(cover, r.topleft)
        border = GOLD if ratio >= 1 and active else (90, 80, 70)
        pygame.draw.rect(s, border, r, 2, border_radius=10)
        k = render_outlined(key, 14, (230, 220, 200), width=1, bold=True)
        s.blit(k, k.get_rect(midtop=(r.centerx, r.bottom + 2)))
        if count is not None:
            c = render_outlined(str(count), 18, (255, 255, 255), width=2, bold=True)
            s.blit(c, c.get_rect(bottomright=(r.right - 2, r.bottom)))

    # --- icônes des compétences ------------------------------------------
    @staticmethod
    def _icon_sword(s, c, on):
        col = (230, 230, 240) if on else (110, 110, 120)
        pygame.draw.line(s, col, (c[0] - 14, c[1] + 14), (c[0] + 12, c[1] - 12), 5)
        pygame.draw.line(s, (180, 140, 60), (c[0] - 12, c[1] + 2), (c[0] - 2, c[1] + 12), 4)

    @staticmethod
    def _icon_spin(s, c, on):
        col = (120, 200, 255) if on else (80, 90, 110)
        pygame.draw.arc(s, col, (c[0] - 16, c[1] - 16, 32, 32), 0.4, 5.6, 4)
        pygame.draw.polygon(s, col, [(c[0] + 16, c[1] - 8), (c[0] + 22, c[1] + 2), (c[0] + 9, c[1] + 2)])

    @staticmethod
    def _icon_dash(s, c, on):
        col = (150, 230, 255) if on else (80, 90, 110)
        for i in range(3):
            pygame.draw.line(s, col, (c[0] - 16 + i * 4, c[1] - 8 + i * 8), (c[0] + 8 + i * 4, c[1] - 8 + i * 8), 3)
        pygame.draw.polygon(s, col, [(c[0] + 12, c[1] - 14), (c[0] + 20, c[1]), (c[0] + 12, c[1] + 14)])

    @staticmethod
    def _icon_potion(s, c, on):
        col = (220, 40, 60) if on else (90, 50, 55)
        pygame.draw.rect(s, (200, 200, 210), (c[0] - 4, c[1] - 16, 8, 7))
        pygame.draw.circle(s, col, (c[0], c[1] + 4), 12)
        pygame.draw.circle(s, (255, 160, 170) if on else (120, 90, 95), (c[0] - 4, c[1]), 3)

    # ------------------------------------------------------------------
    def show_clock(self, game_time, day_duration, start_hour=20, dungeon=False):
        ratio = min(1.0, game_time / max(1, day_duration))
        hour_f = start_hour + 24 * ratio
        h = int(hour_f % 24)
        m = int((hour_f * 60) % 60)
        night = h >= 20 or h < 6
        s = self.display_surface
        rect = pygame.Rect(WIDTH - 176, 12, 160, 44)
        draw_panel(s, rect, alpha=210, radius=10)
        # soleil / lune
        ic = (rect.x + 26, rect.centery)
        if night:
            pygame.draw.circle(s, (230, 230, 255), ic, 12)
            pygame.draw.circle(s, (18, 16, 24), (ic[0] + 6, ic[1] - 4), 11)
        else:
            pygame.draw.circle(s, (255, 200, 60), ic, 10)
            for i in range(8):
                a = i / 8 * math.tau + self.t
                pygame.draw.line(s, (255, 200, 60), (ic[0] + math.cos(a) * 13, ic[1] + math.sin(a) * 13),
                                 (ic[0] + math.cos(a) * 17, ic[1] + math.sin(a) * 17), 2)
        txt = render_outlined(f"{h:02d}:{m:02d}", 30, TEXT_COLOR, width=2, bold=True)
        s.blit(txt, txt.get_rect(midleft=(rect.x + 50, rect.centery)))
        return h

    def show_inventory(self, inventory, potions=None):
        s = self.display_surface
        rect = pygame.Rect(16, HEIGHT - 62, 230 if potions is None else 300, 46)
        draw_panel(s, rect, alpha=210, radius=10)
        for key in ('gold', 'iron'):
            target = inventory.get(key, 0)
            if self.res_display[key] != target:
                if target > self.res_display[key]:
                    self.res_bump[key] = 0.25
                diff = target - self.res_display[key]
                step = max(1, abs(diff) // 8)
                self.res_display[key] += step if diff > 0 else -step
                if (diff > 0 and self.res_display[key] > target) or (diff < 0 and self.res_display[key] < target):
                    self.res_display[key] = target
        x = rect.x + 14
        for key, icon in (('gold', self.coin_icon), ('iron', self.iron_icon)):
            bump = self.res_bump[key]
            img = pygame.transform.rotozoom(icon, 0, 1.3 + bump * 1.5)
            s.blit(img, img.get_rect(center=(x + 12, rect.centery)))
            col = (255, 230, 140) if bump > 0 else (240, 235, 220)
            t = render_outlined(str(self.res_display[key]), 24, col, width=2, bold=True)
            s.blit(t, t.get_rect(midleft=(x + 30, rect.centery)))
            x += 108
        if potions is not None:
            pot = get_icon('potion')[0]
            s.blit(pot, pot.get_rect(center=(x + 8, rect.centery)))
            t = render_outlined(f"{potions}/{MAX_POTIONS}", 22, (255, 190, 200), width=2, bold=True)
            s.blit(t, t.get_rect(midleft=(x + 22, rect.centery)))

    def draw_boss_bar(self, boss):
        s = self.display_surface
        if self.boss_ghost is None:
            self.boss_ghost = boss.hp_ratio
        ratio = boss.hp_ratio
        if self.boss_ghost > ratio:
            self.boss_ghost = max(ratio, self.boss_ghost - 0.25 * self.dt)
        else:
            self.boss_ghost = ratio
        w = 560
        rect = pygame.Rect((WIDTH - w) // 2, 72, w, 16)
        col = (200, 30, 50) if boss.phase == 1 else (255, 70, 30)
        self._fancy_bar(rect, ratio, self.boss_ghost, col, (40, 8, 12))
        name = render_outlined(boss.name.upper(), 22, (255, 210, 190), width=2, bold=True)
        s.blit(name, name.get_rect(midbottom=(rect.centerx, rect.top - 6)))
        if boss.phase > 1:
            ph = render_outlined("ENRAGÉ" if boss.phase == 2 else "FURIE", 16, (255, 120, 60), width=1, bold=True)
            s.blit(ph, ph.get_rect(midleft=(rect.right + 10, rect.centery)))

    def draw_toasts(self):
        s = self.display_surface
        y = 270
        alive = []
        for t in self.toasts:
            t['t'] += self.dt
            if t['t'] > t['dur']:
                continue
            alive.append(t)
            k = min(1.0, t['t'] / 0.25, (t['dur'] - t['t']) / 0.4)
            surf = render_outlined(t['text'], 20, t['color'], width=2, bold=True)
            w = surf.get_width() + 24 + (26 if t['icon'] else 0)
            rect = pygame.Rect(WIDTH - 16 - w + int((1 - k) * 60), y, w, 34)
            bg = pygame.Surface(rect.size, pygame.SRCALPHA)
            bg.fill((12, 10, 16, int(200 * k)))
            s.blit(bg, rect.topleft)
            pygame.draw.rect(s, (*PANEL_BORDER,), rect, 1)
            x = rect.x + 12
            if t['icon']:
                s.blit(t['icon'], t['icon'].get_rect(center=(x + 10, rect.centery)))
                x += 26
            surf.set_alpha(int(255 * k))
            s.blit(surf, surf.get_rect(midleft=(x, rect.centery)))
            y += 40
        self.toasts = alive

    # ------------------------------------------------------------------
    def display(self, player, game_time, day_duration, start_hour=20, show_inventory=True, mode='hub', dt=1 / 60,
                boss=None):
        self.dt = dt
        self.t += dt
        for k in self.res_bump:
            self.res_bump[k] = max(0.0, self.res_bump[k] - dt)
        s = self.display_surface

        # --- Vie ---
        hp_ratio = max(0.0, player.health / max(1, player.max_health))
        if self.ghost_health is None or self.ghost_health < hp_ratio:
            self.ghost_health = hp_ratio
        else:
            self.ghost_health = max(hp_ratio, self.ghost_health - 0.6 * dt)

        # médaillon de niveau
        center = (52, 50)
        pygame.draw.circle(s, (10, 8, 12), center, 36)
        xp_ratio = max(0.0, min(1.0, player.inventory['xp'] / max(1, player.xp_to_next_level)))
        if xp_ratio > 0:
            pygame.draw.arc(s, (90, 220, 140), (center[0] - 34, center[1] - 34, 68, 68),
                            math.pi / 2, math.pi / 2 + math.tau * xp_ratio, 5)
        pygame.draw.circle(s, PANEL_BORDER, center, 36, 2)
        pygame.draw.circle(s, (30, 24, 34), center, 27)
        lv = render_outlined(str(player.level), 30, GOLD, width=2, bold=True)
        s.blit(lv, lv.get_rect(center=(center[0], center[1] + 1)))
        nv = render_outlined("NIV", 12, TEXT_DIM, width=1)
        s.blit(nv, nv.get_rect(center=(center[0], center[1] - 19)))

        hp_rect = pygame.Rect(96, 26, 250, 22)
        low = hp_ratio < 0.3
        col = HEALTH_COLOR if not low else (255, 40 + int(40 * math.sin(self.t * 10)), 40)
        self._fancy_bar(hp_rect, hp_ratio, self.ghost_health, col, (45, 10, 12),
                        f"{max(0, int(player.health))} / {player.max_health}")
        xp_rect = pygame.Rect(96, 56, 200, 9)
        self._fancy_bar(xp_rect, xp_ratio, 0, (90, 200, 120), (15, 35, 20))
        xp_t = render_outlined(f"XP {player.inventory['xp']}/{player.xp_to_next_level}", 14, (180, 230, 190), width=1)
        s.blit(xp_t, xp_t.get_rect(midleft=(xp_rect.right + 8, xp_rect.centery)))

        # artefacts
        x = 98
        for i in range(4):
            r = pygame.Rect(x + i * 24, 74, 20, 22)
            if i < player.artifacts:
                s.blit(self.artifact_icon, self.artifact_icon.get_rect(center=r.center).move(0, 0))
            else:
                pygame.draw.polygon(s, (60, 50, 60), [(r.centerx, r.top + 2), (r.right - 2, r.top + 9),
                                                     (r.centerx, r.bottom), (r.left + 2, r.top + 9)], 2)

        if mode == 'dungeon':
            # --- Barre de compétences ---
            cx = WIDTH // 2
            y = HEIGHT - 52
            atk_ratio = 1.0 if not player.attacking else 0.4
            self._skill_slot((cx - 99, y), "CLIC G", atk_ratio, self._icon_sword)
            self._skill_slot((cx - 33, y), "CLIC D", player.spin_ready_ratio(), self._icon_spin)
            self._skill_slot((cx + 33, y), "ESPACE", player.dash_ready_ratio(), self._icon_dash)
            self._skill_slot((cx + 99, y), "R", 1.0, self._icon_potion, count=player.potions, active=player.potions > 0)
            if player.combo_step >= 1 and player.attacking:
                combo = render_outlined(f"COMBO x{player.combo_step + 1}", 20, GOLD, width=2, bold=True)
                s.blit(combo, combo.get_rect(midbottom=(cx, y - 34)))

            # vignette rouge pulsante quand la vie est basse
            if low and player.health > 0:
                if self.low_hp_overlay is None:
                    from fx import vignette
                    self.low_hp_overlay = vignette(220, (160, 0, 0))
                a = int(120 + 100 * math.sin(self.t * 6))
                self.low_hp_overlay.set_alpha(max(0, a))
                s.blit(self.low_hp_overlay, (0, 0))

        if boss is not None and boss.health > 0:
            self.draw_boss_bar(boss)
        else:
            self.boss_ghost = None

        if show_inventory:
            self.show_inventory(player.inventory, potions=player.potions if mode == 'hub' else None)

        self.show_clock(game_time, day_duration, start_hour, dungeon=(mode == 'dungeon'))
        self.draw_toasts()
