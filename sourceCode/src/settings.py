import pyautogui

WIDTH, HEIGHT = pyautogui.size()

#WIDTH = 1280
#HEIGHT = 720
FPS = 60
TILE_SIZE = 64 # carré de la grille du monde
GAME_NAME = "Greed"

WORLD_MAP = [
    'xxxxxxxxxxxxxxxxxxxx',
    'x.            m    x',
    'x.  xxx            x',
    'x.  xxx            x',
    'x.  xxx            x',
    'x.  m  xxxxxxxxx   x',
    'x.     xxxxxxxxx   x',
    'x.  xxx            x',
    'x.  xxx    p       x',
    'x.  xxx            x',
    'x.                 x',
    'x.                 x',
    'x.         m       x',
    'x.                 x',
    'x.                 x',
    'x. m               x',
    'xxxxxxxxxxxxxxxxxxxx'
]