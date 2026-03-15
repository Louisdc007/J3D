import pygame
from settings import *
import random
import os


# Sprite folder per tier (None = fallback solid color)
TIER_SPRITE_DIRS = {
    'tier1': 'orc_frames_clean',
}

# Visual size per tier (can vary)
TIER_VISUAL_SIZES = {
    'tier1': (320, 320),
}

# Default / Fallback size
DEFAULT_VISUAL_SIZE = (TILE_SIZE, TILE_SIZE)


class Enemy(pygame.sprite.Sprite):
    # Class-level cache: tier -> {'idle': [...], 'walk': [...], 'atk': [...], 'ded': [...]}
    _anim_cache = {}

    def __init__(self, groups, pos, obstacles, tier):
        super().__init__(groups)

        info = MONSTER_DATA[tier]
        self.tier = tier
        self.health = info['health']
        self.speed = info['speed'] * 60 # Convert to pixels per second
        self.damage = info['damage']
        self.notice_radius = info['notice_radius']
        self.loot_table = info['loot']
        self.base_color = info['color']

        # --- Animation setup ---
        self.visual_size = TIER_VISUAL_SIZES.get(tier, DEFAULT_VISUAL_SIZE)
        self.animations = self._get_animations(tier)
        self.has_sprites = any(len(v) > 0 for v in self.animations.values())
        self.status = 'idle'
        self.frame_index = 0.0
        self.animation_speed = 0.12
        self.facing_right = True

        if self.has_sprites:
            self.image = self.animations['idle'][0]
        else:
            self.image = pygame.Surface(self.visual_size)
            self.image.fill(self.base_color)

        # rect is the visual boundary
        self.rect = self.image.get_rect(topleft=pos)
        # hitbox is the physical boundary (STRICTLY 64x64 / 1 tile as requested)
        from settings import TILE_SIZE
        self.hitbox = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        self.hitbox.midbottom = self.rect.midbottom

        self.vulnerable = True
        self.hit_time = 0
        self._is_flashing = False

        self.pos = pygame.math.Vector2(self.hitbox.topleft)
        self.direction = pygame.math.Vector2()
        self.obstacle_sprites = obstacles
        self.start_time = 0
        self.duration = 0
        self.knockback = pygame.math.Vector2(0, 0)

    # ------------------------------------------------------------------
    # Animation loading
    # ------------------------------------------------------------------
    @classmethod
    def _get_animations(cls, tier):
        if tier in cls._anim_cache:
            return cls._anim_cache[tier]

        anims = {'idle': [], 'walk': [], 'atk': [], 'ded': []}

        sprite_dir_name = TIER_SPRITE_DIRS.get(tier)
        visual_size = TIER_VISUAL_SIZES.get(tier, DEFAULT_VISUAL_SIZE)

        if sprite_dir_name is None:
            cls._anim_cache[tier] = anims
            return anims

        base = os.path.join(os.path.dirname(__file__), '..', 'assets', sprite_dir_name)
        if not os.path.isdir(base):
            cls._anim_cache[tier] = anims
            return anims

        # Map our anim keys to the filename prefixes in the folder
        prefix_map = {
            'idle': 'idle_',
            'walk': 'walk_',
            'atk':  'atk_',
            'ded':  'ded',
        }

        for key, prefix in prefix_map.items():
            files = sorted([
                f for f in os.listdir(base)
                if f.lower().startswith(prefix.lower()) and f.lower().endswith('.png')
            ])
            for fname in files:
                try:
                    img = pygame.image.load(os.path.join(base, fname)).convert_alpha()
                    img = pygame.transform.scale(img, visual_size)
                    anims[key].append(img)
                except Exception as e:
                    print(f"[Enemy] Could not load {fname}: {e}")

        cls._anim_cache[tier] = anims
        return anims

    # ------------------------------------------------------------------
    # Animation update
    # ------------------------------------------------------------------
    def _update_status(self, chasing: bool, is_attacking: bool = False):
        old = self.status
        if self.health <= 0:
            self.status = 'ded'
        elif is_attacking:
            self.status = 'atk'
        elif chasing:
            self.status = 'walk'
        elif self.direction.magnitude() > 0:
            self.status = 'walk'
        else:
            self.status = 'idle'
        if self.status != old:
            self.frame_index = 0.0

    def _animate(self):
        if not self.has_sprites:
            return

        anim = self.animations.get(self.status) or self.animations['idle']
        if not anim:
            return

        speed = 0.06 if self.status == 'ded' else self.animation_speed
        self.frame_index += speed

        if self.frame_index >= len(anim):
            if self.status == 'ded':
                self.frame_index = len(anim) - 1
            else:
                self.frame_index = 0.0

        frame = anim[int(self.frame_index)]
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        # White flash on hit
        if self._is_flashing:
            frame = frame.copy()
            frame.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGBA_ADD)

        self.image = frame

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------
    def get_damage(self, player_center, amount):
        if self.vulnerable:
            self.health -= amount
            self.vulnerable = False
            self.hit_time = pygame.time.get_ticks()
            self._is_flashing = True

            if not self.has_sprites:
                self.image.fill('white')

            my_pos = pygame.math.Vector2(self.hitbox.center)
            other_pos = pygame.math.Vector2(player_center)
            diff = my_pos - other_pos
            self.knockback = diff.normalize() * 900 if diff.magnitude() != 0 else pygame.math.Vector2(0, 0) # Pixels/sec (auparavant 15px/f)

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def patrol(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.start_time >= self.duration:
            self.start_time = current_time
            self.duration = random.randint(1000, 3000)
            if random.randint(1, 2) == 1:
                self.direction = pygame.math.Vector2(0, 0)
            else:
                v = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                self.direction = v.normalize() if v.magnitude() != 0 else pygame.math.Vector2(0, 0)

    def collision(self, direction, speed):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.hitbox):
                    if speed > 0: self.hitbox.right = sprite.rect.left; self.pos.x = self.hitbox.x
                    if speed < 0: self.hitbox.left = sprite.rect.right; self.pos.x = self.hitbox.x
        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.hitbox):
                    if speed > 0: self.hitbox.bottom = sprite.rect.top; self.pos.y = self.hitbox.y
                    if speed < 0: self.hitbox.top = sprite.rect.bottom; self.pos.y = self.hitbox.y

    def enemy_update(self, player, dt, is_attacking: bool = False):
        enemy_vect = pygame.math.Vector2(self.hitbox.center)
        player_vect = pygame.math.Vector2(player.rect.center)
        diff = player_vect - enemy_vect
        distance = diff.magnitude()

        chasing = distance < self.notice_radius and distance > 0
        if chasing:
            self.direction = diff.normalize()
            # Update facing direction
            self.facing_right = diff.x >= 0
        else:
            self.patrol()

        self._update_status(chasing, is_attacking)
        self.move(self.speed, dt)

    def reduce_knockback(self, dt):
        # Équivalent à *= 0.8 par frame à 60 FPS
        self.knockback *= (0.8 ** (dt * 60))
        if self.knockback.magnitude() < 10:
            self.knockback = pygame.math.Vector2(0, 0)

    def move(self, speed, dt):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        dx = (self.direction.x * speed + self.knockback.x) * dt
        self.pos.x += dx
        self.hitbox.x = int(self.pos.x)
        self.collision('horizontal', dx)

        dy = (self.direction.y * speed + self.knockback.y) * dt
        self.pos.y += dy
        self.hitbox.y = int(self.pos.y)
        self.collision('vertical', dy)

        # Sync the visual rect with the physical hitbox midbottom
        self.rect.midbottom = self.hitbox.midbottom

    # ------------------------------------------------------------------
    # Main update (called each frame by sprite group)
    # ------------------------------------------------------------------
    def update(self, dt=0.016):
        self.reduce_knockback(dt)
        if not self.vulnerable:
            if pygame.time.get_ticks() - self.hit_time >= 400:
                self._is_flashing = False
                if not self.has_sprites:
                    self.image.fill(self.base_color)
                self.vulnerable = True
        self._animate()
