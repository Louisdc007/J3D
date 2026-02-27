import pygame
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRIEND_SRC = os.path.dirname(CURRENT_DIR)

if FRIEND_SRC not in sys.path:
    sys.path.insert(0, FRIEND_SRC)

try:
    from camera import CameraGroup
    from entities.player import Player as VisualPlayer
    print("DEBUG: Classes chargées avec succès !")
except ImportError as e:
    print(f"ERREUR IMPORT : Impossible de trouver les fichiers dans {FRIEND_SRC}")
    print(f"Détails : {e}")

from .network import Network
from .common.constants import *

def run_multiplayer():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("J3D - Mode Multijoueur")

    n = Network()
    if n.p is None:
        print("ERREUR : Impossible de se connecter au serveur. Vérifie qu'il est bien lancé !")
        pygame.quit()
        return

    initial_data = n.p
    player_id = initial_data.get('player_id', 0)
    spawn_pos = initial_data.get('spawn_pos', (WORLD_WIDTH//2, WORLD_HEIGHT//2))

    camera_group = CameraGroup()
    dummy_obstacles = pygame.sprite.Group()

    try:
        drawer_me = VisualPlayer(spawn_pos, camera_group, dummy_obstacles)
    except TypeError:
        try:
            drawer_me = VisualPlayer(camera_group, dummy_obstacles)
            drawer_me.rect.center = spawn_pos
        except TypeError as e:
            print(f"ERREUR FATALE : Arguments attendus inconnus : {e}")
            pygame.quit()
            return

    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(FPS)
        
        keys = pygame.key.get_pressed()
        inputs = {
            'z': keys[pygame.K_z], 's': keys[pygame.K_s],
            'q': keys[pygame.K_q], 'd': keys[pygame.K_d],
            'space': keys[pygame.K_SPACE]
        }

        payload = {
            'keys': inputs,
            'killed_enemies': [],
            'enemy_positions': {}
        }

        server_data = n.send(payload)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if server_data:
            all_players_data, dead_enemies, server_enemies = server_data
            
            if player_id in all_players_data:
                server_me = all_players_data[player_id]
                drawer_me.rect.x = server_me.x
                drawer_me.rect.y = server_me.y
                
                if hasattr(drawer_me, 'pos'):
                    drawer_me.pos.x = server_me.x
                    drawer_me.pos.y = server_me.y

        screen.fill(GRAY)

        offset = pygame.math.Vector2()
        offset.x = drawer_me.rect.centerx - SCREEN_WIDTH // 2
        offset.y = drawer_me.rect.centery - SCREEN_HEIGHT // 2

        if server_data:
            for other_id, p_data in all_players_data.items():
                if other_id != player_id:
                    other_rect = pygame.Rect(p_data.x - offset.x, p_data.y - offset.y, 40, 40)
                    pygame.draw.rect(screen, BLUE, other_rect)

        camera_group.custom_draw(drawer_me)
        pygame.display.flip()

    pygame.quit()