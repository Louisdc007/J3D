import pygame
import sys
from settings import *
from entities.player import *
from camera import CameraGroup
from tile import Tile
from entities.enemy import Enemy

#uniquement pour le test
import random

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

    def events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def draw(self) :
        self.screen.fill('black')
        self.visible_sprites.custom_draw(self.player)
        pygame.display.flip()
        

    def create_map(self):
        for x, l in enumerate(WORLD_MAP): # enumerate donne l'index et l'element
            for y, e in enumerate(l):
                if e == 'x':
                    Tile((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites, self.obstacle_sprites])
                elif e == 'p':
                    self.player = Player((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites], self.obstacle_sprites)
                elif e == 'm':
                    Enemy([self.visible_sprites, self.attackable_sprites], (x * TILE_SIZE, y * TILE_SIZE), self.obstacle_sprites)

    def update(self):
        self.visible_sprites.update()

        for enemy in self.attackable_sprites:
            enemy.enemy_update(self.player)

        if self.player.current_weapon:
            hitted_enemies = pygame.sprite.spritecollide(self.player.current_weapon, self.attackable_sprites, False) #type: ignore
            for e in hitted_enemies:
                e.get_damage()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
    