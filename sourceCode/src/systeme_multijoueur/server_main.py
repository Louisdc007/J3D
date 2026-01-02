import socket
import sys
import os
import pickle
import random
from _thread import *

#forcage des chemins
# On recupere le chemin du dossier J3D
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # dossier systeme_multijoueur
BASE_DIR = os.path.dirname(CURRENT_DIR) # dossier J3D

# On ajoute J3D et le dossier src du systeme dep solo au système
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    
FRIEND_SRC = os.path.join(BASE_DIR, "sourceCode", "src")
if FRIEND_SRC not in sys.path:
    sys.path.insert(0, FRIEND_SRC)

# On verifie si on peut importer les entite
try:
    from systeme_multijoueur.common.entities import SharedPlayer, SharedObstacle
    from systeme_multijoueur.common.constants import *
    print("DEBUG Serveur: Entités et Constantes chargées !")
except ImportError as e:
    print(f"ERREUR IMPORT SERVEUR : {e}")
    sys.exit()

from systeme_multijoueur.common.entities import SharedPlayer, SharedObstacle
from common.constants import *

# configuration serveur
server = "0.0.0.0" # ecoute toutes les connexions entrantes
port = 55555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    s.bind((server, port))
except socket.error as e:
    print(f"Erreur Bind : {e}")
    sys.exit()

s.listen()
print(f"--- Serveur lancé sur le port {port} ---")
print("En attente de joueurs...")

# Création de la map ,obstacles
obstacles = []
for _ in range(NUM_OBSTACLES):
    obstacles.append(SharedObstacle(
        random.randint(0, WORLD_WIDTH - 150),
        random.randint(0, WORLD_HEIGHT - 150),
        random.randint(50, 150),
        random.randint(50, 150),
        BLACK
    ))

players = {}

def threaded_client(conn, player_id):
    # envoi initial : (ID du joueur, liste des obstacles)
    conn.send(pickle.dumps((player_id, obstacles)))
    
    while True:
        try:
            # recoit les entres clavier (z,q,s,d,space)
            data = pickle.loads(conn.recv(2048))
            if not data:
                print(f"Joueur {player_id} déconnecté.")
                break
            
            # application de la logique (mouvement, collision, roulade)
            players[player_id].update_logic(data, obstacles)
            
            # renvoie l'etat de tous les joueurs au client
            conn.sendall(pickle.dumps(players))
        except Exception as e:
            print(f"Erreur avec le joueur {player_id} : {e}")
            break
    
    if player_id in players:
        del players[player_id]
    conn.close()

curr_id = 0
while True:
    conn, addr = s.accept()
    print(f"Connexion acceptée de : {addr}")
    
    players[curr_id] = SharedPlayer(WORLD_WIDTH//2, WORLD_HEIGHT//2, curr_id)
    start_new_thread(threaded_client, (conn, curr_id))
    curr_id += 1
