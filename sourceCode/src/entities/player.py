import math
import os
import random
import pygame
from settings import *
from weapon import Weapon
from spatial import nearby_obstacles


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
        self.speed = 300  # Pixels par seconde
        self.obstacle_sprites = obstacles

        # --- Attaque & combo ---
        self.attacking = False
        self.attack_cooldown = 340
        self.attack_time = 0
        self.current_weapon = None
        self.attack_kind = 'atk'        # 'atk' | 'finisher' | 'spin'
        self.combo_step = 0
        self.last_attack_end = -10000
        self.aim = pygame.math.Vector2(1, 0)
        self.queued_attack = False
        self.screen_center = (WIDTH // 2, HEIGHT // 2)  # mis à jour par la caméra
        self.last_spin_time = -100000

        # --- Esquive ---
        self.is_dashing = False
        self.dash_speed = 900
        self.dash_duration = 200
        self.dash_start_time = 0
        self.can_dash = True
        self.dash_cooldown = 1500
        self.last_dash_time = 0
        self._afterimage_t = 0
        self.dash_dir = pygame.math.Vector2(1, 0)

        # --- Dégâts reçus ---
        self.vulnerable = True
        self.hurt_time = 0
        self.invincibility_duration = 500
        self.knockback = pygame.math.Vector2(0, 0)
        self.is_remote = False  # True for network-controlled clones

        # --- Progression ---
        self.level = 1
        self.max_health = 50
        self.health = self.max_health
        self.xp_to_next_level = 100
        self.attack_damage = 5
        self.artifacts = 0
        self.inventory = {'gold': 0, 'iron': 0, 'xp': 0}
        self.potions = 1
        self.perks = {}
        self.pending_perks = 0
        self.phoenix_used = False
        self.stats = {'kills': 0, 'deaths': 0, 'bosses': 0, 'expeditions': 0, 'chests': 0, 'best_combo': 0}
        self.upgrades = {'armor': 0, 'sharp': 0}   # améliorations de la forge
        self.buffs = {}                            # bénédictions d'autel : nom -> fin (ms)
        self.poisoned_until = 0

        # Évènements consommés par le jeu (effets, sons...)
        self.events = []

    # ------------------------------------------------------------------
    # Statistiques dérivées des bénédictions
    # ------------------------------------------------------------------
    def perk(self, pid):
        return self.perks.get(pid, 0)

    def has_buff(self, name):
        return pygame.time.get_ticks() < self.buffs.get(name, 0)

    def add_buff(self, name, seconds):
        self.buffs[name] = pygame.time.get_ticks() + int(seconds * 1000)

    def buff_remaining(self, name):
        return max(0.0, (self.buffs.get(name, 0) - pygame.time.get_ticks()) / 1000)

    @property
    def poisoned(self):
        return pygame.time.get_ticks() < self.poisoned_until

    def apply_poison(self, seconds=3.0):
        if self.is_dashing or self.health <= 0:
            return
        self.poisoned_until = max(self.poisoned_until, pygame.time.get_ticks() + int(seconds * 1000))

    @property
    def armor_ratio(self):
        return min(0.6, 0.08 * self.upgrades.get('armor', 0))

    @property
    def damage_mult(self):
        return (1 + 0.15 * self.perk('force')) * (1.5 if self.has_buff('rage') else 1)

    @property
    def crit_chance(self):
        return CRIT_BASE_CHANCE + 0.08 * self.perk('crit') + 0.05 * self.upgrades.get('sharp', 0)

    @property
    def speed_mult(self):
        return (1 + 0.08 * self.perk('swift')) * (1.3 if self.has_buff('haste') else 1)

    @property
    def effective_dash_cooldown(self):
        return self.dash_cooldown * (0.85 ** self.perk('shadow'))

    @property
    def spin_cooldown(self):
        return SPIN_COOLDOWN * (0.85 ** self.perk('whirl'))

    @property
    def magnet_radius(self):
        return MAGNET_BASE_RADIUS + 70 * self.perk('magnet')

    def spin_ready_ratio(self):
        return min(1.0, (pygame.time.get_ticks() - self.last_spin_time) / self.spin_cooldown)

    def dash_ready_ratio(self):
        if self.can_dash:
            return 1.0
        if self.is_dashing:
            return 0.0
        return min(1.0, (pygame.time.get_ticks() - self.last_dash_time) / self.effective_dash_cooldown)

    def roll_damage(self):
        """Dégâts du coup en cours : (montant, critique ?)."""
        base = self.attack_damage * self.damage_mult
        if self.attack_kind == 'finisher':
            base *= 1.6 + 0.4 * self.perk('fury')
        elif self.attack_kind == 'spin':
            base *= 1.3 * (1 + 0.25 * self.perk('whirl'))
        base *= random.uniform(0.9, 1.1)
        crit = random.random() < self.crit_chance
        if crit:
            base *= 2.0
        return max(1, int(round(base))), crit

    # ------------------------------------------------------------------
    def import_player_assets(self):
        self.animations = {'idle': [], 'walk': [], 'atk': [], 'ded': [], 'slash': []}
        mc_path = resource_path(os.path.join('assets', 'mc_frames'))

        def fallback():
            surf = pygame.Surface((108, 96), pygame.SRCALPHA)
            surf.fill('white')
            return [surf]

        if os.path.exists(mc_path):
            for animation in self.animations.keys():
                frames = []
                files = [f for f in os.listdir(mc_path) if f.startswith(animation) and f.endswith('.png')]
                files.sort()
                for f in files:
                    try:
                        img = pygame.image.load(os.path.join(mc_path, f)).convert_alpha()
                        # Les images brutes font 100x100, le personnage occupe le bas
                        crop_rect = (32, 68, 36, 32)
                        cropped = pygame.Surface((36, 32), pygame.SRCALPHA)
                        cropped.blit(img, (0, 0), crop_rect)
                        frames.append(pygame.transform.scale(cropped, (108, 96)))
                    except Exception:
                        pass
                self.animations[animation] = frames if frames else fallback()
        else:
            for animation in self.animations.keys():
                self.animations[animation] = fallback()
        if not self.animations['slash']:
            self.animations['slash'] = self.animations['atk']

    # ------------------------------------------------------------------
    def get_status(self):
        old_status = self.status
        if self.health <= 0:
            self.status = 'ded'
        elif self.attacking:
            self.status = 'slash' if self.attack_kind in ('finisher', 'spin') else 'atk'
        elif self.direction.magnitude() == 0:
            self.status = 'idle'
        else:
            self.status = 'walk'

        if self.status != old_status and self.status in ['atk', 'ded', 'slash']:
            self.frame_index = 0

    def animate(self):
        animation = self.animations.get(self.status) or self.animations['idle']

        if self.status in ('atk', 'slash') and len(animation) > 1:
            # Animation basée sur le temps réel : toutes les frames sont jouées pendant le coup
            elapsed = pygame.time.get_ticks() - self.attack_time
            progress = min(elapsed / max(1, self.attack_cooldown), 1.0)
            self.frame_index = progress * (len(animation) - 1)
        elif self.status == 'ded':
            self.frame_index += 0.07
            if self.frame_index >= len(animation):
                self.frame_index = len(animation) - 1
                self._death_anim_done = True
        else:
            self.frame_index += self.animation_speed
            if self.frame_index >= len(animation):
                self.frame_index = 0

        image = animation[int(self.frame_index) % len(animation)]
        self.image = pygame.transform.flip(image, True, False) if not self.facing_right else image

        if not self.vulnerable and not self.is_dashing:
            self.image.set_alpha(self.wave_value())
        else:
            self.image.set_alpha(255)

    def wave_value(self):
        value = pygame.time.get_ticks() % 200
        return 255 if value < 100 else 110

    # ------------------------------------------------------------------
    # Attaques
    # ------------------------------------------------------------------
    def _aim_vector(self):
        mouse_vect = pygame.math.Vector2(pygame.mouse.get_pos())
        aim = mouse_vect - pygame.math.Vector2(self.screen_center)
        if aim.magnitude() != 0:
            return aim.normalize()
        return pygame.math.Vector2(1 if self.facing_right else -1, 0)

    def attack(self):
        now = pygame.time.get_ticks()
        if now - self.last_attack_end <= COMBO_WINDOW and self.combo_step < 2:
            self.combo_step += 1
        else:
            self.combo_step = 0
        self.attack_kind = 'finisher' if self.combo_step == 2 else 'atk'
        self.attack_cooldown = 470 if self.attack_kind == 'finisher' else 330

        self.attacking = True
        self.attack_time = now
        self.aim = self._aim_vector()
        if self.aim.x != 0:
            self.facing_right = self.aim.x > 0

        if self.attack_kind == 'finisher':
            self.current_weapon = Weapon(self, self.groups(), self.aim, size=(150, 110), distance=58)
        else:
            self.current_weapon = Weapon(self, self.groups(), self.aim, size=(120, 84), distance=50)
        self.events.append(('swing', self.attack_kind, self.aim, self.combo_step))

    def spin_attack(self):
        now = pygame.time.get_ticks()
        if now - self.last_spin_time < self.spin_cooldown:
            return False
        self.last_spin_time = now
        self.attack_kind = 'spin'
        self.attack_cooldown = 420
        self.attacking = True
        self.attack_time = now
        self.combo_step = 0
        self.aim = self._aim_vector()
        self.current_weapon = Weapon(self, self.groups(), pygame.math.Vector2(0, 0), size=(230, 210), distance=0)
        self.events.append(('spin',))
        return True

    def drink_potion(self):
        if self.potions <= 0 or self.health <= 0:
            self.events.append(('potion_fail',))
            return False
        if self.health >= self.max_health:
            self.events.append(('potion_full',))
            return False
        self.potions -= 1
        heal = int(self.max_health * POTION_HEAL_RATIO)
        self.health = min(self.max_health, self.health + heal)
        self.events.append(('potion', heal))
        return True

    def single_input(self, event):
        if self.health <= 0:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and not self.is_dashing:
                if not self.attacking:
                    self.attack()
                else:
                    self.queued_attack = True  # enchaîne dès la fin du coup
            elif event.button == 3 and not self.is_dashing and not self.attacking:
                if not self.spin_attack():
                    self.events.append(('spin_fail',))

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.can_dash and not self.is_dashing:
                self.start_dash()
            elif event.key in (pygame.K_r, pygame.K_f):
                self.drink_potion()
            elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT) and not self.attacking and not self.is_dashing:
                if not self.spin_attack():
                    self.events.append(('spin_fail',))

    def input(self):
        if not self.attacking:
            keys = pygame.key.get_pressed()
            up = keys[pygame.K_z] or keys[pygame.K_w] or keys[pygame.K_UP]
            down = keys[pygame.K_s] or keys[pygame.K_DOWN]
            left = keys[pygame.K_q] or keys[pygame.K_a] or keys[pygame.K_LEFT]
            right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            self.direction.y = -1 if up else (1 if down else 0)
            self.direction.x = -1 if left else (1 if right else 0)

        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
            if not self.attacking:
                if self.direction.x > 0:
                    self.facing_right = True
                elif self.direction.x < 0:
                    self.facing_right = False

    def start_dash(self):
        if self.attacking:
            # l'esquive annule la fin d'un coup (animation-cancel)
            self.end_attack()
        self.is_dashing = True
        self.can_dash = False
        self.dash_start_time = pygame.time.get_ticks()
        if self.direction.magnitude() == 0:
            self.dash_dir = pygame.math.Vector2(1 if self.facing_right else -1, 0)
        else:
            self.dash_dir = self.direction.normalize()
        self.events.append(('dash',))

    def end_attack(self):
        self.attacking = False
        self.last_attack_end = pygame.time.get_ticks()
        if self.current_weapon:
            self.current_weapon.kill()
            self.current_weapon = None

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if self.attacking:
            if current_time - self.attack_time >= self.attack_cooldown:
                was_finisher = self.attack_kind == 'finisher'
                self.end_attack()
                if was_finisher:
                    self.combo_step = -1  # après le coup final, le combo repart de zéro
                if self.queued_attack and self.health > 0:
                    self.queued_attack = False
                    self.attack()

        if self.is_dashing:
            if current_time - self.dash_start_time >= self.dash_duration:
                self.is_dashing = False
                self.last_dash_time = current_time
        elif not self.can_dash:
            if current_time - self.last_dash_time >= self.effective_dash_cooldown:
                self.can_dash = True
                self.events.append(('dash_ready',))

        if not self.vulnerable:
            if current_time - self.hurt_time >= self.invincibility_duration:
                self.vulnerable = True

    # ------------------------------------------------------------------
    # Physique
    # ------------------------------------------------------------------
    def collision(self, direction, speed):
        for sprite in nearby_obstacles(self.obstacle_sprites, self.hitbox):
            if sprite.rect.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if speed > 0:
                        self.hitbox.right = sprite.rect.left
                    elif speed < 0:
                        self.hitbox.left = sprite.rect.right
                    self.pos.x = self.hitbox.x
                else:
                    if speed > 0:
                        self.hitbox.bottom = sprite.rect.top
                    elif speed < 0:
                        self.hitbox.top = sprite.rect.bottom
                    self.pos.y = self.hitbox.y

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

        self.rect.midbottom = self.hitbox.midbottom

    def get_damage(self, amount, origin_center):
        """Applique des dégâts. Retourne le montant réellement subi (0 si esquivé)."""
        if not self.vulnerable or self.health <= 0 or self.is_dashing:
            return 0
        amount = max(1, int(round(amount * (1 - self.armor_ratio))))
        if self.health - amount <= 0 and self.perk('phoenix') and not self.phoenix_used:
            self.phoenix_used = True
            self.health = max(1, int(self.max_health * 0.4))
            self.events.append(('phoenix',))
        else:
            self.health -= amount
        self.vulnerable = False
        self.hurt_time = pygame.time.get_ticks()
        self.invincibility_duration = 600

        diff = pygame.math.Vector2(self.rect.center) - pygame.math.Vector2(origin_center)
        direction = diff.normalize() if diff.magnitude() != 0 else pygame.math.Vector2(1, 0)
        self.knockback = direction * 1100
        self.events.append(('hurt', amount, direction))
        return amount

    def reduce_knockback(self, dt):
        if self.knockback.magnitude() != 0:
            self.knockback *= (0.8 ** (dt * 60))
            if self.knockback.magnitude() < 10:
                self.knockback = pygame.math.Vector2(0, 0)

    def gain_level_if_needed(self):
        while self.inventory['xp'] >= self.xp_to_next_level:
            self.level += 1
            self.inventory['xp'] -= self.xp_to_next_level
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            self.max_health += 5
            self.health = self.max_health
            self.attack_damage += 1
            self.pending_perks += 1
            self.events.append(('levelup', self.level))

    def update(self, dt=0.016):
        # Les clones réseau ne font que s'animer — le mouvement vient du serveur
        if self.is_remote:
            self.animate()
            self.rect.midbottom = self.hitbox.midbottom
            return

        if dt <= 0:  # hit-stop : le monde est figé
            return

        self.reduce_knockback(dt)
        if self.health > 0:
            self.input()
        self.cooldowns()
        self.gain_level_if_needed()

        if self.health <= 0:
            self.direction.x = 0
            self.direction.y = 0
        elif self.is_dashing:
            self.direction = pygame.math.Vector2(self.dash_dir)
            self.move(self.dash_speed, dt)
            self._afterimage_t += dt
            if self._afterimage_t > 0.025:
                self._afterimage_t = 0
                self.events.append(('afterimage',))
        elif self.attacking:
            # léger pas en avant pendant le coup (sensation d'impact)
            lunge = 160 if self.attack_kind == 'finisher' else (60 if self.attack_kind == 'atk' else 0)
            elapsed = pygame.time.get_ticks() - self.attack_time
            self.direction = self.aim if elapsed < 120 and lunge else pygame.math.Vector2()
            self.move(lunge, dt)
            self.direction = pygame.math.Vector2()
        else:
            self.move(self.speed * self.speed_mult, dt)

        self.get_status()
        self.animate()

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def get_save_data(self):
        return {
            'level': self.level,
            'current_health': self.health,
            'max_health': self.max_health,
            'xp': self.inventory['xp'],
            'xp_to_next': self.xp_to_next_level,
            'gold': self.inventory['gold'],
            'iron': self.inventory['iron'],
            'attack_damage': self.attack_damage,
            'artifacts': self.artifacts,
            'potions': self.potions,
            'perks': self.perks,
            'pending_perks': self.pending_perks,
            'stats': self.stats,
            'upgrades': self.upgrades,
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
        self.artifacts = data.get('artifacts', 0)
        self.potions = data.get('potions', 1)
        self.perks = dict(data.get('perks', {}))
        self.pending_perks = data.get('pending_perks', 0)
        self.stats.update(data.get('stats', {}))
        self.upgrades.update(data.get('upgrades', {}))
