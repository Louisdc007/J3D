import pygame
import sys
import random
from settings import *
from entities.player import *
from camera import CameraGroup
from tile import Tile, DungeonEntrance
from entities.enemy import Enemy
from ui import UI
from dungeon import DungeonGenerator
from entities.item import Item
from hub import Hub
from save_manager import SaveManager
from intro import IntroScene

class Game:
    def __init__(self):
        pygame.init()
        self.fullscreen = False
        self.screen = pygame.display.set_mode(size=(WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.clock = pygame.time.Clock()

        self.game_state = 'menu'
        self.paused = False
        self.intro_next_state = 'hub'
        
        self.menu_font = pygame.font.Font(UI_FONT, 40)
        self.title_font = pygame.font.Font(UI_FONT, 100)
        self.loading_font = pygame.font.Font(UI_FONT, 50)
        
        center_x = WIDTH // 2; start_y = HEIGHT // 2 - 50; gap = 80
        self.menu_buttons = [
            {'text': 'SOLO', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'start_game', 'pos': (center_x, start_y)},
            {'text': 'MULTIJOUEUR', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'multi_placeholder', 'pos': (center_x, start_y + gap)},
            {'text': 'OPTIONS', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'go_to_options', 'pos': (center_x, start_y + gap * 2)},
            {'text': 'QUITTER', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'quit_game', 'pos': (center_x, start_y + gap * 3)}
        ]
        for btn in self.menu_buttons: btn['rect'].center = btn['pos']

        self.options_buttons = [
            {'text': 'RÉINITIALISER SAUVEGARDE', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'reset_save', 'pos': (center_x, start_y)},
            {'text': 'PLEIN ÉCRAN : NON', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'toggle_fullscreen', 'pos': (center_x, start_y + gap)},
            {'text': 'REVOIR INTRO', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'replay_intro', 'pos': (center_x, start_y + gap * 2)},
            {'text': 'RETOUR', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'back_to_menu', 'pos': (center_x, start_y + gap * 3)}
        ]
        for btn in self.options_buttons: btn['rect'].center = btn['pos']

        self.save_manager = SaveManager()
        self.intro = IntroScene(self.screen)

        self.game_time = 0
        self.day_duration = 5 * 60 * 100
        self.hours_in_day = 24
        self.morning_hour = 6
        self.evening_hour = 20
        self.hours_day_to_evening = self.evening_hour - self.morning_hour
        self.evening_duration = int(self.day_duration * (self.hours_day_to_evening / 10))
        self.full_day_duration = int(self.day_duration * (self.hours_in_day / 10))

        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        self.hub = Hub(self.obstacle_sprites)
        self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)

        loaded_data = self.save_manager.load_game()
        self.has_save_file = False
        
        if loaded_data:
            self.player.load_save_data(loaded_data['player'])
            self.hub.load_save_data(loaded_data['hub'])
            self.has_save_file = True
            print("Sauvegarde trouvée : Intro sera passée.")
        else:
            self.has_save_file = False
            print("Aucune sauvegarde : Intro sera jouée.")

        self.create_map()
        self.ui = UI()
        self.hub.spawn_npcs(self.player)

        self.transition_active = False
        self.transition_alpha = 0
        self.transition_duration = 420 
        self.transition_text = ""
        self.transition_font = pygame.font.Font(None, 60)
        self.transition_type = None
        
        self.dungeon_entrance_pos = None
        self.dungeon_entrance_rect = None
        self.resources_at_dungeon_start = None

    def get_current_hour(self):
        ratio = self.game_time / self.full_day_duration
        if ratio > 1: ratio = 1
        return int((self.morning_hour + (self.hours_in_day * ratio)) % 24)
    def is_dungeon_time(self):
        h = self.get_current_hour()
        return h >= self.evening_hour or h < self.morning_hour
    def is_player_at_entrance(self):
        if self.dungeon_entrance_rect is None: return False
        return self.player.rect.colliderect(self.dungeon_entrance_rect)
    def save_all(self):
        data = {'player': self.player.get_save_data(), 'hub': self.hub.get_save_data()}
        self.save_manager.save_game(data)
        self.has_save_file = True 
    def revert_dungeon_resources(self):
        if self.resources_at_dungeon_start:
            self.player.inventory['gold'] = self.resources_at_dungeon_start['gold']
            self.player.inventory['iron'] = self.resources_at_dungeon_start['iron']
    def toggle_fullscreen(self, btn):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
            btn['text'] = "PLEIN ÉCRAN : OUI"
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            btn['text'] = "PLEIN ÉCRAN : NON"

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_all()
                pygame.quit()
                sys.exit()


            if self.game_state == 'menu':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.menu_buttons:
                        if btn['rect'].collidepoint(event.pos):
                            if btn['action'] == 'start_game':
                                if self.has_save_file:
                                    self.game_state = 'hub'
                                else:
                                    self.intro.reset()
                                    self.game_state = 'intro'
                                    self.intro_next_state = 'hub'
                                return 
                            elif btn['action'] == 'multi_placeholder': print("Bientôt !")
                            elif btn['action'] == 'go_to_options': self.game_state = 'options'; return
                            elif btn['action'] == 'quit_game': self.save_all(); pygame.quit(); sys.exit()
            
       
            elif self.game_state == 'options':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.options_buttons:
                        if btn['rect'].collidepoint(event.pos):
                            if btn['action'] == 'reset_save':
                                self.save_manager.delete_save()
                                self.obstacle_sprites.empty(); self.visible_sprites.empty()
                                self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
                                self.hub = Hub(self.obstacle_sprites); self.hub.spawn_npcs(self.player)
                                self.game_time = 0; self.has_save_file = False
                                print("Reset effectué.")
                            elif btn['action'] == 'toggle_fullscreen': self.toggle_fullscreen(btn)
                            elif btn['action'] == 'replay_intro':
                                self.intro.reset(); self.game_state = 'intro'; self.intro_next_state = 'options'; return 
                            elif btn['action'] == 'back_to_menu': self.game_state = 'menu'; return

            elif self.game_state == 'intro':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = self.intro_next_state
                        if self.intro_next_state == 'hub': self.save_all()

            elif self.game_state in ['hub', 'dungeon', 'loading']:
                if self.game_state == 'loading':
                    return

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == 'hub' and self.hub.build_mode_active:
                            self.hub.build_mode_active = False
                            self.hub.selected_blueprint = None
                        else:
                            self.paused = not self.paused
                
                if self.paused:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.check_pause_click(event.pos)
                    continue 

                if self.game_state == 'hub':
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        action = self.hub.check_click(event.pos, self.player)
                        
                        if action == "build_action":
                            self.save_all()
                        elif action == "dungeon_random_check":
                            if self.is_dungeon_time():
                                self.game_state = 'loading'
                            else:
                                self.hub.waiting_for_night = True
                                self.hub.pending_dungeon_choice = 'random'
                        elif action == "wait_for_night_random":
                            self.game_time = self.evening_duration
                            self.transition_active = True
                            self.transition_alpha = 0
                            self.transition_type = 'wait_for_dungeon'
                            self.transition_text = "La nuit tombe..."
                        elif action == "rest":
                            self.game_time = self.evening_duration
                            self.transition_active = True
                            self.transition_alpha = 0
                            self.transition_type = 'night'
                            self.transition_text = "La nuit tombe..."
                        elif action == "rest_at_night":
                            self.transition_active = True
                            self.transition_alpha = 0
                            self.transition_type = 'night'
                            self.transition_text = "La nuit tombe..."
                        elif action == "explore_at_night":
                            self.game_state = 'loading'

                elif self.game_state == 'dungeon':
                    self.player.single_input(event)

    def check_pause_click(self, pos):
        center_x = WIDTH // 2; center_y = HEIGHT // 2; btn_width = 300; btn_height = 50; gap = 70
        buttons = []
        if self.game_state == 'hub':
            buttons.append({'text': "SAUVEGARDER & MENU", 'action': 'save_quit'})
            buttons.append({'text': "RETOUR JEU", 'action': 'resume'})
        elif self.game_state == 'dungeon':
            buttons.append({'text': "RETOUR HUB (Perte Loot)", 'action': 'dungeon_to_hub'})
            buttons.append({'text': "SAUVEGARDER & MENU (Perte Loot)", 'action': 'dungeon_to_menu'})
            buttons.append({'text': "RETOUR JEU", 'action': 'resume'})
        
        start_y = center_y - (len(buttons) * gap) // 2
        for i, btn in enumerate(buttons):
            rect = pygame.Rect(0, 0, btn_width, btn_height)
            rect.center = (center_x, start_y + i * gap)
            if rect.collidepoint(pos):
                if btn['action'] == 'resume':
                    self.paused = False
                elif btn['action'] == 'save_quit':
                    self.save_all(); self.paused = False; self.game_state = 'menu'
                elif btn['action'] == 'dungeon_to_hub':
                    self.revert_dungeon_resources(); self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
                    self.game_state = 'hub'; self.game_time = 0; self.paused = False; self.hub.spawn_npcs(self.player); self.save_all()
                elif btn['action'] == 'dungeon_to_menu':
                    self.revert_dungeon_resources(); self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
                    self.game_state = 'menu'; self.game_time = 0; self.paused = False; self.save_all()

    def draw_main_menu(self):
        self.screen.fill((20, 20, 30))
        title_surf = self.title_font.render(GAME_NAME, True, (200, 180, 50))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 150))
        shadow_surf = self.title_font.render(GAME_NAME, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(WIDTH // 2 + 5, 155))
        self.screen.blit(shadow_surf, shadow_rect); self.screen.blit(title_surf, title_rect)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            if btn['rect'].collidepoint(mouse_pos): bg_color = (100, 100, 120); text_color = (255, 255, 255); border_width = 3
            else: bg_color = (50, 50, 60); text_color = (200, 200, 200); border_width = 0
            pygame.draw.rect(self.screen, bg_color, btn['rect'], border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), btn['rect'], 2, border_radius=10)
            text_surf = self.menu_font.render(btn['text'], True, text_color)
            text_rect = text_surf.get_rect(center=btn['rect'].center)
            self.screen.blit(text_surf, text_rect)
        version_surf = pygame.font.Font(UI_FONT, 20).render("v0.3.1 - Stable", True, (80, 80, 80))
        self.screen.blit(version_surf, (10, HEIGHT - 30))
        pygame.display.flip()

    def draw_options_menu(self):
        self.screen.fill((20, 20, 30))
        title_surf = self.title_font.render("OPTIONS", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 150))
        self.screen.blit(title_surf, title_rect)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.options_buttons:
            is_reset = (btn['action'] == 'reset_save')
            if btn['rect'].collidepoint(mouse_pos):
                if is_reset: bg_color = (200, 50, 50) 
                else: bg_color = (100, 100, 120)
                text_color = (255, 255, 255); border_width = 3
            else:
                if is_reset: bg_color = (150, 30, 30)
                else: bg_color = (50, 50, 60)
                text_color = (200, 200, 200); border_width = 0
            pygame.draw.rect(self.screen, bg_color, btn['rect'], border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), btn['rect'], 2, border_radius=10)
            text_surf = self.menu_font.render(btn['text'], True, text_color)
            text_rect = text_surf.get_rect(center=btn['rect'].center)
            self.screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        title_surf = self.menu_font.render("PAUSE", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title_surf, title_rect)
        center_x = WIDTH // 2; center_y = HEIGHT // 2; btn_width = 300; btn_height = 50; gap = 70
        buttons = []
        if self.game_state == 'hub':
            buttons.append({'text': "SAUVEGARDER & MENU", 'color': (50, 150, 50)})
            buttons.append({'text': "RETOUR JEU", 'color': (100, 100, 100)})
        elif self.game_state == 'dungeon':
            buttons.append({'text': "RETOUR HUB (Perte Loot)", 'color': (150, 50, 50)})
            buttons.append({'text': "SAUVEGARDER & MENU (Perte Loot)", 'color': (150, 50, 50)})
            buttons.append({'text': "RETOUR JEU", 'color': (100, 100, 100)})
        start_y = center_y - (len(buttons) * gap) // 2
        mouse_pos = pygame.mouse.get_pos()
        for i, btn in enumerate(buttons):
            rect = pygame.Rect(0, 0, btn_width, btn_height)
            rect.center = (center_x, start_y + i * gap)
            if rect.collidepoint(mouse_pos):
                color = (min(btn['color'][0] + 50, 255), min(btn['color'][1] + 50, 255), min(btn['color'][2] + 50, 255)); border = 3
            else:
                color = btn['color']; border = 0
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=8)
            text_surf = pygame.font.Font(UI_FONT, 20).render(btn['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

    def draw(self):
        if self.game_state == 'menu': self.draw_main_menu()
        elif self.game_state == 'options': self.draw_options_menu()
        elif self.game_state == 'intro': self.intro.draw(); pygame.display.flip()
        
        elif self.game_state == 'hub':
            self.hub.draw()
            show_inv = not self.hub.build_mode_active
            self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour, show_inventory=show_inv)
            if self.transition_active: self.draw_fade_transition()
            if self.paused: self.draw_pause_menu()
            pygame.display.flip()
        
        elif self.game_state == 'loading':
            self.screen.fill((0, 0, 0))
            text = self.loading_font.render("Génération du donjon...", True, (255, 255, 255))
            text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.screen.blit(text, text_rect)
            pygame.display.flip()
        
        elif self.game_state == 'dungeon':
            self.screen.fill('black')
            self.visible_sprites.custom_draw(self.player)
            self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour)
            if self.transition_active: self.draw_fade_transition()
            if self.paused: self.draw_pause_menu()
            pygame.display.flip()

    def draw_fade_transition(self):
        progress = self.transition_alpha / self.transition_duration
        if progress < 1/3: opacity = int((progress / (1/3)) * 255); text_opacity = int((progress / (1/3)) * 255)
        elif progress < 2/3: opacity = 255; text_opacity = 255
        else: fade_out_progress = (progress - 2/3) / (1/3); opacity = int((1 - fade_out_progress) * 255); text_opacity = int((1 - fade_out_progress) * 255)
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.set_alpha(opacity); fade_surface.fill((0, 0, 0)); self.screen.blit(fade_surface, (0, 0))
        if text_opacity > 0:
            text_surface = self.transition_font.render(self.transition_text, True, (255, 255, 255))
            text_surface.set_alpha(text_opacity); text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text_surface, text_rect)

    def create_map(self):
        self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
        dungeon = DungeonGenerator(); map_data, player_spawn = dungeon.generate()
        for row_index, row in enumerate(map_data):
            for col_index, cell in enumerate(row):
                x = col_index * TILE_SIZE; y = row_index * TILE_SIZE
                if cell == 'x': Tile((x, y), [self.visible_sprites, self.obstacle_sprites])
        spawn_x = player_spawn[0] * TILE_SIZE; spawn_y = player_spawn[1] * TILE_SIZE
        entrance_tile = DungeonEntrance((spawn_x, spawn_y), [self.visible_sprites])
        self.dungeon_entrance_pos = pygame.math.Vector2(spawn_x, spawn_y); self.dungeon_entrance_rect = entrance_tile.rect
        self.resources_at_dungeon_start = {'gold': self.player.inventory['gold'], 'iron': self.player.inventory['iron'], 'health': self.player.health}
        self.player.rect.topleft = (spawn_x, spawn_y); self.player.pos = pygame.math.Vector2(self.player.rect.topleft); self.player.obstacle_sprites = self.obstacle_sprites; self.player.add(self.visible_sprites)
        available_monsters = ['tier1', 'tier2']; monster_weights = [70, 30]
        if 5 <= self.player.level < 10: available_monsters = ['tier3', 'tier4']; monster_weights = [60, 40]
        elif self.player.level >= 10: available_monsters = ['tier5']; monster_weights = [100]
        for room in dungeon.rooms[1:]:
            for nb in range(random.randint(2, 4)):
                offset_x = random.randint(-20, 20); offset_y = random.randint(-20, 20)
                enemy_x = room.centerx * TILE_SIZE + offset_x; enemy_y = room.centery * TILE_SIZE + offset_y
                tier_choice = random.choices(available_monsters, weights=monster_weights, k=1)[0]
                Enemy([self.visible_sprites, self.attackable_sprites], (enemy_x, enemy_y), self.obstacle_sprites, tier_choice)

    def update(self):
        if self.game_state == 'loading':
            self.create_map()
            self.game_state = 'dungeon'
            return

        if self.game_state == 'intro':
            finished = self.intro.update()
            if finished:
                self.game_state = self.intro_next_state
                if self.intro_next_state == 'hub':
                    self.save_all()
            return

        if self.game_state == 'menu' or self.game_state == 'options': return
        if self.paused: return 
        if not self.transition_active and not self.hub.night_arrived: self.game_time += self.clock.get_time()
        elif self.transition_active: self.transition_alpha += 1
        
        if self.game_state == 'hub':
            if self.game_time >= self.evening_duration and not self.transition_active and not self.hub.night_arrived: self.hub.night_arrived = True
        elif self.game_state == 'dungeon':
            if self.game_time >= self.full_day_duration and not self.transition_active:
                self.transition_active = True; self.transition_alpha = 0; self.transition_type = 'morning'; self.transition_text = "Il est l'heure de rentrer..."
        
        if self.transition_active:
            if self.transition_alpha == self.transition_duration // 2:
                if self.transition_type == 'morning':
                    if self.is_player_at_entrance():
                        self.game_state = 'hub'; self.game_time = 0; self.transition_text = "Il est l'heure de rentrer..."; self.hub.spawn_npcs(self.player); self.save_all(); print("Journée terminée, retour au hub à 6h. Sauvegarde effectuée.")
                    else:
                        self.game_state = 'hub'; self.game_time = 0; self.transition_text = "Une équipe de secours est venue vous chercher."
                        if self.resources_at_dungeon_start: self.player.inventory['gold'] = self.resources_at_dungeon_start['gold']; self.player.inventory['iron'] = self.resources_at_dungeon_start['iron']; self.player.health = 10
                        self.save_all(); print("Une équipe de secours est venue vous chercher. Ressources perdues, santé à 10.")
                    self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
                elif self.transition_type == 'night':
                    self.game_time = 0; self.save_all(); print("La nuit est tombée. Nouveau jour commence à 6h.")
                
                elif self.transition_type == 'wait_for_dungeon':
                    print("Transition vers le chargement..."); 
                    self.game_state = 'loading'

            if self.transition_alpha >= self.transition_duration: self.transition_active = False; self.transition_alpha = 0; self.transition_type = None
        
        if self.game_state == 'hub' and not self.transition_active: pass
        elif self.game_state == 'dungeon' and not self.transition_active:
            self.visible_sprites.update()
            for enemy in self.attackable_sprites:
                enemy.enemy_update(self.player)
                if pygame.sprite.collide_rect(enemy, self.player): self.player.get_damage(enemy.damage, enemy.rect.center)
                if enemy.health <= 0:
                    for item_type, (min_amt, max_amt) in enemy.loot_table.items():
                        amount = random.randint(min_amt, max_amt)
                        for _ in range(amount):
                            offset_x = random.randint(-30, 30); offset_y = random.randint(-30, 30); pos = (enemy.rect.x + offset_x, enemy.rect.y + offset_y)
                            Item(pos, [self.visible_sprites, self.item_sprites], item_type)
                    enemy.kill()
            for item in pygame.sprite.spritecollide(self.player, self.item_sprites, True):
                if item.type in self.player.inventory: self.player.inventory[item.type] += 1
            if self.player.current_weapon:
                hitted_enemies = pygame.sprite.spritecollide(self.player.current_weapon, self.attackable_sprites, False)
                for e in hitted_enemies: e.get_damage(self.player.rect.center, self.player.attack_damage)
            if self.player.health <= 0: print("GAME OVER"); pygame.quit(); sys.exit()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)