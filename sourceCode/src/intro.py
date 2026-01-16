import pygame
import sys
import os
from settings import WIDTH, HEIGHT, UI_FONT

class IntroScene:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        
        # --- CONFIGURATION ---
        self.fade_speed = 3
        self.slide_duration = 4000
        
        # --- POLICE ---
        try:
            self.font = pygame.font.Font(UI_FONT, 30)
            self.big_font = pygame.font.Font(UI_FONT, 60)
        except:
            self.font = pygame.font.SysFont("arial", 30)
            self.big_font = pygame.font.SysFont("arial", 60)

        # --- SCENARIO (Images + Textes) ---
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
        
        # --- CHARGEMENT DES IMAGES (ROBUSTE) ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # On construit le chemin vers le dossier des assets : src/assets/intro
        assets_path = os.path.join(current_dir, "assets", "intro")

        self.loaded_images = []
        
        print(f"--- Chargement de l'intro ---")
        print(f"Dossier source : {current_dir}")
        print(f"Dossier assets : {assets_path}")

        for slide in self.slides:
            filename = slide["image_name"]
            # Construction du chemin complet: src/assets/intro/1.png
            full_path = os.path.join(assets_path, filename)
            
            if os.path.exists(full_path):
                try:
                    img = pygame.image.load(full_path).convert()
                    img = pygame.transform.scale(img, (WIDTH, HEIGHT))
                    print(f"[OK] Chargé : {filename}")
                except pygame.error as e:
                    print(f"[ERREUR] Echec lecture {filename} : {e}")
                    img = self.create_placeholder(slide["color"])
            else:
                print(f"[MANQUANT] Introuvable : {full_path}")
                img = self.create_placeholder(slide["color"])
                
            self.loaded_images.append(img)

        # --- ETAT DE LA SCENE ---
        self.current_slide_index = 0
        self.state = "FADE_IN"
        self.alpha = 255
        self.timer = 0
        
        self.fade_surf = pygame.Surface((WIDTH, HEIGHT))
        self.fade_surf.fill((0, 0, 0))

    def create_placeholder(self, color):
        img = pygame.Surface((WIDTH, HEIGHT))
        img.fill(color)
        pygame.draw.circle(img, (255,255,255), (WIDTH//2, HEIGHT//2), 100, 5)
        return img

    def run(self):
        while self.running:
            dt = self.clock.tick(60)
            self.handle_events()
            self.update(dt)
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False 
                if event.key == pygame.K_SPACE and self.state == "WAIT":
                    self.state = "FADE_OUT"

    def update(self, dt):
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
                else:
                    self.state = "FADE_IN"

        elif self.state == "FINAL_HERO":
            self.alpha -= 1
            if self.alpha < 0: self.alpha = 0
            
            # Auto-quit après 3 secondes sur l'écran HERO
            if self.alpha == 0 and pygame.time.get_ticks() - self.timer > 3000:
                 # Optionnel : self.running = False pour enchainer direct
                 pass

    def draw(self):
        self.screen.fill((0, 0, 0))

        if self.state == "FINAL_HERO":
            text_surf = self.big_font.render("HEROS", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.screen.blit(text_surf, text_rect)
            
            self.fade_surf.set_alpha(self.alpha)
            self.screen.blit(self.fade_surf, (0,0))
            
            if self.alpha == 0:
                cont_surf = self.font.render("Appuyez pour commencer", True, (100, 100, 100))
                self.screen.blit(cont_surf, (WIDTH//2 - cont_surf.get_width()//2, HEIGHT - 100))
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
                self.running = False

        else:
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

        pygame.display.flip()

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    IntroScene(screen).run()
    pygame.quit()
