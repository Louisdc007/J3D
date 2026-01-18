import pygame
import os
from settings import WIDTH, HEIGHT, UI_FONT

class IntroScene:
    def __init__(self, screen):
        self.screen = screen
        
        self.fade_speed = 3
        self.slide_duration = 4000
        try:
            self.font = pygame.font.Font(UI_FONT, 30)
            self.big_font = pygame.font.Font(UI_FONT, 60)
        except:
            self.font = pygame.font.SysFont("arial", 30)
            self.big_font = pygame.font.SysFont("arial", 60)

        self.slides = [
            {
                "image_name": "1.png", 
                "text": "Jadis, un chevalier servait loyalement son Seigneur...",
                "color": (100, 100, 200)
            },
            {
                "image_name": "2.png",
                "text": "Mais le Seigneur fut corrompu par une soif d'or insatiable.",
                "color": (100, 200, 100)
            },
            {
                "image_name": "3.png",
                "text": "Il partit en quête d'un trésor interdit...",
                "color": (200, 100, 100)
            },
            {
                "image_name": "4.png",
                "text": "...et revint maudit par un sombre artefact.",
                "color": (100, 100, 100)
            },
            {
                "image_name": "5.png",
                "text": "Désormais, les donjons surgissent et le monde attend un...",
                "color": (50, 50, 50)
            }
        ]
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(current_dir, "assets", "intro")

        self.loaded_images = []
        
        for slide in self.slides:
            filename = slide["image_name"]
            full_path = os.path.join(assets_path, filename)
            
            if os.path.exists(full_path):
                try:
                    img = pygame.image.load(full_path).convert()
                    img = pygame.transform.scale(img, (WIDTH, HEIGHT))
                except pygame.error:
                    img = self.create_placeholder(slide["color"])
            else:
                img = self.create_placeholder(slide["color"])
                
            self.loaded_images.append(img)

        self.fade_surf = pygame.Surface((WIDTH, HEIGHT))
        self.fade_surf.fill((0, 0, 0))
        
        self.reset()

    def reset(self):
        self.current_slide_index = 0
        self.state = "FADE_IN"
        self.alpha = 255
        self.timer = pygame.time.get_ticks()
        self.finished = False

    def create_placeholder(self, color):
        img = pygame.Surface((WIDTH, HEIGHT))
        img.fill(color)
        return img

    def update(self):
        if self.finished:
            return True

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and self.state == "WAIT":
            self.state = "FADE_OUT"

        if self.state == "FADE_IN":
            self.alpha -= self.fade_speed
            if self.alpha <= 0:
                self.alpha = 0
                self.state = "WAIT"
                self.timer = pygame.time.get_ticks()

        elif self.state == "WAIT":
            current_time = pygame.time.get_ticks()
            if current_time - self.timer > self.slide_duration:
                self.state = "FADE_OUT"

        elif self.state == "FADE_OUT":
            self.alpha += self.fade_speed
            if self.alpha >= 255:
                self.alpha = 255
                self.current_slide_index += 1
                
                if self.current_slide_index >= len(self.slides):
                    self.state = "FINAL_HERO"
                    self.timer = pygame.time.get_ticks()
                else:
                    self.state = "FADE_IN"

        elif self.state == "FINAL_HERO":
            self.alpha -= 1
            if self.alpha < 0: self.alpha = 0
            
            if (pygame.time.get_ticks() - self.timer > 4000) or keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
                 self.finished = True
                 return True

        return False

    def draw(self):
        self.screen.fill((0, 0, 0))

        if self.state == "FINAL_HERO":
            text_surf = self.big_font.render("HEROS", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.screen.blit(text_surf, text_rect)
            
            self.fade_surf.set_alpha(self.alpha)
            self.screen.blit(self.fade_surf, (0,0))
            
        else:
            if self.current_slide_index < len(self.loaded_images):
                current_img = self.loaded_images[self.current_slide_index]
                self.screen.blit(current_img, (0, 0))
                text = self.slides[self.current_slide_index]["text"]
                text_surf = self.font.render(text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT - 80))
                
                bg_rect = text_rect.inflate(40, 20)
                s = pygame.Surface((bg_rect.width, bg_rect.height))
                s.set_alpha(150)
                s.fill((0,0,0))
                self.screen.blit(s, bg_rect.topleft)
                
                self.screen.blit(text_surf, text_rect)

            self.fade_surf.set_alpha(self.alpha)
            self.screen.blit(self.fade_surf, (0, 0))