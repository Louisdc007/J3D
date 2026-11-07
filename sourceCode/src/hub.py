import math
import pygame
import random
import os
from settings import *
from entities.npc import NPC
from fx import ParticleSystem, render_outlined, draw_panel, additive_glow, get_font
from audio import sfx

from building_art import building_image, ghost_image, thumbnail
from contracts import ContractBoard

UPGRADE_DEFS = {
    # action : (clé, niveau max, or de base, or par niveau, fer de base, fer par niveau, libellé)
    'upgrade_armor': ('armor', 5, 60, 45, 40, 30, "Armure"),
    'upgrade_sharp': ('sharp', 4, 80, 55, 30, 25, "Affûtage"),
}


def upgrade_cost(action, level):
    _, _, g0, g1, i0, i1, _ = UPGRADE_DEFS[action]
    return g0 + g1 * level, i0 + i1 * level

VILLAGER_LINES = [
    "On dit que le Seigneur dort sur une montagne d'or...",
    "Les squelettes parent vos coups : brisez leur garde avec le 3e coup du combo !",
    "Méfiez-vous des coffres qui tremblent, ce sont des mimiques.",
    "L'aube vous surprendra : rentrez par le portail avant 6 h.",
    "Les gobelins foncent tout droit. Esquivez sur le côté !",
    "Les champignons pourrissent même après leur mort. Ne restez pas dans leur nuage.",
    "La forge peut renforcer votre armure, pensez-y.",
    "Un autel brille au fond des donjons. Touchez-le, il vous bénira.",
    "Le tableau des primes paie bien, si on a le cran.",
    "Mon grand-père a connu le village avant la trahison...",
    "Merci de nous protéger, voyageur.",
    "Le marché vend des potions. Ne partez jamais sans !",
    "Quatre artefacts... et le Seigneur tombera.",
]

class Block(pygame.sprite.Sprite):
    def __init__(self, rect, group):
        super().__init__(group)
        self.rect = rect

class Building(pygame.sprite.Sprite):
    def __init__(self, type, pos, group):
        super().__init__(group)
        self.type = type
        data = BUILDING_DATA[type]
        self.image = building_image(type, pos)
        self.rect = self.image.get_rect(topleft=pos)
        self.name = data['name']

