import pyautogui


WIDTH = 1280
HEIGHT = 720

FPS = 60
TILE_SIZE = 64 
GAME_NAME = "Greed"

BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 200
UI_FONT_SIZE = 18
UI_FONT = None
HEALTH_COLOR = (199, 13, 0)
UI_BG_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (230, 230, 230)
TEXT_COLOR = (255, 255, 255)

# --- ECONOMIE & PRIX ---
PRICES = {
    'sell_iron': 2,       # Prix de vente de 1 Fer
    'buy_potion': 50,     # Prix d'une potion (50 Or)
    'upgrade_damage': 100,# Coût amélioration dégats (100 Or)
    'upgrade_iron_cost': 20, # Coût en fer pour l'amélioration
    'pray_cost_xp': 50,   # XP requise pour prier (Autel)
    'sacrifice_hp': 10,   # PV sacrifiés à la statue
    'sacrifice_gain': 50  # Or gagné par sacrifice
}

# --- CONFIGURATION DES MONSTRES ---
MONSTER_DATA = {
    'tier1': {'health': 3, 'damage': 5, 'speed': 2, 'notice_radius': 300, 'color': 'red', 'loot': {'xp': (3, 5), 'iron' : (1, 3)}},
    'tier2': {'health': 8, 'damage': 10, 'speed': 3, 'notice_radius': 350, 'color': (200, 100, 100), 'loot': {'xp': (6, 9), 'iron': (2, 5)}},
    'tier3': {'health': 15, 'damage': 20, 'speed': 4, 'notice_radius': 400, 'color': (150, 50, 50), 'loot': {'xp': (12, 18), 'iron': (4, 8), 'gold': (0, 1)}},
    'tier4': {'health': 25, 'damage': 30, 'speed': 5, 'notice_radius': 450, 'color': (100, 0, 0), 'loot': {'xp': (20, 30), 'iron': (5, 10), 'gold': (2, 5)}},
    'tier5': {'health': 50, 'damage': 40, 'speed': 6, 'notice_radius': 500, 'color': 'white', 'loot': {'xp': (50, 80), 'iron': (10, 20), 'gold': (10, 20)}}
}

# --- CONFIGURATION DES BATIMENTS ---
BUILDING_DATA = {
    'inn': {
        'name': 'Auberge',
        'cost_gold': 20, 'cost_iron': 40, 'cost_npc': 0, 
        'capacity': 3, 'max_count': 5,      
        'desc': 'Logement (+3 Pop)',
        'color': (139, 69, 19), 'size': (128, 64)
    },
    'forge': {
        'name': 'Forge',
        'cost_gold': 5, 'cost_iron': 50, 'cost_npc': 2,
        'desc': 'Améliorer les armes',
        'color': (100, 100, 120), 'size': (128, 128)
    },
    'shop': {
        'name': 'Marché',
        'cost_gold': 30, 'cost_iron': 0, 'cost_npc': 2,
        'desc': 'Vendre Fer / Acheter Potions',
        'color': (200, 180, 50), 'size': (128, 64)
    },
    'bank': {
        'name': 'Banque',
        'cost_gold': 100, 'cost_iron': 20, 'cost_npc': 4,
        'desc': 'Sécuriser l\'or (WIP)',
        'color': (218, 165, 32), 'size': (128, 64)
    },
    'library': {
        'name': 'Bibliothèque',
        'cost_gold': 50, 'cost_iron': 100, 'cost_npc': 3,
        'desc': 'Acheter XP (WIP)',
        'color': (0, 139, 139), 'size': (128, 128)
    },
    'altar': {
        'name': 'Autel',
        'cost_gold': 15, 'cost_iron': 10, 'cost_npc': 1,
        'desc': 'Dépenser XP > Max PV',
        'color': (150, 50, 150), 'size': (64, 128)
    },
    'statue': {
        'name': 'Maudit',
        'cost_gold': 66, 'cost_iron': 66, 'cost_npc': 1,
        'desc': 'Sacrifice PV > Or',
        'color': (75, 0, 130), 'size': (64, 64)
    },
    'path': {
        'name': 'Chemin',
        'cost_gold': 0, 'cost_iron': 2, 'cost_npc': 0,
        'desc': 'Décoration',
        'color': (160, 120, 80), 'size': (64, 64), 'walkable': True
    }
}