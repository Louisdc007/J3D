"""Minimap du donjon avec brouillard de guerre."""
import pygame
from settings import *


class Minimap:
    CELL = 3          # pixels par case (petite carte)
    REVEAL = 6        # rayon de révélation (en cases)

    def __init__(self, floor_cells, width=100, height=100):
        self.w, self.h = width, height
        self.floor = set(floor_cells)
        c = self.CELL
        self.base = pygame.Surface((width * c, height * c), pygame.SRCALPHA)
        for (x, y) in self.floor:
            self.base.fill((150, 140, 125, 255), (x * c, y * c, c, c))
        # bords des salles
        for (x, y) in self.floor:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + dx, y + dy) not in self.floor:
                    self.base.fill((90, 80, 70, 255), ((x + dx) * c, (y + dy) * c, c, c))
        self.fog = pygame.Surface(self.base.get_size(), pygame.SRCALPHA)
        self.fog.fill((0, 0, 0, 255))
        self.explored = set()
        self.last_cell = None
        self.big = False

    def reveal(self, world_pos):
        cx, cy = int(world_pos[0] // TILE_SIZE), int(world_pos[1] // TILE_SIZE)
        if (cx, cy) == self.last_cell:
            return
        self.last_cell = (cx, cy)
        r = self.REVEAL
        c = self.CELL
        for x in range(cx - r, cx + r + 1):
            for y in range(cy - r, cy + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (x, y) not in self.explored:
                    self.explored.add((x, y))
                    self.fog.fill((0, 0, 0, 0), (x * c, y * c, c, c))

    def is_explored(self, world_pos):
        return (int(world_pos[0] // TILE_SIZE), int(world_pos[1] // TILE_SIZE)) in self.explored

    def draw(self, surface, player_pos, markers, big=False):
        """markers : liste de (pos_monde, couleur, rayon, toujours_visible)."""
        c = self.CELL
        if big:
            view_w, view_h = 760, 560
            scale = min(view_w / self.base.get_width(), view_h / self.base.get_height())
            scaled_w, scaled_h = int(self.base.get_width() * scale), int(self.base.get_height() * scale)
            frame = pygame.Rect(0, 0, scaled_w + 20, scaled_h + 20)
            frame.center = (WIDTH // 2, HEIGHT // 2)
            from fx import draw_panel, render_outlined
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            surface.blit(dim, (0, 0))
            draw_panel(surface, frame, alpha=235)
            comp = self.base.copy()
            comp.blit(self.fog, (0, 0))
            comp = pygame.transform.scale(comp, (scaled_w, scaled_h))
            ox, oy = frame.x + 10, frame.y + 10
            surface.blit(comp, (ox, oy))
            k = scale * c / TILE_SIZE
            for pos, col, rad, always in markers:
                if always or self.is_explored(pos):
                    pygame.draw.circle(surface, col, (int(ox + pos[0] * k), int(oy + pos[1] * k)), rad + 2)
            pygame.draw.circle(surface, (255, 255, 255), (int(ox + player_pos[0] * k), int(oy + player_pos[1] * k)), 5)
            title = render_outlined("CARTE DU DONJON  (Tab)", 24, GOLD)
            surface.blit(title, title.get_rect(midbottom=(frame.centerx, frame.top - 6)))
            return

        size = 190
        rect = pygame.Rect(WIDTH - size - 16, 62, size, size)
        view = pygame.Surface((size, size), pygame.SRCALPHA)
        view.fill((10, 8, 14, 215))
        px, py = player_pos[0] / TILE_SIZE * c, player_pos[1] / TILE_SIZE * c
        off = (size // 2 - px, size // 2 - py)
        view.blit(self.base, off)
        view.blit(self.fog, off)
        k = c / TILE_SIZE
        for pos, col, rad, always in markers:
            if always or self.is_explored(pos):
                mx, my = pos[0] * k + off[0], pos[1] * k + off[1]
                if 0 <= mx < size and 0 <= my < size:
                    pygame.draw.circle(view, col, (int(mx), int(my)), rad)
        pygame.draw.circle(view, (255, 255, 255), (size // 2, size // 2), 3)
        # masque circulaire
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
        view.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(view, rect.topleft)
        pygame.draw.circle(surface, PANEL_BORDER, rect.center, size // 2, 3)
        pygame.draw.circle(surface, (40, 30, 20), rect.center, size // 2 + 3, 2)
        # repère nord
        from fx import render_outlined
        n = render_outlined("N", 18, GOLD)
        surface.blit(n, n.get_rect(center=(rect.centerx, rect.top + 2)))
