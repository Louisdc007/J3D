import pygame
import random
import os
from settings import *
from entities.npc import NPC

# Mapping des textures de bâtiments
BUILDING_TEXTURES = {
    'bank': 'bank.jpg',
    'forge': 'forge.jpg',
    'library': 'bibli.jpg',
    'shop': 'marche.jpg',
    'path': ('floor_assets', 'dirt_path.jpg'),  # Tuple = dossier différent
}

# Bâtiments avec mode de rendu spécial (fill-Y, crop-X centré)
BUILDING_CROP_MODE = {'library'}

# Bâtiments avec mode motif : la texture est scalée puis découpée pour être alignée sur la grille
BUILDING_PATTERN_MODE = {'path': (320, 320)}  # 5x5 tiles de 64px

class Block(pygame.sprite.Sprite):
    def __init__(self, rect, group):
        super().__init__(group)
        self.rect = rect

class Building(pygame.sprite.Sprite):
    def __init__(self, type, pos, group):
        super().__init__(group)
        self.type = type
        data = BUILDING_DATA[type]
        # Charger la texture si disponible, sinon rectangle de couleur
        target_w, target_h = data['size']
        if type in BUILDING_TEXTURES:
            base_path = os.path.dirname(os.path.abspath(__file__))
            tex_entry = BUILDING_TEXTURES[type]
            if isinstance(tex_entry, tuple):
                tex_path = os.path.join(base_path, 'assets', tex_entry[0], tex_entry[1])
            else:
                tex_path = os.path.join(base_path, 'assets', 'building', tex_entry)
            try:
                tex = pygame.image.load(tex_path).convert()
                if type in BUILDING_CROP_MODE:
                    # Mode spécial : remplir la hauteur, cropper le surplus en largeur (centré)
                    orig_w, orig_h = tex.get_size()
                    scale_factor = target_h / orig_h
                    scaled_w = int(orig_w * scale_factor)
                    scaled_h = target_h
                    tex_scaled = pygame.transform.scale(tex, (scaled_w, scaled_h))
                    # Crop centré sur X
                    crop_x = (scaled_w - target_w) // 2
                    self.image = tex_scaled.subsurface(pygame.Rect(crop_x, 0, target_w, target_h)).copy()
                elif type in BUILDING_PATTERN_MODE:
                    # Mode motif : redimensionner à la taille du motif global et extraire le bout
                    pat_w, pat_h = BUILDING_PATTERN_MODE[type]
                    tex_scaled = pygame.transform.scale(tex, (pat_w, pat_h))
                    px, py = pos
                    src_x = int(px % pat_w)
                    src_y = int(py % pat_h)
                    self.image = pygame.Surface((target_w, target_h))
                    self.image.blit(tex_scaled, (0, 0), (src_x, src_y, target_w, target_h))
                else:
                    # Mode normal : étirer pour remplir la zone
                    self.image = pygame.transform.scale(tex, (target_w, target_h))
            except Exception:
                self.image = pygame.Surface(data['size'])
                self.image.fill(data['color'])
                pygame.draw.rect(self.image, (30, 30, 30), (0, 0, target_w, target_h), 3)
        else:
            self.image = pygame.Surface(data['size'])
            self.image.fill(data['color'])
            pygame.draw.rect(self.image, (30, 30, 30), (0, 0, target_w, target_h), 3)
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
        base_path = os.path.dirname(os.path.abspath(__file__))
        grass_path = os.path.join(base_path, 'assets', 'floor_assets', 'grass.jpg')
        try:
            self.grass_tile = pygame.image.load(grass_path).convert()
            self.grass_tile = pygame.transform.scale(self.grass_tile, (320, 320))
        except Exception:
            self.grass_tile = None

        # --- TEXTURE CHEMIN (rond-point + route) ---
        dirt_path = os.path.join(base_path, 'assets', 'floor_assets', 'dirt_path.jpg')
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
        self.menu_rect = pygame.Rect(0, 0, 400, 300)
        self.menu_rect.center = (WIDTH//2, HEIGHT//2)
        
        # --- ZONES FIXES ---
        self.campfire_rect = pygame.Rect(0, 0, 60, 60)
        self.campfire_rect.center = (self.center_x, self.center_y)
        self.tent_rect = pygame.Rect(0, 0, 100, 80)
        self.tent_rect.bottomright = (self.center_x - 50, self.center_y - 20)
        self.gate_rect = pygame.Rect(0, 0, 220, 60)
        self.gate_rect.midbottom = (self.center_x, HEIGHT - 30)
        
        self.fixed_obstacles = [self.campfire_rect, self.tent_rect, self.gate_rect]
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

    def open_building_menu(self, b_type):
        """Ouvre le menu spécifique à un type de batiment"""
        self.active_menu = b_type
        self.menu_buttons = []
        
        cx = self.menu_rect.centerx
        start_y = self.menu_rect.top + 80
        gap = 60
        
        # Définition des boutons selon le batiment
        if b_type == 'forge':
            self.menu_buttons.append({
                'text': f"Améliorer Dégâts ({PRICES['upgrade_damage']} Or + {PRICES['upgrade_iron_cost']} Fer)",
                'action': 'upgrade_dmg',
                'rect': pygame.Rect(0, 0, 350, 40),
                'pos': (cx, start_y)
            })
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
                'text': f"Acheter Potion ({PRICES['buy_potion']} Or)",
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

    def draw(self):
        # Fond : tiler la texture d'herbe au lieu d'un aplat vert
        if self.grass_tile:
            tile_w, tile_h = self.grass_tile.get_size()
            for x in range(0, WIDTH, tile_w):
                for y in range(0, HEIGHT, tile_h):
                    self.display_surface.blit(self.grass_tile, (x, y))
        else:
            self.display_surface.fill((34, 139, 34))
        self.draw_environment()
        for sprite in self.path_sprites: self.display_surface.blit(sprite.image, sprite.rect)
        if not self.build_mode_active and not self.paused_ui_active() and not self.active_menu: self.npc_sprites.update()
        for sprite in self.npc_sprites: self.display_surface.blit(sprite.image, sprite.rect)
        for sprite in self.building_sprites:
            self.display_surface.blit(sprite.image, sprite.rect)
            label_surf = pygame.font.Font(None, 20).render(sprite.name, True, (255,255,255))
            label_rect = label_surf.get_rect(midbottom=sprite.rect.midtop)
            self.display_surface.blit(label_surf, label_rect)

        if self.night_arrived: self.draw_night_arrived_menu()
        elif self.waiting_for_night: self.draw_wait_night_menu()
        elif self.menu_state == 'dungeon': self.draw_dungeon_menu()
        
        # Gestion affichage Menu Bâtiment
        if self.active_menu:
            self.draw_active_menu()
        
        # Gestion affichage Construction (seulement si pas d'autre menu)
        if not self.night_arrived and not self.waiting_for_night and self.menu_state is None and not self.active_menu:
            if self.build_mode_active:
                self.draw_build_mode_ui()
                if self.selected_blueprint: self.draw_placement_preview()
            else:
                pygame.draw.rect(self.display_surface, (200, 150, 50), self.btn_open_build, border_radius=5)
                pygame.draw.rect(self.display_surface, (255, 255, 255), self.btn_open_build, 2, border_radius=5)
                self.draw_text("CONSTRUIRE", self.btn_open_build.center)

    def draw_active_menu(self):
        # Fond sombre flou
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.display_surface.blit(overlay, (0, 0))
        
        # Fenêtre
        pygame.draw.rect(self.display_surface, (40, 40, 50), self.menu_rect, border_radius=10)
        pygame.draw.rect(self.display_surface, (200, 200, 200), self.menu_rect, 3, border_radius=10)
        
        # Titre
        title_txt = BUILDING_DATA[self.active_menu]['name'].upper()
        if self.active_menu == 'bank': title_txt += f" (Fer: {self.banked_iron} | Or: {self.banked_gold}) - Taxe: 2%/j"
        self.draw_text(title_txt, (self.menu_rect.centerx, self.menu_rect.top + 30), font=self.title_font, color=(255, 215, 0))
        
        # Boutons
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            rect = btn['rect']
            color = (80, 80, 100)
            if rect.collidepoint(mouse_pos):
                color = (100, 100, 140)
            
            pygame.draw.rect(self.display_surface, color, rect, border_radius=5)
            pygame.draw.rect(self.display_surface, (200, 200, 200), rect, 2, border_radius=5)
            self.draw_text(btn['text'], rect.center, size=18)

    def paused_ui_active(self):
        return self.night_arrived or self.waiting_for_night or self.menu_state is not None or self.active_menu is not None

    def check_click(self, pos, player):
        # 1. Priorité absolue : Menu Bâtiment Actif
        if self.active_menu:
            for btn in self.menu_buttons:
                if btn['rect'].collidepoint(pos):
                    action = btn['action']
                    
                    if action == 'close_menu':
                        self.active_menu = None
                    
                    elif action == 'upgrade_dmg':
                        cost_g = PRICES['upgrade_damage']
                        cost_i = PRICES['upgrade_iron_cost']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.attack_damage += 2 # Gain
                            print("Arme améliorée !")
                            return "save" # On demande une save
                        else: print("Pas assez de ressources !")
                        
                    elif action == 'deposit_iron':
                        if player.inventory['iron'] >= 50:
                            player.inventory['iron'] -= 50
                            self.banked_iron += 50
                            print("50 Fer déposés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else: print("Pas assez de fer !")
                        
                    elif action == 'withdraw_iron':
                        if self.banked_iron >= 50:
                            self.banked_iron -= 50
                            player.inventory['iron'] += 50
                            print("50 Fer retirés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else: print("Pas assez de fer en banque !")
                        
                    elif action == 'deposit_gold':
                        if player.inventory['gold'] >= 50:
                            player.inventory['gold'] -= 50
                            self.banked_gold += 50
                            print("50 Or déposés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else: print("Pas assez d'or !")
                        
                    elif action == 'withdraw_gold':
                        if self.banked_gold >= 50:
                            self.banked_gold -= 50
                            player.inventory['gold'] += 50
                            print("50 Or retirés !")
                            self.open_building_menu('bank') # Refresh menu text
                            return "save"
                        else: print("Pas assez d'or en banque !")
                        
                    elif action == 'sell_iron_20':
                        if player.inventory['iron'] >= 20:
                            player.inventory['iron'] -= 20
                            player.inventory['gold'] += PRICES['sell_iron']
                            print(f"20 Fer vendu pour {PRICES['sell_iron']} Or !")
                            return "save"
                        else: print("Pas assez de fer !")
                        
                    elif action == 'buy_iron_20':
                        if player.inventory['gold'] >= PRICES['buy_iron']:
                            player.inventory['gold'] -= PRICES['buy_iron']
                            player.inventory['iron'] += 20
                            print(f"20 Fer acheté pour {PRICES['buy_iron']} Or !")
                            return "save"
                        else: print("Pas assez d'or !")
                        
                    elif action == 'buy_potion':
                        if player.health < player.max_health:
                            if player.inventory['gold'] >= PRICES['buy_potion']:
                                player.inventory['gold'] -= PRICES['buy_potion']
                                player.health = min(player.health + 50, player.max_health)
                                print("Potion achetée et bue !")
                                return "save"
                            else: print("Pas assez d'or !")
                        else: print("Points de vie au maximum.")
                        
                    elif action == 'study':
                        cost_g = PRICES['study_gold']
                        cost_i = PRICES['study_iron']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.inventory['xp'] += PRICES['study_xp_gain']
                            print(f"Connaissance acquise ! +{PRICES['study_xp_gain']} XP")
                            return "save"
                        else: print("Pas assez de ressources !")
                        
                    elif action == 'research':
                        cost_g = PRICES['research_gold']
                        cost_i = PRICES['research_iron']
                        if player.inventory['gold'] >= cost_g and player.inventory['iron'] >= cost_i:
                            player.inventory['gold'] -= cost_g
                            player.inventory['iron'] -= cost_i
                            player.inventory['xp'] += PRICES['research_xp_gain']
                            print(f"Recherche terminée ! +{PRICES['research_xp_gain']} XP")
                            return "save"
                        else: print("Pas assez de ressources !")
                        
            # Si on clique hors du menu, on le ferme
            if not self.menu_rect.collidepoint(pos):
                self.active_menu = None
            return None

        # 2. Menus contextuels (Nuit, Donjon...)
        if self.night_arrived:
            if self.btn_rest_night.collidepoint(pos):
                self.night_arrived = False
                player.health = player.max_health
                self.apply_daily_tax()
                return "rest_at_night"
            elif self.btn_explore_night.collidepoint(pos):
                self.night_arrived = False
                return "explore_at_night"
            return None
        
        if self.waiting_for_night:
            if self.btn_wait_night.collidepoint(pos): self.waiting_for_night = False; return f"wait_for_night_{self.pending_dungeon_choice}"
            elif self.btn_go_now.collidepoint(pos): self.waiting_for_night = False; self.pending_dungeon_choice = None; return None
            return None

        if self.menu_state == 'dungeon':
            if self.btn_random.collidepoint(pos): self.menu_state = None; return "dungeon_random_check"
            elif self.btn_main_dungeons.collidepoint(pos): self.menu_state = None; return None
            else: self.menu_state = None; return None
        
        # 3. Mode Construction
        if self.build_mode_active:
            for btn in self.build_buttons:
                if btn['rect'].collidepoint(pos): self.selected_blueprint = btn['key']; return None
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
                            else: print("Pas assez de ressources !")
                        else: print("Pas assez d'ouvriers libres !")
                    else: print("Limite atteinte !")
                else: print("Placement invalide !")
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
                        self.open_building_menu(b_sprite.type)
                        return None

            # Autres intéractions
            if self.gate_rect.collidepoint(pos): self.menu_state = 'dungeon'; return None
            if self.tent_rect.collidepoint(pos): 
                player.health = player.max_health
                self.apply_daily_tax()
                return "rest"
            if self.btn_open_build.collidepoint(pos): self.build_mode_active = True; self.selected_blueprint = None; return None
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

    def draw_environment(self):
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
        
        pygame.draw.rect(self.display_surface, (65, 105, 225), self.tent_rect, border_radius=10)
        self.draw_text("Repos", self.tent_rect.center, size=15)
        pygame.draw.circle(self.display_surface, (255, 69, 0), self.campfire_rect.center, 20)
        pygame.draw.rect(self.display_surface, (139, 69, 19), self.gate_rect, border_radius=5)
        self.draw_text("EXPEDITION", self.gate_rect.center, color=(240, 240, 240))

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
            pygame.draw.rect(self.display_surface, data['color'], rect, border_radius=5)
            pygame.draw.rect(self.display_surface, color, rect, border, border_radius=5)
            name_surf = pygame.font.Font(UI_FONT, 12).render(data['name'], True, (220, 220, 220))
            name_rect = name_surf.get_rect(midtop=(rect.centerx, rect.bottom + 5))
            self.display_surface.blit(name_surf, name_rect)

    def get_snapped_pos(self, pos, w, h):
        grid_size = 32
        x, y = pos
        return ((x // grid_size) * grid_size, (y // grid_size) * grid_size)

    def draw_placement_preview(self):
        mouse_pos = pygame.mouse.get_pos()
        data = BUILDING_DATA[self.selected_blueprint]
        w, h = data['size']
        pos = self.get_snapped_pos(mouse_pos, w, h)
        ghost = pygame.Surface((w, h))
        ghost.fill(data['color'])
        ghost.set_alpha(150)
        valid = self.is_placement_valid(pygame.Rect(pos[0], pos[1], w, h))
        npc_cost = data.get('cost_npc', 0)
        free_workers = self.max_population - self.current_workers
        enough_workers = (free_workers >= npc_cost)
        max_cnt = data.get('max_count', None)
        under_limit = True
        if max_cnt:
            if self.get_building_count(self.selected_blueprint) >= max_cnt: under_limit = False
        if valid and enough_workers and under_limit: color = (50, 255, 50) 
        else: color = (255, 50, 50) 
        pygame.draw.rect(ghost, color, (0,0,w,h), 4)
        self.display_surface.blit(ghost, pos)

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

    def draw_overlay(self, title):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.display_surface.blit(overlay, (0, 0))
        self.draw_text(title, (self.center_x, 150), font=self.title_font)
        
    def draw_dungeon_menu(self):
        self.draw_overlay("DESTINATION")
        pygame.draw.rect(self.display_surface, (100, 100, 200), self.btn_random)
        self.draw_text("Donjon Aléatoire", self.btn_random.center)
        pygame.draw.rect(self.display_surface, (200, 50, 50), self.btn_main_dungeons)
        self.draw_text("Majeur (Artefact)", self.btn_main_dungeons.center)
        self.draw_text("(Clic ailleurs pour annuler)", (self.center_x, self.center_y + 150), size=16)

    def draw_wait_night_menu(self):
        self.draw_overlay("ATTENDRE LA NUIT")
        self.draw_text("Les donjons ne sont ouverts que la nuit.", (self.center_x, self.center_y - 80), size=16)
        pygame.draw.rect(self.display_surface, (100, 200, 100), self.btn_wait_night, border_radius=5)
        self.draw_text("Attendre la nuit", self.btn_wait_night.center)
        pygame.draw.rect(self.display_surface, (200, 100, 100), self.btn_go_now, border_radius=5)
        self.draw_text("Annuler", self.btn_go_now.center)

    def draw_night_arrived_menu(self):
        self.draw_overlay("LA NUIT EST TOMBÉE")
        pygame.draw.rect(self.display_surface, (100, 200, 100), self.btn_rest_night, border_radius=5)
        self.draw_text("Se reposer", self.btn_rest_night.center, size=14)
        pygame.draw.rect(self.display_surface, (100, 100, 200), self.btn_explore_night, border_radius=5)
        self.draw_text("Explorer", self.btn_explore_night.center, size=14)

    def get_save_data(self): 
        return {
            'buildings': self.built_buildings,
            'banked_iron': self.banked_iron,
            'banked_gold': self.banked_gold
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