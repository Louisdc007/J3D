import pygame
from settings import *
import random

#from settings import MONSTER_DATA


class Enemy(pygame.sprite.Sprite):
    def __init__(self, groups, pos, obstacles, tier):
        super().__init__(groups)

        info = MONSTER_DATA[tier]

        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(info['color'])
        self.rect = self.image.get_rect(topleft = pos)

        self.health = info['health']
        self.speed = info['speed']
        self.damage = info['damage']
        self.notice_radius = info['notice_radius']
        self.loot_table = info['loot']

        self.vulnerable = True
        self.hit_time = 0

        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()

        self.obstacle_sprites = obstacles

        self.start_time = 0
        self.duration = 0

        self.knockback = pygame.math.Vector2(0, 0)
        self.base_color = info['color']

    def get_damage(self, player_center, amount):
        if self.vulnerable:
            self.health -= amount
            self.vulnerable = False
            self.hit_time = pygame.time.get_ticks()
            self.image.fill('white')

            my_pos = pygame.math.Vector2(self.rect.center)
            other_pos = pygame.math.Vector2(player_center)
            diff = my_pos - other_pos

            if diff.magnitude() != 0:
                self.knockback = diff.normalize() * 15
            else:
                self.knockback = pygame.math.Vector2(0, 0)
    
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

    def collision(self, direction, speed):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if speed > 0:
                        self.rect.right = sprite.rect.left
                        self.pos.x = self.rect.x
                    if speed < 0:
                        self.rect.left = sprite.rect.right
                        self.pos.x = self.rect.x

        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if speed > 0:
                        self.rect.bottom = sprite.rect.top
                        self.pos.y = self.rect.y
                    if speed < 0:
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

    def reduce_knockback(self):

        self.knockback *= 0.8

        if self.knockback.magnitude() < 0.5:
            self.knockback = pygame.math.Vector2(0, 0)


    def move(self, speed):

        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        dx = self.direction.x * speed + self.knockback.x
        
        self.pos.x += dx
        self.rect.x = int(self.pos.x)

        self.collision('horizontal', dx)

        dy = self.direction.y * speed + self.knockback.y
        self.pos.y += dy
        self.rect.y = int(self.pos.y)
        self.collision('vertical', dy)

    def update(self):
        self.reduce_knockback()
        if not self.vulnerable:
            if pygame.time.get_ticks() - self.hit_time >= 400:
                self.image.fill(self.base_color)
                self.vulnerable = True
