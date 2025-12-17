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
    'x.  xxx   m        x',
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

BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 200
UI_FONT_SIZE = 18
UI_FONT = None
HEALTH_COLOR = (199, 13, 0)
UI_BG_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (230, 230, 230)