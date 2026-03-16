import pygame
import os
from settings import *
from weapon import Weapon
import sys


class Player(pygame.sprite.Sprite):
    _animations_cache = None

    def __init__(self, pos, groups, obstacles):
        super().__init__(groups)
        
        # Animations
        if Player._animations_cache:
            self.animations = Player._animations_cache
        else:
            self.import_player_assets()
            Player._animations_cache = self.animations
            
        self.status = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15
        self.facing_right = True
        
        if self.animations[self.status]:
            self.image = self.animations[self.status][self.frame_index]
        else:
            self.image = pygame.surface.Surface((108, 96))
            self.image.fill('white')
            
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = pygame.Rect(0, 0, 50, 40)
        self.hitbox.midbottom = self.rect.midbottom
        self.pos = pygame.math.Vector2(self.hitbox.topleft)
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = 300 # Pixels per second (auparavant 5 pixels/frame à 60fps)
        self.obstacle_sprites = obstacles
        # Attack setup
        self.attacking = False
        self.attack_cooldown = 450
        self.attack_time = 0
        self.current_weapon = None
        self.is_dashing = False
        self.dash_speed = 900 # Pixels per second (auparavant 15 px/f)
        self.dash_duration = 200
        self.dash_start_time = 0
        self.can_dash = True
        self.dash_cooldown = 1500
        self.last_dash_time = 0
        self.vulnerable = True
        self.hurt_time = 0
        self.invincibility_duration = 500
        self.knockback = pygame.math.Vector2(0, 0)
        self.is_remote = False  # True for network-controlled clones

        self.level = 1
        self.max_health = 50
        self.health = self.max_health
        
        self.xp_to_next_level = 100 
        
        self.attack_damage = 5
        self.inventory = {'gold': 0, 'iron': 0, 'xp': 0}

    def import_player_assets(self):
        self.animations = {'idle': [], 'walk': [], 'atk': [], 'ded': []}
        mc_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'mc_frames')
        
        if os.path.exists(mc_path):
            for animation in self.animations.keys():
                frames = []
                
                # Only use correctly named frames for the animation state
                files = [f for f in os.listdir(mc_path) if f.startswith(animation) and f.endswith('.png')]
                files.sort()
                for f in files:
                    try:
                        img = pygame.image.load(os.path.join(mc_path, f)).convert_alpha()
                        
                        # Crop empty space: raw images are 100x100 with content roughly from (33, 77) to (67, 100)
                        crop_rect = (32, 68, 36, 32)
                        cropped = pygame.Surface((36, 32), pygame.SRCALPHA)
                        cropped.blit(img, (0, 0), crop_rect)
                        
                        # Scale the cropped image 3x to get a 108x96 sized sprite
                        scaled_size = (108, 96)
                        img = pygame.transform.scale(cropped, scaled_size)
                        frames.append(img)
                    except Exception as e:
                        pass
                if frames:
                    self.animations[animation] = frames
                else:
                    # Fallback single frame surface
                    scaled_size = (108, 96)
                    surf = pygame.Surface(scaled_size, pygame.SRCALPHA)
                    surf.fill('white')
                    self.animations[animation] = [surf]
        else:
            for animation in self.animations.keys():
                scaled_size = (108, 96)
                surf = pygame.Surface(scaled_size, pygame.SRCALPHA)
                surf.fill('white')
                self.animations[animation] = [surf]

    def get_status(self):
        old_status = self.status
        
        if self.health <= 0:
            self.status = 'ded'
        elif self.attacking:
            self.status = 'atk'
        elif self.direction.magnitude() == 0:
            self.status = 'idle'
        else:
            self.status = 'walk'
            
        if self.status != old_status:
            # Only reset frame index forcibly for critical animations
            if self.status in ['atk', 'ded']:
                self.frame_index = 0

    def animate(self):
        animation = self.animations[self.status]

        # Use a slower speed for death animation so it feels dramatic
        speed = 0.07 if self.status == 'ded' else self.animation_speed
        self.frame_index += speed
        if self.frame_index >= len(animation):
            if self.status in ['atk', 'ded']:
                # Hold last frame — mark death anim complete
                self.frame_index = len(animation) - 1
                if self.status == 'ded':
                    self._death_anim_done = True
            else:
                self.frame_index = 0

        # Set image
        if animation:
            image = animation[int(self.frame_index)]
            if not self.facing_right:
                self.image = pygame.transform.flip(image, True, False)
            else:
                self.image = image
        else:
            if not getattr(self, "fallback_surface", None):
                self.fallback_surface = pygame.Surface((108, 96))
                self.fallback_surface.fill('red') # Red so it's obvious a sprite is missing
            self.image = self.fallback_surface
            
        if not self.vulnerable:
            # Flicker effect when invulnerable
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def wave_value(self):
        value = pygame.time.get_ticks() % 500
        return 255 if value < 250 else 100

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
            if self.direction.x > 0:
                self.facing_right = True
            elif self.direction.x < 0:
                self.facing_right = False

    def start_dash(self):
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
                self.is_dashing = False
                self.last_dash_time = current_time
        elif not self.can_dash:
            if current_time - self.last_dash_time >= self.dash_cooldown:
                self.can_dash = True

        if not self.vulnerable:
            if current_time - self.hurt_time >= self.invincibility_duration:
                self.vulnerable = True
                # self.image.set_alpha(255) is already handled gracefully in animate()

    def collision(self, direction, speed):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.hitbox):
                    if speed > 0:
                        self.hitbox.right = sprite.rect.left
                        self.pos.x = self.hitbox.x
                    if speed < 0:
                        self.hitbox.left = sprite.rect.right
                        self.pos.x = self.hitbox.x
                        
        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.hitbox):
                    if speed > 0:
                        self.hitbox.bottom = sprite.rect.top
                        self.pos.y = self.hitbox.y
                    if speed < 0:
                        self.hitbox.top = sprite.rect.bottom
                        self.pos.y = self.hitbox.y

    def move(self, speed, dt):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        # Scale speed by delta time
        dx = (self.direction.x * speed + self.knockback.x) * dt
        self.pos.x += dx
        self.hitbox.x = int(self.pos.x)
        self.collision('horizontal', dx)

        dy = (self.direction.y * speed + self.knockback.y) * dt
        self.pos.y += dy
        self.hitbox.y = int(self.pos.y)
        self.collision('vertical', dy)
        
        # Sync the visual rect with the physical hitbox bottom to prevent downward wall overlap
        self.rect.midbottom = self.hitbox.midbottom

    def get_damage(self, amount, origin_center):
        if self.vulnerable and self.health > 0:
            self.health -= amount
            self.vulnerable = False
            self.hurt_time = pygame.time.get_ticks()

            my_pos = pygame.math.Vector2(self.rect.center)
            other_pos = pygame.math.Vector2(origin_center)
            diff = my_pos - other_pos

            if diff.magnitude() != 0:
                direction = diff.normalize()
            else:
                direction = pygame.math.Vector2(1, 0)
            self.knockback = direction * 1400 # Augmenté pour le multi

    def reduce_knockback(self, dt):
        if self.knockback.magnitude() != 0:
            # Équivalent à *= 0.8 par frame à 60 FPS
            self.knockback *= (0.8 ** (dt * 60))

            if self.knockback.magnitude() < 10:
                self.knockback = pygame.math.Vector2(0, 0)

    def update(self, dt=0.016):
        # Remote clones only animate — movement/input handled by network sync
        if self.is_remote:
            self.animate()
            self.rect.midbottom = self.hitbox.midbottom
            return
        
        self.reduce_knockback(dt)
        self.input()
        self.cooldowns()

        if self.inventory['xp'] >= self.xp_to_next_level:
            self.level += 1
            self.inventory['xp'] -= self.xp_to_next_level
            
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            
            self.max_health += 5
            self.health = self.max_health
            self.attack_damage += 1
            print(f"LEVEL UP! {self.level} - Next level needs {self.xp_to_next_level} XP")

        if self.attacking:
            self.direction.x = 0
            self.direction.y = 0
        elif self.health <= 0:
            # Dead — don't move or accept input, just animate
            self.direction.x = 0
            self.direction.y = 0
        elif self.is_dashing:
            self.move(self.dash_speed, dt)
        else:
            self.move(self.speed, dt)
            
        self.get_status()
        self.animate()

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