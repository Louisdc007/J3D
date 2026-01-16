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

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(size=(WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.clock = pygame.time.Clock()

        self.save_manager = SaveManager()

        self.game_state = 'hub'
        self.hub = Hub()

        self.game_time = 0
        self.day_duration = 5 * 60 * 100
        self.hours_in_day = 24
        self.morning_hour = 6
        self.evening_hour = 20
        self.hours_day_to_evening = self.evening_hour - self.morning_hour
        
        # Calcul des durées
        # 10h de jeu = day_duration
        # 14h réelles = 14 * (day_duration / 10) = 42000
        # 24h réelles = 24 * (day_duration / 10) = 72000
        self.evening_duration = int(self.day_duration * (self.hours_day_to_evening / 10))  # Jusqu'à 20h
        self.full_day_duration = int(self.day_duration * (self.hours_in_day / 10))  # Cycle complet

        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)

        loaded_data = self.save_manager.load_game()
        if loaded_data:
            self.player.load_save_data(loaded_data['player'])
            self.hub.load_save_data(loaded_data['hub'])
        else:
            print("Nouvelle partie démarrée.")

        self.create_map()
        self.ui = UI()

        # Transition variables
        self.transition_active = False
        self.transition_alpha = 0
        self.transition_duration = 420  # frames pour la transition (7 secondes)
        self.transition_text = "Il est l'heure de rentrer..."
        self.transition_font = pygame.font.Font(None, 60)
        self.transition_type = None  # 'morning' ou 'night'
        
        # Dungeon variables
        self.dungeon_entrance_pos = None  # Position de l'entrée du dungeon
        self.dungeon_entrance_rect = None  # Rectangle de la tuile d'entrée
        self.resources_at_dungeon_start = None  # Ressources sauvegardées au démarrage du dungeon

    def get_current_hour(self):
        ratio = self.game_time / self.full_day_duration
        if ratio > 1:
            ratio = 1
        current_hour_float = self.morning_hour + (self.hours_in_day * ratio)
        return int(current_hour_float % 24)
    
    def is_dungeon_time(self):
        current_hour = self.get_current_hour()
        return current_hour >= self.evening_hour or current_hour < self.morning_hour
    
    def is_player_at_entrance(self):
        if self.dungeon_entrance_rect is None:
            return False
        return self.player.rect.colliderect(self.dungeon_entrance_rect)
    
    def save_all(self):
        data = {
            'player': self.player.get_save_data(),
            'hub': self.hub.get_save_data()
        }
        self.save_manager.save_game(data)

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_all()
                pygame.quit()
                sys.exit()

            if self.game_state == 'hub':
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = self.hub.check_click(event.pos, self.player)

                    if action == "build_action":
                        self.save_all()

                    elif action == "dungeon_random_check":
                        if self.is_dungeon_time():
                            self.create_map()
                            self.game_state = 'dungeon'
                        else:
                            self.hub.waiting_for_night = True

                    elif action == "wait_for_night_random":
                        self.game_time = self.evening_duration
                        self.create_map()
                        self.game_state = 'dungeon'

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
                        self.create_map()
                        self.game_state = 'dungeon'

                    elif action == "reset_game":
                        print("Réinitialisation de la partie...")
                        self.save_manager.delete_save()

                        self.obstacle_sprites.empty()
                        self.visible_sprites.empty()

                        self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
                        self.hub = Hub()

                        print("Partie remise à zéro !")

    def draw(self):
        if self.game_state == 'hub':
            self.hub.draw()
            self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour)
            
            if self.transition_active:
                self.draw_fade_transition()
            
            pygame.display.flip()

        elif self.game_state == 'dungeon':
            self.screen.fill('black')
            self.visible_sprites.custom_draw(self.player)
            self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour)
            
            if self.transition_active:
                self.draw_fade_transition()
            
            pygame.display.flip()

    def draw_fade_transition(self):
        progress = self.transition_alpha / self.transition_duration
        
        if progress < 1/3:
            opacity = int((progress / (1/3)) * 255)
            text_opacity = int((progress / (1/3)) * 255)
        elif progress < 2/3:
            opacity = 255
            text_opacity = 255
        else:
            fade_out_progress = (progress - 2/3) / (1/3)
            opacity = int((1 - fade_out_progress) * 255)
            text_opacity = int((1 - fade_out_progress) * 255)
        
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.set_alpha(opacity)
        fade_surface.fill((0, 0, 0))
        self.screen.blit(fade_surface, (0, 0))
        
        if text_opacity > 0:
            text_surface = self.transition_font.render(self.transition_text, True, (255, 255, 255))
            text_surface.set_alpha(text_opacity)
            text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text_surface, text_rect)

    def create_map(self):
        self.visible_sprites.empty()
        self.obstacle_sprites.empty()
        self.attackable_sprites.empty()
        self.item_sprites.empty()

        dungeon = DungeonGenerator()
        map_data, player_spawn = dungeon.generate()

        for row_index, row in enumerate(map_data):
            for col_index, cell in enumerate(row):
                x = col_index * TILE_SIZE
                y = row_index * TILE_SIZE
                if cell == 'x':
                    Tile((x, y), [self.visible_sprites, self.obstacle_sprites])

        spawn_x = player_spawn[0] * TILE_SIZE
        spawn_y = player_spawn[1] * TILE_SIZE

        entrance_tile = DungeonEntrance((spawn_x, spawn_y), [self.visible_sprites])
        
        self.dungeon_entrance_pos = pygame.math.Vector2(spawn_x, spawn_y)
        self.dungeon_entrance_rect = entrance_tile.rect
        
        self.resources_at_dungeon_start = {
            'gold': self.player.inventory['gold'],
            'iron': self.player.inventory['iron'],
            'health': self.player.health
        }

        self.player.rect.topleft = (spawn_x, spawn_y)
        self.player.pos = pygame.math.Vector2(self.player.rect.topleft)
        self.player.obstacle_sprites = self.obstacle_sprites
        self.player.add(self.visible_sprites)

        available_monsters = ['tier1', 'tier2']
        monster_weights = [70, 30]

        if 5 <= self.player.level < 10:
            available_monsters = ['tier3', 'tier4']
            monster_weights = [60, 40]
        elif self.player.level >= 10:
            available_monsters = ['tier5']
            monster_weights = [100]

        for room in dungeon.rooms[1:]:
            for nb in range(random.randint(2, 4)):
                offset_x = random.randint(-20, 20)
                offset_y = random.randint(-20, 20)
                enemy_x = room.centerx * TILE_SIZE + offset_x
                enemy_y = room.centery * TILE_SIZE + offset_y

                tier_choice = random.choices(available_monsters, weights=monster_weights, k=1)[0]
                Enemy([self.visible_sprites, self.attackable_sprites], (enemy_x, enemy_y), self.obstacle_sprites,
                      tier_choice)

    def update(self):
        if not self.transition_active and not self.hub.night_arrived:
            self.game_time += self.clock.get_time()
        elif self.transition_active:
            self.transition_alpha += 1
        
        if self.game_state == 'hub':
            if self.game_time >= self.evening_duration and not self.transition_active and not self.hub.night_arrived:
                self.hub.night_arrived = True
        
        elif self.game_state == 'dungeon':
            if self.game_time >= self.full_day_duration and not self.transition_active:
                self.transition_active = True
                self.transition_alpha = 0
                self.transition_type = 'morning'
                self.transition_text = "Il est l'heure de rentrer..."
        
        if self.transition_active:
            if self.transition_alpha == self.transition_duration // 2:
                if self.transition_type == 'morning':
                    if self.is_player_at_entrance():
                        self.game_state = 'hub'
                        self.game_time = 0
                        self.transition_text = "Il est l'heure de rentrer..."
                        self.save_all()
                        print("Journée terminée, retour au hub à 6h. Sauvegarde effectuée.")
                    else:
                        self.game_state = 'hub'
                        self.game_time = 0
                        self.transition_text = "Une équipe de secours est venue vous chercher."
                        if self.resources_at_dungeon_start:
                            self.player.inventory['gold'] = self.resources_at_dungeon_start['gold']
                            self.player.inventory['iron'] = self.resources_at_dungeon_start['iron']
                            self.player.health = 10
                        self.save_all()
                        print("Une équipe de secours est venue vous chercher. Ressources perdues, santé à 10.")

                    self.visible_sprites.empty()
                    self.obstacle_sprites.empty()
                    self.attackable_sprites.empty()
                    self.item_sprites.empty()
                    
                elif self.transition_type == 'night':
                    self.game_time = 0
                    self.save_all()
                    print("La nuit est tombée. Nouveau jour commence à 6h.")
            
            if self.transition_alpha >= self.transition_duration:
                self.transition_active = False
                self.transition_alpha = 0
                self.transition_type = None
        
        if self.game_state == 'hub' and not self.transition_active:
            pass

        elif self.game_state == 'dungeon' and not self.transition_active:
            self.visible_sprites.update()

            for enemy in self.attackable_sprites:
                enemy.enemy_update(self.player)
                if pygame.sprite.collide_rect(enemy, self.player):
                    self.player.get_damage(enemy.damage, enemy.rect.center)

                if enemy.health <= 0:
                    for item_type, (min_amt, max_amt) in enemy.loot_table.items():
                        amount = random.randint(min_amt, max_amt)
                        for _ in range(amount):
                            offset_x = random.randint(-30, 30)
                            offset_y = random.randint(-30, 30)
                            pos = (enemy.rect.x + offset_x, enemy.rect.y + offset_y)
                            Item(pos, [self.visible_sprites, self.item_sprites], item_type)
                    enemy.kill()

            for item in pygame.sprite.spritecollide(self.player, self.item_sprites, True):
                if item.type in self.player.inventory:
                    self.player.inventory[item.type] += 1

            if self.player.current_weapon:
                hitted_enemies = pygame.sprite.spritecollide(self.player.current_weapon, self.attackable_sprites, False)
                for e in hitted_enemies:
                    e.get_damage(self.player.rect.center, self.player.attack_damage)

            if self.player.health <= 0:
                print("GAME OVER")
                pygame.quit()
                sys.exit()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
