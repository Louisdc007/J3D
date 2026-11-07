import pygame
import random
import os
from settings import *

class Tile(pygame.sprite.Sprite):
    _wall_images = []  # list of loaded wall variants

    def __init__(self, pos, groups):
        super().__init__(groups)
        if not Tile._wall_images:
            Tile._load_wall_images()
        self.image = random.choice(Tile._wall_images) if Tile._wall_images else pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(topleft=pos)

    def update(self, dt=0.016):
        pass

    @classmethod
    def _load_wall_images(cls):
        wall_dir = resource_path(os.path.join('assets', 'wall'))
        # (filename, weight per tile) — mossy wall tiles appear ~25% of the time overall
        variants = [('brick wall.png', 3), ('brick wall moss.png', 1)]
        for filename, weight in variants:
            path = os.path.join(wall_dir, filename)
            try:
                sheet = pygame.image.load(path).convert_alpha()
                sw, sh = sheet.get_size()
                # Slice into 3x3 = 9 individual tiles
                for row in range(3):
                    for col in range(3):
                        rect = pygame.Rect(col * sw // 3, row * sh // 3, sw // 3, sh // 3)
                        tile = sheet.subsurface(rect).copy()
                        tile = pygame.transform.scale(tile, (TILE_SIZE, TILE_SIZE))
                        for _ in range(weight):
                            cls._wall_images.append(tile)
            except Exception as e:
                print(f"Could not load wall image {filename}: {e}")
        if not cls._wall_images:
            fallback = pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
            fallback.fill('gray')
            cls._wall_images.append(fallback)

class Floor(pygame.sprite.Sprite):
    _floor_images = []
    _images_loaded = False

    def __init__(self, pos, groups):
        super().__init__(groups)
        
        if not Floor._images_loaded:
            Floor.load_images()
            
        if layer_images := Floor._floor_images:
            # 4 base tile variants + 2 decors — bones/skulls at ~1 in 80
            n_base = 4
            n_decor = len(layer_images) - n_base
            weights = [80] * n_base + [1] * n_decor
            if len(weights) != len(layer_images):
                weights = [1] * len(layer_images)
            idx = random.choices(range(len(layer_images)), weights=weights, k=1)[0]
            self.image = layer_images[idx]
        else:
            self.image = pygame.surface.Surface((TILE_SIZE, TILE_SIZE))
            self.image.fill((20, 20, 20)) # Dark floor if no assets
        
        self.rect = self.image.get_rect(topleft=pos)

    def update(self, dt=0.016):
        pass

    @classmethod
    def load_images(cls):
        cls._images_loaded = True
        floor_assets_path = resource_path(os.path.join('assets', 'floor_assets'))
        if not os.path.exists(floor_assets_path):
            return
        
        # Load base floor tile sheet and split into 2x2 = 4 individual tiles
        base_tiles = []
        try:
            sheet = pygame.image.load(os.path.join(floor_assets_path, 'floor tiles.png')).convert_alpha()
            sw, sh = sheet.get_size()
            # Split into 2 cols x 2 rows
            for row in range(2):
                for col in range(2):
                    rect = pygame.Rect(col * sw // 2, row * sh // 2, sw // 2, sh // 2)
                    tile = sheet.subsurface(rect).copy()
                    tile = pygame.transform.scale(tile, (TILE_SIZE, TILE_SIZE))
                    base_tiles.append(tile)
                    cls._floor_images.append(tile)
        except Exception as e:
            print(f"Error loading base floor sheet: {e}")
        
        # For decor PNGs (bone, skull), composite them on top of a base tile
        # so transparent pixels show the floor texture beneath instead of black
        for filename in ['bone.png.png', 'skull.png']:
            try:
                decor = pygame.image.load(os.path.join(floor_assets_path, filename)).convert_alpha()
                # Scale decor to half the tile size, then center it on the base tile
                decor_size = TILE_SIZE // 2
                decor = pygame.transform.scale(decor, (decor_size, decor_size))
                
                base = base_tiles[0] if base_tiles else None
                if base:
                    composite = base.copy()
                    offset = (TILE_SIZE - decor_size) // 2
                    composite.blit(decor, (offset, offset))
                    cls._floor_images.append(composite)
                else:
                    cls._floor_images.append(decor)
            except Exception as e:
                print(f"Error loading floor decor {filename}: {e}")

class DungeonEntrance(pygame.sprite.Sprite):
    """Portail de retour au village : vortex animé + lumière.
    `rect` (64x64) reste la zone d'extraction utilisée par le jeu."""
    _frames = None
    SIZE = 128

    def __init__(self, pos, groups):
        super().__init__(groups)
        if DungeonEntrance._frames is None:
            DungeonEntrance._frames = [self._make_frame(i / 32) for i in range(32)]
        self.frame = 0.0
        self.image = DungeonEntrance._frames[0]
        self.rect = pygame.Rect(pos[0], pos[1], TILE_SIZE, TILE_SIZE)
        self.draw_rect = self.image.get_rect(center=self.rect.center)
        self.is_portal = True

    @classmethod
    def _make_frame(cls, t):
        import math
        S = cls.SIZE
        s = pygame.Surface((S, S), pygame.SRCALPHA)
        c = S // 2
        # anneau de pierre runique
        pygame.draw.ellipse(s, (40, 36, 48), (6, 30, S - 12, S - 60))
        pygame.draw.ellipse(s, (85, 80, 100), (6, 30, S - 12, S - 60), 4)
        # vortex : bras spiralés
        for arm in range(4):
            for k in range(26):
                u = k / 26
                ang = t * math.tau + arm * math.tau / 4 + u * 4.0
                r = 6 + u * (c - 20)
                x = c + math.cos(ang) * r
                y = c + math.sin(ang) * r * 0.55
                col = (int(90 + 120 * (1 - u)), int(60 + 180 * (1 - u)), 255, int(255 * (1 - u * 0.7)))
                pygame.draw.circle(s, col, (int(x), int(y)), max(1, int(6 * (1 - u)) + 1))
        pygame.draw.ellipse(s, (230, 240, 255, 230), (c - 9, c - 5, 18, 10))
        # runes clignotantes autour
        for i in range(8):
            ang = i / 8 * math.tau
            x = c + math.cos(ang) * (c - 10)
            y = c + math.sin(ang) * (c - 34)
            a = int(140 + 115 * math.sin(t * math.tau * 2 + i))
            pygame.draw.circle(s, (120, 200, 255, max(0, a)), (int(x), int(y)), 3)
        return s

    def update(self, dt=0.016):
        self.frame = (self.frame + dt * 20) % len(DungeonEntrance._frames)
        self.image = DungeonEntrance._frames[int(self.frame)]
        self.draw_rect = self.image.get_rect(center=self.rect.center)
