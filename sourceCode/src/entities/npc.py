import pygame
import random
from settings import *

class NPC(pygame.sprite.Sprite):
    def __init__(self, groups, pos, obstacles):
        super().__init__(groups)
        
        self.image = pygame.Surface((14, 28), pygame.SRCALPHA)
        colors = [(150, 60, 60), (70, 120, 70), (70, 80, 140), (160, 140, 60), (120, 80, 50), (110, 70, 130)]
        self.shirt = random.choice(colors)
        self.skin = random.choice([(240, 200, 170), (210, 160, 120), (160, 110, 80), (110, 75, 55)])
        self.hair = random.choice([(50, 35, 20), (120, 80, 30), (20, 20, 20), (200, 180, 120), (150, 150, 150)])
        self.walk_t = random.uniform(0, 6)
        self.speech = None
        self.speech_until = 0
        
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()
        
        self.speed = 0.8 

        self.obstacle_sprites = obstacles
        
        self.start_time = pygame.time.get_ticks()
        self.duration = random.randint(2000, 6000)
        self.center_village = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
        self.village_radius = 400 

    def patrol(self):
        current_time = pygame.time.get_ticks()
        
        if current_time - self.start_time >= self.duration:
            self.start_time = pygame.time.get_ticks()
            self.duration = random.randint(3000, 8000)

            choice = random.randint(0, 3)
            if choice == 0:
                self.direction = pygame.math.Vector2(0, 0)
            else:
                self.direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                if self.direction.magnitude() != 0:
                    self.direction = self.direction.normalize()

    def check_boundaries(self):
        dist = (self.pos - self.center_village).magnitude()
        if dist > self.village_radius:
            direction_to_center = self.center_village - self.pos
            if direction_to_center.magnitude() != 0:
                self.direction = direction_to_center.normalize()

    def collision(self, direction):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.x > 0:
                        self.rect.right = sprite.rect.left
                        self.pos.x = self.rect.x
                        self.direction.x *= -1
                    elif self.direction.x < 0:
                        self.rect.left = sprite.rect.right
                        self.pos.x = self.rect.x
                        self.direction.x *= -1

        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.rect.colliderect(self.rect):
                    if self.direction.y > 0:
                        self.rect.bottom = sprite.rect.top
                        self.pos.y = self.rect.y
                        self.direction.y *= -1
                    elif self.direction.y < 0:
                        self.rect.top = sprite.rect.bottom
                        self.pos.y = self.rect.y
                        self.direction.y *= -1

    def move(self):
        if self.direction.magnitude() != 0:
            self.pos.x += self.direction.x * self.speed
            self.rect.x = int(self.pos.x)
            self.collision('horizontal')

            self.pos.y += self.direction.y * self.speed
            self.rect.y = int(self.pos.y)
            self.collision('vertical')

    def update(self):
        if self.speech and pygame.time.get_ticks() < self.speech_until:
            return  # il s'arrête pour parler
        self.patrol()
        self.check_boundaries()
        self.move()
        if self.direction.magnitude() != 0:
            self.walk_t += 0.25

    def say(self, text, ms=3500):
        self.speech = text
        self.speech_until = pygame.time.get_ticks() + ms

    def draw_speech(self, surface):
        if not self.speech or pygame.time.get_ticks() > self.speech_until:
            return
        from fx import get_font
        font = get_font(15)
        words, lines, line = self.speech.split(), [], ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] > 220:
                lines.append(line); line = w
            else:
                line = test
        lines.append(line)
        w = max(font.size(l)[0] for l in lines) + 16
        h = len(lines) * 17 + 10
        box = pygame.Rect(0, 0, w, h)
        box.midbottom = (self.rect.centerx, self.rect.top - 22)
        box.clamp_ip(surface.get_rect().inflate(-8, -8))
        pygame.draw.rect(surface, (250, 244, 228), box, border_radius=8)
        pygame.draw.rect(surface, (60, 45, 30), box, 2, border_radius=8)
        tip = [(self.rect.centerx - 5, box.bottom - 1), (self.rect.centerx + 5, box.bottom - 1), (self.rect.centerx, box.bottom + 7)]
        pygame.draw.polygon(surface, (250, 244, 228), tip)
        for i, l in enumerate(lines):
            surface.blit(font.render(l, True, (40, 30, 22)), (box.x + 8, box.y + 5 + i * 17))

    def draw(self, surface):
        import math
        x, y = self.rect.midbottom
        moving = self.direction.magnitude() != 0
        step = math.sin(self.walk_t) * 3 if moving else 0
        bob = abs(math.sin(self.walk_t)) * 1.5 if moving else 0
        sh = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        surface.blit(sh, (x - 9, y - 3))
        # jambes
        pygame.draw.line(surface, (50, 40, 35), (x - 3, y - 9), (x - 3 + step, y - 1), 3)
        pygame.draw.line(surface, (50, 40, 35), (x + 3, y - 9), (x + 3 - step, y - 1), 3)
        # corps
        body = pygame.Rect(0, 0, 12, 12)
        body.midbottom = (x, y - 8 - bob)
        pygame.draw.rect(surface, self.shirt, body, border_radius=3)
        pygame.draw.rect(surface, tuple(max(0, c - 50) for c in self.shirt), body, 1, border_radius=3)
        # tête
        hx, hy = x, int(body.top - 5)
        pygame.draw.circle(surface, self.skin, (hx, hy), 5)
        pygame.draw.arc(surface, self.hair, (hx - 5, hy - 6, 10, 9), 0, math.pi, 3)
        facing = 1 if self.direction.x >= 0 else -1
        surface.fill((20, 20, 20), (hx + facing * 2, hy - 1, 1, 2))