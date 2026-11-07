import math
import os
import random
import pygame
from settings import *
from spatial import nearby_obstacles


# Sprite folder per tier (None = fallback solid color)
TIER_SPRITE_DIRS = {
    'tier1': 'orc_frames_clean',
    'tier2': 'toimp/Mushroom_frames',
    'tier3': 'toimp/Fly_frames',
    'tier4': 'toimp/Skeleton_frames',
    'tier5': 'toimp/BigGoblin_frames',
    'boss': 'toimp/BigGoblin_frames',
}

# Visual size per tier (can vary)
TIER_VISUAL_SIZES = {
    'tier1': (320, 320),
    'tier2': (225, 225),
    'tier3': (225, 225),
    'tier4': (225, 225),
    'tier5': (225, 225),
    'boss': (600, 600),
}

TIER_NAMES = {
    'tier1': "Orc", 'tier2': "Champignon", 'tier3': "Mouche", 'tier4': "Squelette",
    'tier5': "Gobelin", 'boss': "Gardien",
}

# Default / Fallback size
DEFAULT_VISUAL_SIZE = (TILE_SIZE, TILE_SIZE)


class Enemy(pygame.sprite.Sprite):
    # Class-level cache: tier -> {'idle': [...], 'walk': [...], 'atk': [...], 'ded': [...]}
    _anim_cache = {}
    _bbox_cache = {}

    def __init__(self, groups, pos, obstacles, tier):
        super().__init__(groups)

        info = MONSTER_DATA[tier]
        self.tier = tier
        self.health = info['health']
        self.max_health = info['health']
        self.speed = info['speed'] * 60  # pixels / seconde
        self.damage = info['damage']
        self.notice_radius = info['notice_radius']
        self.loot_table = info['loot']
        self.base_color = info['color']
        self.elite = False
        self.tint = None
        self.name = TIER_NAMES.get(tier, "Monstre")

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

        # rect = zone visuelle, hitbox = zone physique (1 tuile)
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)

        self.is_centered = (tier != 'tier1')
        self.is_flying = (tier == 'tier3')
        self._sync_rect_from_hitbox(initial=True)

        self.vulnerable = True
        self.hit_time = 0
        self._is_flashing = False
        self.invuln_ms = 400

        self.pos = pygame.math.Vector2(self.hitbox.topleft)
        self.direction = pygame.math.Vector2()
        self.obstacle_sprites = obstacles
        self.start_time = 0
        self.duration = 0
        self.knockback = pygame.math.Vector2(0, 0)
        self.knockback_resist = 0.0

        # --- IA solo (attaques télégraphiées) ---
        windup, reach = ENEMY_ATTACK_PROFILE.get(tier, (450, 75))
        self.windup_ms = windup
        self.attack_reach = reach
        self.ai_state = 'chase'
        self.ai_timer = 0.0
        self.attack_cd = random.uniform(0.2, 0.8)
        self.ranged = (tier == 'tier3')
        self.charger = (tier == 'tier5')          # les gobelins chargent
        self.shielded = (tier == 'tier4')         # les squelettes parent
        self.charge_cd = random.uniform(2.0, 4.0)
        self.charge_dir = pygame.math.Vector2(1, 0)
        self.charge_hit = False
        self.awake = False
        self.content_box = Enemy._bbox_cache.get(tier)

    # ------------------------------------------------------------------
    # Élites
    # ------------------------------------------------------------------
    def make_elite(self):
        self.elite = True
        self.health = self.max_health = int(self.max_health * 2.6)
        self.damage = int(self.damage * 1.3)
        self.speed *= 1.12
        self.loot_table = {k: (lo * 2 + 1, hi * 3 + 1) for k, (lo, hi) in self.loot_table.items()}
        self.tint = (70, 50, 0)
        self.name = f"{self.name} élite"
        self.knockback_resist = 0.4

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

        base = resource_path(os.path.join('assets', sprite_dir_name))
        if not os.path.isdir(base):
            cls._anim_cache[tier] = anims
            return anims

        # 1. Fichiers directement dans le dossier (préfixes)
        prefix_map = {'idle': 'idle_', 'walk': 'walk_', 'atk': 'atk_', 'ded': 'ded'}
        for key, prefix in prefix_map.items():
            files = sorted([
                f for f in os.listdir(base)
                if os.path.isfile(os.path.join(base, f)) and f.lower().startswith(prefix.lower()) and f.lower().endswith('.png')
            ])
            for fname in files:
                try:
                    img = pygame.image.load(os.path.join(base, fname)).convert_alpha()
                    anims[key].append(pygame.transform.scale(img, visual_size))
                except Exception as e:
                    print(f"[Enemy] Could not load {fname}: {e}")

        # 2. Sous-dossiers (assets toimp)
        folder_keywords = {
            'idle': ['idle', 'flight'],
            'walk': ['walk', 'run', 'flight', 'shield'],
            'atk': ['attack', 'atk'],
            'ded': ['death', 'ded']
        }
        subdirs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
        for d in subdirs:
            d_lower = d.lower()
            target_keys = [k for k, kws in folder_keywords.items() if any(kw in d_lower for kw in kws)]
            if target_keys:
                d_path = os.path.join(base, d)
                files = sorted([f for f in os.listdir(d_path) if f.lower().endswith('.png')])
                loaded_imgs = []
                for fname in files:
                    try:
                        img = pygame.image.load(os.path.join(d_path, fname)).convert_alpha()
                        loaded_imgs.append(pygame.transform.scale(img, visual_size))
                    except Exception as e:
                        print(f"[Enemy] Could not load {fname}: {e}")
                for k in target_keys:
                    if len(anims[k]) == 0:
                        anims[k].extend(loaded_imgs)

        # 3. Animations manquantes
        if not anims['walk'] and anims['idle']:
            anims['walk'] = anims['idle'].copy()
        if not anims['idle'] and anims['walk']:
            anims['idle'] = anims['walk'].copy()

        if anims['idle']:
            cls._bbox_cache[tier] = anims['idle'][0].get_bounding_rect()
        cls._anim_cache[tier] = anims
        return anims

    # ------------------------------------------------------------------
    def _sync_rect_from_hitbox(self, initial=False):
        if self.is_centered:
            if self.is_flying:
                if initial:
                    self.hitbox.midbottom = self.rect.midbottom
                else:
                    self.rect.midbottom = self.hitbox.midbottom
            else:
                if initial:
                    self.hitbox.center = self.rect.center
                else:
                    self.rect.center = self.hitbox.center
        else:
            if initial:
                self.hitbox.midbottom = self.rect.midbottom
            else:
                self.rect.midbottom = self.hitbox.midbottom

    def head_pos(self):
        """Position (monde) du sommet visible du sprite — pour barre de vie / étiquettes."""
        box = self.content_box or Enemy._bbox_cache.get(self.tier)
        if box:
            return self.rect.x + box.centerx, self.rect.y + box.top
        return self.hitbox.centerx, self.hitbox.top - 10

    def body_center(self):
        box = self.content_box or Enemy._bbox_cache.get(self.tier)
        if box:
            return self.rect.x + box.centerx, self.rect.y + box.centery
        return self.hitbox.center

    # ------------------------------------------------------------------
    # Animation update
    # ------------------------------------------------------------------
    def _update_status(self, chasing: bool, is_attacking: bool = False):
        old = self.status
        if self.health <= 0:
            self.status = 'ded'
        elif is_attacking:
            self.status = 'atk'
        elif chasing or self.direction.magnitude() > 0:
            self.status = 'walk'
        else:
            self.status = 'idle'
        if self.status != old:
            self.frame_index = 0.0

    def _animate(self, dt=0.016):
        if not self.has_sprites:
            return
        anim = self.animations.get(self.status) or self.animations['idle']
        if not anim:
            return

        if self.status == 'atk' and self.ai_state in ('windup', 'recover'):
            # synchronise l'animation avec l'attaque : frappe au milieu de l'anim
            total = self.windup_ms / 1000 + 0.35
            elapsed = (self.windup_ms / 1000 - self.ai_timer) if self.ai_state == 'windup' else (self.windup_ms / 1000 + 0.35 - self.ai_timer)
            self.frame_index = max(0.0, min(len(anim) - 1, elapsed / total * len(anim)))
        else:
            speed = 0.06 if self.status == 'ded' else self.animation_speed
            self.frame_index += speed * dt * 60
            if self.frame_index >= len(anim):
                self.frame_index = len(anim) - 1 if self.status == 'ded' else 0.0

        frame = anim[int(self.frame_index) % len(anim)]
        if self.tint:
            from fx import tint_surface
            frame = tint_surface(frame, self.tint)
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        if self._is_flashing:
            frame = frame.copy()
            frame.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif self.ai_state == 'windup':
            # l'ennemi rougeoie avant de frapper (signal d'esquive)
            k = 1 - max(0.0, self.ai_timer) / (self.windup_ms / 1000)
            frame = frame.copy()
            frame.fill((int(140 * k), 0, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        self.image = frame

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------
    def get_damage(self, player_center, amount):
        """Retourne True si le coup a porté."""
        if self.vulnerable and self.health > 0:
            self.health -= amount
            self.vulnerable = False
            self.hit_time = pygame.time.get_ticks()
            self._is_flashing = True

            if not self.has_sprites:
                self.image.fill('white')

            diff = pygame.math.Vector2(self.hitbox.center) - pygame.math.Vector2(player_center)
            power = 900 * (1 - self.knockback_resist)
            self.knockback = diff.normalize() * power if diff.magnitude() != 0 else pygame.math.Vector2(0, 0)
            # un coup interrompt l'armement d'une attaque (sauf élites / boss)
            if self.ai_state in ('windup', 'charge_windup') and self.knockback_resist < 0.3:
                self.ai_state = 'recover'
                self.ai_timer = 0.3
            return True
        return False

    def try_block(self, attacker_center, attack_kind):
        """Squelette : pare les coups venant de face (le coup final brise la garde)."""
        if not self.shielded or attack_kind in ('finisher', 'spin') or self.ai_state != 'chase':
            return False
        facing_attacker = (attacker_center[0] >= self.hitbox.centerx) == self.facing_right
        return facing_attacker and random.random() < 0.4

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
        for sprite in nearby_obstacles(self.obstacle_sprites, self.hitbox):
            if sprite.rect.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if speed > 0: self.hitbox.right = sprite.rect.left
                    elif speed < 0: self.hitbox.left = sprite.rect.right
                    self.pos.x = self.hitbox.x
                else:
                    if speed > 0: self.hitbox.bottom = sprite.rect.top
                    elif speed < 0: self.hitbox.top = sprite.rect.bottom
                    self.pos.y = self.hitbox.y

    def enemy_update(self, player, dt, is_attacking: bool = False, speed=None):
        """IA historique (utilisée par l'hôte multijoueur)."""
        enemy_vect = pygame.math.Vector2(self.hitbox.center)
        player_vect = pygame.math.Vector2(player.rect.center)
        diff = player_vect - enemy_vect
        distance = diff.magnitude()

        chasing = distance < self.notice_radius and distance > 0
        if chasing:
            self.direction = diff.normalize()
            self.facing_right = diff.x >= 0
        else:
            self.patrol()

        self._update_status(chasing, is_attacking)
        move_speed = speed if speed is not None else self.speed
        self.move(move_speed, dt)

    def solo_update(self, player, dt):
        """IA solo : poursuite, attaque armée (esquivable), tir à distance.
        Retourne un évènement : None, ('strike', dégâts) ou ('shoot', direction)."""
        event = None
        my = pygame.math.Vector2(self.hitbox.center)
        target = pygame.math.Vector2(player.hitbox.center)
        diff = target - my
        dist = diff.length()
        self.attack_cd -= dt

        if not self.awake:
            if dist < self.notice_radius:
                self.awake = True
                event = ('notice',)
            else:
                self.patrol()
                self._update_status(False)
                self.move(self.speed * 0.5, dt)
                return None

        if player.health <= 0:
            self.direction = pygame.math.Vector2()
            self.ai_state = 'chase'
            self._update_status(False)
            self.move(0, dt)
            return None

        self.charge_cd -= dt
        if self.ai_state == 'chase' and self.charger and self.charge_cd <= 0 and 160 < dist < 420:
            from fx import fx, Telegraph
            self.ai_state = 'charge_windup'
            self.ai_timer = 0.6
            self.charge_dir = diff.normalize()
            end = my + self.charge_dir * 430
            fx.telegraphs.append(Telegraph('line', my.x, my.y, 0.6, end=(end.x, end.y), width=52))
            event = ('telegraph',)

        if self.ai_state == 'charge_windup':
            self.direction = pygame.math.Vector2()
            self.facing_right = self.charge_dir.x >= 0
            self.ai_timer -= dt
            self._update_status(False, True)
            self.move(0, dt)
            if self.ai_timer <= 0:
                self.ai_state = 'charging'
                self.ai_timer = 0.42
                self.charge_hit = False
            return event
        if self.ai_state == 'charging':
            self.direction = self.charge_dir
            self.ai_timer -= dt
            self._update_status(True)
            self.move(self.speed * 4.2, dt)
            if not self.charge_hit and self.hitbox.inflate(10, 10).colliderect(player.hitbox):
                self.charge_hit = True
                event = ('strike', int(self.damage * 1.3))
            if self.ai_timer <= 0:
                self.ai_state = 'recover'
                self.ai_timer = 0.6
                self.charge_cd = random.uniform(3.5, 5.5)
            return event

        if self.ai_state == 'chase':
            if dist > 0:
                self.facing_right = diff.x >= 0
            if self.ranged:
                # garde ses distances et tire
                if dist > self.attack_reach * 1.1:
                    self.direction = diff.normalize() if dist else pygame.math.Vector2()
                elif dist < self.attack_reach * 0.6:
                    self.direction = -diff.normalize() if dist else pygame.math.Vector2()
                else:
                    self.direction = pygame.math.Vector2(-diff.y, diff.x).normalize() * 0.6 if dist else pygame.math.Vector2()
                if dist < self.attack_reach * 1.3 and self.attack_cd <= 0:
                    self.ai_state = 'windup'
                    self.ai_timer = self.windup_ms / 1000
            else:
                self.direction = diff.normalize() if dist > 0 else pygame.math.Vector2()
                if dist < self.attack_reach and self.attack_cd <= 0:
                    self.ai_state = 'windup'
                    self.ai_timer = self.windup_ms / 1000
            move_speed = self.speed if self.vulnerable else self.speed * 0.3
            self._update_status(True, self.ai_state == 'windup')
            self.move(move_speed, dt)

        elif self.ai_state == 'windup':
            self.direction = pygame.math.Vector2()
            self.ai_timer -= dt
            self._update_status(True, True)
            self.move(0, dt)
            if self.ai_timer <= 0:
                self.ai_state = 'recover'
                self.ai_timer = 0.35
                if self.ranged:
                    event = ('shoot', diff.normalize() if dist else pygame.math.Vector2(1, 0))
                    self.attack_cd = random.uniform(1.6, 2.4)
                else:
                    # petite ruée vers l'avant au moment de frapper
                    if dist > 0:
                        self.knockback = diff.normalize() * 380
                    if dist < self.attack_reach + 28:
                        event = ('strike', self.damage)
                    self.attack_cd = random.uniform(0.7, 1.2)

        elif self.ai_state == 'recover':
            self.ai_timer -= dt
            self._update_status(True, True)
            self.direction = pygame.math.Vector2()
            self.move(0, dt)
            if self.ai_timer <= 0:
                self.ai_state = 'chase'
        return event

    def reduce_knockback(self, dt):
        self.knockback *= (0.8 ** (dt * 60))
        if self.knockback.magnitude() < 10:
            self.knockback = pygame.math.Vector2(0, 0)

    def move(self, speed, dt):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        total_x = (self.direction.x * speed + self.knockback.x) * dt
        total_y = (self.direction.y * speed + self.knockback.y) * dt
        # Sous-pas : jamais plus de 16 px par pas, pour ne pas traverser un mur
        steps = max(1, int(max(abs(total_x), abs(total_y)) // 16) + 1)
        sx, sy = total_x / steps, total_y / steps
        for _ in range(steps):
            self.pos.x += sx
            self.hitbox.x = int(self.pos.x)
            self.collision('horizontal', sx)
            self.pos.y += sy
            self.hitbox.y = int(self.pos.y)
            self.collision('vertical', sy)

        self._sync_rect_from_hitbox()

    def update(self, dt=0.016):
        if dt <= 0:
            return
        self.reduce_knockback(dt)
        if not self.vulnerable:
            if pygame.time.get_ticks() - self.hit_time >= self.invuln_ms:
                self._is_flashing = False
                if not self.has_sprites:
                    self.image.fill(self.base_color)
                self.vulnerable = True
        self._animate(dt)
