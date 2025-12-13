import pygame
from settings import *

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
        self.half_w = WIDTH / 2
        self.half_h = HEIGHT / 2
    
    def custom_draw(self, player):
        self.offset.x = player.pos.x - self.half_w
        self.offset.y = player.pos.y - self.half_h

        for sprite in self.sprites():
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)