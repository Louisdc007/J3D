"""Tableau des primes : contrats à remplir pendant les expéditions."""
import random
import pygame
from settings import *

TIER_LABEL = {'tier1': "Orcs", 'tier2': "Champignons", 'tier3': "Mouches", 'tier4': "Squelettes", 'tier5': "Gobelins"}


def _tiers_for(level):
    tiers = ['tier1']
    if level >= 3: tiers.append('tier2')
    if level >= 6: tiers.append('tier3')
    if level >= 10: tiers.append('tier4')
    if level >= 15: tiers.append('tier5')
    return tiers


def new_contract(level, taken_kinds=()):
    """Tire un contrat adapté au niveau du joueur."""
    kinds = ['kill_tier', 'kill_any', 'chests', 'elites', 'barrels', 'extract_iron', 'streak']
    if level >= 4:
        kinds.append('boss')
    kinds = [k for k in kinds if k not in taken_kinds] or kinds
    kind = random.choice(kinds)
    scale = 1 + level / 8
    c = {'kind': kind, 'progress': 0, 'target': None}
    if kind == 'kill_tier':
        tier = random.choice(_tiers_for(level))
        c['target'] = tier
        c['goal'] = int(random.randint(8, 14) * (1 + level / 20))
        c['desc'] = f"Éliminer {c['goal']} {TIER_LABEL[tier]}"
    elif kind == 'kill_any':
        c['goal'] = int(random.randint(20, 30) * (1 + level / 15))
        c['desc'] = f"Vaincre {c['goal']} monstres"
    elif kind == 'chests':
        c['goal'] = random.randint(3, 5)
        c['desc'] = f"Ouvrir {c['goal']} coffres"
    elif kind == 'elites':
        c['goal'] = random.randint(2, 4)
        c['desc'] = f"Abattre {c['goal']} élites"
    elif kind == 'barrels':
        c['goal'] = random.randint(10, 16)
        c['desc'] = f"Briser {c['goal']} tonneaux ou jarres"
    elif kind == 'extract_iron':
        c['goal'] = int(random.randint(15, 25) * scale)
        c['desc'] = f"Rapporter {c['goal']} fer en une expédition"
    elif kind == 'streak':
        c['goal'] = random.randint(4, 6)
        c['desc'] = f"Réussir une série de {c['goal']} victimes"
    elif kind == 'boss':
        c['goal'] = 1
        c['desc'] = "Terrasser un Gardien"
    rich = kind in ('boss', 'elites', 'extract_iron', 'streak')
    c['reward'] = {
        'gold': int(random.randint(30, 50) * scale * (1.8 if rich else 1)),
        'iron': int(random.randint(20, 40) * scale),
        'xp': int(random.randint(25, 45) * scale * (1.5 if rich else 1)),
    }
    return c


