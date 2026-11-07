"""Boss des donjons majeurs : Gardiens de l'Artefact et Seigneur de la Cupidité."""
import math
import random
import pygame
from settings import *
from entities.enemy import Enemy

BOSS_NAMES = [
    "Gorgath, Gardien du Rubis",
    "Morvhal, le Dévoreur",
    "Skarn, Bourreau des Cendres",
]
FINAL_NAME = "Le Seigneur de la Cupidité"


class Boss(Enemy):
    def __init__(self, groups, pos, obstacles, player_level=1, artifact_index=0):
        super().__init__(groups, pos, obstacles, 'boss')
        self.final = artifact_index >= 3
        self.name = FINAL_NAME if self.final else BOSS_NAMES[artifact_index % len(BOSS_NAMES)]
        scale = 1 + 0.18 * player_level + 0.6 * artifact_index
        if self.final:
            scale *= 1.6
        self.health = self.max_health = int(MONSTER_DATA['boss']['health'] * scale)
        self.damage = int(MONSTER_DATA['boss']['damage'] * (1 + 0.08 * player_level + 0.25 * artifact_index))
        self.hitbox = pygame.Rect(0, 0, 120, 110)
        self.hitbox.center = self.rect.center
        self.pos = pygame.math.Vector2(self.hitbox.topleft)
        self.is_centered = True
        self.is_flying = False
        self.knockback_resist = 0.92
        self.invuln_ms = 160
        self.tint = (90, 0, 40) if self.final else (60, 0, 0)
        self.awake = False
        self.phase = 1
        self.state = 'sleep'
        self.state_t = 0.0
        self.next_attack = 1.2
        self.charge_dir = pygame.math.Vector2(1, 0)
        self.volley_left = 0
        self.volley_t = 0.0
        self.spiral_angle = 0.0
        self.attack_history = []
        self.rain_spots = []
        self.dying = False
        self.contact_hit_done = False

    # ------------------------------------------------------------------
    @property
    def hp_ratio(self):
        return max(0.0, self.health / self.max_health)

    def get_damage(self, player_center, amount):
        if self.state == 'sleep':
            return False
        return super().get_damage(player_center, amount)

    def _choose_attack(self, dist):
        options = ['charge', 'slam', 'volley']
        if self.phase >= 2:
            options += ['summon', 'volley', 'charge']
        if self.final:
            options += ['rain', 'rain'] if self.phase >= 2 else ['rain']
        if dist > 420:
            options += ['charge', 'volley']
        if dist < 220:
            options += ['slam', 'slam']
        # évite de répéter trois fois la même attaque
        recent = self.attack_history[-2:]
        if len(recent) == 2 and recent[0] == recent[1]:
            options = [o for o in options if o != recent[0]] or options
        choice = random.choice(options)
        self.attack_history.append(choice)
        return choice

    def boss_update(self, player, dt, game):
        """IA du boss. `game` fournit fx/spawn ; retourne une liste d'évènements."""
        from fx import fx, Telegraph, Projectile
        from audio import sfx
        events = []
        if dt <= 0:
            return events
        me = pygame.math.Vector2(self.hitbox.center)
        tgt = pygame.math.Vector2(player.hitbox.center)
        diff = tgt - me
        dist = diff.length()
        if dist > 0:
            dirv = diff.normalize()
        else:
            dirv = pygame.math.Vector2(1, 0)

        if self.state == 'sleep':
            self._update_status(False)
            self.move(0, dt)
            if dist < 520:
                self.state = 'intro'
                self.state_t = 1.6
                events.append(('boss_awake',))
            return events

        # changement de phase
        if self.phase == 1 and self.hp_ratio <= 0.5:
            self.phase = 2
            self.speed *= 1.25
            self.state = 'roar'
            self.state_t = 1.2
            events.append(('boss_phase', 2))
        elif self.final and self.phase == 2 and self.hp_ratio <= 0.22:
            self.phase = 3
            self.speed *= 1.15
            self.state = 'roar'
            self.state_t = 1.2
            events.append(('boss_phase', 3))

        self.state_t -= dt
        speed_k = 1.0 if self.phase == 1 else 1.3
        st = self.state

        if st in ('intro', 'roar'):
            self.direction = pygame.math.Vector2()
            self._update_status(False, True)
            if random.random() < 0.3:
                fx.particles.embers(self.hitbox.centerx, self.hitbox.top, 2, spread_x=60)
            self.move(0, dt)
            if self.state_t <= 0:
                self.state = 'walk'
                self.state_t = 0.8

        elif st == 'walk':
            self.facing_right = diff.x >= 0
            self.direction = dirv if dist > 140 else pygame.math.Vector2()
            self._update_status(True)
            self.move(self.speed, dt)
            self.next_attack -= dt
            if self.next_attack <= 0:
                attack = self._choose_attack(dist)
                self.start_attack(attack, player, events)

        elif st == 'charge_windup':
            self.direction = pygame.math.Vector2()
            self.facing_right = self.charge_dir.x >= 0
            self._update_status(False, True)
            self.move(0, dt)
            if self.state_t <= 0:
                self.state = 'charging'
                self.state_t = 0.65
                self.contact_hit_done = False
                events.append(('boss_charge',))

        elif st == 'charging':
            self.direction = self.charge_dir
            self._update_status(True)
            old = pygame.math.Vector2(self.hitbox.topleft)
            self.move(980 * speed_k, dt)
            moved = (pygame.math.Vector2(self.hitbox.topleft) - old).length()
            if random.random() < 0.6:
                fx.particles.dust(self.hitbox.centerx, self.hitbox.bottom, 2)
            if not self.contact_hit_done and self.hitbox.inflate(20, 20).colliderect(player.hitbox):
                self.contact_hit_done = True
                events.append(('boss_hit', int(self.damage * 1.2), me))
            if moved < 980 * speed_k * dt * 0.3 or self.state_t <= 0:
                # percute un mur ou fin de charge
                hit_wall = moved < 980 * speed_k * dt * 0.3
                self.state = 'stunned' if hit_wall else 'walk'
                self.state_t = 1.1 if hit_wall else 0.6
                self.next_attack = 1.0 / speed_k
                if hit_wall:
                    events.append(('boss_wall',))

        elif st == 'stunned':
            self.direction = pygame.math.Vector2()
            self._update_status(False)
            self.move(0, dt)
            if random.random() < 0.2:
                fx.particles.emit(self.hitbox.centerx, self.hitbox.top - 40, 1, (255, 255, 120),
                                  speed=(30, 60), life=(0.3, 0.5), size=(2, 3), glow=True)
            if self.state_t <= 0:
                self.state = 'walk'

        elif st == 'slam_windup':
            self.direction = pygame.math.Vector2()
            self._update_status(False, True)
            self.move(0, dt)
            if self.state_t <= 0:
                events.append(('boss_slam', self.hitbox.center, 230, int(self.damage * 1.1)))
                if self.phase >= 2:
                    self._radial(game, 14 if self.phase == 2 else 20, 260, 0)
                self.state = 'recover'
                self.state_t = 0.7

        elif st == 'volley':
            self.direction = pygame.math.Vector2()
            self._update_status(False, True)
            self.move(0, dt)
            self.volley_t -= dt
            if self.volley_t <= 0 and self.volley_left > 0:
                self.volley_left -= 1
                self.volley_t = 0.28 if self.phase == 1 else 0.18
                if self.phase >= 2:
                    self.spiral_angle += 0.35
                    self._radial(game, 10, 300, self.spiral_angle)
                else:
                    self._radial(game, 12, 260, self.volley_left * 0.26)
                # tir visé au joueur
                self._aimed(game, dirv, 3 if self.phase == 1 else 5)
                sfx('shoot', 0.6)
            if self.volley_left <= 0 and self.volley_t <= 0:
                self.state = 'recover'
                self.state_t = 0.6

        elif st == 'summon':
            self.direction = pygame.math.Vector2()
            self._update_status(False, True)
            self.move(0, dt)
            if self.state_t <= 0:
                events.append(('boss_summon', 2 + self.phase))
                self.state = 'recover'
                self.state_t = 0.8

        elif st == 'rain':
            self.direction = pygame.math.Vector2()
            self._update_status(False, True)
            self.move(0, dt)
            if self.state_t <= 0:
                for spot in self.rain_spots:
                    events.append(('boss_rain_hit', spot, 70, int(self.damage * 0.9)))
                self.rain_spots = []
                self.state = 'recover'
                self.state_t = 0.5

        elif st == 'recover':
            self.direction = pygame.math.Vector2()
            self._update_status(False)
            self.move(0, dt)
            if self.state_t <= 0:
                self.state = 'walk'
                self.next_attack = random.uniform(0.9, 1.6) / speed_k

        return events

    # ------------------------------------------------------------------
    def start_attack(self, attack, player, events):
        from fx import fx, Telegraph
        me = pygame.math.Vector2(self.hitbox.center)
        tgt = pygame.math.Vector2(player.hitbox.center)
        speed_k = 1.0 if self.phase == 1 else 1.3
        if attack == 'charge':
            d = tgt - me
            self.charge_dir = d.normalize() if d.length() else pygame.math.Vector2(1, 0)
            self.state = 'charge_windup'
            self.state_t = 0.75 / speed_k
            end = me + self.charge_dir * 640
            fx.telegraphs.append(Telegraph('line', me.x, me.y, self.state_t, end=(end.x, end.y), width=90))
            events.append(('boss_telegraph',))
        elif attack == 'slam':
            self.state = 'slam_windup'
            self.state_t = 0.95 / speed_k
            fx.telegraphs.append(Telegraph('circle', me.x, me.y, self.state_t, radius=230))
            events.append(('boss_telegraph',))
        elif attack == 'volley':
            self.state = 'volley'
            self.volley_left = 4 if self.phase == 1 else 6
            self.volley_t = 0.4
        elif attack == 'summon':
            self.state = 'summon'
            self.state_t = 0.9
            fx.particles.ring(me.x, me.y, (190, 80, 255), 40, 300)
            events.append(('boss_roar',))
        elif attack == 'rain':
            self.state = 'rain'
            self.state_t = 1.1 / speed_k
            self.rain_spots = []
            n = 7 if self.phase < 3 else 11
            for i in range(n):
                if i == 0:
                    spot = (tgt.x, tgt.y)
                else:
                    a = random.uniform(0, math.tau)
                    r = random.uniform(60, 330)
                    spot = (tgt.x + math.cos(a) * r, tgt.y + math.sin(a) * r)
                self.rain_spots.append(spot)
                fx.telegraphs.append(Telegraph('circle', spot[0], spot[1], self.state_t, radius=70,
                                               color=(255, 200, 40)))
            events.append(('boss_telegraph',))

    def _radial(self, game, count, speed, offset):
        from fx import fx, Projectile
        cx, cy = self.hitbox.center
        col = (255, 90, 200) if self.final else (255, 120, 60)
        for i in range(count):
            a = offset + i / count * math.tau
            fx.projectiles.append(Projectile(cx, cy, math.cos(a) * speed, math.sin(a) * speed,
                                             int(self.damage * 0.55), color=col, radius=10))

    def _aimed(self, game, dirv, count):
        from fx import fx, Projectile
        cx, cy = self.hitbox.center
        base = math.atan2(dirv.y, dirv.x)
        for i in range(count):
            a = base + (i - (count - 1) / 2) * 0.16
            fx.projectiles.append(Projectile(cx, cy, math.cos(a) * 380, math.sin(a) * 380,
                                             int(self.damage * 0.6), color=(255, 230, 120), radius=8))
