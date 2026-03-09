import socket
import pickle
import random
import threading
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
        self.x = x
        self.y = y
        self.id = pid
        self.status = 'idle'
        self.facing_right = True

class GameServer:
    def __init__(self, port=55555, max_retries=10):
        self.pin_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
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
        self.spawn_x = 0
        self.spawn_y = 0

    def generate_world(self):
        self.obstacles.clear()
        self.server_enemies.clear()
        self.dead_enemies.clear()
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
            for _ in range(random.randint(3, 5 + self.current_level * 2)):
                offset_x = random.randint(-20, 20)
                offset_y = random.randint(-20, 20)
                ex = room.centerx * TILE_SIZE + offset_x
                ey = room.centery * TILE_SIZE + offset_y
                tier = random.choice(available_monsters)
                self.server_enemies[eid] = [ex, ey, tier]
                eid += 1
                
        for p in self.players.values():
            p.x = self.spawn_x
            p.y = self.spawn_y

    def start(self):
        if not self.setup_socket():
            return False
        
        self.running = True
        threading.Thread(target=self.discovery_listener, daemon=True).start()
        threading.Thread(target=self.accept_players, daemon=True).start()
        return True

    def setup_socket(self):
        for attempt in range(self.max_retries):
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if hasattr(socket, 'SO_REUSEPORT'):
                    self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                else:
                    self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

    def discovery_listener(self):
        discovery_socket = None
        try:
            discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if hasattr(socket, 'SO_REUSEPORT'):
                discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            else:
                discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            discovery_socket.bind(('', 55666))
            discovery_socket.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = discovery_socket.recvfrom(1024)
                    message = data.decode().strip()
                    if message.startswith("J3D_DISCOVER"):
                        parts = message.split(':')
                        requested_pin = parts[1].strip() if len(parts) > 1 else None
                        
                        if requested_pin is None or requested_pin == str(self.pin_code).strip():
                            response = f"J3D_SERVER:OK:{self.port}"
                            discovery_socket.sendto(response.encode(), addr)
                except socket.timeout:
                    continue
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            if discovery_socket:
                discovery_socket.close()

    def accept_players(self):
        while self.running:
            try:
                if self.server_socket:
                    client_socket, addr = self.server_socket.accept()
                    threading.Thread(target=self.handle_player, args=(client_socket, addr), daemon=True).start()
            except Exception:
                pass

    def handle_player(self, client_socket, addr):
        with self.lock:
            player_id = self.player_count
            self.player_count += 1
            self.players[player_id] = SharedPlayer(self.spawn_x, self.spawn_y, player_id)
        
        try:
            init_data = {'player_id': player_id}
            client_socket.sendall(pickle.dumps(init_data))
            
            while self.running and player_id in self.players:
                data = client_socket.recv(8192)
                if not data:
                    break
                
                payload = pickle.loads(data)
                action = payload.get('action', 'idle')
                pos = payload.get('pos')
                
                with self.lock:
                    if action == 'start_game' and player_id == 0 and self.game_state == 'LOBBY':
                        self.generate_world()
                        self.game_state = 'PLAYING'
                        
                    elif action == 'player_died':
                        self.game_state = 'GAME_OVER'
                        
                    elif action == 'ready_next':
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
                                    self.server_enemies[e_id][0] = epos[0]
                                    self.server_enemies[e_id][1] = epos[1]
                        
                        if action == 'resting':
                            self.resting_players.add(player_id)
                            if player_id in self.players:
                                self.players[player_id].x = -9999
                                self.players[player_id].y = -9999
                        else:
                            self.resting_players.discard(player_id)
                            if pos and player_id in self.players:
                                self.players[player_id].x = pos[0]
                                self.players[player_id].y = pos[1]
                            p_status = payload.get('status', 'idle')
                            p_facing = payload.get('facing_right', True)
                            if player_id in self.players:
                                self.players[player_id].status = p_status
                                self.players[player_id].facing_right = p_facing
                                
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
                    enemies_list = [{'id': eid, 'x': d[0], 'y': d[1], 'type': d[2]} for eid, d in self.server_enemies.items()]
                    client_needs_map = payload.get('client_level', 0) != self.current_level
                    obs_list = [{'x': o.rect.x, 'y': o.rect.y} for o in self.obstacles] if (self.game_state == 'PLAYING' and client_needs_map) else []
                    floor_list = getattr(self, 'floor_tiles', []) if (self.game_state == 'PLAYING' and client_needs_map) else []
                    
                    response = {
                        'state': self.game_state,
                        'level': self.current_level,
                        'spawn_pos': (self.spawn_x, self.spawn_y),
                        'players': self.players,
                        'dead_enemies': list(self.dead_enemies),
                        'server_enemies': enemies_list,
                        'obstacles': obs_list,
                        'floor_tiles': floor_list,
                        'ready_count': len(self.players_ready_for_next),
                        'total_players': len(self.players)
                    }
                
                client_socket.sendall(pickle.dumps(response))
                
        except Exception:
            pass
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