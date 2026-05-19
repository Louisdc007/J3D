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

    def generate(self, num_rooms=8):
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
            
        return self.map, self.rooms[0].center