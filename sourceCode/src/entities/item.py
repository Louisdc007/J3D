import pygame

class Item(pygame.sprite.Sprite):
    def __init__(self, pos, groups, type):
        super().__init__(groups)

        self.type = type

        self.image = pygame.Surface((16, 16))
        if type == 'gold':
            self.image.fill((255, 215, 0))
        elif type == 'iron':
            self.image.fill((172, 169, 164))
        elif type == 'xp':
            self.image.fill((93, 179, 103))
        elif type == 'health':
            self.image.fill((178, 53, 45))

        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)

    def update(self, dt=0.016):
        pass