class ContractBoard:
    SIZE = 3

    def __init__(self):
        self.contracts = []

    def ensure(self, level):
        while len(self.contracts) < self.SIZE:
            self.contracts.append(new_contract(level, [c['kind'] for c in self.contracts]))

    def done(self, c):
        return c['progress'] >= c['goal']

    def notify(self, event, **kw):
        """Fait progresser les contrats. Retourne la liste de ceux qui viennent d'être remplis."""
        finished = []
        for c in self.contracts:
            if self.done(c):
                continue
            k, before = c['kind'], c['progress']
            if event == 'kill':
                if k == 'kill_any' or (k == 'kill_tier' and kw.get('tier') == c['target']):
                    c['progress'] += 1
                if k == 'elites' and kw.get('elite'):
                    c['progress'] += 1
            elif event == 'chest' and k == 'chests':
                c['progress'] += 1
            elif event == 'barrel' and k == 'barrels':
                c['progress'] += 1
            elif event == 'boss' and k == 'boss':
                c['progress'] += 1
            elif event == 'extract' and k == 'extract_iron':
                c['progress'] = max(c['progress'], min(c['goal'], kw.get('iron', 0)))
            elif event == 'streak' and k == 'streak':
                c['progress'] = max(c['progress'], min(c['goal'], kw.get('count', 0)))
            c['progress'] = min(c['goal'], c['progress'])
            if before < c['goal'] <= c['progress']:
                finished.append(c)
        return finished

    def claim(self, index, player):
        c = self.contracts[index]
        if not self.done(c):
            return None
        r = c['reward']
        player.inventory['gold'] += r['gold']
        player.inventory['iron'] += r['iron']
        player.inventory['xp'] += r['xp']
        player.stats['contracts'] = player.stats.get('contracts', 0) + 1
        self.contracts[index] = new_contract(player.level, [x['kind'] for x in self.contracts])
        return r

    def to_save(self):
        return [dict(c) for c in self.contracts]

    def load(self, data):
        self.contracts = []
        for c in data or []:
            if isinstance(c, dict) and {'kind', 'goal', 'progress', 'desc', 'reward'} <= set(c):
                self.contracts.append(c)
        self.contracts = self.contracts[:self.SIZE]

    # ------------------------------------------------------------------
    def draw_tracker(self, surface, x, y):
        """Petit suivi des contrats dans le HUD du donjon."""
        from fx import render_outlined
        title = render_outlined("CONTRATS", 14, GOLD, width=1, bold=True)
        surface.blit(title, (x, y))
        y += 18
        for c in self.contracts:
            done = self.done(c)
            col = (140, 255, 150) if done else (220, 210, 195)
            txt = f"{c['desc']}  {c['progress']}/{c['goal']}"
            s = render_outlined(txt, 14, col, width=1)
            surface.blit(s, (x, y))
            bar = pygame.Rect(x, y + 16, 150, 3)
            pygame.draw.rect(surface, (40, 34, 30), bar)
            bar.width = int(150 * c['progress'] / max(1, c['goal']))
            pygame.draw.rect(surface, (120, 220, 130) if done else GOLD_DARK, bar)
            y += 24

    def board_layout(self, panel):
        rows = []
        for i in range(len(self.contracts)):
            row = pygame.Rect(panel.x + 24, panel.y + 80 + i * 92, panel.width - 48, 80)
            btn = pygame.Rect(0, 0, 130, 40)
            btn.midright = (row.right - 14, row.centery)
            rows.append((row, btn))
        return rows

    def draw_board(self, surface, panel, t=0.0):
        from fx import render_outlined, draw_panel, get_font
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        draw_panel(surface, panel, alpha=242, radius=12)
        title = render_outlined("TABLEAU DES PRIMES", 34, GOLD, width=2, bold=True)
        surface.blit(title, title.get_rect(center=(panel.centerx, panel.y + 34)))
        sub = get_font(16).render("Remplissez les contrats en expédition, puis revenez réclamer la prime.", True, TEXT_DIM)
        surface.blit(sub, sub.get_rect(center=(panel.centerx, panel.y + 62)))
        mouse = pygame.mouse.get_pos()
        for c, (row, btn) in zip(self.contracts, self.board_layout(panel)):
            done = self.done(c)
            pygame.draw.rect(surface, (34, 30, 26) if not done else (30, 46, 30), row, border_radius=8)
            pygame.draw.rect(surface, (90, 76, 56) if not done else (110, 200, 120), row, 2, border_radius=8)
            d = render_outlined(c['desc'], 21, (240, 230, 210), width=1, bold=True)
            surface.blit(d, (row.x + 16, row.y + 10))
            bar = pygame.Rect(row.x + 16, row.y + 40, 300, 10)
            pygame.draw.rect(surface, (20, 18, 16), bar, border_radius=4)
            fill = bar.copy()
            fill.width = int(bar.width * c['progress'] / max(1, c['goal']))
            pygame.draw.rect(surface, (110, 210, 120) if done else GOLD, fill, border_radius=4)
            prog = get_font(15).render(f"{c['progress']} / {c['goal']}", True, (220, 210, 190))
            surface.blit(prog, (bar.right + 10, bar.y - 3))
            r = c['reward']
            rew = get_font(15).render(f"Prime : {r['gold']} or · {r['iron']} fer · {r['xp']} XP", True, (230, 200, 120))
            surface.blit(rew, (row.x + 16, row.y + 56))
            hov = btn.collidepoint(mouse)
            if done:
                col = (90, 170, 90) if not hov else (120, 210, 120)
                pygame.draw.rect(surface, col, btn, border_radius=6)
                lab = render_outlined("RÉCLAMER", 18, (255, 255, 255), width=1, bold=True)
            else:
                pygame.draw.rect(surface, (50, 44, 40), btn, border_radius=6)
                lab = render_outlined("EN COURS", 18, (150, 140, 130), width=1, bold=True)
            surface.blit(lab, lab.get_rect(center=btn.center))
        close = pygame.Rect(0, 0, 180, 40)
        close.midbottom = (panel.centerx, panel.bottom - 14)
        hov = close.collidepoint(mouse)
        pygame.draw.rect(surface, (70, 40, 40) if hov else (40, 32, 30), close, border_radius=6)
        pygame.draw.rect(surface, GOLD if hov else PANEL_BORDER, close, 2, border_radius=6)
        lab = render_outlined("Fermer", 18, (240, 230, 210), width=1)
        surface.blit(lab, lab.get_rect(center=close.center))
        return close
