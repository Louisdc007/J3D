import pygame
import sys
import random
import os
import threading
import time
from settings import *
from entities.player import *
from camera import CameraGroup
from tile import Tile, DungeonEntrance, Floor
from entities.enemy import Enemy
from ui import UI
from dungeon import DungeonGenerator
from entities.item import Item
from hub import Hub
from save_manager import SaveManager
from intro import IntroScene

base_path = os.path.dirname(os.path.abspath(__file__))
multi_path = os.path.join(base_path, "systeme_multijoueur")
if multi_path not in sys.path:
    sys.path.append(multi_path)

from network import Network
from game_server import GameServer

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.fullscreen = False
        self.screen = pygame.display.set_mode(size=(WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.clock = pygame.time.Clock()
        
        try:
            music_path = os.path.join(base_path, 'assets', 'greed_hub.mp3')
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(0.4)
            self.music_playing = False
        except Exception as e:
            print(f"Erreur lors du chargement de la musique: {e}")

        self.game_state = 'menu'
        self.paused = False
        self.intro_next_state = 'hub'
        
        self.game_time = 0
        self.day_duration = 5 * 60 * 500
        self.hours_in_day = 24
        self.morning_hour = 6
        self.evening_hour = 20
        self.hours_day_to_evening = self.evening_hour - self.morning_hour
        self.evening_duration = int(self.day_duration * (self.hours_day_to_evening / 10))
        self.full_day_duration = int(self.day_duration * (self.hours_in_day / 10))

        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        self.hub = Hub(self.obstacle_sprites)
        self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)

        self.ui = UI()
        self.save_manager = SaveManager()
        self.intro = IntroScene(self.screen)
        self.menu_font = pygame.font.Font(UI_FONT, 40)
        self.title_font = pygame.font.Font(UI_FONT, 100)
        self.loading_font = pygame.font.Font(UI_FONT, 50)
        
        self.is_multiplayer = False
        self.network = None
        self.game_server = None
        self.player_id = None
        self.host_id = 0
        self.other_players = {}
        self.multi_mode = None
        self.multi_code = ""
        self.multi_status = ""
        self.multi_state = 'lobby'
        self.multi_level = 1
        self.multi_resting_for_level = -1 
        self.killed_enemies_queue = []
        self.multi_server_data_cache = None
        self.pending_multi_action = None
        
        self.transition_active = False
        self.transition_alpha = 0
        self.transition_duration = 420 
        self.transition_text = ""
        self.transition_font = pygame.font.Font(None, 60)
        self.transition_type = None
        self.dungeon_entrance_pos = None
        self.dungeon_entrance_rect = None
        self.resources_at_dungeon_start = None

        self.setup_menus()
        self.load_save_if_exists()

    def setup_menus(self):
        center_x = WIDTH // 2; start_y = HEIGHT // 2 - 50; gap = 80
        self.menu_buttons = [
            {'text': 'SOLO', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'start_game', 'pos': (center_x, start_y)},
            {'text': 'MULTIJOUEUR', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'multi_placeholder', 'pos': (center_x, start_y + gap)},
            {'text': 'OPTIONS', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'go_to_options', 'pos': (center_x, start_y + gap * 2)},
            {'text': 'QUITTER', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'quit_game', 'pos': (center_x, start_y + gap * 3)}
        ]
        for btn in self.menu_buttons: btn['rect'].center = btn['pos']

        self.options_buttons = [
            {'text': 'RÉINITIALISER SAUVEGARDE', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'reset_save', 'pos': (center_x, start_y)},
            {'text': 'PLEIN ÉCRAN : NON', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'toggle_fullscreen', 'pos': (center_x, start_y + gap)},
            {'text': 'REVOIR INTRO', 'rect': pygame.Rect(0, 0, 450, 60), 'action': 'replay_intro', 'pos': (center_x, start_y + gap * 2)},
            {'text': 'RETOUR', 'rect': pygame.Rect(0, 0, 300, 60), 'action': 'back_to_menu', 'pos': (center_x, start_y + gap * 3)}
        ]
        for btn in self.options_buttons: btn['rect'].center = btn['pos']

    def load_save_if_exists(self):
        loaded_data = self.save_manager.load_game()
        self.has_save_file = False
        if loaded_data:
            self.player.load_save_data(loaded_data['player'])
            self.hub.load_save_data(loaded_data['hub'])
            self.has_save_file = True
        self.hub.spawn_npcs(self.player)

    def launch_game_server(self):
        try:
            self.game_server = GameServer(port=55555)
            if self.game_server.start():
                self.multi_code = self.game_server.pin_code
                self.is_multiplayer = True
                self.multi_mode = 'server'
                time.sleep(0.5)
                
                self.network = Network(server="127.0.0.1", port=self.game_server.port)
                if self.network.p:
                    self.player_id = self.network.p.get('player_id', 0)
                    self.player.kill()
                    self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
                    self.game_state = 'multi_lobby'
                    self.multi_state = 'lobby'
                    self.pending_multi_action = None
                    self.start_network_thread()
            else:
                self.multi_status = "Erreur serveur"
                self.game_state = 'multi_mode_select'
        except Exception as e:
            self.multi_status = f"Erreur: {str(e)}"
            self.game_state = 'multi_mode_select'

    def _finalize_connection(self, host, port):
        """Shared logic to finish connecting once we have host:port."""
        self.network = Network(server=host, port=port)
        if self.network.p:
            self.player_id = self.network.p.get('player_id', 1)
            self.player.kill()
            self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
            self.is_multiplayer = True
            self.game_state = 'multi_lobby'
            self.multi_state = 'lobby'
            self.pending_multi_action = None
            self.start_network_thread()
            return True
        return False

    def connect_to_server(self):
        try:
            # Detect if input is an IP address or a PIN code
            code = self.multi_code.strip()
            if '.' in code:
                # Direct IP connection — bypass broadcast entirely
                self.connect_direct(code)
                return
            
            discovered = Network.discover(pin=code)
            if discovered:
                host, port = discovered
                if not self._finalize_connection(host, port):
                    self.multi_status = "Serveur non prêt"
                    self.game_state = 'multi_code_input'
            else:
                self.multi_status = "Serveur non trouvé"
                self.game_state = 'multi_code_input'
        except Exception as e:
            self.multi_status = f"Erreur: {str(e)}"
            self.game_state = 'multi_code_input'

    def connect_direct(self, ip_address):
        """Connect directly to a server IP, bypassing UDP broadcast."""
        try:
            port = 55555
            print(f"[DEBUG-CLIENT] Connexion directe a {ip_address}:{port}")
            if not self._finalize_connection(ip_address, port):
                # Try a few ports in case the server had to use an alternate
                for offset in range(1, 5):
                    print(f"[DEBUG-CLIENT] Essai port {port + offset}...")
                    if self._finalize_connection(ip_address, port + offset):
                        return
                self.multi_status = f"Connexion échouée à {ip_address}"
                self.game_state = 'multi_code_input'
        except Exception as e:
            self.multi_status = f"Erreur: {str(e)}"
            self.game_state = 'multi_code_input'

    def is_player_at_entrance(self):
        if self.dungeon_entrance_rect is None: return False
        return self.player.rect.colliderect(self.dungeon_entrance_rect)

    def start_network_thread(self):
        self.network_running = True
        self.current_payload = {
            'action': 'idle', 
            'pos': (0, 0),
            'status': 'idle',
            'facing_right': True,
            'client_level': 0
        }
        self.multi_server_data_cache = None
        self.network_thread = threading.Thread(target=self._network_task, daemon=True)
        self.network_thread.start()

    def _network_task(self):
        while self.network_running and self.network and self.network.client:
            try:
                # Always send the latest payload
                response = self.network.send(self.current_payload)
                if response:
                    self.multi_server_data_cache = response
                time.sleep(0.016) # Target 60 updates/sec for smooth enemy movement on client
            except Exception as e:
                print(f"Network thread error: {e}")
                break
        self.network_running = False

    def save_all(self):
        data = {'player': self.player.get_save_data(), 'hub': self.hub.get_save_data()}
        self.save_manager.save_game(data)
        self.has_save_file = True 

    def toggle_fullscreen(self, btn):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
            btn['text'] = "PLEIN ÉCRAN : OUI"
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            btn['text'] = "PLEIN ÉCRAN : NON"

    def return_to_menu(self):
        self.network_running = False
        if self.game_server:
            self.game_server.stop()
            self.game_server = None
        if self.network and self.network.client:
            try: self.network.client.close()
            except: pass
            self.network = None
            
        if not self.is_multiplayer:
            self.save_all()
            
        self.is_multiplayer = False
        self.other_players.clear()
        self.multi_state = 'lobby'
        self.game_state = 'menu'
        self._menu_lock_time = time.time() + 0.5  # Prevent accidental double-click into SOLO mode
        self.game_time = 0
        self.paused = False
        self.paused = False
        self.transition_active = False
        self.killed_enemies_queue.clear()
        self.request_start = False
        
        self.visible_sprites.empty()
        self.obstacle_sprites.empty()
        self.attackable_sprites.empty()
        self.item_sprites.empty()
        
        self.player.kill()
        self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
        self.hub = Hub(self.obstacle_sprites)
        self.load_save_if_exists()

    def clean_exit(self):
        self.network_running = False
        if self.game_server: self.game_server.stop()
        if self.network and self.network.client:
            try: self.network.client.close()
            except: pass
        if not self.is_multiplayer: self.save_all()
        pygame.quit()
        sys.exit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.clean_exit()

            if self.game_state == 'menu':
                if getattr(self, '_menu_lock_time', 0) > time.time(): continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.menu_buttons:
                        if btn['rect'].collidepoint(event.pos):
                            if btn['action'] == 'start_game':
                                self.is_multiplayer = False 
                                if self.has_save_file: self.game_state = 'hub'
                                else: self.intro.reset(); self.game_state = 'intro'; self.intro_next_state = 'hub'
                            elif btn['action'] == 'multi_placeholder': 
                                self.multi_mode = None; self.multi_code = ""; self.multi_status = ""; self.game_state = 'multi_mode_select'
                            elif btn['action'] == 'go_to_options': self.game_state = 'options'
                            elif btn['action'] == 'quit_game': self.clean_exit()
            
            elif self.game_state == 'options':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in self.options_buttons:
                        if btn['rect'].collidepoint(event.pos):
                            if btn['action'] == 'reset_save':
                                self.save_manager.delete_save(); self.obstacle_sprites.empty(); self.visible_sprites.empty()
                                self.player = Player((0, 0), [self.visible_sprites], self.obstacle_sprites)
                                self.hub = Hub(self.obstacle_sprites); self.hub.spawn_npcs(self.player)
                                self.game_time = 0; self.has_save_file = False
                            elif btn['action'] == 'toggle_fullscreen': self.toggle_fullscreen(btn)
                            elif btn['action'] == 'replay_intro': self.intro.reset(); self.game_state = 'intro'; self.intro_next_state = 'options'
                            elif btn['action'] == 'back_to_menu': self.game_state = 'menu'

            elif self.game_state == 'multi_mode_select':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    cx, cy = WIDTH // 2, HEIGHT // 2
                    if pygame.Rect(cx - 220, cy - 80, 180, 70).collidepoint(event.pos): self.launch_game_server()
                    elif pygame.Rect(cx + 40, cy - 80, 180, 70).collidepoint(event.pos): self.game_state = 'multi_code_input'; self.multi_code = ""; self.multi_status = ""
                    elif pygame.Rect(cx - 90, cy + 80, 180, 50).collidepoint(event.pos): self.game_state = 'menu'

            elif self.game_state == 'multi_code_input':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: self.game_state = 'multi_mode_select'
                    elif event.key == pygame.K_BACKSPACE: self.multi_code = self.multi_code[:-1]
                    elif hasattr(event, 'unicode') and event.unicode.isdigit() and len(self.multi_code) < 6: self.multi_code += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(WIDTH // 2 - 100, 290, 200, 50).collidepoint(event.pos) and len(self.multi_code) == 6:
                        self.game_state = 'multi_searching'; self.multi_status = "Recherche..."; self.connect_to_server()
                    elif pygame.Rect(WIDTH // 2 - 100, 360, 200, 50).collidepoint(event.pos): self.game_state = 'multi_mode_select'

            elif self.game_state == 'multi_lobby':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_state == 'multi_lobby' and self.player_id == 0:
                        btn = pygame.Rect(WIDTH//2 - 100, 450, 200, 60)
                        if btn.collidepoint(event.pos):
                            self.request_start = True

            elif self.game_state == 'multi_gameover':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 150, 300, 60).collidepoint(event.pos):
                        self.return_to_menu()

            elif self.game_state == 'game_over':
                if self._handle_game_over_event(event):
                    self.return_to_menu()

            elif self.game_state == 'dying':
                pass  # Block all input during death animation

            elif self.game_state == 'intro':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.game_state = self.intro_next_state
                    if self.intro_next_state == 'hub': self.save_all()

            elif self.game_state in ['hub', 'dungeon', 'loading']:
                if self.game_state == 'loading': return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.game_state == 'hub' and self.hub.build_mode_active: self.hub.build_mode_active = False; self.hub.selected_blueprint = None
                    else: self.paused = not self.paused
                
                if self.paused and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.check_pause_click(event.pos); continue 

                if not self.is_multiplayer:
                    if self.game_state == 'hub':
                        ui_was_active = self.hub.paused_ui_active() or self.hub.build_mode_active
                        action = None
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            action = self.hub.check_click(event.pos, self.player)
                            if action == "build_action": self.save_all()
                            elif action == "dungeon_random_check":
                                ratio = self.game_time / self.full_day_duration
                                h = int((self.morning_hour + (self.hours_in_day * ratio)) % 24)
                                if h >= self.evening_hour or h < self.morning_hour: 
                                    self.resources_at_dungeon_start = self.player.inventory['iron']
                                    self.game_state = 'loading'
                                else: self.hub.waiting_for_night = True; self.hub.pending_dungeon_choice = 'random'
                            elif action in ["wait_for_night_random", "rest", "rest_at_night"]:
                                self.game_time = self.evening_duration; self.transition_active = True; self.transition_alpha = 0
                                self.transition_type = 'wait_for_dungeon' if action == "wait_for_night_random" else 'night'
                                self.transition_text = "La nuit tombe..."
                            elif action == "explore_at_night": 
                                self.resources_at_dungeon_start = self.player.inventory['iron']
                                self.game_state = 'loading'
                        
                        # Pass input to player if they didn't click inside a UI menu
                        if action is None and not ui_was_active:
                            self.player.single_input(event)
                            
                    elif self.game_state == 'dungeon':
                        self.player.single_input(event)
                
                else:
                    if self.multi_state == 'playing':
                        self.player.single_input(event)
                    elif self.multi_state in ['upgrade', 'rescue'] and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_multi_end_night_clicks(event.pos)

    def handle_multi_end_night_clicks(self, pos):
        btn_width, btn_height = 250, 60; start_y = 300; gap = 100
        if self.multi_state == 'upgrade':
            upgrades = [("health", 50), ("damage", 10), ("speed", 5)]
            for i, (utype, val) in enumerate(upgrades):
                if pygame.Rect(WIDTH//2 - btn_width//2, start_y + i * gap, btn_width, btn_height).collidepoint(pos):
                    if utype == "health": self.player.health = min(self.player.health + val, self.player.max_health)
                    elif utype == "damage": self.player.attack_damage += val
                    elif utype == "speed": self.player.speed *= 1.05
                    self.pending_multi_action = 'ready_next'
                    self.multi_state = 'waiting_others'
                    break
        elif self.multi_state == 'rescue':
            if pygame.Rect(WIDTH//2 - btn_width//2, 300, btn_width, btn_height).collidepoint(pos):
                self.player.health = 10
                self.player.inventory = {k: 0 for k in self.player.inventory.keys()}
                self.multi_state = 'waiting_others'
            elif pygame.Rect(WIDTH//2 - btn_width//2, 400, btn_width, btn_height).collidepoint(pos):
                self.multi_resting_for_level = self.multi_level + 1
                self.pending_multi_action = 'ready_next'
                self.multi_state = 'waiting_others'

    def check_pause_click(self, pos):
        center_x = WIDTH // 2; center_y = HEIGHT // 2; btn_width = 300; btn_height = 50; gap = 70
        buttons = []
        
        # On reproduit exactement les boutons affichés dans draw_pause_menu
        if self.game_state == 'hub':
            buttons.append('save_menu')
            buttons.append('resume')
        elif self.game_state == 'dungeon':
            if self.is_multiplayer:
                buttons.append('dungeon_to_menu')
                buttons.append('resume')
            else:
                buttons.append('dungeon_to_hub')
                buttons.append('dungeon_to_menu')
                buttons.append('resume')

        start_y = center_y - (len(buttons) * gap) // 2
        for i, btn_action in enumerate(buttons):
            rect = pygame.Rect(0, 0, btn_width, btn_height)
            rect.center = (center_x, start_y + i * gap)
            if rect.collidepoint(pos):
                if btn_action == 'resume': 
                    self.paused = False
                elif btn_action == 'save_menu' or btn_action == 'dungeon_to_menu': 
                    self.return_to_menu()
                elif btn_action == 'dungeon_to_hub':
                    self.game_state = 'hub'
                    self.game_time = 0
                    self.hub.night_arrived = False
                    self.paused = False
                    self.save_all()
                    
                    self.visible_sprites.empty()
                    self.obstacle_sprites.empty()
                    self.attackable_sprites.empty()
                    self.item_sprites.empty()
                    
                    self.player.obstacle_sprites = self.obstacle_sprites
                    self.player.add(self.visible_sprites)
                    self.player.pos.x = 0
                    self.player.pos.y = 0
                    self.player.hitbox.topleft = (0, 0)
                    self.player.rect.midbottom = self.player.hitbox.midbottom
                    self.hub.spawn_npcs(self.player)
                return 

    def update(self):
        if self.game_state in ['menu', 'options', 'multi_mode_select', 'multi_code_input', 'multi_searching']: return
        
        if self.game_state == 'intro':
            if self.intro.update(): self.game_state = self.intro_next_state; self.save_all()
            return
            
        if self.paused: return

        if self.is_multiplayer: self.update_multi()
        else: self.update_solo()

    def _handle_game_over_event(self, event):
        """Returns True if game over button was clicked."""
        if not hasattr(self, '_go_btn'): return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._go_btn.collidepoint(event.pos):
                return True
        return False

    def _draw_game_over(self):
        """Draws the game over overlay on top of the dungeon."""
        # Dark red semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((80, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        # "GAME OVER" text
        font_big = pygame.font.Font(None, 120)
        font_small = pygame.font.Font(None, 36)
        title = font_big.render('GAME OVER', True, (220, 50, 50))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        sub = font_small.render('Vous avez perdu votre or et votre fer.', True, (200, 160, 160))
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))

        # Button
        btn = getattr(self, '_go_btn', None)
        if btn:
            mouse = pygame.mouse.get_pos()
            hover = btn.collidepoint(mouse)
            color = (180, 40, 40) if hover else (120, 20, 20)
            pygame.draw.rect(self.screen, color, btn, border_radius=10)
            pygame.draw.rect(self.screen, (220, 80, 80), btn, 2, border_radius=10)
            label = font_small.render('Retour au menu', True, (255, 255, 255))
            self.screen.blit(label, label.get_rect(center=btn.center))

    def update_solo(self):
        if self.game_state == 'loading':
            self.build_map_solo(); self.game_state = 'dungeon'; return

        if not self.transition_active:
            if self.game_state == 'hub' and self.hub.night_arrived:
                pass 
            else:
                self.game_time += self.clock.get_time()
        else:
            self.transition_alpha += 1
        
        if self.game_state == 'hub' and self.game_time >= self.evening_duration: self.hub.night_arrived = True
        
        if self.game_state == 'dungeon' and self.game_time >= self.full_day_duration and not self.transition_active:
            self.transition_active = True; self.transition_alpha = 0; self.transition_type = 'morning'; self.transition_text = "Il est l'heure de rentrer..."
        
        if self.transition_active and self.transition_alpha == self.transition_duration // 2:
            if self.transition_type == 'morning':
                self.game_state = 'hub'
                self.game_time = 0
                self.hub.night_arrived = False
                
                if self.is_player_at_entrance():
                    self.transition_text = "Retour réussi"
                else:
                    self.transition_text = "Sauvé de justesse, mais vous avez tout perdu..."
                    self.player.health = 1
                    self.player.inventory['gold'] = 0
                    self.player.inventory['iron'] = 0
                        
                self.save_all()
            elif self.transition_type in ['night', 'wait_for_dungeon']:
                if self.transition_type == 'wait_for_dungeon':
                    self.resources_at_dungeon_start = self.player.inventory['iron']
                    self.game_time = self.evening_duration
                    self.game_state = 'loading'
                else:
                    self.game_time = 0
                self.hub.night_arrived = False
                self.save_all()

        if self.transition_alpha >= self.transition_duration: self.transition_active = False; self.transition_alpha = 0
        
        if self.game_state == 'dungeon' and not self.transition_active:
            self.visible_sprites.update()
            
            if self.player.current_weapon:
                # Use a custom collision check against the enemy's hitbox instead of its massive visual rect
                hitted_enemies = [
                    e for e in self.attackable_sprites 
                    if self.player.current_weapon.rect.colliderect(e.hitbox)
                ]
                for e in hitted_enemies: 
                    e.get_damage(self.player.rect.center, self.player.attack_damage)

            for enemy in self.attackable_sprites:
                # Use hitbox-to-hitbox distance for precise melee range regardless of sprite scale
                enemy_dist = pygame.math.Vector2(enemy.hitbox.center).distance_to(self.player.hitbox.center)
                in_attack_range = enemy_dist < 55
                
                enemy.enemy_update(self.player, is_attacking=in_attack_range)
                
                if in_attack_range:
                    self.player.get_damage(enemy.damage, enemy.hitbox.center)
                if enemy.health <= 0: 
                    for item_type, (min_amt, max_amt) in enemy.loot_table.items():
                        amount = random.randint(min_amt, max_amt)
                        for _ in range(amount):
                            # Drop items relative to hitbox center (the enemy's feet)
                            offset_x = random.randint(-30, 30); offset_y = random.randint(-30, 30); 
                            pos = (enemy.hitbox.centerx + offset_x, enemy.hitbox.centery + offset_y)
                            Item(pos, [self.visible_sprites, self.item_sprites], item_type)
                    enemy.kill()

            for item in pygame.sprite.spritecollide(self.player, self.item_sprites, True):
                if item.type in self.player.inventory: self.player.inventory[item.type] += 1

            if len([e for e in self.attackable_sprites if hasattr(e, 'health')]) == 0 and not self.transition_active:
                self.transition_active = True; self.transition_alpha = 0; self.transition_type = 'morning'; self.game_time = self.full_day_duration
            if self.player.health <= 0 and self.game_state == 'dungeon':
                # Start death sequence: clear loot, enter 'dying' state
                self.player.inventory['gold'] = 0
                self.player.inventory['iron'] = 0
                self.game_state = 'dying'
                self.player._death_anim_done = False

        if self.game_state == 'dying':
            # Keep updating animations while death animation plays
            self.visible_sprites.update()
            if getattr(self.player, '_death_anim_done', False):
                self.game_state = 'game_over'
                # Build game over button once
                btn_w, btn_h = 260, 56
                self._go_btn = pygame.Rect((WIDTH - btn_w) // 2, HEIGHT // 2 + 60, btn_w, btn_h)

    def update_multi(self):
        if not self.network: return
        
        if self.transition_active:
            self.transition_alpha += 1
            if self.transition_alpha >= self.transition_duration:
                self.transition_active = False
                self.transition_alpha = 0
                self.transition_type = None

        action = 'idle'
        if self.multi_state == 'resting':
            action = 'resting'
        elif self.multi_state == 'waiting_others':
            action = 'ready_next'
        elif getattr(self, 'request_start', False):
            action = 'start_game'
            self.request_start = False
        
        if self.player.health <= 0 and self.multi_state not in ['gameover', 'resting']:
            action = 'player_died'
            
        payload = {
            'action': action, 
            'pos': (self.player.hitbox.x, self.player.hitbox.y),
            'status': self.player.status,
            'facing_right': self.player.facing_right,
            'client_level': self.multi_level if self.game_state != 'multi_lobby' else 0
        }
        
        if self.multi_state == 'playing':
            my_enemy_pos = {}
            if self.player_id == self.host_id:
                for enemy in self.attackable_sprites:
                    # Send hitbox position as the authoritative physics point
                    if hasattr(enemy, 'multiplayer_id'): 
                        my_enemy_pos[enemy.multiplayer_id] = (enemy.hitbox.x, enemy.hitbox.y)
            
            payload['killed_enemies'] = list(self.killed_enemies_queue) 
            payload['enemy_positions'] = my_enemy_pos
            
        self.current_payload = payload
        
        server_data = self.multi_server_data_cache
        if server_data:
            self.multi_server_data_cache = server_data
            srv_state = server_data.get('state')
            srv_level = server_data.get('level')
            
            if srv_state == 'GAME_OVER':
                self.game_state = 'multi_gameover'; self.multi_state = 'gameover'; return
                
            if srv_state == 'PLAYING':
                if self.game_state == 'multi_lobby' or self.multi_level != srv_level:
                    self.multi_level = srv_level
                    if self.multi_resting_for_level == self.multi_level:
                        self.multi_state = 'resting'
                        self.game_state = 'multi_resting'
                    else:
                        if self.multi_resting_for_level != -1 and self.multi_resting_for_level < self.multi_level: 
                            self.player.health = self.player.max_health
                            self.multi_resting_for_level = -1
                            
                        self.build_map_multi(server_data)
                        self.game_state = 'dungeon'
                        self.multi_state = 'playing'
                        self.game_time = self.evening_duration
                        
                        self.transition_active = True
                        self.transition_alpha = 0
                        self.transition_duration = 180
                        self.transition_type = 'multi_level_start'
                        self.transition_text = f"Donjon {self.multi_level}"
                        
            if self.multi_state == 'playing':
                self.game_time += self.clock.get_time()
                self.sync_multi_entities(server_data)
                
                if self.game_time >= self.full_day_duration:
                    if self.is_player_at_entrance(): self.multi_state = 'upgrade'
                    else: self.multi_state = 'rescue'

    def sync_multi_entities(self, server_data):
        players_data = server_data.get('players', {})
        active_pids = list(players_data.keys())
        if active_pids: self.host_id = min(active_pids)
        
        for pid, pdata in players_data.items():
            if pid != self.player_id:
                if pid not in self.other_players: 
                    clone = Player((pdata.x, pdata.y), [self.visible_sprites], self.obstacle_sprites)
                    clone.input = lambda: None
                    clone.is_remote = True
                    self.other_players[pid] = clone
                else:
                    clone = self.other_players[pid]
                    # Apply to hitbox (authoritative physics position), then sync visual rect
                    clone.hitbox.x = pdata.x
                    clone.hitbox.y = pdata.y
                    clone.pos.x = pdata.x
                    clone.pos.y = pdata.y
                    clone.rect.midbottom = clone.hitbox.midbottom
                    # Sync animation state
                    new_status = getattr(pdata, 'status', 'idle')
                    if clone.status != new_status:
                        clone.status = new_status
                        clone.frame_index = 0
                    clone.facing_right = getattr(pdata, 'facing_right', True)
        
        for pid in list(self.other_players.keys()):
            if pid not in active_pids: self.other_players[pid].kill(); del self.other_players[pid]

        dead_enemies = server_data.get('dead_enemies', [])
        srv_enemies = {e['id']: e for e in server_data.get('server_enemies', [])}
        
        for enemy in list(self.attackable_sprites):
            if hasattr(enemy, 'multiplayer_id'):
                eid = enemy.multiplayer_id
                if eid in dead_enemies or eid not in srv_enemies: enemy.kill()
                elif self.player_id != self.host_id:
                    # Target authoritative hitbox position, then sync visual rect
                    enemy.hitbox.x = srv_enemies[eid]['x']; enemy.hitbox.y = srv_enemies[eid]['y']
                    enemy.pos.x = enemy.hitbox.x; enemy.pos.y = enemy.hitbox.y
                    enemy.rect.midbottom = enemy.hitbox.midbottom

        self.visible_sprites.update()

        if self.player.current_weapon:
            hitted_enemies = [
                e for e in self.attackable_sprites 
                if self.player.current_weapon.rect.colliderect(e.hitbox)
            ]
            for e in hitted_enemies: 
                e.get_damage(self.player.rect.center, self.player.attack_damage)

        for enemy in self.attackable_sprites:
            # Use hitbox-to-hitbox distance for precise range regardless of sprite scale
            enemy_dist = pygame.math.Vector2(enemy.hitbox.center).distance_to(self.player.hitbox.center)
            in_attack_range = enemy_dist < 55

            # Only the HOST runs enemy AI (pathfinding, movement, collisions)
            # The non-host receives positions from the server — no need to compute them
            if self.player_id == self.host_id: 
                target = self.player
                min_dist = pygame.math.Vector2(self.player.rect.center).distance_to(enemy.rect.center)
                for p in self.other_players.values():
                    if p.rect.x > -1000: 
                        dist = pygame.math.Vector2(p.rect.center).distance_to(enemy.rect.center)
                        if dist < min_dist:
                            min_dist = dist
                            target = p
                enemy.enemy_update(target, is_attacking=in_attack_range)

            if in_attack_range:
                self.player.get_damage(enemy.damage, enemy.hitbox.center)

            if enemy.health <= 0:
                if hasattr(enemy, 'multiplayer_id'): self.killed_enemies_queue.append(enemy.multiplayer_id)
                for item_type, (min_amt, max_amt) in enemy.loot_table.items():
                    amount = random.randint(min_amt, max_amt)
                    for _ in range(amount):
                        offset_x = random.randint(-30, 30); offset_y = random.randint(-30, 30); pos = (enemy.hitbox.centerx + offset_x, enemy.hitbox.centery + offset_y)
                        Item(pos, [self.visible_sprites, self.item_sprites], item_type)
                enemy.kill()

        for item in pygame.sprite.spritecollide(self.player, self.item_sprites, True):
            if item.type in self.player.inventory: self.player.inventory[item.type] += 1

    def build_map_solo(self):
        self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
        dungeon = DungeonGenerator(); map_data, player_spawn = dungeon.generate()
        for row_index, row in enumerate(map_data):
            for col_index, cell in enumerate(row):
                pos = (col_index * TILE_SIZE, row_index * TILE_SIZE)
                if cell == 'x': 
                    Tile(pos, [self.visible_sprites, self.obstacle_sprites])
                elif cell == ' ':
                    Floor(pos, [self.visible_sprites])
        spawn_pos = (player_spawn[0] * TILE_SIZE, player_spawn[1] * TILE_SIZE)
        entrance = DungeonEntrance(spawn_pos, [self.visible_sprites])
        self.dungeon_entrance_pos = pygame.math.Vector2(spawn_pos); self.dungeon_entrance_rect = entrance.rect
        self.player.rect.topleft = spawn_pos; self.player.pos = pygame.math.Vector2(spawn_pos); self.player.obstacle_sprites = self.obstacle_sprites; self.player.add(self.visible_sprites)
        # Restore HP and grant spawn invincibility so player can't be insta-killed
        self.player.health = self.player.max_health
        self.player.vulnerable = False
        self.player.hurt_time = pygame.time.get_ticks()
        self.player.invincibility_duration = 3000  # 3 seconds of spawn protection
        for room in dungeon.rooms[1:]:
            available_tiers = ['tier1']
            if self.player.level >= 3: available_tiers.append('tier2')
            if self.player.level >= 6: available_tiers.append('tier3')
            
            spawn_count = random.randint(3, 5 + self.player.level)
            for _ in range(spawn_count): 
                chosen_tier = random.choice(available_tiers)
                offset_x = random.randint(-40, 40)
                offset_y = random.randint(-40, 40)
                Enemy([self.visible_sprites, self.attackable_sprites], (room.centerx * TILE_SIZE + offset_x, room.centery * TILE_SIZE + offset_y), self.obstacle_sprites, chosen_tier)

    def build_map_multi(self, server_data):
        self.visible_sprites.empty(); self.obstacle_sprites.empty(); self.attackable_sprites.empty(); self.item_sprites.empty()
        self.other_players.clear() 
        self.killed_enemies_queue.clear()
        
        for obs in server_data.get('obstacles', []): Tile((obs['x'], obs['y']), [self.visible_sprites, self.obstacle_sprites])
        for floor in server_data.get('floor_tiles', []): Floor((floor['x'], floor['y']), [self.visible_sprites])
        
        spawn_pos = server_data.get('spawn_pos', (0,0))
        entrance = DungeonEntrance(spawn_pos, [self.visible_sprites])
        self.dungeon_entrance_pos = pygame.math.Vector2(spawn_pos); self.dungeon_entrance_rect = entrance.rect
        self.player.rect.topleft = spawn_pos; self.player.pos = pygame.math.Vector2(spawn_pos); self.player.obstacle_sprites = self.obstacle_sprites; self.player.add(self.visible_sprites)
        self.player.rect.topleft = spawn_pos; self.player.pos = pygame.math.Vector2(spawn_pos); self.player.obstacle_sprites = self.obstacle_sprites; self.player.add(self.visible_sprites)
        # Spawn protection
        if self.multi_level <= 1:
            self.player.health = self.player.max_health
        self.player.vulnerable = False
        self.player.hurt_time = pygame.time.get_ticks()
        self.player.invincibility_duration = 3000
        for edata in server_data.get('server_enemies', []):
            enemy = Enemy([self.visible_sprites, self.attackable_sprites], (edata['x'], edata['y']), self.obstacle_sprites, edata['type'])
            enemy.multiplayer_id = edata['id']

    def draw(self):
        if self.game_state == 'menu': self.draw_main_menu()
        elif self.game_state == 'options': self.draw_options_menu()
        elif self.game_state == 'multi_mode_select': self.draw_multi_mode_select()
        elif self.game_state == 'multi_code_input': self.draw_multi_code_input()
        elif self.game_state == 'multi_searching': self.draw_multi_searching()
        elif self.game_state == 'multi_lobby': self.draw_multi_lobby()
        elif self.game_state == 'multi_resting': self.draw_multi_resting()
        elif self.game_state == 'multi_gameover': self.draw_multi_gameover()
        elif self.game_state == 'intro': self.intro.draw(); pygame.display.flip()
        
        elif self.game_state == 'hub':
            self.hub.draw(); self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour, show_inventory=not self.hub.build_mode_active)
            if self.transition_active: self.draw_fade_transition()
            if self.paused: self.draw_pause_menu()
            pygame.display.flip()
        
        elif self.game_state == 'loading':
            self.screen.fill((0, 0, 0)); text = self.loading_font.render("Génération...", True, (255, 255, 255))
            self.screen.blit(text, text.get_rect(center=(WIDTH//2, HEIGHT//2))); pygame.display.flip()
        
        elif self.game_state == 'dungeon':
            self.screen.fill('black'); self.visible_sprites.custom_draw(self.player); self.ui.display(self.player, self.game_time, self.full_day_duration, self.morning_hour)
            if self.is_multiplayer:
                if self.multi_state == 'upgrade': self.draw_multi_upgrade()
                elif self.multi_state == 'rescue': self.draw_multi_rescue()
                elif self.multi_state == 'waiting_others': self.draw_multi_waiting()
            if self.transition_active: self.draw_fade_transition()
            if self.paused: self.draw_pause_menu()
            pygame.display.flip()

        elif self.game_state == 'dying':
            # Keep dungeon visible while death animation plays
            self.screen.fill('black')
            self.visible_sprites.custom_draw(self.player)
            pygame.display.flip()

        elif self.game_state == 'game_over':
            # Dungeon behind + dark overlay
            self.screen.fill('black')
            self.visible_sprites.custom_draw(self.player)
            self._draw_game_over()
            pygame.display.flip()

    def draw_multi_lobby(self):
        self.screen.fill((30, 30, 40))
        title = self.title_font.render("LOBBY", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))
        code = pygame.font.Font(None, 60).render(f"Code : {self.multi_code}", True, (0, 255, 100))
        self.screen.blit(code, code.get_rect(center=(WIDTH//2, 180)))
        
        primary_ip = Network.get_primary_ip()
        ip_txt = pygame.font.Font(None, 30).render(f"IP Serveur : {primary_ip}", True, (100, 150, 255))
        self.screen.blit(ip_txt, ip_txt.get_rect(center=(WIDTH//2, 230)))
        
        players_count = self.multi_server_data_cache.get('total_players', 1) if self.multi_server_data_cache else 1
        ptext = pygame.font.Font(None, 40).render(f"Joueurs connectés : {players_count}", True, (200, 200, 200))
        self.screen.blit(ptext, ptext.get_rect(center=(WIDTH//2, 280)))
        
        if self.player_id == 0:
            btn = pygame.Rect(WIDTH//2 - 100, 450, 200, 60)
            color = (100, 180, 100) if btn.collidepoint(pygame.mouse.get_pos()) else (80, 150, 80)
            pygame.draw.rect(self.screen, color, btn); pygame.draw.rect(self.screen, (255,255,255), btn, 2)
            txt = self.menu_font.render("LANCER", True, (255,255,255))
            self.screen.blit(txt, txt.get_rect(center=btn.center))
        else:
            txt = pygame.font.Font(None, 30).render("En attente de l'hôte...", True, (150, 150, 150))
            self.screen.blit(txt, txt.get_rect(center=(WIDTH//2, 480)))
        pygame.display.flip()

    def draw_multi_upgrade(self):
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(200); overlay.fill((0,0,0)); self.screen.blit(overlay, (0,0))
        title = self.title_font.render(f"EXTRACTION RÉUSSIE (Donjon {self.multi_level})", True, (50, 255, 50))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 100)))
        for i, (utype, val, desc) in enumerate([("health", 50, "Soin +50"), ("damage", 10, "Dégâts +10"), ("speed", 5, "Vitesse +5%")]):
            rect = pygame.Rect(WIDTH//2 - 125, 300 + i*100, 250, 60)
            pygame.draw.rect(self.screen, (80,120,80), rect); pygame.draw.rect(self.screen, (255,255,255), rect, 2)
            txt = pygame.font.Font(None, 32).render(desc, True, (255,255,255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))

    def draw_multi_rescue(self):
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(200); overlay.fill((50,0,0)); self.screen.blit(overlay, (0,0))
        title = self.title_font.render("ÉQUIPE DE SECOURS", True, (255, 100, 100))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 100)))
        
        btn1 = pygame.Rect(WIDTH//2 - 150, 300, 300, 60)
        pygame.draw.rect(self.screen, (120,80,80), btn1); pygame.draw.rect(self.screen, (255,255,255), btn1, 2)
        txt1 = pygame.font.Font(None, 24).render("POURSUIVRE (10 PV max)", True, (255,255,255))
        self.screen.blit(txt1, txt1.get_rect(center=btn1.center))
        
        btn2 = pygame.Rect(WIDTH//2 - 150, 400, 300, 60)
        pygame.draw.rect(self.screen, (80,80,120), btn2); pygame.draw.rect(self.screen, (255,255,255), btn2, 2)
        txt2 = pygame.font.Font(None, 24).render("SE REPOSER (Passer le prochain)", True, (255,255,255))
        self.screen.blit(txt2, txt2.get_rect(center=btn2.center))

    def draw_multi_waiting(self):
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(200); overlay.fill((0,0,0)); self.screen.blit(overlay, (0,0))
        txt = self.loading_font.render("En attente des autres joueurs...", True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))

    def draw_multi_resting(self):
        self.screen.fill((10, 10, 20))
        txt = self.title_font.render("VOUS VOUS REPOSEZ", True, (100, 150, 255))
        self.screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        txt2 = pygame.font.Font(None, 40).render(f"Retour au donjon {self.multi_level + 1}...", True, (150, 150, 150))
        self.screen.blit(txt2, txt2.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
        pygame.display.flip()

    def draw_multi_gameover(self):
        self.screen.fill((50, 0, 0))
        txt = self.title_font.render("GAME OVER", True, (255, 50, 50))
        self.screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        txt2 = pygame.font.Font(None, 40).render("Un membre de l'équipe a péri...", True, (255, 255, 255))
        self.screen.blit(txt2, txt2.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
        
        btn = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 150, 300, 60)
        color = (150, 50, 50) if btn.collidepoint(pygame.mouse.get_pos()) else (100, 30, 30)
        pygame.draw.rect(self.screen, color, btn)
        pygame.draw.rect(self.screen, (255, 255, 255), btn, 2)
        txt3 = self.menu_font.render("RETOUR AU MENU", True, (255, 255, 255))
        self.screen.blit(txt3, txt3.get_rect(center=btn.center))
        
        pygame.display.flip()

    def draw_main_menu(self):
        self.screen.fill((20, 20, 30))
        title_surf = self.title_font.render(GAME_NAME, True, (200, 180, 50))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 150))
        shadow_surf = self.title_font.render(GAME_NAME, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(WIDTH // 2 + 5, 155))
        self.screen.blit(shadow_surf, shadow_rect); self.screen.blit(title_surf, title_rect)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            if btn['rect'].collidepoint(mouse_pos): bg_color = (100, 100, 120); text_color = (255, 255, 255); border_width = 3
            else: bg_color = (50, 50, 60); text_color = (200, 200, 200); border_width = 0
            pygame.draw.rect(self.screen, bg_color, btn['rect'], border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), btn['rect'], 2, border_radius=10)
            text_surf = self.menu_font.render(btn['text'], True, text_color)
            text_rect = text_surf.get_rect(center=btn['rect'].center)
            self.screen.blit(text_surf, text_rect)
        version_surf = pygame.font.Font(UI_FONT, 20).render("v0.3.1 - Stable", True, (80, 80, 80))
        self.screen.blit(version_surf, (10, HEIGHT - 30))
        pygame.display.flip()

    def draw_options_menu(self):
        self.screen.fill((20, 20, 30))
        title_surf = self.title_font.render("OPTIONS", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 150))
        self.screen.blit(title_surf, title_rect)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.options_buttons:
            is_reset = (btn['action'] == 'reset_save')
            if btn['rect'].collidepoint(mouse_pos):
                if is_reset: bg_color = (200, 50, 50) 
                else: bg_color = (100, 100, 120)
                text_color = (255, 255, 255); border_width = 3
            else:
                if is_reset: bg_color = (150, 30, 30)
                else: bg_color = (50, 50, 60)
                text_color = (200, 200, 200); border_width = 0
            pygame.draw.rect(self.screen, bg_color, btn['rect'], border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), btn['rect'], 2, border_radius=10)
            text_surf = self.menu_font.render(btn['text'], True, text_color)
            text_rect = text_surf.get_rect(center=btn['rect'].center)
            self.screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        title_surf = self.menu_font.render("PAUSE", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title_surf, title_rect)
        center_x = WIDTH // 2; center_y = HEIGHT // 2; btn_width = 300; btn_height = 50; gap = 70
        
        buttons = []
        if self.game_state == 'hub':
            buttons.append({'text': "SAUVEGARDER & MENU", 'color': (50, 150, 50)})
            buttons.append({'text': "RETOUR JEU", 'color': (100, 100, 100)})
        elif self.game_state == 'dungeon':
            if self.is_multiplayer:
                buttons.append({'text': "RETOUR MENU", 'color': (150, 50, 50)})
                buttons.append({'text': "RETOUR JEU", 'color': (100, 100, 100)})
            else:
                buttons.append({'text': "RETOUR HUB", 'color': (150, 50, 50)})
                buttons.append({'text': "SAUVEGARDER & MENU", 'color': (150, 50, 50)})
                buttons.append({'text': "RETOUR JEU", 'color': (100, 100, 100)})
                
        start_y = center_y - (len(buttons) * gap) // 2
        mouse_pos = pygame.mouse.get_pos()
        for i, btn in enumerate(buttons):
            rect = pygame.Rect(0, 0, btn_width, btn_height)
            rect.center = (center_x, start_y + i * gap)
            if rect.collidepoint(mouse_pos):
                color = (min(btn['color'][0] + 50, 255), min(btn['color'][1] + 50, 255), min(btn['color'][2] + 50, 255)); border = 3
            else: color = btn['color']; border = 0
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=8)
            text_surf = pygame.font.Font(UI_FONT, 20).render(btn['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

    def draw_multi_mode_select(self):
        self.screen.fill((30, 30, 40))
        title = self.title_font.render("Multijoueur", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))
        cx, cy = WIDTH // 2, HEIGHT // 2
        server_btn = pygame.Rect(cx - 220, cy - 80, 180, 70)
        client_btn = pygame.Rect(cx + 40, cy - 80, 180, 70)
        back_btn = pygame.Rect(cx - 90, cy + 80, 180, 50)
        mouse_pos = pygame.mouse.get_pos()
        for rect, text in [(server_btn, "SERVEUR"), (client_btn, "CLIENT"), (back_btn, "RETOUR")]:
            is_hovered = rect.collidepoint(mouse_pos)
            color = (80, 120, 80) if is_hovered else (60, 100, 60) if text != "RETOUR" else (80, 80, 80)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2)
            txt = self.menu_font.render(text, True, (255, 255, 255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))
        
        if self.multi_status:
            status_txt = pygame.font.Font(None, 20).render(self.multi_status, True, (200, 100, 100))
            self.screen.blit(status_txt, status_txt.get_rect(center=(WIDTH//2, 430)))
            
        pygame.display.flip()

    def draw_multi_code_input(self):
        self.screen.fill((30, 30, 40))
        title = self.title_font.render("Rejoindre", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))
        hint = pygame.font.Font(None, 24).render("Entrez le PIN (6 chiffres) ou l'IP du serveur", True, (180, 180, 180))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH//2, 140)))
        code_rect = pygame.Rect(WIDTH//2 - 150, 200, 300, 60)
        pygame.draw.rect(self.screen, (100, 100, 100), code_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), code_rect, 2)
        # Support both PIN (fixed length) and IP (variable length)
        display_text = self.multi_code
        if len(self.multi_code) <= 6 and '.' not in self.multi_code:
             display_text += "_" * (6 - len(self.multi_code))
             
        code_display = self.menu_font.render(display_text, True, (0, 0, 0))
        self.screen.blit(code_display, (code_rect.x + 10, code_rect.y + 10))
        search_btn = pygame.Rect(WIDTH//2 - 100, 290, 200, 50)
        back_btn = pygame.Rect(WIDTH//2 - 100, 360, 200, 50)
        mouse_pos = pygame.mouse.get_pos()
        for rect, text in [(search_btn, "RECHERCHER"), (back_btn, "RETOUR")]:
            is_hovered = rect.collidepoint(mouse_pos)
            is_enabled = text == "RETOUR" or len(self.multi_code) >= 6 or '.' in self.multi_code
            color = (100, 150, 100) if is_hovered and is_enabled else (80, 80, 80)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2)
            txt = self.menu_font.render(text, True, (255, 255, 255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))
        if self.multi_status:
            status_txt = pygame.font.Font(None, 20).render(self.multi_status, True, (200, 100, 100))
            self.screen.blit(status_txt, status_txt.get_rect(center=(WIDTH//2, 430)))
        pygame.display.flip()

    def draw_multi_searching(self):
        self.screen.fill((30, 30, 40))
        title = self.title_font.render("Recherche...", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2)))
        pygame.display.flip()

    def draw_fade_transition(self):
        progress = self.transition_alpha / self.transition_duration
        if progress < 1/3: opacity = int((progress / (1/3)) * 255); text_opacity = int((progress / (1/3)) * 255)
        elif progress < 2/3: opacity = 255; text_opacity = 255
        else: fade_out_progress = (progress - 2/3) / (1/3); opacity = int((1 - fade_out_progress) * 255); text_opacity = int((1 - fade_out_progress) * 255)
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.set_alpha(opacity); fade_surface.fill((0, 0, 0)); self.screen.blit(fade_surface, (0, 0))
        if text_opacity > 0:
            text_surface = self.transition_font.render(self.transition_text, True, (255, 255, 255))
            text_surface.set_alpha(text_opacity); text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text_surface, text_rect)

    def manage_music(self):
        should_play = False
        
        if not self.is_multiplayer and self.game_state == 'hub':
            should_play = True
        elif self.game_state in ['multi_mode_select', 'multi_code_input', 'multi_searching', 'multi_lobby']:
            should_play = True
            
        if should_play and not getattr(self, 'music_playing', False):
            try:
                pygame.mixer.music.play(-1)
                self.music_playing = True
            except: pass
        elif not should_play and getattr(self, 'music_playing', False):
            try:
                pygame.mixer.music.stop()
                self.music_playing = False
            except: pass

    def run(self):
        while True:
            self.manage_music()
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)