import pygame
import sys
import os

#trouver dossier sys dep solo
# On remonte de 'common' vers 'systeme_multijoueur' puis vers 'J3D'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRIEND_SRC = os.path.join(BASE_DIR, "sourceCode", "src")

if FRIEND_SRC not in sys.path:
    sys.path.append(FRIEND_SRC)

#on importe les constantes 
try:
    from settings import WIDTH, HEIGHT, FPS
    SCREEN_WIDTH = WIDTH
    SCREEN_HEIGHT = HEIGHT
    print(f"DEBUG Constants: Tailles récupérées ({WIDTH}x{HEIGHT})")
except ImportError:
    # Valeurs de secours si l'import échoue
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    FPS = 60
    print("DEBUG Constants: Import échoué, utilisation des valeurs par défaut (800x600)")

#constantes multijoueur
WORLD_WIDTH = SCREEN_WIDTH * 3
WORLD_HEIGHT = SCREEN_HEIGHT * 3

GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

PLAYER_SIZE = 40
PLAYER_HEIGHT_MULT = 3
PLAYER_SPEED = 4
PLAYER_MAX_HEALTH = 20
ROLL_SPEED = 12
ROLL_DURATION_FRAMES = 15
RECOIL_INITIAL_FORCE = 8
RECOIL_DRAG = 0.85
STUN_DURATION = 30
INVINCIBILITY_DURATION = 30
NUM_OBSTACLES = 50
