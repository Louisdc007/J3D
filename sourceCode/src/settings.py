import pyautogui

WIDTH, HEIGHT = pyautogui.size()
HEIGHT-=50

#WIDTH = 1280
#HEIGHT = 720
FPS = 60
TILE_SIZE = 64 # carré de la grille du monde
GAME_NAME = "Greed"

"""
WORLD_MAP = [
    'xxxxxxxxxxxxxxxxxxxx',
    'x.            m    x',
    'x.  xxx   m        x',
    'x.  xxx            x',
    'x.  xxx            x',
    'x.  m  xxxxxxxxx   x',
    'x.     xxxxx.      x',
    'x.  xxx            x',
    'x.  xxx    p   xx  x',
    'x.  xxx        x   x',
    'x.      xxxx   x   x',
    'x. x    xxxx       x',
    'x.   x     m       x',
    'x.    xxx          x',
    'x.                 x',
    'x. m               x',
    'xxxxxxxxxxxxxxxxxxxx'
]
"""

BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 200
UI_FONT_SIZE = 18
UI_FONT = None
HEALTH_COLOR = (199, 13, 0)
UI_BG_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (230, 230, 230)

MONSTER_DATA = {
    'tier1': {
        'health': 3,
        'damage': 10,
        'speed': 2,
        'notice_radius': 300,
        'color': 'red',
        'loot': {
            'xp': (1, 2)
        }
    },
    'tier2': {
        'health': 5,
        'damage': 15,
        'speed': 3,
        'notice_radius': 350,
        'color': (200, 100, 100),
        'loot': {
            'xp': (2, 3),
            'iron': (0, 1)
        }
    },
    'tier3': {
        'health': 8,
        'damage': 25,
        'speed': 4,
        'notice_radius': 400,
        'color': (150, 50, 50),
        'loot': {
            'xp': (3, 5),
            'iron': (1, 2)
        }
    },
    'tier4': {
        'health': 12,
        'damage': 35,
        'speed': 5,
        'notice_radius': 450,
        'color': (100, 0, 0),
        'loot': {
            'xp': (5, 8),
            'iron': (2, 3),
            'gold': (0, 1)
        }
    },
    'tier5': {
        'health': 20,
        'damage': 50,
        'speed': 6,
        'notice_radius': 500,
        'color': 'black',
        'loot': {
            'xp': (10, 15),
            'iron': (3, 5),
            'gold': (1, 2)
        }
    }
}
