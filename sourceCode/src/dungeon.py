import random
import pygame

class DungeonGenerator:
    def __init__(self):
        self.width = 100 
        self.height = 100
        self.map = [['x' for _ in range(self.width)] for _ in range(self.height)]
        self.rooms = []

    def create_room(self, x, y, w, h):
        self.rooms.append(pygame.Rect(x, y, w, h))
        
        for i in range(h):
            for j in range(w):
                if 0 <= y + i < self.height and 0 <= x + j < self.width:
                    self.map[y + i][x + j] = ' '

    def create_organic_tunnel(self, start, end):

        x, y = start
        target_x, target_y = end
        
        while (x, y) != (target_x, target_y):
            
            if 0 <= y < self.height and 0 <= x < self.width:
                self.map[y][x] = ' '
                
                if x + 1 < self.width: self.map[y][x+1] = ' '
                if y + 1 < self.height: self.map[y+1][x] = ' '

            move_options = []
            
            if x < target_x: move_options.append((1, 0))
            elif x > target_x: move_options.append((-1, 0))
            
            if y < target_y: move_options.append((0, 1))
            elif y > target_y: move_options.append((0, -1))
            
            for _ in range(2):
                move_options.append((1, 0))
                move_options.append((-1, 0))
                move_options.append((0, 1))
                move_options.append((0, -1))
            
            dx, dy = random.choice(move_options)
            x += dx
            y += dy
            
            x = max(1, min(x, self.width - 2))
            y = max(1, min(y, self.height - 2))

    def generate(self, num_rooms=8, boss_room=False):
        self.boss_room = None
        for _ in range(num_rooms):
            w = random.randint(6, 10)
            h = random.randint(6, 10)
            
            x = random.randint(2, self.width - w - 2)
            y = random.randint(2, self.height - h - 2)
            
            self.create_room(x, y, w, h)
            
        for i in range(len(self.rooms) - 1):

            start_pos = (int(self.rooms[i].centerx), int(self.rooms[i].centery))

            end_pos = (int(self.rooms[i+1].centerx), int(self.rooms[i+1].centery))
            
            self.create_organic_tunnel(start_pos, end_pos)

        if boss_room:
            self._add_boss_arena()

        return self.map, self.rooms[0].center

    def _add_boss_arena(self):
        """Grande arène pour le boss, la plus éloignée possible du départ."""
        w, h = 16, 13
        spawn = pygame.math.Vector2(self.rooms[0].center)
        best = None
        for _ in range(60):
            x = random.randint(2, self.width - w - 2)
            y = random.randint(2, self.height - h - 2)
            cand = pygame.Rect(x, y, w, h)
            d = spawn.distance_to(cand.center)
            if best is None or d > best[0]:
                best = (d, cand)
        arena = best[1]
        nearest = min(self.rooms, key=lambda r: pygame.math.Vector2(r.center).distance_to(arena.center))
        self.create_room(arena.x, arena.y, w, h)
        self.create_organic_tunnel((int(nearest.centerx), int(nearest.centery)),
                                   (int(arena.centerx), int(arena.centery)))
        self.boss_room = arena

def split_cells(map_data):
    """Sépare la carte en (cases de sol, murs utiles).

    Seuls les murs à 2 cases ou moins du sol sont conservés : la roche
    pleine au-delà n'est jamais visible ni atteignable, inutile d'en faire des
    sprites (gain énorme en mémoire, en rendu et en collisions).
    """
    h = len(map_data)
    w = len(map_data[0]) if h else 0
    floors, walls = [], []
    for y in range(h):
        row = map_data[y]
        for x in range(w):
            if row[x] == ' ':
                floors.append((x, y))
            elif row[x] == 'x':
                touch = False
                for dy in (-2, -1, 0, 1, 2):
                    yy = y + dy
                    if 0 <= yy < h:
                        r2 = map_data[yy]
                        for dx in (-2, -1, 0, 1, 2):
                            xx = x + dx
                            if 0 <= xx < w and r2[xx] == ' ':
                                touch = True
                                break
                    if touch:
                        break
                if touch:
                    walls.append((x, y))
    return floors, walls


def torch_spots(floor_set, wall_set, every=11):
    """Murs (avec du sol juste en dessous) choisis de façon déterministe pour
    accueillir une torche : identique chez tous les joueurs en multijoueur."""
    spots = []
    for (x, y) in wall_set:
        if (x, y + 1) in floor_set and (x - 1, y) in wall_set and (x + 1, y) in wall_set:
            if (x * 7349 + y * 1931) % every == 0:
                spots.append((x, y))
    return spots
