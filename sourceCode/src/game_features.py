"""Gameplay et rendu de l'Édition Abysses.

`Game` hérite de `GameFeatures` : on garde ainsi dans game.py la machine à
états et toute la logique réseau, et on regroupe ici les nouveautés
(combat, boss, butin, coffres, bénédictions, menus, écrans de fin...).
"""
import math
import random
import time
import pygame

from settings import *
from fx import fx, Slash, Afterimage, Projectile, render_outlined, get_font, draw_panel, additive_glow, vignette
from audio import get_audio, sfx
from tile import Tile, Floor, DungeonEntrance
from dungeon import DungeonGenerator, split_cells, torch_spots
from entities.enemy import Enemy
from entities.boss import Boss
from entities.item import Item, get_icon
from entities.props import Torch, Chest
from minimap import Minimap
from perks import PerkScreen, apply_perk, roll_choices, PERKS, RARITY_COLORS
from menu_scene import MenuBackground, draw_button
from save_manager import SaveManager

DEFAULT_OPTIONS = {'sfx': 0.7, 'music': 0.6, 'shake': True, 'lighting': True, 'fps': False, 'fullscreen': False}


class GameFeatures:
    # ==================================================================
    # Initialisation & options
    # ==================================================================
    def init_features(self):
        self.audio = get_audio()
        self.options_store = SaveManager("options.json")
        self.options = dict(DEFAULT_OPTIONS)
        try:
            self.options.update(self.options_store.load_game() or {})
        except Exception:
            pass
        self.menu_bg = MenuBackground()
        self.perk_screen = None
        self.boss = None
        self.chests = []
        self.minimap = None
        self.show_big_map = False
        self.run_stats = self._new_run()
        self.dt = 1 / 60
        self.ui_t = 0.0
        self.dawn_warned = False
        self.victory_t = 0.0
        self.transition_sub = ""
        self.reset_confirm = False
        self._hovered_btn = None
        self._last_spin_fail = 0
        self._heartbeat_t = 0.0
        self.apply_options()

    def _new_run(self):
        return {'kills': 0, 'gold': 0, 'iron': 0, 'xp': 0, 'damage': 0, 'start': time.time(),
                'elites': 0, 'chests': 0, 'best_combo': 0}

    def apply_options(self):
        o = self.options
        self.audio.sfx_volume = o['sfx']
        try:
            pygame.mixer.music.set_volume(0.55 * o['music'])
        except Exception:
            pass
        fx.shake_enabled = o['shake']
        self.visible_sprites.lighting_enabled = o['lighting']

    def save_options(self):
        self.options_store.save_game(self.options)

    def options_labels(self):
        o = self.options
        return {
            'reset_save': "CONFIRMER LA SUPPRESSION ?" if self.reset_confirm else "RÉINITIALISER SAUVEGARDE",
            'toggle_fullscreen': f"PLEIN ÉCRAN : {'OUI' if self.fullscreen else 'NON'}",
            'sfx_volume': f"VOLUME EFFETS : {int(round(o['sfx'] * 100))} %",
            'music_volume': f"VOLUME MUSIQUE : {int(round(o['music'] * 100))} %",
            'toggle_shake': f"SECOUSSES D'ÉCRAN : {'OUI' if o['shake'] else 'NON'}",
            'toggle_lighting': f"ÉCLAIRAGE DYNAMIQUE : {'OUI' if o['lighting'] else 'NON'}",
            'toggle_fps': f"AFFICHER FPS : {'OUI' if o['fps'] else 'NON'}",
            'replay_intro': "REVOIR L'INTRODUCTION",
            'back_to_menu': "RETOUR",
        }

    def handle_option_action(self, action, button=1):
        o = self.options
        step = 0.1 if button == 1 else -0.1
        if action == 'sfx_volume':
            o['sfx'] = round((o['sfx'] + step) % 1.1, 1)
        elif action == 'music_volume':
            o['music'] = round((o['music'] + step) % 1.1, 1)
        elif action == 'toggle_shake':
            o['shake'] = not o['shake']
        elif action == 'toggle_lighting':
            o['lighting'] = not o['lighting']
        elif action == 'toggle_fps':
            o['fps'] = not o['fps']
        else:
            return False
        self.apply_options()
        self.save_options()
        sfx('ui_click')
        return True

    # ==================================================================
    # Évènements du joueur -> effets
    # ==================================================================
    def process_player_events(self):
        p = self.player
        for ev in p.events:
            kind = ev[0]
            if kind == 'swing':
                _, akind, aim, step = ev
                ang = math.degrees(math.atan2(aim.y, aim.x))
                cx, cy = p.hitbox.centerx, p.hitbox.centery - 22
                if akind == 'finisher':
                    fx.slashes.append(Slash(cx + aim.x * 46, cy + aim.y * 46, ang, radius=96, thickness=36,
                                            color=(255, 200, 120), life=0.2, arc=170))
                    sfx('swing', 1.0)
                else:
                    flip = 1 if step % 2 == 0 else -1
                    fx.slashes.append(Slash(cx + aim.x * 40, cy + aim.y * 40, ang + 12 * flip, radius=78,
                                            thickness=26, life=0.15))
                    sfx('swing', 0.7)
            elif kind == 'spin':
                cx, cy = p.hitbox.centerx, p.hitbox.centery - 20
                fx.slashes.append(Slash(cx, cy, 0, radius=118, thickness=34, color=(140, 210, 255), life=0.38,
                                        full_circle=True))
                fx.particles.ring(cx, cy, (140, 210, 255), 30, 380)
                fx.shake(0.15)
                sfx('spin')
            elif kind == 'spin_fail':
                now = pygame.time.get_ticks()
                if now - self._last_spin_fail > 700:
                    self._last_spin_fail = now
                    fx.text(p.hitbox.centerx, p.hitbox.top - 70, "Recharge...", (160, 180, 220), 18, 0.6, 40)
            elif kind == 'dash':
                fx.particles.dust(p.hitbox.centerx, p.hitbox.bottom, 8)
                sfx('dash', 0.8)
            elif kind == 'afterimage':
                fx.afterimages.append(Afterimage(p.image, p.rect.x, p.rect.y))
            elif kind == 'hurt':
                _, amount, direction = ev
                fx.text(p.hitbox.centerx, p.hitbox.top - 60, f"-{amount}", (255, 70, 70), 26, 0.8, 80, 1.4)
                fx.particles.blood(p.hitbox.centerx, p.hitbox.centery - 20, (direction.x, direction.y), 12)
                fx.shake(0.4)
                fx.flash((160, 0, 0), 70)
                sfx('hurt')
            elif kind == 'potion':
                fx.text(p.hitbox.centerx, p.hitbox.top - 60, f"+{ev[1]} PV", (90, 255, 120), 26, 1.0, 70, 1.3)
                fx.particles.emit(p.hitbox.centerx, p.hitbox.centery - 20, 26, (90, 255, 140), speed=(30, 140),
                                  life=(0.5, 1.0), size=(2, 4), gravity=-140, glow=True, jitter=20)
                sfx('potion')
            elif kind == 'potion_fail':
                self.ui.toast("Aucune potion ! (achetez-en au Marché)", (255, 140, 140))
            elif kind == 'potion_full':
                self.ui.toast("Vos PV sont déjà au maximum", (200, 200, 200))
            elif kind == 'levelup':
                fx.show_banner(f"NIVEAU {ev[1]}", "Vous gagnez en puissance  (+5 PV, +1 dégât)", GOLD)
                fx.particles.ring(p.hitbox.centerx, p.hitbox.centery - 20, (255, 210, 90), 48, 360)
                fx.particles.soul(p.hitbox.centerx, p.hitbox.centery, (255, 220, 120))
                sfx('levelup')
            elif kind == 'phoenix':
                fx.show_banner("SECONDE CHANCE", "Le phénix refuse votre mort...", (255, 160, 60))
                fx.flash((255, 180, 60), 160)
                fx.particles.ring(p.hitbox.centerx, p.hitbox.centery, (255, 150, 40), 60, 420)
                sfx('levelup')
        p.events.clear()

    def damage_player(self, amount, origin, source=None):
        dealt = self.player.get_damage(amount, origin)
        if dealt and source is not None and self.player.perk('thorns') and source.health > 0:
            back = max(1, int(dealt * 0.6 * self.player.perk('thorns')))
            source.vulnerable = True
            if source.get_damage(self.player.hitbox.center, back):
                bx, by = source.body_center()
                fx.text(bx, by - 30, f"{back}", (190, 255, 120), 20, 0.7)
                fx.particles.sparks(bx, by, (180, 255, 120), 8)
        return dealt

    # ==================================================================
    # Combat : coups portés
    # ==================================================================
    def fx_enemy_hit(self, enemy, dmg, crit, kind):
        bx, by = enemy.body_center()
        pdir = pygame.math.Vector2(bx, by) - pygame.math.Vector2(self.player.hitbox.center)
        d = (pdir.x, pdir.y) if pdir.length_squared() else (1, 0)
        if crit:
            fx.text(bx, by - 40, f"{dmg}!", (255, 215, 60), 34, 0.9, 90, 1.8)
            fx.particles.sparks(bx, by, (255, 230, 120), 16, d)
            sfx('crit')
            fx.hitstop(0.075)
            fx.shake(0.28)
        else:
            col = (255, 170, 80) if kind in ('finisher', 'spin') else (255, 255, 255)
            fx.text(bx, by - 40, str(dmg), col, 28 if kind == 'finisher' else 24, 0.75, 70, 1.4)
            fx.particles.sparks(bx, by, (255, 220, 160), 7, d)
            sfx('hit', 0.8)
            fx.hitstop(0.06 if kind == 'finisher' else 0.035)
            fx.shake(0.2 if kind == 'finisher' else 0.08)
        fx.particles.blood(bx, by, d, 10 if not crit else 18)
        if random.random() < 0.35:
            fx.decal_blood(enemy.hitbox.centerx + random.randint(-20, 20), enemy.hitbox.bottom - random.randint(0, 20))
        self.run_stats['damage'] += dmg
        if self.player.combo_step + 1 > self.run_stats['best_combo']:
            self.run_stats['best_combo'] = self.player.combo_step + 1

    def player_hit_enemy(self, enemy):
        dmg, crit = self.player.roll_damage()
        if enemy.get_damage(self.player.hitbox.center, dmg):
            self.fx_enemy_hit(enemy, dmg, crit, self.player.attack_kind)
            return True
        return False

    def enemy_death_fx(self, enemy):
        bx, by = enemy.body_center()
        fx.add_corpse(enemy)
        fx.particles.death(bx, by)
        fx.particles.soul(bx, by)
        fx.decal_blood(enemy.hitbox.centerx, enemy.hitbox.bottom - 10, 30)
        sfx('enemy_die', 0.8)
        fx.shake(0.12)

    def spawn_loot_solo(self, enemy):
        greed = 1 + 0.25 * self.player.perk('greed')
        cx, cy = enemy.hitbox.center
        for item_type, (min_amt, max_amt) in enemy.loot_table.items():
            amount = random.randint(min_amt, max_amt)
            amount = int(amount * greed + random.random())
            for _ in range(amount):
                Item((cx + random.randint(-12, 12), cy + random.randint(-12, 12)),
                     [self.visible_sprites, self.item_sprites], item_type, burst=True)
        if random.random() < (0.12 if not enemy.elite else 0.6):
            Item((cx, cy), [self.visible_sprites, self.item_sprites], 'health', burst=True)
        if random.random() < (0.025 if not enemy.elite else 0.3):
            Item((cx, cy), [self.visible_sprites, self.item_sprites], 'potion', burst=True)

    def on_enemy_killed_solo(self, enemy):
        self.enemy_death_fx(enemy)
        self.player.stats['kills'] = self.player.stats.get('kills', 0) + 1
        self.run_stats['kills'] += 1
        if self.player.perk('vamp'):
            heal = 3 * self.player.perk('vamp')
            if self.player.health < self.player.max_health:
                self.player.health = min(self.player.max_health, self.player.health + heal)
                fx.text(self.player.hitbox.centerx, self.player.hitbox.top - 50, f"+{heal}", (120, 255, 140), 18, 0.6)
        if enemy.elite:
            self.run_stats['elites'] += 1
            self.ui.toast(f"{enemy.name} vaincu !", GOLD)
            fx.shake(0.3)
        if isinstance(enemy, Boss):
            self.on_boss_defeated(enemy)
        else:
            self.spawn_loot_solo(enemy)
        enemy.kill()

    # ==================================================================
    # Boss
    # ==================================================================
    def handle_boss_events(self, boss, events):
        p = self.player
        for ev in events:
            k = ev[0]
            if k == 'boss_awake':
                self.boss = boss
                fx.show_banner(boss.name.upper(), "Gardien de l'Artefact" if not boss.final else "Le maître du donjon",
                               (255, 90, 70), 3.0)
                fx.shake(0.6)
                sfx('roar')
            elif k == 'boss_phase':
                fx.show_banner("ENRAGÉ !" if ev[1] == 2 else "FURIE FINALE !", "Ses attaques s'intensifient",
                               (255, 120, 40), 2.2)
                fx.flash((255, 60, 20), 90)
                fx.shake(0.7)
                fx.particles.ring(boss.hitbox.centerx, boss.hitbox.centery, (255, 90, 40), 60, 500)
                sfx('roar')
            elif k == 'boss_roar':
                sfx('roar', 0.6)
                fx.shake(0.3)
            elif k == 'boss_charge':
                sfx('dash', 1.0)
            elif k == 'boss_wall':
                fx.shake(0.65)
                sfx('slam', 0.8)
                fx.particles.emit(boss.hitbox.centerx, boss.hitbox.centery, 30, (120, 110, 100), speed=(80, 300),
                                  life=(0.4, 0.9), size=(3, 7), gravity=500, drag=2)
            elif k == 'boss_hit':
                self.damage_player(ev[1], ev[2], boss)
            elif k == 'boss_slam':
                center, radius, dmg = ev[1], ev[2], ev[3]
                fx.particles.ring(center[0], center[1], (255, 140, 60), 60, 520)
                fx.particles.emit(center[0], center[1], 30, (110, 100, 90), speed=(60, 260), life=(0.4, 0.9),
                                  size=(3, 7), gravity=400)
                fx.shake(0.8)
                sfx('slam')
                if pygame.math.Vector2(center).distance_to(p.hitbox.center) < radius:
                    self.damage_player(dmg, center, boss)
            elif k == 'boss_summon':
                tiers = ['tier1', 'tier2', 'tier3']
                if p.level >= 6:
                    tiers.append('tier4')
                for i in range(ev[1]):
                    a = i / ev[1] * math.tau
                    x = boss.hitbox.centerx + math.cos(a) * 150
                    y = boss.hitbox.centery + math.sin(a) * 150
                    e = Enemy([self.visible_sprites, self.attackable_sprites], (0, 0), self.obstacle_sprites,
                              random.choice(tiers))
                    e.hitbox.center = (int(x), int(y))
                    e.pos = pygame.math.Vector2(e.hitbox.topleft)
                    e.move(0, 0.001)
                    e.awake = True
                    fx.particles.ring(x, y, (190, 80, 255), 24, 200)
            elif k == 'boss_rain_hit':
                spot, radius, dmg = ev[1], ev[2], ev[3]
                fx.particles.emit(spot[0], spot[1], 18, (255, 210, 60), speed=(60, 260), life=(0.3, 0.7),
                                  size=(2, 4), glow=True, gravity=300)
                fx.shake(0.15)
                if random.random() < 0.35:
                    Item(spot, [self.visible_sprites, self.item_sprites], 'gold', burst=True)
                if pygame.math.Vector2(spot).distance_to(p.hitbox.center) < radius:
                    self.damage_player(dmg, spot, boss)
        if events and any(e[0] == 'boss_rain_hit' for e in events):
            sfx('coin', 0.7)
            sfx('slam', 0.4)

    def on_boss_defeated(self, boss):
        cx, cy = boss.hitbox.center
        fx.slowmo(1.4, 0.25)
        fx.flash((255, 255, 255), 200)
        fx.shake(1.0)
        for _ in range(3):
            fx.particles.ring(cx, cy, random.choice([(255, 120, 60), (255, 220, 120), (200, 60, 255)]), 50,
                              random.randint(300, 600))
        fx.particles.death(cx, cy)
        sfx('roar', 0.8)
        sfx('victory')
        self.audio.stop_loop('boss_loop')
        self.player.stats['bosses'] = self.player.stats.get('bosses', 0) + 1
        for item_type, (lo, hi) in boss.loot_table.items():
            for _ in range(random.randint(lo, hi)):
                Item((cx, cy), [self.visible_sprites, self.item_sprites], item_type, burst=True)
        Item((cx, cy + 10), [self.visible_sprites, self.item_sprites], 'potion', burst=True)
        art = Item((cx, cy), [self.visible_sprites, self.item_sprites], 'artifact')
        art.vz = 380
        fx.show_banner("GARDIEN TERRASSÉ", "Ramassez l'Artefact !", GOLD, 3.2)
        # les serviteurs restants s'effondrent
        for e in list(self.attackable_sprites):
            if e is not boss:
                self.enemy_death_fx(e)
                e.kill()
        self.boss = None

    # ==================================================================
    # Construction du niveau
    # ==================================================================
    def build_level_common(self, floor_cells, wall_cells, spawn_px):
        self.visible_sprites.empty()
        self.obstacle_sprites.empty()
        self.attackable_sprites.empty()
        self.item_sprites.empty()
        fx.reset()
        floors = [Floor((x * TILE_SIZE, y * TILE_SIZE), []) for (x, y) in floor_cells]
        walls = [Tile((x * TILE_SIZE, y * TILE_SIZE), [self.obstacle_sprites]) for (x, y) in wall_cells]
        self.visible_sprites.set_level(floors, walls)
        fset, wset = set(floor_cells), set(wall_cells)
        for (x, y) in torch_spots(fset, wset, every=6):
            Torch((x * TILE_SIZE, y * TILE_SIZE), [self.visible_sprites])
        self.minimap = Minimap(floor_cells)
        self.show_big_map = False
        entrance = DungeonEntrance(spawn_px, [self.visible_sprites])
        self.dungeon_entrance_pos = pygame.math.Vector2(spawn_px)
        self.dungeon_entrance_rect = entrance.rect
        self.player.rect.topleft = spawn_px
        self.player.pos = pygame.math.Vector2(spawn_px)
        self.player.hitbox.topleft = spawn_px
        self.player.rect.midbottom = self.player.hitbox.midbottom
        self.player.obstacle_sprites = self.obstacle_sprites
        self.player.add(self.visible_sprites)
        self.player.knockback = pygame.math.Vector2()
        self.player.events.clear()
        self.boss = None
        self.chests = []
        self.dawn_warned = False
        self.cleared_announced = False
        self.visible_sprites.snap_next = True
        return fset

    def build_map_solo(self):
        self.major_dungeon_won = False
        d_type = getattr(self, 'current_dungeon_type', 'random')
        major = d_type == 'major'
        dungeon = DungeonGenerator()
        map_data, player_spawn = dungeon.generate(num_rooms=5 if major else 8, boss_room=major)
        floor_cells, wall_cells = split_cells(map_data)
        spawn_pos = (player_spawn[0] * TILE_SIZE, player_spawn[1] * TILE_SIZE)
        fset = self.build_level_common(floor_cells, wall_cells, spawn_pos)

        p = self.player
        p.health = p.max_health
        p.vulnerable = False
        p.hurt_time = pygame.time.get_ticks()
        p.invincibility_duration = 3000
        p.phoenix_used = False
        p.stats['expeditions'] = p.stats.get('expeditions', 0) + 1
        self.run_stats = self._new_run()

        base_tiers = ['tier1']
        if p.level >= 3: base_tiers.append('tier2')
        if p.level >= 6: base_tiers.append('tier3')
        if p.level >= 10: base_tiers.append('tier4')
        if p.level >= 15: base_tiers.append('tier5')
        if major:
            base_tiers = ['tier3', 'tier4', 'tier5'] if p.level < 8 else ['tier4', 'tier5']
        elite_chance = min(0.25, 0.06 + p.level * 0.008 + (0.08 if major else 0))

        def free_spot(room, tries=12):
            for _ in range(tries):
                rx = random.randint(room.left + 1, max(room.left + 1, room.right - 2))
                ry = random.randint(room.top + 1, max(room.top + 1, room.bottom - 2))
                if (rx, ry) in fset:
                    return rx * TILE_SIZE + random.randint(0, 20), ry * TILE_SIZE + random.randint(0, 20)
            return room.centerx * TILE_SIZE, room.centery * TILE_SIZE

        rooms = [r for r in dungeon.rooms[1:] if r is not dungeon.boss_room]
        for room in rooms:
            if major:
                spawn_count = random.randint(2, 4)
            else:
                spawn_count = random.randint(3, min(10, 5 + p.level // 5))
            for _ in range(spawn_count):
                pos = free_spot(room)
                e = Enemy([self.visible_sprites, self.attackable_sprites], (0, 0), self.obstacle_sprites,
                          random.choice(base_tiers))
                e.hitbox.center = pos
                e.pos = pygame.math.Vector2(e.hitbox.topleft)
                e.move(0, 0.001)
                if random.random() < elite_chance:
                    e.make_elite()
            # coffres
            if random.random() < 0.5:
                pos = free_spot(room)
                mimic = random.random() < 0.12
                self.chests.append(Chest(pos, [self.visible_sprites], mimic=mimic))

        if major and dungeon.boss_room:
            br = dungeon.boss_room
            boss = Boss([self.visible_sprites, self.attackable_sprites], (0, 0), self.obstacle_sprites,
                        player_level=p.level, artifact_index=p.artifacts)
            boss.hitbox.center = (br.centerx * TILE_SIZE, br.centery * TILE_SIZE)
            boss.pos = pygame.math.Vector2(boss.hitbox.topleft)
            boss.move(0, 0.001)
            self.boss_ref = boss
            for _ in range(2):
                self.chests.append(Chest(free_spot(br), [self.visible_sprites]))
        else:
            self.boss_ref = None

        fx.show_banner("DONJON MAJEUR" if major else "EXPÉDITION NOCTURNE",
                       "Terrassez le Gardien de l'Artefact" if major else "Pillez avant l'aube, puis rejoignez le portail",
                       (255, 100, 80) if major else (170, 190, 255), 3.0)
        sfx('portal')

    # ==================================================================
    # Mise à jour du donjon (solo)
    # ==================================================================
    def update_items(self, dt):
        p = self.player
        target = p.hitbox.center
        radius = p.magnet_radius
        for item in list(self.item_sprites):
            item.attract(target, dt, radius)
            if item.pickup_ready and item.hitbox.colliderect(p.hitbox):
                if getattr(self, 'is_multiplayer', False):
                    continue  # en multi, le ramassage passe par le serveur (update_multi)
                self.pickup_item(item)

    def pickup_item(self, item):
        p = self.player
        x, y = item.rect.center
        t = item.type
        if t == 'health':
            heal = max(5, int(p.max_health * 0.12))
            p.health = min(p.max_health, p.health + heal)
            fx.text(x, y - 20, f"+{heal} PV", (110, 255, 130), 18, 0.7)
            sfx('potion', 0.5)
        elif t == 'potion':
            if p.potions < MAX_POTIONS:
                p.potions += 1
                self.ui.toast("Potion ramassée", (255, 150, 170), get_icon('potion')[0])
            else:
                heal = int(p.max_health * 0.25)
                p.health = min(p.max_health, p.health + heal)
            sfx('potion', 0.6)
        elif t == 'artifact':
            self.collect_artifact()
        elif t in p.inventory:
            p.inventory[t] += 1
            if t in self.run_stats:
                self.run_stats[t] += 1
            if t == 'gold':
                sfx('coin', 0.5, cooldown=0.05)
            elif t == 'iron':
                sfx('iron', 0.4, cooldown=0.05)
            else:
                sfx('xp', 0.3, cooldown=0.04)
        fx.particles.emit(x, y, 5, item.glow_color, speed=(30, 90), life=(0.2, 0.4), size=(2, 3), glow=True)
        item.kill()

    def collect_artifact(self):
        if getattr(self, 'major_dungeon_won', False):
            return
        self.major_dungeon_won = True
        self.player.artifacts += 1
        sfx('victory')
        fx.flash((255, 40, 80), 140)
        self.transition_active = True
        self.transition_timer = 0
        self.transition_duration = 4.0
        self.transition_type = 'major_victory'
        self._transition_mid_triggered = False
        if self.player.artifacts >= 4:
            self.transition_text = "Le Seigneur de la Cupidité est tombé..."
            self.transition_sub = "Le royaume est libéré."
        else:
            self.transition_text = f"Artefact récupéré ({self.player.artifacts}/4)"
            self.transition_sub = "Le pouvoir du Seigneur faiblit..."

    def can_extract(self):
        return (getattr(self, 'current_dungeon_type', 'random') != 'major' and not self.transition_active
                and self.player.health > 0 and self.is_player_at_entrance())

    def start_extraction(self):
        self.transition_active = True
        self.transition_timer = 0
        self.transition_duration = 3.0
        self.transition_type = 'morning'
        self._transition_mid_triggered = False
        self.transition_text = "Retour au village..."
        self.transition_sub = ""
        sfx('portal')
        fx.particles.ring(self.player.hitbox.centerx, self.player.hitbox.centery, (120, 160, 255), 40, 300)

    def try_interact(self):
        chest = self.nearest_chest()
        if chest is None:
            if self.can_extract():
                self.start_extraction()
            return
        p = self.player
        chest.open()
        cx, cy = chest.rect.center
        if chest.mimic:
            chest.kill()
            self.chests.remove(chest)
            sfx('mimic')
            fx.shake(0.5)
            fx.show_banner("MIMIQUE !", "Ce coffre avait des dents...", (255, 80, 80), 2.0)
            tier = random.choice(['tier4', 'tier5'] if p.level >= 6 else ['tier2', 'tier4'])
            e = Enemy([self.visible_sprites, self.attackable_sprites], (0, 0), self.obstacle_sprites, tier)
            e.hitbox.center = (cx, cy)
            e.pos = pygame.math.Vector2(e.hitbox.topleft)
            e.move(0, 0.001)
            e.make_elite()
            e.name = "Mimique"
            e.awake = True
            e.loot_table = {'gold': (6, 12), 'iron': (8, 14), 'xp': (10, 16)}
            return
        sfx('chest')
        self.run_stats['chests'] += 1
        p.stats['chests'] = p.stats.get('chests', 0) + 1
        fx.particles.emit(cx, cy - 10, 30, (255, 210, 90), speed=(80, 260), life=(0.4, 0.9), size=(2, 4),
                          gravity=300, glow=True, angle=-math.pi / 2, spread=1.6)
        lvl = p.level
        loot = {'gold': random.randint(2, 5) + lvl // 3, 'iron': random.randint(6, 12) + lvl // 2,
                'xp': random.randint(5, 10)}
        for t, n in loot.items():
            for _ in range(n):
                Item((cx, cy), [self.visible_sprites, self.item_sprites], t, burst=True)
        if random.random() < 0.4:
            Item((cx, cy), [self.visible_sprites, self.item_sprites], 'potion', burst=True)

    def nearest_chest(self):
        best, best_d = None, 80
        for c in self.chests:
            if c.opened:
                continue
            d = pygame.math.Vector2(c.rect.center).distance_to(self.player.hitbox.center)
            if d < best_d:
                best, best_d = c, d
        return best

    def separate_enemies(self, enemies):
        for i in range(len(enemies)):
            a = enemies[i]
            for j in range(i + 1, len(enemies)):
                b = enemies[j]
                dx = b.hitbox.centerx - a.hitbox.centerx
                dy = b.hitbox.centery - a.hitbox.centery
                d2 = dx * dx + dy * dy
                min_d = 52 if not (isinstance(a, Boss) or isinstance(b, Boss)) else 110
                if 0 < d2 < min_d * min_d:
                    d = math.sqrt(d2)
                    push = (min_d - d) * 0.5
                    nx, ny = dx / d * push, dy / d * push
                    if not isinstance(a, Boss):
                        a.knockback.x -= nx * 6
                        a.knockback.y -= ny * 6
                    if not isinstance(b, Boss):
                        b.knockback.x += nx * 6
                        b.knockback.y += ny * 6

    def update_dungeon_solo(self, dt):
        p = self.player
        self.visible_sprites.update(dt)
        self.process_player_events()
        if dt <= 0:
            return

        # --- coups du joueur ---
        if p.current_weapon:
            wrect = p.current_weapon.rect
            for e in list(self.attackable_sprites):
                if e.health > 0 and wrect.colliderect(e.hitbox):
                    self.player_hit_enemy(e)

        # --- IA des monstres ---
        pc = pygame.math.Vector2(p.hitbox.center)
        active = []
        for enemy in list(self.attackable_sprites):
            dist = pc.distance_to(enemy.hitbox.center)
            if isinstance(enemy, Boss):
                events = enemy.boss_update(p, dt, self)
                self.handle_boss_events(enemy, events)
                active.append(enemy)
            elif dist < 1500:
                active.append(enemy)
                ev = enemy.solo_update(p, dt)
                if ev:
                    if ev[0] == 'strike':
                        self.damage_player(ev[1], enemy.hitbox.center, enemy)
                        sfx('swing', 0.5)
                    elif ev[0] == 'shoot':
                        d = ev[1]
                        bx, by = enemy.body_center()
                        fx.projectiles.append(Projectile(bx, by, d.x * 330, d.y * 330, enemy.damage,
                                                         color=(150, 255, 80), radius=8))
                        sfx('shoot', 0.5)
            if enemy.health <= 0:
                self.on_enemy_killed_solo(enemy)
        self.separate_enemies([e for e in active if e.health > 0][:40])

        # --- projectiles ---
        for proj in fx.projectiles:
            proj.update(dt, self.obstacle_sprites, fx.particles)
            if proj.alive and p.health > 0 and proj.rect.colliderect(p.hitbox.inflate(-6, -6)):
                proj.alive = False
                if self.damage_player(proj.damage, (proj.pos.x, proj.pos.y)):
                    fx.particles.sparks(proj.pos.x, proj.pos.y, proj.color, 10)
        fx.projectiles = [pr for pr in fx.projectiles if pr.alive]

        self.update_items(dt)
        if self.minimap:
            self.minimap.reveal(p.hitbox.center)

        # --- battement de cœur quand la vie est basse ---
        if 0 < p.health < p.max_health * 0.3:
            self._heartbeat_t -= dt
            if self._heartbeat_t <= 0:
                self._heartbeat_t = 1.0
                sfx('heartbeat', 0.7)

        # --- avertissement de l'aube ---
        if getattr(self, 'current_dungeon_type', 'random') != 'major':
            remaining = (self.full_day_duration - self.game_time) / 1000
            if remaining < 25 and not self.dawn_warned:
                self.dawn_warned = True
                fx.show_banner("L'AUBE APPROCHE", "Rejoignez le portail ou perdez votre butin !", (255, 190, 120))
                sfx('portal')

    # ==================================================================
    # Bénédictions
    # ==================================================================
    def check_perks(self):
        p = self.player
        if p.pending_perks <= 0 or self.perk_screen is not None:
            return
        if self.is_multiplayer:
            # pas de pause en ligne : bénédiction tirée au hasard
            choice = roll_choices(p.perks, 1)
            p.pending_perks -= 1
            if choice:
                apply_perk(p, choice[0])
                self.ui.toast(f"Bénédiction : {PERKS[choice[0]][0]}", RARITY_COLORS[PERKS[choice[0]][2]])
            return
        if self.game_state in ('hub', 'dungeon') and not self.transition_active and p.health > 0 and not self.paused:
            screen = PerkScreen(p)
            if screen.empty:
                p.pending_perks = 0
                return
            self.perk_screen = screen

    def choose_perk(self, pid):
        apply_perk(self.player, pid)
        self.player.pending_perks = max(0, self.player.pending_perks - 1)
        self.perk_screen = None
        name, desc, rarity, _, _ = PERKS[pid]
        self.ui.toast(f"{name} : {desc}", RARITY_COLORS[rarity])
        sfx('levelup', 0.6)
        if self.game_state == 'hub':
            self.save_all()

    # ==================================================================
    # Musique / ambiances
    # ==================================================================
    def manage_ambience(self):
        in_dungeon = self.game_state in ('dungeon', 'dying', 'game_over')
        if in_dungeon:
            self.audio.loop('drone', 0.45 * self.options['music'])
        else:
            self.audio.stop_loop('drone')
        boss_on = in_dungeon and self.boss is not None and self.boss.health > 0 and self.boss.state != 'sleep'
        if boss_on:
            self.audio.loop('boss_loop', 0.55 * self.options['music'])
        else:
            self.audio.stop_loop('boss_loop', 1500)

    # ==================================================================
    # Rendu du donjon
    # ==================================================================
    def dungeon_ambient(self):
        start, end = self.evening_duration, self.full_day_duration
        k = max(0.0, min(1.0, (self.game_time - start) / max(1, end - start)))
        k = k ** 3  # l'aube ne se lève qu'à la fin
        base = (50, 42, 66)
        dawn = (110, 85, 95)
        return tuple(int(base[i] + (dawn[i] - base[i]) * k) for i in range(3))

    def draw_dungeon_scene(self, overlays=True):
        cam = self.visible_sprites
        cam.dt = self.dt
        cam.ambient = self.dungeon_ambient()
        cam.custom_draw(self.player)
        if not overlays:
            return
        self.draw_compass()
        self.draw_interaction_prompt()
        boss = self.boss if (self.boss is not None and self.boss.health > 0 and self.boss.state != 'sleep') else None
        self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour,
                        mode='dungeon', dt=self.dt, boss=boss)
        if self.minimap and not self.show_big_map:
            self.minimap.draw(self.screen, self.player.hitbox.center, self.minimap_markers())
        if getattr(self, 'current_dungeon_type', 'random') == 'major' and not self.is_multiplayer:
            rem = len([e for e in self.attackable_sprites if not isinstance(e, Boss)])
            label = "Gardien en éveil" if boss else ("Trouvez le Gardien" if self.boss_ref and self.boss_ref.alive()
                                                    else "Artefact libéré !")
            txt = render_outlined(f"{label}   ·   Monstres : {rem}", 20, (255, 200, 180), width=2)
            self.screen.blit(txt, txt.get_rect(center=(WIDTH // 2, 24)))
        else:
            remaining = max(0, (self.full_day_duration - self.game_time) / 1000)
            col = (255, 120, 90) if remaining < 30 else (210, 200, 230)
            txt = render_outlined(f"Aube dans {int(remaining) // 60}:{int(remaining) % 60:02d}   ·   "
                                  f"Monstres : {len(self.attackable_sprites)}", 20, col, width=2)
            self.screen.blit(txt, txt.get_rect(center=(WIDTH // 2, 24)))

    def minimap_markers(self):
        m = []
        if self.dungeon_entrance_rect:
            m.append((self.dungeon_entrance_rect.center, (110, 170, 255), 4, True))
        for c in self.chests:
            if not c.opened:
                m.append((c.rect.center, (255, 210, 80), 3, False))
        for e in self.attackable_sprites:
            if isinstance(e, Boss):
                m.append((e.hitbox.center, (255, 40, 40), 6, False))
            elif pygame.math.Vector2(e.hitbox.center).distance_to(self.player.hitbox.center) < 600:
                m.append((e.hitbox.center, (220, 60, 60), 2, False))
        for it in self.item_sprites:
            if it.type == 'artifact':
                m.append((it.rect.center, (255, 60, 120), 5, True))
        return m

    def draw_compass(self):
        if not self.dungeon_entrance_rect:
            return
        cam = self.visible_sprites
        px, py = cam.world_to_screen(self.dungeon_entrance_rect.center)
        if 0 <= px <= WIDTH and 0 <= py <= HEIGHT:
            return
        urgent = False
        if getattr(self, 'current_dungeon_type', 'random') != 'major':
            urgent = (self.full_day_duration - self.game_time) < 45000 or len(self.attackable_sprites) == 0
        else:
            urgent = getattr(self, 'major_dungeon_won', False)
        center = pygame.math.Vector2(WIDTH / 2, HEIGHT / 2)
        d = pygame.math.Vector2(px, py) - center
        if d.length() == 0:
            return
        d = d.normalize()
        edge = center + pygame.math.Vector2(d.x * (WIDTH / 2 - 60), d.y * (HEIGHT / 2 - 60))
        ang = math.atan2(d.y, d.x)
        pulse = 1 + (0.15 * math.sin(fx.time * 8) if urgent else 0)
        size = 16 * pulse
        pts = [(edge.x + math.cos(ang) * size, edge.y + math.sin(ang) * size),
               (edge.x + math.cos(ang + 2.5) * size, edge.y + math.sin(ang + 2.5) * size),
               (edge.x + math.cos(ang - 2.5) * size, edge.y + math.sin(ang - 2.5) * size)]
        col = (120, 180, 255) if not urgent else (255, 220, 120)
        if urgent:
            additive_glow(self.screen, int(edge.x), int(edge.y), 40, (60, 50, 20))
        pygame.draw.polygon(self.screen, col, pts)
        pygame.draw.polygon(self.screen, (10, 10, 20), pts, 2)
        dist = pygame.math.Vector2(self.dungeon_entrance_rect.center).distance_to(self.player.hitbox.center)
        lab = render_outlined(f"Portail {int(dist / TILE_SIZE)} m", 15, col, width=1)
        self.screen.blit(lab, lab.get_rect(center=(edge.x - d.x * 34, edge.y - d.y * 30)))

    def draw_interaction_prompt(self):
        if self.is_multiplayer:
            return
        chest = self.nearest_chest()
        if chest is not None:
            anchor, label = (chest.rect.centerx, chest.rect.top - 18), "[E] Ouvrir"
        elif self.can_extract():
            r = self.dungeon_entrance_rect
            anchor, label = (r.centerx, r.top - 60), "[E] Rentrer au village"
        else:
            return
        x, y = self.visible_sprites.world_to_screen(anchor)
        bob = math.sin(fx.time * 5) * 3
        box = render_outlined(label, 20, (255, 235, 180), width=2, bold=True)
        r = box.get_rect(center=(x, y + bob))
        bg = pygame.Surface(r.inflate(14, 8).size, pygame.SRCALPHA)
        bg.fill((10, 8, 14, 180))
        self.screen.blit(bg, r.inflate(14, 8).topleft)
        self.screen.blit(box, r)

    def draw_cursor(self):
        mx, my = pygame.mouse.get_pos()
        col = (255, 235, 200)
        pygame.draw.circle(self.screen, (0, 0, 0), (mx, my), 11, 3)
        pygame.draw.circle(self.screen, col, (mx, my), 10, 1)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(self.screen, col, (mx + dx * 5, my + dy * 5), (mx + dx * 14, my + dy * 14), 2)

    def draw_fps(self):
        if self.options.get('fps'):
            t = render_outlined(f"{self.clock.get_fps():.0f} FPS", 16, (180, 255, 180), width=1)
            self.screen.blit(t, (8, HEIGHT - 22 if self.game_state not in ('hub', 'dungeon') else 104))

    # ==================================================================
    # Menus
    # ==================================================================
    def _hover_sound(self, key):
        if key != self._hovered_btn:
            self._hovered_btn = key
            if key is not None:
                sfx('ui_hover', 0.6)

    def draw_main_menu(self):
        self.menu_bg.draw(self.screen, self.dt)
        self.menu_bg.draw_title(self.screen, 150)
        mouse = pygame.mouse.get_pos()
        hovered = None
        for btn in self.menu_buttons:
            label = btn['text']
            if btn['action'] == 'start_game':
                label = "CONTINUER" if self.has_save_file else "NOUVELLE PARTIE"
            h = btn['rect'].collidepoint(mouse)
            if h:
                hovered = btn['action']
            draw_button(self.screen, btn['rect'], label, h, danger=btn['action'] == 'quit_game', t=self.menu_bg.t)
        self._hover_sound(hovered)
        if self.has_save_file:
            p = self.player
            info = f"Niveau {p.level}   ·   Artefacts {p.artifacts}/4   ·   {p.stats.get('kills', 0)} monstres vaincus"
            s = render_outlined(info, 18, (200, 185, 160), width=2)
            self.screen.blit(s, s.get_rect(center=(WIDTH // 2, self.menu_buttons[0]['rect'].top - 26)))
        v = render_outlined(f"{GAME_VERSION}", 16, (140, 130, 120), width=1)
        self.screen.blit(v, (12, HEIGHT - 28))
        c = render_outlined("ZQSD/WASD : bouger · Clic : frapper · Espace : esquive", 16, (140, 130, 120), width=1)
        self.screen.blit(c, c.get_rect(bottomright=(WIDTH - 12, HEIGHT - 10)))
        self.draw_fps()
        pygame.display.flip()

    def draw_options_menu(self):
        self.menu_bg.draw(self.screen, self.dt)
        t = render_outlined("OPTIONS", 64, GOLD, width=3, bold=True)
        self.screen.blit(t, t.get_rect(center=(WIDTH // 2, 70)))
        labels = self.options_labels()
        mouse = pygame.mouse.get_pos()
        hovered = None
        for btn in self.options_buttons:
            h = btn['rect'].collidepoint(mouse)
            if h:
                hovered = btn['action']
            draw_button(self.screen, btn['rect'], labels.get(btn['action'], btn['text']), h,
                        danger=btn['action'] == 'reset_save', size=24, t=self.menu_bg.t)
        self._hover_sound(hovered)
        hint = render_outlined("Clic gauche : augmenter · Clic droit : diminuer", 16, TEXT_DIM, width=1)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 20)))
        self.draw_fps()
        pygame.display.flip()

    def pause_buttons(self):
        buttons = []
        if self.game_state == 'hub':
            buttons = [('resume', "REPRENDRE"), ('save_menu', "SAUVEGARDER & MENU")]
        elif self.game_state == 'dungeon':
            if self.is_multiplayer:
                buttons = [('resume', "REPRENDRE"), ('dungeon_to_menu', "QUITTER LA PARTIE")]
            else:
                buttons = [('resume', "REPRENDRE"), ('dungeon_to_hub', "FUIR (BUTIN PERDU)"),
                           ('dungeon_to_menu', "SAUVEGARDER & MENU")]
        rects = []
        for i, (action, text) in enumerate(buttons):
            r = pygame.Rect(0, 0, 320, 54)
            r.center = (WIDTH // 2 - 200, HEIGHT // 2 - 40 + i * 74)
            rects.append((action, text, r))
        return rects

    def check_pause_click(self, pos):
        for action, text, rect in self.pause_buttons():
            if rect.collidepoint(pos):
                sfx('ui_click')
                if action == 'resume':
                    self.paused = False
                elif action in ('save_menu', 'dungeon_to_menu'):
                    self.return_to_menu()
                elif action == 'dungeon_to_hub':
                    self.leave_dungeon_to_hub()
                return

    def leave_dungeon_to_hub(self):
        # Fuir par le menu revient à abandonner le butin de cette expédition
        inv = self.player.inventory
        inv['gold'] = max(0, inv['gold'] - self.run_stats.get('gold', 0))
        inv['iron'] = max(0, inv['iron'] - self.run_stats.get('iron', 0))
        self.audio.stop_all_loops()
        self.game_state = 'hub'
        self.game_time = 0
        self.hub.night_arrived = False
        self.paused = False
        self.visible_sprites.empty()
        self.obstacle_sprites.empty()
        self.attackable_sprites.empty()
        self.item_sprites.empty()
        fx.reset()
        self.boss = None
        self.player.obstacle_sprites = self.obstacle_sprites
        self.player.add(self.visible_sprites)
        self.player.pos.x = 0
        self.player.pos.y = 0
        self.player.hitbox.topleft = (0, 0)
        self.player.rect.midbottom = self.player.hitbox.midbottom
        self.hub.spawn_npcs(self.player)
        self.save_all()

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 4, 10, 200))
        self.screen.blit(overlay, (0, 0))
        t = render_outlined("PAUSE", 64, GOLD, width=3, bold=True)
        self.screen.blit(t, t.get_rect(center=(WIDTH // 2, 90)))
        mouse = pygame.mouse.get_pos()
        hovered = None
        for action, text, rect in self.pause_buttons():
            h = rect.collidepoint(mouse)
            if h:
                hovered = action
            draw_button(self.screen, rect, text, h, danger=action == 'dungeon_to_hub', size=24, t=fx.time)
        self._hover_sound(hovered)

        # Panneau des commandes & statistiques
        panel = pygame.Rect(WIDTH // 2 + 20, 160, 420, 430)
        draw_panel(self.screen, panel)
        lines = [("COMMANDES", GOLD),
                 ("ZQSD / WASD / Flèches : se déplacer", None),
                 ("Clic gauche : attaquer (combo x3)", None),
                 ("Clic droit / Maj : Tourbillon", None),
                 ("Espace : esquive (invulnérable)", None),
                 ("R / F : boire une potion", None),
                 ("E : ouvrir un coffre", None),
                 ("Tab / M : carte du donjon", None),
                 ("Échap : pause", None),
                 ("", None),
                 ("BÉNÉDICTIONS", GOLD)]
        perks = [f"{PERKS[k][0]} x{v}" for k, v in self.player.perks.items() if k in PERKS]
        if not perks:
            perks = ["Aucune pour l'instant"]
        y = panel.y + 22
        for text, col in lines:
            s = render_outlined(text, 20 if col else 18, col or (225, 215, 200), width=1, bold=bool(col))
            self.screen.blit(s, (panel.x + 22, y))
            y += 28 if col else 24
        txt = ", ".join(perks)
        font = get_font(17)
        words, line = txt.split(" "), ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] > panel.width - 44:
                self.screen.blit(font.render(line, True, (200, 190, 230)), (panel.x + 22, y))
                y += 22
                line = w
            else:
                line = test
        if line:
            self.screen.blit(font.render(line, True, (200, 190, 230)), (panel.x + 22, y))

    # ==================================================================
    # Transitions, mort, victoire
    # ==================================================================
    def draw_fade_transition(self):
        progress = self.transition_timer / max(0.01, self.transition_duration)
        if progress < 1 / 3:
            opacity = int((progress * 3) * 255)
        elif progress < 2 / 3:
            opacity = 255
        else:
            opacity = int((1 - (progress - 2 / 3) * 3) * 255)
        opacity = max(0, min(255, opacity))
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.set_alpha(opacity)
        fade_surface.fill((4, 2, 8))
        self.screen.blit(fade_surface, (0, 0))
        if opacity > 0:
            text_surface = render_outlined(self.transition_text, 52, (240, 225, 200), width=3, bold=True)
            text_surface.set_alpha(opacity)
            self.screen.blit(text_surface, text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
            if self.transition_sub:
                sub = render_outlined(self.transition_sub, 24, (190, 175, 150), width=2)
                sub.set_alpha(opacity)
                self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 42)))

    def run_report(self):
        r = self.run_stats
        return f"+{r['gold']} or   ·   +{r['iron']} fer   ·   {r['kills']} monstres vaincus"

    def _draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        t = getattr(self, '_go_t', 0.0) + self.dt
        self._go_t = t
        k = min(1.0, t / 1.2)
        overlay.fill((40, 0, 4, int(200 * k)))
        self.screen.blit(overlay, (0, 0))
        title = render_outlined("VOUS AVEZ PÉRI", 92, (220, 40, 40), width=4, bold=True)
        title.set_alpha(int(255 * k))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 120)))
        sub = render_outlined("La cupidité a eu raison de vous... votre butin est perdu.", 24, (220, 180, 170), width=2)
        sub.set_alpha(int(255 * k))
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 55)))
        r = self.run_stats
        dur = int(time.time() - r['start'])
        stats = [("Monstres vaincus", r['kills']), ("Élites", r['elites']), ("Dégâts infligés", r['damage']),
                 ("Coffres ouverts", r['chests']), ("Temps survécu", f"{dur // 60}:{dur % 60:02d}")]
        y = HEIGHT // 2 - 15
        for i, (name, val) in enumerate(stats):
            if t < 0.6 + i * 0.12:
                break
            a = render_outlined(name, 22, (200, 190, 180), width=2)
            b = render_outlined(str(val), 22, GOLD, width=2, bold=True)
            self.screen.blit(a, a.get_rect(midright=(WIDTH // 2 + 20, y)))
            self.screen.blit(b, b.get_rect(midleft=(WIDTH // 2 + 40, y)))
            y += 30
        btn = getattr(self, '_go_btn', None)
        if btn and t > 1.0:
            draw_button(self.screen, btn, "RETOUR AU MENU", btn.collidepoint(pygame.mouse.get_pos()), size=26, t=t)

    def draw_victory(self):
        self.victory_t += self.dt
        t = self.victory_t
        self.menu_bg.draw(self.screen, self.dt)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 6, 2, 120))
        self.screen.blit(overlay, (0, 0))
        if random.random() < 0.3:
            self.menu_bg.particles.emit(random.randint(0, WIDTH), -10, 1,
                                        lambda: random.choice([(255, 210, 90), (255, 160, 60), (255, 240, 180)]),
                                        speed=(60, 140), life=(3, 5), size=(2, 4), angle=math.pi / 2, spread=0.6,
                                        drag=0.1, glow=True)
        title = render_outlined("VICTOIRE", 110, GOLD, width=4, bold=True)
        sc = 1 + max(0.0, 0.6 - t) * 0.6
        if sc != 1:
            title = pygame.transform.rotozoom(title, 0, sc)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        lines = [
            "Les quatre Artefacts sont réunis.",
            "Le Seigneur de la Cupidité s'est effondré dans son propre trésor,",
            "et la lumière revient enfin sur le royaume.",
        ]
        y = 205
        for i, l in enumerate(lines):
            if t > 0.8 + i * 0.6:
                s = render_outlined(l, 24, (235, 220, 200), width=2)
                self.screen.blit(s, s.get_rect(center=(WIDTH // 2, y)))
            y += 32
        p = self.player
        st = p.stats
        stats = [("Niveau atteint", p.level), ("Monstres vaincus", st.get('kills', 0)),
                 ("Gardiens terrassés", st.get('bosses', 0)), ("Expéditions", st.get('expeditions', 0)),
                 ("Coffres ouverts", st.get('chests', 0)), ("Morts", st.get('deaths', 0))]
        panel = pygame.Rect(WIDTH // 2 - 230, 320, 460, 230)
        if t > 2.6:
            draw_panel(self.screen, panel)
            yy = panel.y + 24
            for name, val in stats:
                a = render_outlined(name, 22, (210, 200, 185), width=1)
                b = render_outlined(str(val), 22, GOLD, width=1, bold=True)
                self.screen.blit(a, (panel.x + 30, yy))
                self.screen.blit(b, b.get_rect(topright=(panel.right - 30, yy)))
                yy += 33
        credits = "Greed - par Louis Da Costa, Ghita Abelaoui, Adam Sellam & Amine Aaddi"
        c = render_outlined(credits, 18, (170, 150, 120), width=1)
        self.screen.blit(c, c.get_rect(center=(WIDTH // 2, HEIGHT - 70)))
        if t > 3.5:
            k = render_outlined("Cliquez pour revenir au menu (votre héros garde sa puissance)", 20,
                                (230, 220, 200) if int(t * 2) % 2 == 0 else (170, 160, 150), width=2)
            self.screen.blit(k, k.get_rect(center=(WIDTH // 2, HEIGHT - 34)))
        pygame.display.flip()