class Hub:
    def __init__(self, obstacle_sprites):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, 18)
        self.title_font = pygame.font.Font(UI_FONT, 30)
        self.info_font = pygame.font.Font(UI_FONT, 20)

        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2
        
        self.obstacle_sprites = obstacle_sprites
        self.built_buildings = [] 
        
        self.building_sprites = pygame.sprite.Group() 
        self.path_sprites = pygame.sprite.Group()     
        self.npc_sprites = pygame.sprite.Group() 
        self.hub_obstacles = pygame.sprite.Group()

        # --- TEXTURE HERBE (fond) ---
        grass_path = resource_path(os.path.join('assets', 'floor_assets', 'grass.jpg'))
        try:
            self.grass_tile = pygame.image.load(grass_path).convert()
            self.grass_tile = pygame.transform.scale(self.grass_tile, (320, 320))
        except Exception:
            self.grass_tile = None

        # --- TEXTURE CHEMIN (rond-point + route) ---
        dirt_path = resource_path(os.path.join('assets', 'floor_assets', 'dirt_path.jpg'))
        try:
            self.dirt_tile = pygame.image.load(dirt_path).convert()
            # La texture représente 5x5 tiles de 64px -> 320x320
            self.dirt_tile = pygame.transform.scale(self.dirt_tile, (320, 320))
        except Exception:
            self.dirt_tile = None

        # --- LAYOUT UI (CONSTANTES) ---
        self.panel_height = 180 
        self.panel_top = HEIGHT - self.panel_height
        self.buttons_y = HEIGHT - 90 
        
        # --- MENUS BATIMENTS ---
        self.active_menu = None # 'forge', 'shop', 'bank', 'library' ou None
        self.menu_buttons = []  # Liste des boutons du menu actif
        self.menu_rect = pygame.Rect(0, 0, 460, 320)
        self.menu_rect.center = (WIDTH//2, HEIGHT//2)
        self.state_lock_time = 0
        self.warning_msg = None
        self.warning_timer = 0
        
        # --- ZONES FIXES ---
        self.campfire_rect = pygame.Rect(0, 0, 60, 60)
        self.campfire_rect.center = (self.center_x, self.center_y)
        self.tent_rect = pygame.Rect(0, 0, 100, 80)
        self.tent_rect.bottomright = (self.center_x - 50, self.center_y - 20)
        self.gate_rect = pygame.Rect(0, 0, 220, 60)
        self.gate_rect.midbottom = (self.center_x, HEIGHT - 30)
        
        self.board_rect = pygame.Rect(0, 0, 76, 66)
        self.board_rect.bottomleft = (self.center_x + 64, self.center_y - 34)
        self.board = ContractBoard()
        self.board_open = False
        self.board_panel = pygame.Rect(0, 0, 640, 420)
        self.board_panel.center = (WIDTH // 2, HEIGHT // 2)
        self.bark_t = 4.0
        self.fixed_obstacles = [self.campfire_rect, self.tent_rect, self.gate_rect, self.board_rect]
        for rect in self.fixed_obstacles: Block(rect, [self.hub_obstacles])

        # --- POPULATION ---
        self.max_population = 0 
        self.max_cap_limit = 15 

        self.banked_iron = 0
        self.banked_gold = 0

        # --- ETATS ---
        self.waiting_for_night = False
        self.night_arrived = False
        self.pending_dungeon_choice = None
        self.menu_state = None 

        # --- BOUTONS ---
        self.btn_random = pygame.Rect(0, 0, 300, 50)
        self.btn_random.center = (self.center_x, self.center_y - 50)
        self.btn_main_dungeons = pygame.Rect(0, 0, 300, 50)
        self.btn_main_dungeons.center = (self.center_x, self.center_y + 50)
        
        self.btn_wait_night = pygame.Rect(0, 0, 300, 50)
        self.btn_wait_night.center = (self.center_x, self.center_y - 50)
        self.btn_go_now = pygame.Rect(0, 0, 300, 50)
        self.btn_go_now.center = (self.center_x, self.center_y + 50)
        
        self.btn_rest_night = pygame.Rect(0, 0, 300, 50)
        self.btn_rest_night.center = (self.center_x, self.center_y - 50)
        self.btn_explore_night = pygame.Rect(0, 0, 300, 50)
        self.btn_explore_night.center = (self.center_x, self.center_y + 50)

        # --- CONSTRUCTION ---
        self.build_mode_active = False
        self.selected_blueprint = None 
        self.build_buttons = []
        
        self.btn_open_build = pygame.Rect(20, HEIGHT - 180, 160, 50)

        self.generate_build_ui()

    def get_building_count(self, b_type):
        count = 0
        for b in self.built_buildings:
            if b['type'] == b_type: count += 1
        return count

    def recalculate_population(self):
        self.max_population = 0 
        self.current_workers = 0
        for b in self.built_buildings:
            b_type = b['type']
            if b_type in BUILDING_DATA:
                data = BUILDING_DATA[b_type]
                self.max_population += data.get('capacity', 0)
                self.current_workers += data.get('cost_npc', 0)
        if self.max_population > self.max_cap_limit: self.max_population = self.max_cap_limit

    def spawn_npcs(self, player):
        self.recalculate_population()
        self.npc_sprites.empty()
        count = self.max_population
        for _ in range(count):
            attempts = 0
            while attempts < 20:
                x = self.center_x + random.randint(-300, 300)
                y = self.center_y + random.randint(-250, 250)
                test_rect = pygame.Rect(x, y, 14, 28)
                collides = False
                for obs in self.fixed_obstacles:
                    if test_rect.colliderect(obs): collides = True
                for b in self.building_sprites:
                    if test_rect.colliderect(b.rect): collides = True
                if not collides:
                    NPC([self.npc_sprites], (x, y), self.hub_obstacles)
                    break
                attempts += 1

    def generate_build_ui(self):
        self.build_buttons = []
        button_size = 64; gap = 20
        nb_buildings = len(BUILDING_DATA)
        total_width = (nb_buildings * button_size) + ((nb_buildings - 1) * gap)
        start_x = (WIDTH - total_width) // 2
        y = self.buttons_y 
        for i, (key, data) in enumerate(BUILDING_DATA.items()):
            rect = pygame.Rect(start_x + i * (button_size + gap), y, button_size, button_size)
            self.build_buttons.append({'rect': rect, 'key': key, 'data': data})

    def open_building_menu(self, b_type, player=None):
        """Ouvre le menu spécifique à un type de batiment"""
        if player is not None:
            self._player = player
        player = getattr(self, '_player', None)
        self.active_menu = b_type
        self.menu_buttons = []
        self.state_lock_time = pygame.time.get_ticks() + 300
        
        cx = self.menu_rect.centerx
        start_y = self.menu_rect.top + 80
        gap = 60
        
        # Définition des boutons selon le batiment
        if b_type == 'forge':
            self.menu_buttons.append({
                'text': f"Améliorer Dégâts ({PRICES['upgrade_damage']} Or + {PRICES['upgrade_iron_cost']} Fer)",
                'action': 'upgrade_dmg',
                'rect': pygame.Rect(0, 0, 400, 40),
                'pos': (cx, start_y)
            })
            for i, (action, d) in enumerate(UPGRADE_DEFS.items()):
                lvl = player.upgrades.get(d[0], 0) if player else 0
                if lvl >= d[1]:
                    text = f"{d[6]} niveau {lvl}/{d[1]} (MAX)"
                else:
                    g, fe = upgrade_cost(action, lvl)
                    bonus = "-8 % dégâts subis" if d[0] == 'armor' else "+5 % critique"
                    text = f"{d[6]} {lvl}/{d[1]} : {bonus} ({g} Or + {fe} Fer)"
                self.menu_buttons.append({'text': text, 'action': action,
                                          'rect': pygame.Rect(0, 0, 400, 40), 'pos': (cx, start_y + gap * (i + 1))})
        elif b_type == 'shop':
            self.menu_buttons.append({
                'text': f"Vendre 20 Fer (+{PRICES['sell_iron']} Or)",
                'action': 'sell_iron_20',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y)
            })
            self.menu_buttons.append({
                'text': f"Acheter 20 Fer (-{PRICES['buy_iron']} Or)",
                'action': 'buy_iron_20',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y + gap)
            })
            self.menu_buttons.append({
                'text': f"Acheter Potion de soin ({PRICES['buy_potion']} Or)",
                'action': 'buy_potion',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y + gap * 2)
            })
        elif b_type == 'bank':
            self.menu_buttons.append({
                'text': f"Sécuriser 50 Fer",
                'action': 'deposit_iron',
                'rect': pygame.Rect(0, 0, 165, 40),
                'pos': (cx - 90, start_y)
            })
            self.menu_buttons.append({
                'text': f"Retirer 50 Fer",
                'action': 'withdraw_iron',
                'rect': pygame.Rect(0, 0, 165, 40),
                'pos': (cx + 90, start_y)
            })
            self.menu_buttons.append({
                'text': f"Sécuriser 50 Or",
                'action': 'deposit_gold',
                'rect': pygame.Rect(0, 0, 165, 40),
                'pos': (cx - 90, start_y + gap)
            })
            self.menu_buttons.append({
                'text': f"Retirer 50 Or",
                'action': 'withdraw_gold',
                'rect': pygame.Rect(0, 0, 165, 40),
                'pos': (cx + 90, start_y + gap)
            })
        elif b_type == 'library':
            self.menu_buttons.append({
                'text': f"Étudier: +{PRICES['study_xp_gain']} XP ({PRICES['study_gold']} Or + {PRICES['study_iron']} Fer)",
                'action': 'study',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y)
            })
            self.menu_buttons.append({
                'text': f"Recherche: +{PRICES['research_xp_gain']} XP ({PRICES['research_gold']} Or + {PRICES['research_iron']} Fer)",
                'action': 'research',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y + gap)
            })
        
        # Bouton fermer commun
        self.menu_buttons.append({
            'text': "Fermer",
            'action': 'close_menu',
            'rect': pygame.Rect(0, 0, 350, 40),
            'pos': (cx, self.menu_rect.bottom - 40)
        })
        
        for btn in self.menu_buttons:
            btn['rect'].center = btn['pos']

    # ------------------------------------------------------------------
    # Rendu du village
    # ------------------------------------------------------------------
    def _build_static_background(self):
        bg = pygame.Surface((WIDTH, HEIGHT))
        if self.grass_tile:
            tile_w, tile_h = self.grass_tile.get_size()
            for x in range(0, WIDTH, tile_w):
                for y in range(0, HEIGHT, tile_h):
                    bg.blit(self.grass_tile, (x, y))
        else:
            bg.fill((34, 139, 34))
        target = self.display_surface
        self.display_surface = bg
        self.draw_environment(static_only=True)
        self.display_surface = target
        return bg

    @staticmethod
    def day_tint(hour):
        """Couleur multipliée sur la scène selon l'heure (aube, jour, crépuscule, nuit)."""
        keys = [(0, (70, 80, 140)), (5, (80, 85, 150)), (6.5, (255, 190, 160)), (8.5, (255, 255, 255)),
                (16, (255, 255, 255)), (18, (255, 200, 150)), (19.5, (190, 120, 140)), (20.5, (90, 90, 160)),
                (24, (70, 80, 140))]
        for i in range(len(keys) - 1):
            h0, c0 = keys[i]
            h1, c1 = keys[i + 1]
            if h0 <= hour <= h1:
                k = (hour - h0) / (h1 - h0)
                return tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
        return (255, 255, 255)

    def draw(self, hour=12.0, dt=1 / 60, player=None):
        if not hasattr(self, '_bg'):
            self._bg = self._build_static_background()
            self.particles = ParticleSystem()
            self.t = 0.0
            self.ember_t = 0.0
            self.fireflies = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT - 200), random.uniform(0, 6.28)]
                              for _ in range(28)]
        self.t += dt
        surf = self.display_surface
        surf.blit(self._bg, (0, 0))
        mouse_pos = pygame.mouse.get_pos()

        for sprite in self.path_sprites: surf.blit(sprite.image, sprite.rect)
        self.draw_landmarks(mouse_pos)
        if not self.build_mode_active and not self.paused_ui_active() and not self.active_menu: self.npc_sprites.update()

        # Bâtiments et villageois triés en profondeur
        drawables = list(self.building_sprites) + list(self.npc_sprites)
        drawables.sort(key=lambda sp: sp.rect.bottom)
        for sprite in drawables:
            if sprite in self.building_sprites and sprite.type in ('tree', 'flower'):
                surf.blit(sprite.image, sprite.rect)  # décoration : ni cadre ni étiquette
            elif sprite in self.building_sprites:
                shadow = pygame.Surface((sprite.rect.width + 10, 18), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
                surf.blit(shadow, (sprite.rect.x - 5, sprite.rect.bottom - 10))
                surf.blit(sprite.image, sprite.rect)
                hovered = (sprite.rect.collidepoint(mouse_pos) and not self.paused_ui_active()
                           and not self.build_mode_active and sprite.type in ('forge', 'shop', 'bank', 'library'))
                pygame.draw.rect(surf, GOLD if hovered else (40, 30, 20), sprite.rect, 3 if hovered else 2)
                label = render_outlined(sprite.name, 17, GOLD if hovered else (240, 230, 210), width=2, bold=True)
                surf.blit(label, label.get_rect(midbottom=(sprite.rect.centerx, sprite.rect.top - 2)))
            else:
                sprite.draw(surf)

        # Ambiance jour / nuit
        tint = self.day_tint(hour)
        darkness = 1 - sum(tint) / (3 * 255)
        if tint != (255, 255, 255):
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill(tint)
            surf.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        self.draw_campfire(dt, darkness)
        if darkness > 0.15:
            # fenêtres éclairées et lucioles
            for b in self.building_sprites:
                if b.type != 'path':
                    additive_glow(surf, b.rect.centerx, b.rect.centery, 50, (int(120 * darkness), int(80 * darkness), int(20 * darkness)))
            for ff in self.fireflies:
                ff[2] += dt
                ff[0] += math.cos(ff[2] * 0.7) * 20 * dt
                ff[1] += math.sin(ff[2] * 1.3) * 14 * dt
                a = 0.5 + 0.5 * math.sin(ff[2] * 3)
                additive_glow(surf, int(ff[0]), int(ff[1]), 10, (int(160 * a * darkness), int(220 * a * darkness), int(60 * a * darkness)))
        self.particles.update(dt)
        self.particles.draw(surf, 0, 0, glow_pass=False)
        self.particles.draw(surf, 0, 0, glow_pass=True)
        for npc in self.npc_sprites:
            npc.draw_speech(surf)

        if self.night_arrived: self.draw_night_arrived_menu()
        elif self.waiting_for_night: self.draw_wait_night_menu()
        elif self.menu_state == 'dungeon': self.draw_dungeon_menu()

        if self.active_menu:
            self.draw_active_menu()
        if self.board_open:
            self.board.draw_board(surf, self.board_panel, self.t)

        # bavardages spontanés des villageois
        self.bark_t -= dt
        if self.bark_t <= 0 and self.npc_sprites:
            self.bark_t = random.uniform(7, 13)
            random.choice(list(self.npc_sprites)).say(random.choice(VILLAGER_LINES))

        if not self.night_arrived and not self.waiting_for_night and self.menu_state is None and not self.active_menu:
            if self.build_mode_active:
                self.draw_build_mode_ui()
                if self.selected_blueprint: self.draw_placement_preview(player)
            else:
                from menu_scene import draw_button
                draw_button(surf, self.btn_open_build, "CONSTRUIRE", self.btn_open_build.collidepoint(mouse_pos),
                            size=22, t=self.t)

        if self.warning_msg and pygame.time.get_ticks() < self.warning_timer:
            self.draw_warning_banner()

    def draw_campfire(self, dt, darkness):
        cx, cy = self.campfire_rect.center
        surf = self.display_surface
        flick = 1 + 0.08 * math.sin(self.t * 13) + 0.05 * math.sin(self.t * 29)
        strength = 0.35 + 0.65 * darkness
        additive_glow(surf, cx, cy, int(150 * flick * (0.6 + darkness)),
                      (int(150 * strength), int(80 * strength), int(20 * strength)))
        # bûches
        pygame.draw.line(surf, (90, 50, 25), (cx - 18, cy + 10), (cx + 18, cy + 2), 7)
        pygame.draw.line(surf, (70, 40, 20), (cx - 18, cy + 2), (cx + 18, cy + 10), 7)
        for i in range(8):
            a = i / 8 * math.tau
            pygame.draw.circle(surf, (100, 95, 90), (int(cx + math.cos(a) * 24), int(cy + 8 + math.sin(a) * 10)), 5)
        # flammes
        for i, (w, h, col) in enumerate([(26, 34, (255, 110, 30)), (18, 26, (255, 180, 60)), (9, 15, (255, 245, 190))]):
            hh = h * (1 + 0.15 * math.sin(self.t * (10 + i * 3)))
            pygame.draw.ellipse(surf, col, (cx - w // 2 + math.sin(self.t * 7 + i) * 2, cy + 6 - hh, w, hh))
        self.ember_t += dt
        if self.ember_t > 0.06:
            self.ember_t = 0
            self.particles.embers(cx, cy - 10, 1, spread_x=8)

    def draw_landmarks(self, mouse_pos):
        """Tente, feu de camp et porte de l'expédition (dessinés, interactifs)."""
        surf = self.display_surface
        idle = not self.paused_ui_active() and not self.build_mode_active
        # --- Tente ---
        t = self.tent_rect
        hov = idle and t.collidepoint(mouse_pos)
        shadow = pygame.Surface((t.width + 20, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surf.blit(shadow, (t.x - 10, t.bottom - 12))
        pygame.draw.polygon(surf, (120, 40, 40), [(t.left, t.bottom), (t.centerx, t.top), (t.right, t.bottom)])
        pygame.draw.polygon(surf, (165, 60, 50), [(t.left + 10, t.bottom), (t.centerx, t.top + 6), (t.centerx, t.bottom)])
        pygame.draw.polygon(surf, (40, 15, 15), [(t.centerx - 14, t.bottom), (t.centerx, t.top + 30), (t.centerx + 14, t.bottom)])
        pygame.draw.line(surf, (80, 60, 40), (t.centerx, t.top - 8), (t.centerx, t.top + 4), 3)
        pygame.draw.polygon(surf, GOLD if hov else (60, 20, 20),
                            [(t.left, t.bottom), (t.centerx, t.top), (t.right, t.bottom)], 2)
        if hov:
            lab = render_outlined("Se reposer (soin + passer la journée)", 16, GOLD, width=2)
            surf.blit(lab, lab.get_rect(midbottom=(t.centerx, t.top - 10)))
        # --- Tableau des primes ---
        b = self.board_rect
        hov = idle and b.collidepoint(mouse_pos)
        pygame.draw.rect(surf, (75, 50, 28), (b.x + 8, b.y + 20, 6, b.height - 20))
        pygame.draw.rect(surf, (75, 50, 28), (b.right - 14, b.y + 20, 6, b.height - 20))
        board = pygame.Rect(b.x, b.y, b.width, 46)
        pygame.draw.rect(surf, (120, 82, 46), board, border_radius=3)
        pygame.draw.rect(surf, GOLD if hov else (60, 40, 22), board, 2, border_radius=3)
        for i, (px, py) in enumerate(((8, 6), (40, 8), (20, 24), (50, 26))):
            pygame.draw.rect(surf, (230, 220, 190), (b.x + px, b.y + py, 20, 14))
            pygame.draw.circle(surf, (160, 30, 30), (b.x + px + 10, b.y + py + 2), 2)
        if any(self.board.done(c) for c in self.board.contracts):
            k = abs(math.sin(getattr(self, 't', 0) * 4))
            bang = render_outlined("!", 30, (255, 220, 80), width=2, bold=True)
            surf.blit(bang, bang.get_rect(midbottom=(b.centerx, b.top - 2 - int(6 * k))))
        if hov:
            lab = render_outlined("Tableau des primes", 16, GOLD, width=2)
            surf.blit(lab, lab.get_rect(midbottom=(b.centerx, b.top - 26)))

        # --- Porte de l'expédition ---
        g = self.gate_rect
        hov = idle and g.collidepoint(mouse_pos)
        pygame.draw.rect(surf, (70, 66, 72), (g.x - 14, g.y - 34, 30, g.height + 34))
        pygame.draw.rect(surf, (70, 66, 72), (g.right - 16, g.y - 34, 30, g.height + 34))
        pygame.draw.rect(surf, (95, 90, 100), (g.x - 20, g.y - 46, g.width + 40, 18))
        for x in range(g.x - 20, g.right + 20, 20):
            pygame.draw.line(surf, (60, 56, 64), (x, g.y - 46), (x, g.y - 28), 1)
        door = g.inflate(-30, 0)
        pygame.draw.rect(surf, (25, 15, 30), door)
        k = 0.5 + 0.5 * math.sin(getattr(self, 't', 0) * 2)
        additive_glow(surf, door.centerx, door.centery, int(60 + 20 * k), (60, 30, 90))
        for x in range(door.x, door.right, 16):
            pygame.draw.line(surf, (90, 60, 35), (x, door.y), (x, door.bottom), 2)
        pygame.draw.rect(surf, GOLD if hov else (40, 30, 25), g.inflate(4, 4), 2)
        lab = render_outlined("EXPÉDITION", 20, GOLD if hov else (235, 225, 210), width=2, bold=True)
        surf.blit(lab, lab.get_rect(center=g.center))

    def show_warning(self, msg):
        self.warning_msg = msg
        self.warning_color = (255, 110, 100)
        self.warning_timer = pygame.time.get_ticks() + 2000
        sfx('ui_click', 0.6)

    def show_info(self, msg):
        self.warning_msg = msg
        self.warning_color = (140, 255, 160)
        self.warning_timer = pygame.time.get_ticks() + 2200

    def draw_warning_banner(self):
        col = getattr(self, 'warning_color', (255, 110, 100))
        txt_surf = render_outlined(self.warning_msg, 22, col, width=2, bold=True)
        y = self.menu_rect.bottom + 34 if self.active_menu else (self.panel_top - 28 if self.build_mode_active else HEIGHT // 2 + 180)
        txt_rect = txt_surf.get_rect(center=(WIDTH // 2, y))
        bg_rect = txt_rect.inflate(34, 16)
        pygame.draw.rect(self.display_surface, (20, 14, 18), bg_rect, border_radius=6)
        pygame.draw.rect(self.display_surface, col, bg_rect, 2, border_radius=6)
        self.display_surface.blit(txt_surf, txt_rect)

    def draw_active_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.display_surface.blit(overlay, (0, 0))
        draw_panel(self.display_surface, self.menu_rect, alpha=240, radius=12)
        title_txt = BUILDING_DATA[self.active_menu]['name'].upper()
        self.draw_text(title_txt, (self.menu_rect.centerx, self.menu_rect.top + 30), font=self.title_font, color=GOLD)
        if self.active_menu == 'bank':
            self.draw_text(f"En coffre : {self.banked_iron} Fer  ·  {self.banked_gold} Or   (taxe 2 %/jour)",
                           (self.menu_rect.centerx, self.menu_rect.top + 58), size=17, color=TEXT_DIM)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            rect = btn['rect']
            hov = rect.collidepoint(mouse_pos)
            close = btn['action'] == 'close_menu'
            pygame.draw.rect(self.display_surface, (70, 40, 40) if close and hov else ((60, 52, 40) if hov else (32, 28, 38)), rect, border_radius=6)
            pygame.draw.rect(self.display_surface, GOLD if hov else PANEL_BORDER, rect, 2, border_radius=6)
            self.draw_text(btn['text'], rect.center, size=18, color=(255, 245, 225) if hov else (215, 205, 190))

    def paused_ui_active(self):
        return (self.night_arrived or self.waiting_for_night or self.menu_state is not None
                or self.active_menu is not None or self.board_open)

    def check_click(self, pos, player):
        now = pygame.time.get_ticks()
        if now < self.state_lock_time:
            return None
        
        # 0. Tableau des primes
        if self.board_open:
            self.state_lock_time = now + 200
            for i, (row, btn) in enumerate(self.board.board_layout(self.board_panel)):
                if btn.collidepoint(pos) and i < len(self.board.contracts):
                    reward = self.board.claim(i, player)
                    if reward:
                        self.show_info(f"Prime : +{reward['gold']} or, +{reward['iron']} fer, +{reward['xp']} XP")
                        sfx('coin'); sfx('levelup', 0.5)
                        return "save"
                    self.show_warning("Contrat pas encore rempli.")
                    return None
            close = pygame.Rect(0, 0, 180, 40)
            close.midbottom = (self.board_panel.centerx, self.board_panel.bottom - 14)
            if close.collidepoint(pos) or not self.board_panel.collidepoint(pos):
                self.board_open = False
            return None

        # 1. Priorité absolue : Menu Bâtiment Actif
        if self.active_menu:
            for btn in self.menu_buttons:
                if btn['rect'].collidepoint(pos):
                    action = btn['action']
                    self.state_lock_time = pygame.time.get_ticks() + 300 # Lock click on any active menu button interaction
                    
                    if action == 'close_menu':
                        self.active_menu = None
                    
                    elif action in UPGRADE_DEFS:
                        key, max_lvl = UPGRADE_DEFS[action][0], UPGRADE_DEFS[action][1]
                        lvl = player.upgrades.get(key, 0)
                        if lvl >= max_lvl:
                            self.show_warning("Niveau maximum atteint.")
                        else:
                            g, fe = upgrade_cost(action, lvl)
                            if player.inventory['gold'] >= g and player.inventory['iron'] >= fe:
                                player.inventory['gold'] -= g
                                player.inventory['iron'] -= fe
                                player.upgrades[key] = lvl + 1
                                self.show_info(f"{UPGRADE_DEFS[action][6]} niveau {lvl + 1} !")
                                sfx('iron', 0.8)
                                self.open_building_menu('forge', player)
                                return "save"
                            self.show_warning("Pas assez de ressources !")

                    elif action == 'upgrade_dmg':
                        cost_g = PRICES['upgrade_damage']
                        cost_i = PRICES['upgrade_iron_cost']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.attack_damage += 2 # Gain
                            self.show_info("Arme améliorée : +2 dégâts !")
                            sfx('iron', 0.8)
                            return "save" # On demande une save
                        else:
                            self.show_warning("Pas assez de ressources !")
                            print("Pas assez de ressources !")
                        
                    elif action == 'deposit_iron':
                        if player.inventory['iron'] >= 50:
                            player.inventory['iron'] -= 50
                            self.banked_iron += 50
                            print("50 Fer déposés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else:
                            self.show_warning("Pas assez de fer !")
                            print("Pas assez de fer !")
                        
                    elif action == 'withdraw_iron':
                        if self.banked_iron >= 50:
                            self.banked_iron -= 50
                            player.inventory['iron'] += 50
                            print("50 Fer retirés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else:
                            self.show_warning("Pas assez de fer en banque !")
                            print("Pas assez de fer en banque !")
                        
                    elif action == 'deposit_gold':
                        if player.inventory['gold'] >= 50:
                            player.inventory['gold'] -= 50
                            self.banked_gold += 50
                            print("50 Or déposés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else:
                            self.show_warning("Pas assez d'or !")
                            print("Pas assez d'or !")
                        
                    elif action == 'withdraw_gold':
                        if self.banked_gold >= 50:
                            self.banked_gold -= 50
                            player.inventory['gold'] += 50
                            print("50 Or retirés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else:
                            self.show_warning("Pas assez d'or en banque !")
                            print("Pas assez d'or en banque !")
                        
                    elif action == 'sell_iron_20':
                        if player.inventory['iron'] >= 20:
                            player.inventory['iron'] -= 20
                            player.inventory['gold'] += PRICES['sell_iron']
                            print(f"20 Fer vendu pour {PRICES['sell_iron']} Or !")
                            return "save"
                        else:
                            self.show_warning("Pas assez de fer !")
                            print("Pas assez de fer !")
                        
                    elif action == 'buy_iron_20':
                        if player.inventory['gold'] >= PRICES['buy_iron']:
                            player.inventory['gold'] -= PRICES['buy_iron']
                            player.inventory['iron'] += 20
                            print(f"20 Fer acheté pour {PRICES['buy_iron']} Or !")
                            return "save"
                        else:
                            self.show_warning("Pas assez d'or !")
                            print("Pas assez d'or !")
                        
                    elif action == 'buy_potion':
                        if player.potions < MAX_POTIONS:
                            if player.inventory['gold'] >= PRICES['buy_potion']:
                                player.inventory['gold'] -= PRICES['buy_potion']
                                player.potions += 1
                                self.show_info(f"Potion achetée ({player.potions}/{MAX_POTIONS}) - touche R en donjon")
                                sfx('potion', 0.6)
                                return "save"
                            else:
                                self.show_warning("Pas assez d'or !")
                        else:
                            self.show_warning(f"Sacoche pleine ({MAX_POTIONS} potions max).")
                        
                    elif action == 'study':
                        cost_g = PRICES['study_gold']
                        cost_i = PRICES['study_iron']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.inventory['xp'] += PRICES['study_xp_gain']
                            print(f"Connaissance acquise ! +{PRICES['study_xp_gain']} XP")
                            return "save"
                        else:
                            self.show_warning("Pas assez de ressources !")
                            print("Pas assez de ressources !")
                        
                    elif action == 'research':
                        cost_g = PRICES['research_gold']
                        cost_i = PRICES['research_iron']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.inventory['xp'] += PRICES['research_xp_gain']
                            print(f"Recherche terminée ! +{PRICES['research_xp_gain']} XP")
                            return "save"
                        else:
                            self.show_warning("Pas assez de ressources !")
                            print("Pas assez de ressources !")
                        
            # Si on clique hors du menu, on le ferme
            if not self.menu_rect.collidepoint(pos):
                self.active_menu = None
                self.state_lock_time = pygame.time.get_ticks() + 300
            return None

        # 2. Menus contextuels (Nuit, Donjon...)
        if self.night_arrived:
            if self.btn_rest_night.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.night_arrived = False
                player.health = player.max_health
                self.apply_daily_tax()
                return "rest_at_night"
            elif self.btn_explore_night.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.night_arrived = False
                return "explore_at_night"
            return None
        
        if self.waiting_for_night:
            if self.btn_wait_night.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.waiting_for_night = False
                return f"wait_for_night_{self.pending_dungeon_choice}"
            elif self.btn_go_now.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.waiting_for_night = False
                self.pending_dungeon_choice = None
                return None
            return None

        if self.menu_state == 'dungeon':
            if self.btn_random.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.menu_state = None
                return "dungeon_random_check"
            elif self.btn_main_dungeons.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.menu_state = None
                return "dungeon_major_check"
            else:
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.menu_state = None
                return None
        
        # 3. Mode Construction
        if self.build_mode_active:
            for btn in self.build_buttons:
                if btn['rect'].collidepoint(pos):
                    self.state_lock_time = pygame.time.get_ticks() + 300
                    self.selected_blueprint = btn['key']
                    return None
            if self.selected_blueprint and pos[1] < self.panel_top:
                data = BUILDING_DATA[self.selected_blueprint]
                w, h = data['size']
                snapped_pos = self.get_snapped_pos(pos, w, h)
                rect_check = pygame.Rect(snapped_pos[0], snapped_pos[1], w, h)
                self.recalculate_population()
                free_workers = self.max_population - self.current_workers
                npc_cost = data.get('cost_npc', 0)
                max_cnt = data.get('max_count', None)
                limit_reached = False
                if max_cnt:
                    if self.get_building_count(self.selected_blueprint) >= max_cnt: limit_reached = True
                if self.is_placement_valid(rect_check):
                    if not limit_reached:
                        if free_workers >= npc_cost:
                            c_gold = data['cost_gold']; c_iron = data['cost_iron']
                            if player.inventory['gold'] >= c_gold and player.inventory['iron'] >= c_iron:
                                player.inventory['gold'] -= c_gold; player.inventory['iron'] -= c_iron
                                is_walkable = data.get('walkable', False)
                                if is_walkable: Building(self.selected_blueprint, snapped_pos, [self.path_sprites])
                                else: Building(self.selected_blueprint, snapped_pos, [self.building_sprites, self.obstacle_sprites, self.hub_obstacles])
                                self.built_buildings.append({'type': self.selected_blueprint, 'x': snapped_pos[0], 'y': snapped_pos[1]})
                                if not is_walkable: self.spawn_npcs(player)
                                print(f"Batiment {data['name']} construit !"); return "build_action"
                            else:
                                self.show_warning("Pas assez de ressources !")
                                print("Pas assez de ressources !")
                        else:
                            self.show_warning("Pas assez d'ouvriers libres !")
                            print("Pas assez d'ouvriers libres !")
                    else:
                        self.show_warning("Limite de batiments atteinte !")
                        print("Limite atteinte !")
                else:
                    self.show_warning("Placement invalide !")
                    print("Placement invalide !")
            return None 

        # 4. Mode Normal (Interaction Batiments)
        else:
            # On vérifie si on clique sur un batiment construit
            for b_sprite in self.building_sprites:
                if b_sprite.rect.collidepoint(pos):
                    print(f"Clic sur {b_sprite.name}")
                    # On vérifie si ce batiment a un menu
                    # b_sprite.type contient la clé (ex: 'forge')
                    if b_sprite.type in ['forge', 'shop', 'bank', 'library']:
                        self.open_building_menu(b_sprite.type, player)
                        return None

            # Villageois : un clic les fait parler
            for npc in self.npc_sprites:
                if npc.rect.inflate(16, 16).collidepoint(pos):
                    npc.say(random.choice(VILLAGER_LINES))
                    sfx('ui_hover')
                    return None

            if self.board_rect.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 250
                self.board.ensure(player.level)
                self.board_open = True
                sfx('ui_click')
                return None

            # Autres intéractions
            if self.gate_rect.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.menu_state = 'dungeon'
                return None
            if self.tent_rect.collidepoint(pos): 
                self.state_lock_time = pygame.time.get_ticks() + 300
                player.health = player.max_health
                self.apply_daily_tax()
                return "rest"
            if self.btn_open_build.collidepoint(pos):
                self.state_lock_time = pygame.time.get_ticks() + 300
                self.build_mode_active = True
                self.selected_blueprint = None
                return None
        return None

    def apply_daily_tax(self):
        """Applique une taxe de 2% sur les ressources stockées en banque chaque nuit"""
        tax_rate = 0.02
        if self.banked_iron > 0:
            taxed_iron = int(self.banked_iron * tax_rate)
            # Minimum 1 de taxe si on a de l'argent pour éviter que les petits montants soient ignorés
            if taxed_iron == 0 and self.banked_iron >= 50: taxed_iron = 1
            self.banked_iron = max(0, self.banked_iron - taxed_iron)
            
        if self.banked_gold > 0:
            taxed_gold = int(self.banked_gold * tax_rate)
            if taxed_gold == 0 and self.banked_gold >= 50: taxed_gold = 1
            self.banked_gold = max(0, self.banked_gold - taxed_gold)
            
        print(f"[Banque] Les taxes journalières ont été perçues (2%).")

    def draw_environment(self, static_only=True):
        path_color = (160, 130, 90)
        radius = 100
        cx, cy = self.center_x, self.center_y
        
        # --- Rond-point texturé ---
        if self.dirt_tile:
            circle_size = radius * 2
            circle_surf = pygame.Surface((circle_size, circle_size), pygame.SRCALPHA)
            tile_w, tile_h = self.dirt_tile.get_size()
            
            # Alignement de la texture globale sur le monde
            wx = cx - radius
            wy = cy - radius
            offset_x = int(wx % tile_w)
            offset_y = int(wy % tile_h)
            
            for tx in range(-offset_x, circle_size, tile_w):
                for ty in range(-offset_y, circle_size, tile_h):
                    circle_surf.blit(self.dirt_tile, (tx, ty))
                    
            # Appliquer un masque circulaire
            mask_surf = pygame.Surface((circle_size, circle_size), pygame.SRCALPHA)
            pygame.draw.circle(mask_surf, (255, 255, 255, 255), (radius, radius), radius)
            circle_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.display_surface.blit(circle_surf, (wx, wy))
            
            # --- Route vers la porte (texturée) ---
            road_width = 60
            gate_cx, gate_cy = self.gate_rect.center
            road_height = gate_cy - cy
            if road_height > 0:
                road_surf = pygame.Surface((road_width, road_height), pygame.SRCALPHA)
                wx_road = cx - road_width // 2
                wy_road = cy
                r_offset_x = int(wx_road % tile_w)
                r_offset_y = int(wy_road % tile_h)
                
                for tx in range(-r_offset_x, road_width, tile_w):
                    for ty in range(-r_offset_y, road_height, tile_h):
                        road_surf.blit(self.dirt_tile, (tx, ty))
                self.display_surface.blit(road_surf, (wx_road, wy_road))
        else:
            pygame.draw.circle(self.display_surface, path_color, (cx, cy), radius)
            pygame.draw.line(self.display_surface, path_color, (cx, cy), self.gate_rect.center, 60)
        

    def draw_build_mode_ui(self):
        s = pygame.Surface((WIDTH, self.panel_height))
        s.set_alpha(240)
        s.fill((20, 20, 30))
        self.display_surface.blit(s, (0, self.panel_top))
        title_y = self.panel_top + 15
        self.draw_text("Mode Construction (Echap pour annuler)", (WIDTH//2, title_y), size=18, color=(200, 200, 200))
        free_workers = self.max_population - self.current_workers
        pop_text = f"Pop: {self.current_workers}/{self.max_population} (Libres: {free_workers})"
        if self.max_population >= self.max_cap_limit: pop_text += " [MAX]"
        pop_surf = self.info_font.render(pop_text, True, (100, 255, 100))
        pop_rect = pop_surf.get_rect(topright=(WIDTH - 20, title_y))
        self.display_surface.blit(pop_surf, pop_rect)
        info_y_center = self.panel_top + 50 
        mouse_pos = pygame.mouse.get_pos()
        hovered_data = None
        hovered_key = None
        for btn in self.build_buttons:
            if btn['rect'].collidepoint(mouse_pos): hovered_data = btn['data']; hovered_key = btn['key']
            if self.selected_blueprint == btn['key']: hovered_data = btn['data']; hovered_key = btn['key']
        if hovered_data:
            info_str = f"{hovered_data['name']} : {hovered_data['desc']}  |  Coût: {hovered_data['cost_gold']} Or, {hovered_data['cost_iron']} Fer"
            npc_cost = hovered_data.get('cost_npc', 0)
            if npc_cost > 0: info_str += f"  |  Ouvriers: {npc_cost}"
            cap = hovered_data.get('capacity', 0)
            if cap > 0: info_str += f"  |  Capacité: +{cap}"
            self.draw_text(info_str, (WIDTH//2, info_y_center), size=18, color=(255, 215, 0))
            max_cnt = hovered_data.get('max_count', None)
            if max_cnt:
                current = self.get_building_count(hovered_key)
                col = (255, 100, 100) if current >= max_cnt else (150, 150, 150)
                limit_y = info_y_center + 20
                self.draw_text(f"Construit: {current}/{max_cnt}", (WIDTH//2, limit_y), size=14, color=col)
        for btn in self.build_buttons:
            rect = btn['rect']
            data = btn['data']
            key = btn['key']
            is_selected = (self.selected_blueprint == key)
            is_hovered = rect.collidepoint(mouse_pos)
            if is_selected: color = (255, 255, 255); border = 3
            elif is_hovered: color = (200, 200, 200); border = 2
            else: color = (100, 100, 100); border = 1
            pygame.draw.rect(self.display_surface, (40, 34, 30) if not is_hovered else (62, 54, 44), rect, border_radius=6)
            th = thumbnail(key, rect.width)
            self.display_surface.blit(th, th.get_rect(center=rect.center))
            if is_selected: color = GOLD
            pygame.draw.rect(self.display_surface, color, rect, border, border_radius=6)
            name_surf = pygame.font.Font(UI_FONT, 12).render(data['name'], True, (220, 220, 220))
            name_rect = name_surf.get_rect(midtop=(rect.centerx, rect.bottom + 5))
            self.display_surface.blit(name_surf, name_rect)

    def get_snapped_pos(self, pos, w, h):
        grid_size = 32
        x, y = pos
        return ((x // grid_size) * grid_size, (y // grid_size) * grid_size)

    def placement_problem(self, b_type, rect, player=None):
        """Raison pour laquelle on ne peut pas construire ici (None si tout va bien)."""
        data = BUILDING_DATA[b_type]
        if not self.is_placement_valid(rect):
            return "Emplacement occupé"
        max_cnt = data.get('max_count')
        if max_cnt and self.get_building_count(b_type) >= max_cnt:
            return "Limite atteinte"
        self.recalculate_population()
        if self.max_population - self.current_workers < data.get('cost_npc', 0):
            return "Ouvriers insuffisants"
        if player is not None and (player.inventory['gold'] < data['cost_gold'] or player.inventory['iron'] < data['cost_iron']):
            return "Ressources insuffisantes"
        return None

    def draw_placement_preview(self, player=None):
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[1] >= self.panel_top:
            return
        data = BUILDING_DATA[self.selected_blueprint]
        w, h = data['size']
        pos = self.get_snapped_pos(mouse_pos, w, h)
        rect = pygame.Rect(pos[0], pos[1], w, h)
        problem = self.placement_problem(self.selected_blueprint, rect, player)
        valid = problem is None
        surf = self.display_surface
        # ombre au sol puis bâtiment fantôme (vraie texture)
        shadow = pygame.Surface((w + 10, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        surf.blit(shadow, (rect.x - 5, rect.bottom - 9))
        surf.blit(ghost_image(self.selected_blueprint, pos, valid), pos)
        col = (90, 255, 120) if valid else (255, 80, 70)
        pulse = 2 + int(abs(math.sin(getattr(self, 't', 0) * 6)) * 2)
        pygame.draw.rect(surf, col, rect, pulse, border_radius=3)
        # grille d'aide autour du curseur
        for gx in range(rect.left - 64, rect.right + 64, 32):
            pygame.draw.line(surf, (*col,), (gx, rect.top - 4), (gx, rect.top - 1))
        label = data['name'] if valid else problem
        info = render_outlined(label, 17, col, width=2, bold=True)
        cost = render_outlined(f"{data['cost_gold']} or · {data['cost_iron']} fer", 15, (235, 225, 205), width=2)
        surf.blit(info, info.get_rect(midbottom=(rect.centerx, rect.top - 18)))
        surf.blit(cost, cost.get_rect(midbottom=(rect.centerx, rect.top - 3)))

    def is_placement_valid(self, new_rect):
        for obst in self.fixed_obstacles:
            if new_rect.colliderect(obst): return False
        for sprite in self.building_sprites:
            if new_rect.colliderect(sprite.rect): return False
        if not (0 <= new_rect.left and new_rect.right <= WIDTH and 
                0 <= new_rect.top and new_rect.bottom <= self.panel_top): 
            return False
        return True

    def draw_text(self, text, pos, color=(255, 255, 255), font=None, size=None):
        if size: current_font = pygame.font.Font(UI_FONT, size)
        else: current_font = font if font else self.font
        text_surf = current_font.render(text, True, color)
        text_rect = text_surf.get_rect(center=pos)
        self.display_surface.blit(text_surf, text_rect)

    def draw_overlay(self, title, subtitle=None):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 2, 10, 200))
        self.display_surface.blit(overlay, (0, 0))
        t = render_outlined(title, 52, GOLD, width=3, bold=True)
        self.display_surface.blit(t, t.get_rect(center=(self.center_x, 150)))
        if subtitle:
            st = render_outlined(subtitle, 22, (220, 210, 195), width=2)
            self.display_surface.blit(st, st.get_rect(center=(self.center_x, 200)))

    def _menu_btn(self, rect, text, danger=False):
        from menu_scene import draw_button
        draw_button(self.display_surface, rect, text, rect.collidepoint(pygame.mouse.get_pos()), danger=danger,
                    size=22, t=getattr(self, 't', 0))

    def draw_dungeon_menu(self):
        self.draw_overlay("DESTINATION", "Les donjons ne s'ouvrent qu'à la nuit tombée")
        self._menu_btn(self.btn_random, "Donjon aléatoire")
        self._menu_btn(self.btn_main_dungeons, "Donjon majeur (Gardien)", danger=True)
        self.draw_text("Aléatoire : butin et XP, rentrez avant l'aube.", (self.center_x, self.center_y + 110), size=16, color=TEXT_DIM)
        self.draw_text("Majeur : affrontez un Gardien pour lui arracher un Artefact (4 requis).", (self.center_x, self.center_y + 132), size=16, color=TEXT_DIM)
        self.draw_text("(Clic ailleurs pour annuler)", (self.center_x, self.center_y + 170), size=15, color=(150, 140, 130))

    def draw_wait_night_menu(self):
        self.draw_overlay("ATTENDRE LA NUIT", "Les donjons ne sont ouverts que la nuit.")
        self._menu_btn(self.btn_wait_night, "Attendre la nuit")
        self._menu_btn(self.btn_go_now, "Annuler", danger=True)

    def draw_night_arrived_menu(self):
        self.draw_overlay("LA NUIT EST TOMBÉE", "Le village s'endort... mais les donjons s'éveillent.")
        self._menu_btn(self.btn_rest_night, "Se reposer")
        self._menu_btn(self.btn_explore_night, "Partir en expédition", danger=True)

    def get_save_data(self): 
        return {
            'buildings': self.built_buildings,
            'banked_iron': self.banked_iron,
            'banked_gold': self.banked_gold,
            'contracts': self.board.to_save(),
        }
        
    def load_save_data(self, data):
        self.built_buildings = []; self.building_sprites.empty(); self.path_sprites.empty(); self.hub_obstacles.empty()
        for rect in self.fixed_obstacles: Block(rect, [self.hub_obstacles])
        
        b_list = []
        if isinstance(data, list):
            b_list = data
            self.banked_iron = 0
            self.banked_gold = 0
        elif isinstance(data, dict):
            b_list = data.get('buildings', [])
            self.banked_iron = data.get('banked_iron', 0)
            self.banked_gold = data.get('banked_gold', 0)
            self.board.load(data.get('contracts'))
        else:
            print("Format invalide."); return
            
        for b in b_list:
            if isinstance(b, dict) and 'type' in b and 'x' in b and 'y' in b:
                if b['type'] in BUILDING_DATA:
                    info = BUILDING_DATA[b['type']]
                    is_walkable = info.get('walkable', False)
                    if is_walkable: Building(b['type'], (b['x'], b['y']), [self.path_sprites])
                    else: Building(b['type'], (b['x'], b['y']), [self.building_sprites, self.obstacle_sprites, self.hub_obstacles])
                    self.built_buildings.append(b)
                else: print(f"Batiment inconnu: {b['type']}")
            else: print("Format batiment ignoré.")
        self.recalculate_population()