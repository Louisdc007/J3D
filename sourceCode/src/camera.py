import math
import pygame
from settings import *
from fx import fx, Lighting, vignette, additive_glow, render_outlined, get_font


class CameraGroup(pygame.sprite.Group):
    """Caméra du donjon.

    * le décor statique (sols / murs) est rangé dans une grille et seules les
      cases visibles sont dessinées (culling) ;
    * les entités sont triées en profondeur (y-sort) ;
    * suivi fluide avec anticipation vers la souris + secousses d'écran ;
    * éclairage dynamique (torche du joueur, flambeaux, portail, projectiles).
    """

    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
        self.half_w = WIDTH / 2
        self.half_h = HEIGHT / 2
        self.floor_grid = {}
        self.wall_grid = {}
        self._chunks = {}
        self.snap_next = True
        self.dt = 1 / 60
        self.lighting = Lighting()
        self.lighting_enabled = True
        self.ambient = (38, 32, 52)
        self.player_light = 340

        # Ombres pré-calculées
        self._player_shadow = pygame.Surface((52, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(self._player_shadow, (0, 0, 0, 90), self._player_shadow.get_rect())
        self._wall_shadow = pygame.Surface((TILE_SIZE, 22), pygame.SRCALPHA)
        for y in range(22):
            self._wall_shadow.fill((0, 0, 0, int(110 * (1 - y / 22))), (0, y, TILE_SIZE, 1))
        self._wall_front = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        for y in range(TILE_SIZE):
            k = y / TILE_SIZE
            if k > 0.55:
                self._wall_front.fill((0, 0, 0, int(150 * (k - 0.55) / 0.45)), (0, y, TILE_SIZE, 1))
        self._wall_top_edge = pygame.Surface((TILE_SIZE, 4), pygame.SRCALPHA)
        self._wall_top_edge.fill((255, 240, 220, 40))
        self._enemy_shadow_standard = pygame.Surface((80, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(self._enemy_shadow_standard, (0, 0, 0, 90), self._enemy_shadow_standard.get_rect())
        sw_c, sh_c = int(80 / 1.5), int(26 / 1.5)
        self._enemy_shadow_centered = pygame.Surface((sw_c, sh_c), pygame.SRCALPHA)
        pygame.draw.ellipse(self._enemy_shadow_centered, (0, 0, 0, 90), self._enemy_shadow_centered.get_rect())
        self._boss_shadow = pygame.Surface((170, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(self._boss_shadow, (0, 0, 0, 120), self._boss_shadow.get_rect())

    # ------------------------------------------------------------------
    def set_level(self, floors, walls):
        """Enregistre le décor statique (listes de sprites Floor / Tile)."""
        self.floor_grid = {(f.rect.x // TILE_SIZE, f.rect.y // TILE_SIZE): f for f in floors}
        self.wall_grid = {}
        for w in walls:
            key = (w.rect.x // TILE_SIZE, w.rect.y // TILE_SIZE)
            below = (key[0], key[1] + 1) in self.floor_grid
            above = (key[0], key[1] - 1) in self.floor_grid
            self.wall_grid[key] = (w, below, above)
        self.snap_next = True
        self._chunks = {}

    CHUNK = 512  # pixels (8x8 tuiles)

    def _get_chunk(self, kx, ky):
        """Pré-rend un bloc de décor statique (sols, murs, ombres) pour éviter
        des centaines de blits par image."""
        key = (kx, ky)
        surf = self._chunks.get(key)
        if surf is not None:
            return surf
        C = self.CHUNK
        n = C // TILE_SIZE
        x0, y0 = kx * n, ky * n
        surf = pygame.Surface((C, C))
        surf.fill((0, 0, 0))
        empty = True
        for cx in range(x0, x0 + n):
            for cy in range(y0, y0 + n):
                f = self.floor_grid.get((cx, cy))
                if f is not None:
                    surf.blit(f.image, ((cx - x0) * TILE_SIZE, (cy - y0) * TILE_SIZE))
                    empty = False
        for cx in range(x0, x0 + n):
            for cy in range(y0 - 1, y0 + n):
                w = self.wall_grid.get((cx, cy))
                if w is None:
                    continue
                tile, below, above = w
                x, y = (cx - x0) * TILE_SIZE, (cy - y0) * TILE_SIZE
                surf.blit(tile.image, (x, y))
                empty = False
                if below:
                    surf.blit(self._wall_front, (x, y))
                    surf.blit(self._wall_shadow, (x, y + TILE_SIZE))
                if above:
                    surf.blit(self._wall_top_edge, (x, y))
        if empty:
            surf = False
        if len(self._chunks) > 48:
            self._chunks.clear()
        self._chunks[key] = surf
        return surf

    def clear_level(self):
        self.floor_grid = {}
        self.wall_grid = {}
        self._chunks = {}

    def empty(self):
        super().empty()
        self.clear_level()

    # ------------------------------------------------------------------
    def _update_offset(self, player):
        target = pygame.math.Vector2(player.hitbox.center)
        if not getattr(player, 'is_remote', False) and player.health > 0:
            mouse = pygame.math.Vector2(pygame.mouse.get_pos()) - pygame.math.Vector2(self.half_w, self.half_h)
            target += mouse * 0.12
        desired = target - pygame.math.Vector2(self.half_w, self.half_h - 20)
        if self.snap_next:
            self.offset = desired
            self.snap_next = False
        else:
            k = 1 - math.exp(-10 * self.dt)
            self.offset += (desired - self.offset) * k

    def world_to_screen(self, pos):
        return pos[0] - self._ox, pos[1] - self._oy

    def custom_draw(self, player):
        from entities.player import Player
        from entities.enemy import Enemy
        from entities.item import Item

        self._update_offset(player)
        sx, sy = fx.shake_offset()
        ox, oy = int(self.offset.x + sx), int(self.offset.y + sy)
        self._ox, self._oy = ox, oy
        surf = self.display_surface
        blit = surf.blit
        surf.fill((0, 0, 0))

        player.screen_center = (player.hitbox.centerx - ox, player.hitbox.centery - 22 - oy)

        # --- Décor statique visible (blocs pré-rendus) --------------------
        C = self.CHUNK
        for kx in range(ox // C, (ox + WIDTH) // C + 1):
            for ky in range(oy // C, (oy + HEIGHT) // C + 1):
                chunk = self._get_chunk(kx, ky)
                if chunk:
                    blit(chunk, (kx * C - ox, ky * C - oy))

        fx.draw_ground(surf, ox, oy)

        # --- Classement des sprites ----------------------------------------
        view = pygame.Rect(ox - 400, oy - 400, WIDTH + 800, HEIGHT + 800)
        entities, flat, lights_world = [], [], []
        for sprite in self.sprites():
            if getattr(sprite, 'is_weapon', False):
                continue
            r = getattr(sprite, 'draw_rect', None) or sprite.rect
            if not view.colliderect(r):
                continue
            if isinstance(sprite, Item) or getattr(sprite, 'is_portal', False):
                flat.append(sprite)
            else:
                entities.append(sprite)
            if getattr(sprite, 'is_portal', False):
                lights_world.append((sprite.rect.centerx, sprite.rect.centery, 260, (120, 140, 255)))
            elif hasattr(sprite, 'light_pos'):
                fl = sprite.flicker(fx.time) if hasattr(sprite, 'flicker') else 1
                lights_world.append((sprite.light_pos[0], sprite.light_pos[1], 230 * fl, (255, 170, 90)))
            elif isinstance(sprite, Item):
                lights_world.append((sprite.rect.centerx, sprite.rect.centery, 46, sprite.glow_color))
            elif isinstance(sprite, Player) and sprite is not player and sprite.health > 0:
                lights_world.append((sprite.hitbox.centerx, sprite.hitbox.centery - 20, 260, (255, 210, 160)))

        # --- Ombres --------------------------------------------------------
        for sprite in entities:
            if isinstance(sprite, Player):
                shadow, sw, sh = self._player_shadow, 52, 18
            elif isinstance(sprite, Enemy):
                if sprite.tier == 'boss':
                    shadow, sw, sh = self._boss_shadow, 170, 50
                elif getattr(sprite, 'is_centered', False):
                    shadow, sw, sh = self._enemy_shadow_centered, int(80 / 1.5), int(26 / 1.5)
                else:
                    shadow, sw, sh = self._enemy_shadow_standard, 80, 26
            else:
                continue
            blit(shadow, (sprite.hitbox.centerx - sw // 2 - ox, sprite.hitbox.bottom - sh // 2 - oy))

        # --- Objets au sol puis entités triées en profondeur ----------------
        for sprite in flat:
            r = getattr(sprite, 'draw_rect', None) or sprite.rect
            blit(sprite.image, (r.x - ox, r.y - oy))

        def depth(s):
            hb = getattr(s, 'hitbox', None)
            return hb.bottom if hb is not None else s.rect.bottom
        entities.sort(key=depth)
        for sprite in entities:
            if isinstance(sprite, Enemy) and sprite.elite:
                gx, gy = sprite.body_center()
                additive_glow(surf, int(gx - ox), int(gy - oy), 60, (90, 70, 10))
            blit(sprite.image, (sprite.rect.x - ox, sprite.rect.y - oy))

        fx.draw_world(surf, ox, oy)

        # --- Éclairage -------------------------------------------------------
        if self.lighting_enabled:
            L = self.lighting
            L.begin(self.ambient)
            fl = 1 + 0.04 * math.sin(fx.time * 11) + 0.03 * math.sin(fx.time * 27)
            px, py = player.screen_center
            L.add(px, py, self.player_light * fl, (255, 225, 180))
            L.add(px, py, 120, (120, 100, 80))
            for wx, wy, rad, col in lights_world:
                L.add(wx - ox, wy - oy, rad, col)
            for p in fx.projectiles:
                L.add(p.pos.x - ox, p.pos.y - oy, 110, p.color)
            for s in fx.slashes:
                L.add(s.x - ox, s.y - oy, 150, (140, 150, 170))
            L.apply(surf)

        # --- Passe lumineuse additive --------------------------------------
        for sprite in flat:
            if isinstance(sprite, Item):
                additive_glow(surf, sprite.rect.centerx - ox, sprite.rect.centery - oy, 22, sprite.glow_color)
        fx.draw_glow(surf, ox, oy)

        # --- Surcouches lisibles (barres de vie, textes) ----------------------
        for sprite in entities:
            if isinstance(sprite, Enemy) and sprite.tier != 'boss' and sprite.health > 0:
                if sprite.health < sprite.max_health or sprite.elite:
                    hx, hy = sprite.head_pos()
                    self._draw_enemy_bar(surf, hx - ox, hy - oy - 12, sprite)
        fx.draw_texts(surf, ox, oy)
        blit(vignette(), (0, 0))

    def _draw_enemy_bar(self, surf, x, y, enemy):
        w = 56 if not enemy.elite else 76
        ratio = max(0.0, enemy.health / max(1, enemy.max_health))
        rect = pygame.Rect(int(x - w / 2), int(y), w, 7)
        pygame.draw.rect(surf, (15, 10, 10), rect.inflate(2, 2))
        pygame.draw.rect(surf, (70, 20, 20), rect)
        fill = rect.copy()
        fill.width = int(w * ratio)
        pygame.draw.rect(surf, (230, 60, 50) if not enemy.elite else (240, 190, 60), fill)
        pygame.draw.line(surf, (255, 255, 255), fill.topleft, (fill.right - 1, fill.top), 1)
        if enemy.elite:
            name = render_outlined(enemy.name.upper(), 15, GOLD, width=1, bold=True)
            surf.blit(name, name.get_rect(midbottom=(x, y - 2)))
