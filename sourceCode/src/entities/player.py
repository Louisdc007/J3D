import pygame
from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacles):
        super().__init__(groups)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill('white')
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2(0 ,0)
        self.speed = 5
        self.obstacle_sprites = obstacles

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

    def collision(self, direction : str): # un texte pour indiquer une droite de mouvement
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.x > 0:
                        self.rect.right = sprite.rect.left
                        self.pos.x = self.rect.x
                    elif self.direction.x < 0:
                        self.rect.left = sprite.rect.right
                        self.pos.x = self.rect.x
        elif direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.y > 0:
                        self.rect.bottom = sprite.rect.top
                        self.pos.y = self.rect.y
                    elif self.direction.y < 0:
                        self.rect.top = sprite.rect.bottom
                        self.pos.y = self.rect.y
    
    def move(self, speed):
        if self.direction.magnitude() != 0:
            self.direction= self.direction.normalize()
        self.pos.x += self.direction.x * speed
        self.rect.x = int(self.pos.x)
        self.collision('horizontal')
        self.pos.y += self.direction.y * speed
        self.rect.y = int(self.pos.y)
        self.collision('vertical')


    def update(self):
        self.input()
        self.move(self.speed)