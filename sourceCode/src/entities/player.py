import pygame
from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(groups)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill('white')
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2(0 ,0)
        self.speed = 5

    def input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_z]:
            self.direction.y = -1
        elif keys[pygame.K_s]:
            self.direction.y = 1
        else:
            self.direction.y = 0

        if keys[pygame.K_q]:
            self.direction.x = -1
        elif keys[pygame.K_d]:
            self.direction.x = 1
        else:
            self.direction.x = 0
        
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        
    def update(self):
        self.input()
        self.pos += self.direction * self.speed
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))