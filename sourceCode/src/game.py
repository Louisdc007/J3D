import pygame
import sys
import random
from settings import *
from entities.player import *
from camera import CameraGroup
from tile import Tile
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

                    elif action == "dungeon_random":
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
            self.ui.display(self.player, 0, 1)
            pygame.display.flip()

        elif self.game_state == 'dungeon':
            self.screen.fill('black')
            self.visible_sprites.custom_draw(self.player)
            self.ui.display(self.player, self.game_time, self.day_duration)
            pygame.display.flip()

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
        if self.game_state == 'hub':
            pass

        elif self.game_state == 'dungeon':
            self.game_time += self.clock.get_time()

            if self.game_time >= self.day_duration:
                self.game_state = 'hub'
                self.game_time = 0
                self.save_all()
                print("Journée terminée, retour au hub. Sauvegarde effectuée.")

                self.visible_sprites.empty()
                self.obstacle_sprites.empty()
                self.attackable_sprites.empty()
                self.item_sprites.empty()

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
