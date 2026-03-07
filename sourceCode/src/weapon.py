import pygame

class Weapon(pygame.sprite.Sprite):
    def __init__(self, player, groups, direction):
        super().__init__(groups)
        self.image = pygame.Surface((60, 20), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0)) # Fully transparent so it doesn't show the blue rectangle anymore

        distance = 15

        offset = direction * distance

        ref_vect = pygame.math.Vector2((1, 0))
        angle = ref_vect.angle_to(direction)

        self.image = pygame.transform.rotozoom(self.image, -angle, 1)

        self.rect = self.image.get_rect()
        self.rect.center = player.rect.center + offset