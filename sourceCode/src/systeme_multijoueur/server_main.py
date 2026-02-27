import socket
import sys
import os
import pickle
import random
from _thread import *

# --- FIX DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, ".."))

if src_path not in sys.path: sys.path.insert(0, src_path)
if current_dir not in sys.path: sys.path.insert(0, current_dir)

try:
    from dungeon import DungeonGenerator
    from settings import TILE_SIZE
    from common.entities import SharedPlayer, SharedObstacle
    from common.constants import WORLD_WIDTH, WORLD_HEIGHT, BLACK
except ImportError as e:
    print(f"ERREUR CRITIQUE : {e}"); sys.exit()

server = "0.0.0.0"
port = 55555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try: s.bind((server, port))
except socket.error as e: print(f"Erreur Bind : {e}"); sys.exit()

s.listen()
print("Génération du donjon et des monstres en cours...")

obstacles = []
server_enemies = {} # {ID: [x, y, tier]} -> On utilise une liste pour modifier x et y
dead_enemies = set() 

dg = DungeonGenerator()
map_data, spawn_grid = dg.generate() 
SPAWN_X = spawn_grid[0] * TILE_SIZE
SPAWN_Y = spawn_grid[1] * TILE_SIZE

for y, row in enumerate(map_data):
    for x, col in enumerate(row):
        if col == 'x':
            obstacles.append(SharedObstacle(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE, BLACK))

available_monsters = ['tier1', 'tier2', 'tier3']
eid = 0
for room in dg.rooms[1:]:
    for _ in range(random.randint(2, 4)):
        offset_x = random.randint(-20, 20)
        offset_y = random.randint(-20, 20)
        ex = room.centerx * TILE_SIZE + offset_x
        ey = room.centery * TILE_SIZE + offset_y
        tier = random.choice(available_monsters)
        # On sauvegarde sous forme de liste pour pouvoir la modifier
        server_enemies[eid] = [ex, ey, tier] 
        eid += 1

players = {}

def threaded_client(conn, player_id):
    conn.send(pickle.dumps((player_id, obstacles, (SPAWN_X, SPAWN_Y), server_enemies)))
    
    while True:
        try:
            data = conn.recv(4096)
            if not data: break
            payload = pickle.loads(data)
            
            inputs = payload.get('keys', {})
            killed_by_client = payload.get('killed_enemies', [])
            enemy_positions = payload.get('enemy_positions', {})
            
            # Mise à jour des morts
            for k_eid in killed_by_client:
                if k_eid in server_enemies:
                    del server_enemies[k_eid]
                dead_enemies.add(k_eid)
                
            # LE MAÎTRE DU JEU MET À JOUR LES POSITIONS
            # Si le joueur est le plus ancien (plus petit ID), c'est lui le Maître
            if players and player_id == min(players.keys()):
                for e_id, pos in enemy_positions.items():
                    if e_id in server_enemies:
                        server_enemies[e_id][0] = pos[0] # X
                        server_enemies[e_id][1] = pos[1] # Y
            
            if player_id in players:
                players[player_id].update_logic(inputs, obstacles)
            
            # On renvoie les joueurs, les morts ET les positions en direct !
            conn.sendall(pickle.dumps((players, list(dead_enemies), server_enemies)))
        except: break
    
    print(f"Joueur {player_id} déconnecté.")
    if player_id in players: del players[player_id]
    conn.close()

print(f"SERVEUR EN LIGNE (Port: {port})")
curr_id = 0
while True:
    conn, addr = s.accept()
    players[curr_id] = SharedPlayer(SPAWN_X, SPAWN_Y, curr_id)
    start_new_thread(threaded_client, (conn, curr_id))
    curr_id += 1
