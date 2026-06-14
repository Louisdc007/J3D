import socket
import pickle
import struct
import random
import threading
import subprocess
import sys
import os
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, ".."))

if src_path not in sys.path:
    sys.path.insert(0, src_path)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dungeon import DungeonGenerator
from settings import TILE_SIZE

class MockRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class SharedObstacle:
    def __init__(self, x, y, w, h, color):
        self.rect = MockRect(x, y, w, h)

class SharedPlayer:
    def __init__(self, x, y, pid):
        self.x = int(x)
        self.y = int(y)
        self.id = pid
        self.status = 'idle'
        self.facing_right = True
        self.vulnerable = True

class GameServer:
    def __init__(self, port=55555, max_retries=10):
        self.port = port
        self.max_retries = max_retries
        self.server_socket = None
        self.running = False
        
        self.game_state = 'LOBBY'
        self.players_ready_for_next = set()
        self.resting_players = set() # NOUVEAU : Traque les dormeurs
        
        self.players = {}
        self.player_count = 0
        self.current_level = 1
        self.lock = threading.Lock()
        
        self.obstacles = []
        self.server_enemies = {}
        self.dead_enemies = set()
        self.server_items = {} # ID -> {'x':x, 'y':y, 'type':type}
        self.item_id_counter = 0
        self.pending_hits = []
        self.spawn_x = 0
        self.spawn_y = 0

    def generate_world(self):
        self.obstacles.clear()
        self.server_enemies.clear()
        self.dead_enemies.clear()
        self.server_items.clear()
        self.item_id_counter = 0
        self.floor_tiles = []
        
        dg = DungeonGenerator()
        map_data, spawn_grid = dg.generate()
        self.spawn_x = spawn_grid[0] * TILE_SIZE
        self.spawn_y = spawn_grid[1] * TILE_SIZE

        for y, row in enumerate(map_data):
            for x, col in enumerate(row):
                if col == 'x':
                    self.obstacles.append(SharedObstacle(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE, "black"))
                elif col == ' ':
                    self.floor_tiles.append({'x': x * TILE_SIZE, 'y': y * TILE_SIZE})

        available_monsters = ['tier1']
        if self.current_level >= 2: available_monsters.append('tier2')
        if self.current_level >= 4: available_monsters.append('tier3')
        if self.current_level >= 6: available_monsters.append('tier4')
        if self.current_level >= 8: available_monsters.append('tier5')
        
        eid = 0
        for room in dg.rooms[1:]:
            for _ in range(random.randint(3, min(10, 5 + self.current_level))):
                # Try to find a valid floor position within the room
                placed = False
                for _attempt in range(10):
                    # Pick a random position inside the room bounds
                    rx = random.randint(room.left + 1, room.right - 2)
                    ry = random.randint(room.top + 1, room.bottom - 2)
                    # Validate it's a floor tile
                    if 0 <= ry < len(map_data) and 0 <= rx < len(map_data[0]) and map_data[ry][rx] == ' ':
                        ex = rx * TILE_SIZE
                        ey = ry * TILE_SIZE
                        tier = random.choice(available_monsters)
                        self.server_enemies[eid] = [ex, ey, tier]
                        eid += 1
                        placed = True
                        break
                if not placed:
                    # Fallback: use room center (guaranteed to be floor)
                    ex = room.centerx * TILE_SIZE
                    ey = room.centery * TILE_SIZE
                    tier = random.choice(available_monsters)
                    self.server_enemies[eid] = [ex, ey, tier]
                    eid += 1
                
        for p in self.players.values():
            p.x = self.spawn_x
            p.y = self.spawn_y

    def _ensure_firewall_rule(self):
        """Configure automatiquement le pare-feu Windows pour autoriser le serveur.
        - Supprime toute règle existante (y compris les blocages auto de Windows Defender)
        - Ajoute une règle d'autorisation ciblant le .exe spécifiquement
        Ne fait rien sur macOS/Linux. Nécessite les droits admin (fournis par uac_admin=True).
        """
        if sys.platform != 'win32':
            return

        rule_name = "Greed Game Server"

        # Récupère le chemin de l'exe si on tourne en mode compilé (PyInstaller)
        exe_path = sys.executable if getattr(sys, 'frozen', False) else None

        try:
            # Étape 1 : supprimer TOUTE règle existante portant ce nom
            # (bloque ou autorise — on repart de zéro pour écraser le bloc auto de Windows)
            subprocess.run(
                ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}'],
                capture_output=True, text=True, timeout=5
            )

            # Étape 2 : ajouter la règle d'autorisation en entrée
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule_name}',
                'dir=in',
                'action=allow',
                'protocol=TCP',
                'localport=55555-55560',
                'profile=any',   # Couvre Public, Private et Domain
            ]
            if exe_path:
                # Règle ciblant le .exe : plus autoritaire qu'une règle de port seule
                cmd.append(f'program={exe_path}')

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                cible = f"exe ({exe_path})" if exe_path else "port 55555-55560"
                print(f"[SERVER] Pare-feu Windows configuré automatiquement ({cible}).")
            else:
                print(f"[SERVER] Avertissement pare-feu : {result.stderr.strip()}")

            # Étape 3 : ajouter aussi une règle sortante pour la réponse
            cmd_out = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule_name} OUT',
                'dir=out',
                'action=allow',
                'protocol=TCP',
                'localport=55555-55560',
                'profile=any',
            ]
            if exe_path:
                cmd_out.append(f'program={exe_path}')
            subprocess.run(cmd_out, capture_output=True, text=True, timeout=5)

        except Exception as e:
            print(f"[SERVER] Avertissement pare-feu : {e}")


    def start(self):
        self._ensure_firewall_rule()  # Ouvre les ports sur Windows automatiquement
        if not self.setup_socket():
            return False
        
        self.running = True
        from network import Network
        print(f"=====================================")
        print(f"[SERVER] Serveur J3D lancé !")
        print(f"[SERVER] IP Locale : {Network.get_primary_ip()}")
        print(f"[SERVER] Port : {self.port}")
        print(f"=====================================")
        threading.Thread(target=self.accept_players, daemon=True).start()
        return True

    def setup_socket(self):
        for attempt in range(self.max_retries):
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Remove SO_REUSEPORT so that we correctly get an OSError and try the next port 
                # if a zombie server process is clinging to port 55555.
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.server_socket.bind(('0.0.0.0', self.port + attempt))
                self.server_socket.listen(4)
                self.port = self.port + attempt
                return True
            except OSError:
                if self.server_socket:
                    self.server_socket.close()
                    self.server_socket = None
                continue
        return False


    def accept_players(self):
        while self.running:
            try:
                if self.server_socket:
                    client_socket, addr = self.server_socket.accept()
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    print(f"[SERVER] Connexion TCP acceptée de {addr}")
                    threading.Thread(target=self.handle_player, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[SERVER] Erreur accept_players : {e}")

    def _send_msg(self, sock, data):
        """Send a length-prefixed pickled message."""
        raw = pickle.dumps(data)
        header = struct.pack('>I', len(raw))
        sock.sendall(header + raw)

    def _recv_exact(self, sock, n):
        """Read exactly n bytes from a socket."""
        data = b""
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def _recv_msg(self, sock):
        """Receive a length-prefixed pickled message."""
        raw_len = self._recv_exact(sock, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack('>I', raw_len)[0]
        if msg_len > 10_000_000:
            return None
        data = self._recv_exact(sock, msg_len)
        if data is None:
            return None
        return pickle.loads(data)

    def handle_player(self, client_socket, addr):
        # Priorité de thread basse sur Windows pour laisser le CPU au jeu
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadPriority(
                    ctypes.windll.kernel32.GetCurrentThread(),
                    -1  # THREAD_PRIORITY_BELOW_NORMAL
                )
            except Exception:
                pass

        with self.lock:
            player_id = self.player_count
            self.player_count += 1
            self.players[player_id] = SharedPlayer(self.spawn_x, self.spawn_y, player_id)
        
        try:
            client_socket.settimeout(5)
            init_data = {'player_id': player_id}
            self._send_msg(client_socket, init_data)
            
            while self.running and player_id in self.players:
                payload = self._recv_msg(client_socket)
                if payload is None:
                    break
                
                action = payload.get('action', 'idle')
                pos = payload.get('pos')
                
                with self.lock:
                    if action == 'start_game' and player_id == 0 and self.game_state == 'LOBBY':
                        self.generate_world()
                        self.game_state = 'PLAYING'
                        
                    elif action == 'player_died':
                        self.game_state = 'GAME_OVER'
                        
                    elif action == 'ready_next' and payload.get('client_level', 0) == self.current_level:
                        self.players_ready_for_next.add(player_id)
                            
                    if self.game_state == 'PLAYING':
                        killed = payload.get('killed_enemies', [])
                        enemy_pos = payload.get('enemy_positions', {})
                        
                        for k_eid in killed:
                            if k_eid in self.server_enemies:
                                del self.server_enemies[k_eid]
                            self.dead_enemies.add(k_eid)
                            
                        if self.players and player_id == min(self.players.keys()):
                            for e_id, epos in enemy_pos.items():
                                if e_id in self.server_enemies:
                                    # epos can now be (x, y, facing, status, vulnerable)
                                    self.server_enemies[e_id][0] = epos[0] # x
                                    self.server_enemies[e_id][1] = epos[1] # y
                                    if len(epos) > 2:
                                        if len(self.server_enemies[e_id]) < 6:
                                            # Ensure enough slots for [x, y, tier, facing, status, vulnerable]
                                            while len(self.server_enemies[e_id]) < 6:
                                                self.server_enemies[e_id].append(None)
                                        self.server_enemies[e_id][3] = epos[2] # facing
                                        self.server_enemies[e_id][4] = epos[3] # status
                                        if len(epos) > 4:
                                            self.server_enemies[e_id][5] = epos[4] # vulnerable
                            
                            # ITEMS: Host spawns new items
                            new_items = payload.get('new_items', [])
                            for item in new_items:
                                i_id = self.item_id_counter
                                self.item_id_counter += 1
                                self.server_items[i_id] = {
                                    'x': item['x'], 
                                    'y': item['y'], 
                                    'type': item['type']
                                }
                        else:
                            # Non-host players can report hits
                            hits = payload.get('reported_hits', [])
                            for hit in hits:
                                self.pending_hits.append(hit)
                        
                        if action == 'resting' and payload.get('client_level', 0) == self.current_level:
                            self.resting_players.add(player_id)
                            if player_id in self.players:
                                self.players[player_id].x = -9999
                                self.players[player_id].y = -9999
                        else:
                            self.resting_players.discard(player_id)
                            if player_id in self.players:
                                if pos:
                                    self.players[player_id].x = int(pos[0])
                                    self.players[player_id].y = int(pos[1])
                                self.players[player_id].status = payload.get('status', 'idle')
                                self.players[player_id].facing_right = payload.get('facing_right', True)
                                self.players[player_id].vulnerable = payload.get('vulnerable', True)
                                
                        # PICKUP: Any player can report picking up multiple items
                        picked_list = payload.get('pickup_items', [])
                        for p_id in picked_list:
                            if p_id in self.server_items:
                                del self.server_items[p_id]
                                
                    # VERIFICATION DU PASSAGE AU NIVEAU SUIVANT
                    # (Si le nombre de joueurs prêts + ceux qui dorment = tous les joueurs)
                    if self.game_state == 'PLAYING':
                        ready_pool = self.players_ready_for_next.union(self.resting_players)
                        if len(self.players) > 0 and len(ready_pool) >= len(self.players):
                            self.current_level += 1
                            self.generate_world()
                            self.players_ready_for_next.clear()
                            self.resting_players.clear()

                with self.lock:
                    enemies_list = []
                    for eid, d in self.server_enemies.items():
                        e_dict = {'id': eid, 'x': int(d[0]), 'y': int(d[1]), 'type': d[2]}
                        if len(d) > 3 and d[3] is not None: e_dict['f'] = d[3] # facing
                        if len(d) > 4 and d[4] is not None: e_dict['s'] = d[4] # status
                        if len(d) > 5 and d[5] is not None: e_dict['v'] = d[5] # vulnerable
                        enemies_list.append(e_dict)
                    client_needs_map = payload.get('client_level', 0) != self.current_level or payload.get('need_map', False)
                    obs_list = [{'x': int(o.rect.x), 'y': int(o.rect.y)} for o in self.obstacles] if (self.game_state == 'PLAYING' and client_needs_map) else []
                    floor_list = [{'x': int(f['x']), 'y': int(f['y'])} for f in getattr(self, 'floor_tiles', [])] if (self.game_state == 'PLAYING' and client_needs_map) else []
                    
                    # Serialize players as lightweight dicts to reduce pickle overhead
                    players_dict = {}
                    for pid, p in self.players.items():
                        players_dict[pid] = {
                            'x': p.x, 
                            'y': p.y, 
                            'status': p.status, 
                            'facing_right': p.facing_right,
                            'vulnerable': getattr(p, 'vulnerable', True)
                        }
                    
                    response = {
                        'state': self.game_state,
                        'level': self.current_level,
                        'spawn_pos': (self.spawn_x, self.spawn_y),
                        'players': players_dict,
                        'dead_enemies': list(self.dead_enemies),
                        'server_enemies': enemies_list,
                        'server_items': self.server_items,
                        'obstacles': obs_list,
                        'floor_tiles': floor_list,
                        'ready_count': len(self.players_ready_for_next),
                        'total_players': len(self.players),
                        'pending_hits': self.pending_hits[:] # Copy for this response
                    }
                
                # Clear pending hits after sending to Host (ID 0 usually)
                if player_id == 0:
                    with self.lock:
                        self.pending_hits = []
                
                self._send_msg(client_socket, response)
                # Tick serveur à 20 Hz : suffisant pour la sync multijoueur
                # et beaucoup moins gourmand que 60 Hz — le game loop garde la priorité
                time.sleep(0.05)
                
        except Exception as e:
            print(f"[SERVER] Erreur handle_player (ID:{player_id}, Addr:{addr}) : {e}")
        finally:
            with self.lock:
                if player_id in self.players:
                    del self.players[player_id]
                self.players_ready_for_next.discard(player_id)
                self.resting_players.discard(player_id)
            client_socket.close()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None