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
    'sell_iron': 2,       # Prix de vente de 20 Fer -> 2 Or
    'buy_iron': 5,        # Or requis pour acheter 20 Fer -> 5 Or
    'buy_potion': 50,     # Prix d'une potion (50 Or)
    'upgrade_damage': 150,# Coût amélioration dégats (150 Or)
    'upgrade_iron_cost': 30, # Coût en fer pour l'amélioration
    'study_gold': 30,     # Or requis pour étudier (Bibliothèque)
    'study_iron': 15,     # Fer requis pour étudier
    'study_xp_gain': 25,  # XP gagnée en étudiant
    'research_gold': 80,  # Or requis pour recherche approfondie
    'research_iron': 40,  # Fer requis pour recherche approfondie
    'research_xp_gain': 75 # XP gagnée en recherche approfondie
}

# --- CONFIGURATION DES MONSTRES ---
MONSTER_DATA = {
    'tier1': {'health': 15, 'damage': 8, 'speed': 2, 'notice_radius': 300, 'color': 'red', 'loot': {'xp': (3, 5), 'iron' : (0, 2)}},
    'tier2': {'health': 30, 'damage': 15, 'speed': 3, 'notice_radius': 350, 'color': (200, 100, 100), 'loot': {'xp': (6, 9), 'iron': (1, 3)}},
    'tier3': {'health': 50, 'damage': 25, 'speed': 4, 'notice_radius': 400, 'color': (150, 50, 50), 'loot': {'xp': (12, 18), 'iron': (2, 4), 'gold': (0, 1)}},
    'tier4': {'health': 100, 'damage': 40, 'speed': 5, 'notice_radius': 450, 'color': (100, 0, 0), 'loot': {'xp': (20, 30), 'iron': (3, 6), 'gold': (1, 2)}},
    'tier5': {'health': 200, 'damage': 60, 'speed': 6, 'notice_radius': 500, 'color': 'white', 'loot': {'xp': (50, 80), 'iron': (5, 10), 'gold': (2, 5)}}
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
        'cost_gold': 20, 'cost_iron': 50, 'cost_npc': 2,
        'desc': 'Améliorer les armes',
        'color': (100, 100, 120), 'size': (128, 128)
    },
    'shop': {
        'name': 'Marché',
        'cost_gold': 30, 'cost_iron': 15, 'cost_npc': 2,
        'desc': 'Vendre Fer / Acheter Potions',
        'color': (200, 180, 50), 'size': (128, 64)
    },
    'bank': {
        'name': 'Banque',
        'cost_gold': 100, 'cost_iron': 20, 'cost_npc': 4,
        'desc': 'Stocker Fer et Or (Taxe 2%/jr)',
        'color': (218, 165, 32), 'size': (128, 64)
    },
    'library': {
        'name': 'Bibliothèque',
        'cost_gold': 50, 'cost_iron': 100, 'cost_npc': 3,
        'desc': 'Échanger Or et Fer contre XP',
        'color': (0, 139, 139), 'size': (128, 128)
    },
    'path': {
        'name': 'Chemin',
        'cost_gold': 0, 'cost_iron': 2, 'cost_npc': 0,
        'desc': 'Décoration',
        'color': (160, 120, 80), 'size': (32, 32), 'walkable': True
    },
    'tree': {
        'name': 'Arbre',
        'cost_gold': 5, 'cost_iron': 5, 'cost_npc': 0,
        'desc': 'Décoration',
        'color': (34, 139, 34), 'size': (64, 64)
    },
    'flower': {
        'name': 'Fleur',
        'cost_gold': 2, 'cost_iron': 0, 'cost_npc': 0,
        'desc': 'Décoration',
        'color': (255, 105, 180), 'size': (32, 32)
    }
}