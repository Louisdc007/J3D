import random
from settings import *
from entities.player import *
from camera import CameraGroup
from tile import Tile
from entities.enemy import Enemy
from ui import UI
from dungeon import DungeonGenerator
from entities.item import Item

class Game() :
    def __init__(self) :
        pygame.init()
        self.screen = pygame.display.set_mode(size = (WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.clock = pygame.time.Clock()
        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.create_map()
        self.ui = UI()
        self.item_sprites = pygame.sprite.Group()

    def events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def draw(self) :
        self.screen.fill('black')
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)
        pygame.display.flip()
        

    def create_map(self):
        """
        on en a finit de ce truc pourri, place a la gestion automatique

        for x, l in enumerate(WORLD_MAP): # enumerate donne l'index et l'element
            for y, e in enumerate(l):
                if e == 'x':
                    Tile((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites, self.obstacle_sprites])
                elif e == 'p':
                    self.player = Player((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites], self.obstacle_sprites)
                elif e == 'm':
                    Enemy([self.visible_sprites, self.attackable_sprites], (x * TILE_SIZE, y * TILE_SIZE), self.obstacle_sprites)
        """

        dungeon = DungeonGenerator()
        map_data, player_spawn = dungeon.generate()

        for x, l in enumerate(map_data):
            for y, e in enumerate(l):
                if e == 'x':
                    Tile((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites, self.obstacle_sprites])
                elif e == 'p':
                    self.player = Player((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites], self.obstacle_sprites)
                elif e == 'm':
                    Enemy([self.visible_sprites, self.attackable_sprites], (x * TILE_SIZE, y * TILE_SIZE), self.obstacle_sprites)
                
        self.player = Player((player_spawn[1] * TILE_SIZE, player_spawn[0] * TILE_SIZE), [self.visible_sprites], self.obstacle_sprites)

        for room in dungeon.rooms[1:]:
            for nb in range(random.randint(1, 5)):
                enemy_x = room.center[1] * TILE_SIZE
                enemy_y = room.center[0] * TILE_SIZE

                Enemy([self.visible_sprites, self.attackable_sprites], (enemy_x, enemy_y), self.obstacle_sprites, 'tier1')


    def update(self):
        self.visible_sprites.update()

        for enemy in self.attackable_sprites:
            enemy.enemy_update(self.player)
            if pygame.sprite.collide_rect(enemy, self.player):
                self.player.get_damage(10, enemy.rect.center)

            if enemy.health <= 0:
                for i in range(random.randint(1, 3)):
                    x = enemy.rect.x + random.randint(-TILE_SIZE, TILE_SIZE)
                    y = enemy.rect.y + random.randint(-TILE_SIZE, TILE_SIZE)
                    Item((x, y), [self.visible_sprites, self.item_sprites], 'xp')
                for i in range(random.randint(1, 5)):
                    x = enemy.rect.x + random.randint(-TILE_SIZE, TILE_SIZE)
                    y = enemy.rect.y + random.randint(-TILE_SIZE, TILE_SIZE)
                    Item((x, y), [self.visible_sprites, self.item_sprites], 'iron')
                enemy.kill()

        for item in pygame.sprite.spritecollide(self.player, self.item_sprites, True):
            self.player.inventory[item.type] += 1
            print(self.player.inventory)


        if self.player.current_weapon:
            hitted_enemies = pygame.sprite.spritecollide(self.player.current_weapon, self.attackable_sprites, False) #type: ignore
            for e in hitted_enemies:
                e.get_damage(self.player.rect.center)
        
        if self.player.health <= 0:
            pygame.quit()
            sys.exit()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
    