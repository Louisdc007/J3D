import pygame
from settings import *


class Hub:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, 18)
        self.title_font = pygame.font.Font(UI_FONT, 30)

        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2

        self.blueprints = {
            'forge': {
                'name': 'Forge',
                'cost_gold': 5,
                'cost_iron': 50,
                'desc': 'Améliorer les armes',
                'color': (100, 100, 120)
            },
            'altar': {
                'name': 'Autel',
                'cost_gold': 15,
                'cost_iron': 10,
                'desc': 'Bonus passifs',
                'color': (150, 50, 150)
            },
            'shop': {
                'name': 'Marché',
                'cost_gold': 30,
                'cost_iron': 0,
                'desc': 'Acheter potions',
                'color': (200, 180, 50)
            }
        }

        self.campfire_rect = pygame.Rect(0, 0, 60, 60)
        self.campfire_rect.center = (self.center_x, self.center_y)

        self.tent_rect = pygame.Rect(0, 0, 100, 80)
        self.tent_rect.bottomright = (self.center_x - 50, self.center_y - 20)

        self.gate_rect = pygame.Rect(0, 0, 220, 60)
        self.gate_rect.midbottom = (self.center_x, HEIGHT - 30)

        self.parcels = []
        parcel_positions = [
            (-320, -180), (300, -200),
            (-380, 50), (360, 80),
            (-200, 250), (200, 250),
        ]

        for i, pos in enumerate(parcel_positions):
            rect = pygame.Rect(0, 0, 130, 90)
            rect.center = (self.center_x + pos[0], self.center_y + pos[1])
            self.parcels.append({
                'rect': rect,
                'building_type': None,
                'label': f"Vide",
                'id': i
            })

        self.menu_state = None
        self.selected_parcel_index = None

        self.btn_random = pygame.Rect(0, 0, 300, 50)
        self.btn_random.center = (self.center_x, self.center_y - 50)
        self.btn_main_dungeons = pygame.Rect(0, 0, 300, 50)
        self.btn_main_dungeons.center = (self.center_x, self.center_y + 50)

        self.build_buttons = []
        self.reset_rect = pygame.Rect(10, 10, 100, 40)

    def draw(self):
        self.display_surface.fill((34, 139, 34))
        self.draw_village()

        if self.menu_state == 'dungeon':
            self.draw_dungeon_menu()
        elif self.menu_state == 'build':
            self.draw_build_menu()

        pygame.draw.rect(self.display_surface, (200, 0, 0), self.reset_rect, border_radius=5)
        self.draw_text("RESET", self.reset_rect.center, size=14)

    def draw_village(self):
        path_color = (160, 130, 90)
        pygame.draw.circle(self.display_surface, path_color, (self.center_x, self.center_y), 100)
        for p in self.parcels:
            pygame.draw.line(self.display_surface, path_color, (self.center_x, self.center_y), p['rect'].center, 40)
            pygame.draw.circle(self.display_surface, path_color, p['rect'].center, 55)
        pygame.draw.line(self.display_surface, path_color, (self.center_x, self.center_y), self.gate_rect.center, 60)

        pygame.draw.rect(self.display_surface, (65, 105, 225), self.tent_rect, border_radius=10)
        self.draw_text("Repos", self.tent_rect.center, size=15)
        pygame.draw.circle(self.display_surface, (255, 69, 0), self.campfire_rect.center, 20)

        for p in self.parcels:
            b_type = p['building_type']
            if b_type is None:
                color = (80, 80, 80)
                label = "Vide"
            else:
                color = self.blueprints[b_type]['color']
                label = self.blueprints[b_type]['name']

            pygame.draw.rect(self.display_surface, color, p['rect'], border_radius=8)
            pygame.draw.rect(self.display_surface, (30, 30, 30), p['rect'], 2, border_radius=8)
            self.draw_text(label, p['rect'].center)

        pygame.draw.rect(self.display_surface, (139, 69, 19), self.gate_rect, border_radius=5)
        self.draw_text("EXPEDITION", self.gate_rect.center, color=(240, 240, 240))

    def draw_dungeon_menu(self):
        self.draw_overlay("DESTINATION")
        pygame.draw.rect(self.display_surface, (100, 100, 200), self.btn_random)
        self.draw_text("Donjon Aléatoire", self.btn_random.center)
        pygame.draw.rect(self.display_surface, (200, 50, 50), self.btn_main_dungeons)
        self.draw_text("Majeur (Artefact)", self.btn_main_dungeons.center)
        self.draw_text("(Clic ailleurs pour annuler)", (self.center_x, self.center_y + 150), size=16)

    def draw_build_menu(self):
        self.draw_overlay("CONSTRUIRE")

        for btn in self.build_buttons:
            rect = btn['rect']
            data = btn['data']

            can_afford = btn['can_afford']
            color = (50, 200, 50) if can_afford else (200, 50, 50)

            pygame.draw.rect(self.display_surface, color, rect, border_radius=5)
            pygame.draw.rect(self.display_surface, (255, 255, 255), rect, 2, border_radius=5)

            info_text = f"{data['name']} : {data['cost_gold']} Or | {data['cost_iron']} Fer"
            self.draw_text(info_text, (rect.centerx, rect.centery - 10))
            self.draw_text(data['desc'], (rect.centerx, rect.centery + 15), size=14)

        self.draw_text("(Clic ailleurs pour annuler)", (self.center_x, HEIGHT - 100), size=16)

    def draw_overlay(self, title):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.display_surface.blit(overlay, (0, 0))
        self.draw_text(title, (self.center_x, 150), font=self.title_font)

    def draw_text(self, text, pos, color=(255, 255, 255), font=None, size=None):
        if size:
            current_font = pygame.font.Font(UI_FONT, size)
        else:
            current_font = font if font else self.font
        text_surf = current_font.render(text, True, color)
        text_rect = text_surf.get_rect(center=pos)
        self.display_surface.blit(text_surf, text_rect)

    def check_click(self, pos, player):
        if self.reset_rect.collidepoint(pos):
            return "reset_game"
        if self.menu_state == 'dungeon':
            if self.btn_random.collidepoint(pos):
                self.menu_state = None
                return "dungeon_random"
            elif self.btn_main_dungeons.collidepoint(pos):
                self.menu_state = None
                return None
            else:
                self.menu_state = None
                return None

        elif self.menu_state == 'build':
            for btn in self.build_buttons:
                if btn['rect'].collidepoint(pos):
                    c_gold = btn['data']['cost_gold']
                    c_iron = btn['data']['cost_iron']
                    key = btn['key']

                    if player.inventory['gold'] >= c_gold and player.inventory['iron'] >= c_iron:
                        player.inventory['gold'] -= c_gold
                        player.inventory['iron'] -= c_iron

                        self.parcels[self.selected_parcel_index]['building_type'] = key
                        self.menu_state = None

                    return "build_action"

            self.menu_state = None
            return None

        else:
            if self.gate_rect.collidepoint(pos):
                self.menu_state = 'dungeon'
                return None

            if self.tent_rect.collidepoint(pos):
                player.health = player.max_health
                return "heal"

            for index, p in enumerate(self.parcels):
                if p['rect'].collidepoint(pos):
                    if p['building_type'] is None:
                        self.menu_state = 'build'
                        self.selected_parcel_index = index
                        self.generate_build_buttons(player)
                    else:
                        print(f"Bâtiment : {p['building_type']}")
                    return "parcel_click"

        return None

    def generate_build_buttons(self, player):
        self.build_buttons = []
        start_y = 250
        gap = 80

        for i, (key, data) in enumerate(self.blueprints.items()):
            rect = pygame.Rect(0, 0, 450, 60)
            rect.center = (self.center_x, start_y + i * gap)

            c_gold = data['cost_gold']
            c_iron = data['cost_iron']
            can_afford = (player.inventory['gold'] >= c_gold and player.inventory['iron'] >= c_iron)

            self.build_buttons.append({
                'rect': rect,
                'data': data,
                'key': key,
                'can_afford': can_afford
            })

    def get_save_data(self):
        parcels_data = []
        for p in self.parcels:
            parcels_data.append({
                'id': p['id'],
                'building_type': p['building_type']
            })
        return parcels_data

    def load_save_data(self, data):
        for saved_parcel in data:
            idx = saved_parcel['id']
            if 0 <= idx < len(self.parcels):
                self.parcels[idx]['building_type'] = saved_parcel['building_type']