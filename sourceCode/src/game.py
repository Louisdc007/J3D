import pygame
import sys
from settings import *
from entities.player import *
from camera import CameraGroup

#uniquement pour le test
import random

class Game() :
    def __init__(self) :
        pygame.init()
        self.screen = pygame.display.set_mode(size = (WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.clock = pygame.time.Clock()
        self.visible_sprites = CameraGroup()
        self.player = Player((WIDTH//2, HEIGHT//2), [self.visible_sprites])


        # Test de la caméra : on crée des obstacles aléatoires
        for i in range(20):
            x = random.randint(0, 2000)
            y = random.randint(0, 2000)
            
            sprite = pygame.sprite.Sprite(self.visible_sprites)
            sprite.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            sprite.image.fill('gray')
            sprite.rect = sprite.image.get_rect(topleft=(x,y))

    def events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def draw(self) :
        self.screen.fill('black')
        self.visible_sprites.custom_draw(self.player)
        pygame.display.flip()
        

    def update(self):
        self.visible_sprites.update()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
    
    