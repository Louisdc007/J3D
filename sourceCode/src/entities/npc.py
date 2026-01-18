import pygame
import random
from settings import *

class NPC(pygame.sprite.Sprite):
    def __init__(self, groups, pos, obstacles):
        super().__init__(groups)
        
        self.image = pygame.Surface((14, 28))
        
        colors = [(180, 90, 90), (90, 180, 90), (90, 90, 180), (180, 180, 80), (150, 100, 50)]
        self.image.fill(random.choice(colors))
        
        pygame.draw.rect(self.image, (0,0,0), (4, 4, 2, 2))
        
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()
        
        self.speed = 0.8 

        self.obstacle_sprites = obstacles
        
        self.start_time = pygame.time.get_ticks()
        self.duration = random.randint(2000, 6000)
        self.center_village = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
        self.village_radius = 400 

    def patrol(self):
        current_time = pygame.time.get_ticks()
        
        if current_time - self.start_time >= self.duration:
            self.start_time = pygame.time.get_ticks()
            self.duration = random.randint(3000, 8000)

            choice = random.randint(0, 3)
            if choice == 0:
                self.direction = pygame.math.Vector2(0, 0)
            else:
                self.direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                if self.direction.magnitude() != 0:
                    self.direction = self.direction.normalize()

    def check_boundaries(self):
        dist = (self.pos - self.center_village).magnitude()
        if dist > self.village_radius:
            direction_to_center = self.center_village - self.pos
            if direction_to_center.magnitude() != 0:
                self.direction = direction_to_center.normalize()

    def collision(self, direction):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.x > 0:
                        self.rect.right = sprite.rect.left
                        self.pos.x = self.rect.x
                        self.direction.x *= -1
                    elif self.direction.x < 0:
                        self.rect.left = sprite.rect.right
                        self.pos.x = self.rect.x
                        self.direction.x *= -1

        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.y > 0:
                        self.rect.bottom = sprite.rect.top
                        self.pos.y = self.rect.y
                        self.direction.y *= -1
                    elif self.direction.y < 0:
                        self.rect.top = sprite.rect.bottom
                        self.pos.y = self.rect.y
                        self.direction.y *= -1

    def move(self):
        if self.direction.magnitude() != 0:
            self.pos.x += self.direction.x * self.speed
            self.rect.x = int(self.pos.x)
            self.collision('horizontal')

            self.pos.y += self.direction.y * self.speed
            self.rect.y = int(self.pos.y)
            self.collision('vertical')

    def update(self):
        self.patrol()
        self.check_boundaries()
        self.move()