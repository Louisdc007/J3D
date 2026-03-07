import pygame
from settings import *

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
        self.half_w = WIDTH / 2
        self.half_h = HEIGHT / 2

        # Player oval shadow — pre-built once
        self._player_shadow = pygame.Surface((52, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(self._player_shadow, (0, 0, 0, 90), self._player_shadow.get_rect())

        # Wall floor-shadow strip — same width as a tile, short height
        self._wall_shadow = pygame.Surface((TILE_SIZE, 20), pygame.SRCALPHA)
        self._wall_shadow.fill((0, 0, 0, 60))

    def custom_draw(self, player):
        from tile import Floor, Tile
        from entities.player import Player

        self.offset.x = player.pos.x - self.half_w
        self.offset.y = player.pos.y - self.half_h

        ox, oy = int(self.offset.x), int(self.offset.y)
        blit = self.display_surface.blit

        # Pass 1 — floor tiles
        for sprite in self.sprites():
            if isinstance(sprite, Floor):
                blit(sprite.image, (sprite.rect.x - ox, sprite.rect.y - oy))

        # Pass 2 — wall shadows projected onto the floor below each wall tile
        for sprite in self.sprites():
            if isinstance(sprite, Tile):
                sx = sprite.rect.x - ox
                sy = sprite.rect.bottom - oy - 4   # just below the wall, overlapping the floor
                blit(self._wall_shadow, (sx, sy))

        # Pass 3 — entity shadows (on the floor, before entities)
        from entities.enemy import Enemy
        for sprite in self.sprites():
            if isinstance(sprite, (Player, Enemy)):
                # Shadow size/offset based on type
                if isinstance(sprite, Player):
                    sw, sh = 52, 18
                    shadow_surf = self._player_shadow
                else: # Enemy
                    sw, sh = 80, 26 # Smaller, more centered shadow for the massive orcs
                    shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), shadow_surf.get_rect())
                
                sx = sprite.rect.centerx - (sw // 2) - ox
                sy = sprite.rect.bottom - (sh // 2) - oy
                blit(shadow_surf, (sx, sy))

        # Pass 4 — everything else (walls, enemies, items, weapons…)
        for sprite in self.sprites():
            if not isinstance(sprite, Floor):
                blit(sprite.image, (sprite.rect.x - ox, sprite.rect.y - oy))