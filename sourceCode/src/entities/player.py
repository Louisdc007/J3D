import pygame
from settings import *
from weapon import Weapon

# juste pour quitter avec echap
import sys

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
        self.attacking = False
        self.attack_cooldown = 400
        self.attack_time = 0

    def input(self):
        if not self.attacking:
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
            
            # pour quitter avec echap
            if keys[pygame.K_ESCAPE] == 1:
                pygame.quit()
                sys.exit()
        
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0] and not self.attacking:
            self.attack_time = pygame.time.get_ticks()
            self.direction.x = 0
            self.direction.y = 0
            self.attacking = True
            
            mouse_pos = pygame.mouse.get_pos()
            mouse_vect = pygame.math.Vector2(mouse_pos)
            center_vect = pygame.math.Vector2((WIDTH//2, HEIGHT//2))
            aim_vect = mouse_vect-center_vect

            if aim_vect.magnitude() != 0:
                aim_vect = aim_vect.normalize()
            self.current_weapon = Weapon(self, self.groups(), aim_vect)
            print(f'attaque vers : {aim_vect.x} {aim_vect.y}')

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if self.attacking:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.attacking = False
                self.current_weapon.kill() # si tu utilises vscode tu vas surement voir du rouge ici, c'est juste que vscode est débile
                self.current_weapon = None

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
        self.cooldowns()
        self.move(self.speed)
        