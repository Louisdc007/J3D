import pygame
from settings import *
from weapon import Weapon
import sys


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacles):
        super().__init__(groups)
        self.image = pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill('white')
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = 5
        self.obstacle_sprites = obstacles
        self.attacking = False
        self.attack_cooldown = 400
        self.attack_time = 0
        self.current_weapon = None
        self.is_dashing = False
        self.dash_speed = 15
        self.dash_duration = 200
        self.dash_start_time = 0
        self.can_dash = True
        self.dash_cooldown = 1000
        self.last_dash_time = 0
        self.vulnerable = True
        self.hurt_time = 0
        self.invincibility_duration = 500
        self.knockback = pygame.math.Vector2(0, 0)

        self.level = 1
        self.max_health = 100
        self.health = self.max_health
        
        self.xp_to_next_level = 50 
        
        self.attack_damage = 10
        self.inventory = {'gold': 0, 'iron': 0, 'xp': 0}

    def attack(self):
        self.attacking = True
        self.attack_time = pygame.time.get_ticks()

        mouse_pos = pygame.mouse.get_pos()
        mouse_vect = pygame.math.Vector2(mouse_pos)
        center_vect = pygame.math.Vector2((WIDTH // 2, HEIGHT // 2))
        aim_vect = mouse_vect - center_vect

        if aim_vect.magnitude() != 0:
            aim_vect = aim_vect.normalize()

        self.current_weapon = Weapon(self, self.groups(), aim_vect)

    def single_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and not self.attacking and not self.is_dashing:
                self.attack()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.can_dash and not self.is_dashing:
                self.start_dash()

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

            if keys[pygame.K_SPACE]:
                if not self.attacking and not self.is_dashing and self.can_dash:
                    self.start_dash()

        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0] and not self.attacking:
            self.attack()

    def start_dash(self):
        self.image.fill('blue')
        self.is_dashing = True
        self.can_dash = False
        self.dash_start_time = pygame.time.get_ticks()

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if self.attacking:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.attacking = False
                if self.current_weapon:
                    self.current_weapon.kill()
                    self.current_weapon = None

        if self.is_dashing:
            if current_time - self.dash_start_time >= self.dash_duration:
                self.image.fill('white')
                self.is_dashing = False
                self.last_dash_time = current_time
        elif not self.can_dash:
            if current_time - self.last_dash_time >= self.dash_cooldown:
                self.can_dash = True

        if not self.vulnerable:
            if current_time - self.hurt_time >= self.invincibility_duration:
                self.vulnerable = True
                self.image.fill('white')

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

    def get_damage(self, amount, origin_center):
        if self.vulnerable:
            self.health -= amount
            self.vulnerable = False
            self.hurt_time = pygame.time.get_ticks()
            self.image.fill('gray')

            my_pos = pygame.math.Vector2(self.rect.center)
            other_pos = pygame.math.Vector2(origin_center)

            diff = my_pos - other_pos

            if diff.magnitude() != 0:
                direction = diff.normalize()
            else:
                direction = pygame.math.Vector2(1, 0)
            self.knockback = direction * 20

    def reduce_knockback(self):
        if self.knockback.magnitude() != 0:
            self.knockback *= 0.8

            if self.knockback.magnitude() < 0.5:
                self.knockback = pygame.math.Vector2(0, 0)

    def update(self):
        self.reduce_knockback()
        self.input()
        self.cooldowns()

        if self.inventory['xp'] >= self.xp_to_next_level:
            self.level += 1
            self.inventory['xp'] -= self.xp_to_next_level
            
            self.xp_to_next_level = int(self.xp_to_next_level * 1.3)
            
            self.max_health += 20
            self.health = self.max_health
            self.attack_damage += 2
            print(f"LEVEL UP! {self.level} - Next level needs {self.xp_to_next_level} XP")

        if self.attacking:
            self.direction.x = 0
            self.direction.y = 0
        elif self.is_dashing:
            self.move(self.dash_speed)
        else:
            self.move(self.speed)

    def get_save_data(self):
        return {
            'level': self.level,
            'current_health': self.health,
            'max_health': self.max_health,
            'xp': self.inventory['xp'],
            'xp_to_next': self.xp_to_next_level,
            'gold': self.inventory['gold'],
            'iron': self.inventory['iron'],
            'attack_damage': self.attack_damage
        }

    def load_save_data(self, data):
        self.level = data['level']
        self.health = data['current_health']
        self.max_health = data['max_health']
        self.inventory['xp'] = data['xp']
        self.xp_to_next_level = data['xp_to_next']
        self.inventory['gold'] = data['gold']
        self.inventory['iron'] = data['iron']
        self.attack_damage = data['attack_damage']