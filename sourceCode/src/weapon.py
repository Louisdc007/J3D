import pygame


class Weapon(pygame.sprite.Sprite):
    """Zone de frappe invisible de l'épée (l'arc visuel est dessiné par fx)."""

    def __init__(self, player, groups, direction, size=(120, 84), distance=50):
        super().__init__(groups)
        direction = pygame.math.Vector2(direction)
        base = pygame.Surface(size, pygame.SRCALPHA)
        if direction.length_squared() > 0:
            angle = pygame.math.Vector2(1, 0).angle_to(direction)
            base = pygame.transform.rotate(base, -angle)
        self.image = base
        self.rect = self.image.get_rect()
        # centrée sur le corps du joueur (et non sur son grand rectangle visuel)
        self.rect.center = pygame.math.Vector2(player.hitbox.center) + pygame.math.Vector2(0, -22) + direction * distance
        self.is_weapon = True

    def update(self, dt=0.016):
        pass
