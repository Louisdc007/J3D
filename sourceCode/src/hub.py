import pygame
from settings import *


class Hub:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()

        self.background = pygame.Surface((WIDTH, HEIGHT))
        self.background.fill((50, 168, 82))

        self.tent_rect = pygame.Rect(100, 100, 200, 150)
        self.forge_rect = pygame.Rect(900, 100, 200, 150)
        self.gate_rect = pygame.Rect(540, 500, 200, 100)

    def draw(self):
        self.display_surface.blit(self.background, (0, 0))

        pygame.draw.rect(self.display_surface, (50, 50, 200), self.tent_rect)
        pygame.draw.rect(self.display_surface, (100, 100, 100), self.forge_rect)
        pygame.draw.rect(self.display_surface, (100, 50, 0), self.gate_rect)

    def check_click(self, pos):
        if self.gate_rect.collidepoint(pos):
            return "dungeon"
        return None