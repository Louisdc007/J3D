import pygame
from settings import *

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(groups)
        self.image = pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill('gray')
        self.rect = self.image.get_rect(topleft = pos)

class DungeonEntrance(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(groups)
        self.image = pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill((0, 255, 0))  # Vert vif pour l'entrée
        self.rect = self.image.get_rect(topleft = pos)