import pygame
from settings import *
import random

class Enemy(pygame.sprite.Sprite):
    def __init__(self, groups, pos, obstacles):
        super().__init__(groups)

        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill('red')
        self.rect = self.image.get_rect(topleft = pos)

        self.health = 3
        self.speed = 3

        self.vulnerable = True
        self.hit_time = 0

        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()

        self.obstacle_sprites = obstacles

        self.start_time = 0
        self.duration = 0

    def get_damage(self):
        if self.vulnerable:
            self.health -= 1
            self.vulnerable = False
            self.hit_time = pygame.time.get_ticks()
            self.image.fill('white')
        if self.health <= 0:
            self.kill()
    
    def patrol(self):
        current_time = pygame.time.get_ticks()
        duration = current_time - self.start_time

        if duration >= self.duration:
            self.start_time = pygame.time.get_ticks()
            self.duration = random.randint(1000, 3000)

            next_action = random.randint(1, 2)

            match next_action:
                case 1:
                    self.direction = pygame.math.Vector2((0,0))
                case 2:
                    new_x = random.uniform(-1, 1)
                    new_y = random.uniform(-1, 1)
                    new_vect = pygame.math.Vector2((new_x, new_y))
                    if new_vect.magnitude() != 0:
                        new_vect = new_vect.normalize()
                    
                    self.direction = new_vect

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

    def enemy_update(self, player):
        enemy_vect = pygame.math.Vector2(self.rect.center)
        player_vect = pygame.math.Vector2(player.rect.center)
        distance_vect = player_vect - enemy_vect
        distance = distance_vect.magnitude()

        if distance < 300 and distance > 0:
            self.direction = distance_vect.normalize()
        else:
            self.patrol()

        self.move(self.speed)

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
        if not self.vulnerable:
            if pygame.time.get_ticks() - self.hit_time >= 400:
                self.image.fill('red')
                self.vulnerable = True