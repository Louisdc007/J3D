import pygame
import sys
import math

# --- IMPORTS DE TES MODULES ---
try:
    from systeme_multijoueur.client_main import run_multiplayer
except ImportError as e:
    print(f"Erreur import multijoueur : {e}")

try:
    from game import Game
except ImportError as e:
    print(f"Erreur import solo : {e}")

pygame.init()
pygame.mixer.init()

# 🎵 Musique d'intro
try:
    pygame.mixer.music.load("intro_mixkit.mp3")
    pygame.mixer.music.set_volume(0.6)
    pygame.mixer.music.play()
except:
    print("Fichier audio intro_mixkit.mp3 introuvable, suite sans musique.")

# 🔊 Son crash
try:
    crash_sound = pygame.mixer.Sound("crash.mp3")
    crash_sound.set_volume(0.8)
except:
    pass

# Fenêtre du Menu
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GREED")

clock = pygame.time.Clock()
NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
ROUGE = (180, 0, 0)

# --- VARIABLES TEMPORELLES ET D'ANIMATION (LOUIS) ---
start_time = pygame.time.get_ticks()

font_greed = pygame.font.SysFont("arial", 125, bold=True)
font_question = pygame.font.SysFont("arial", 30)
font_action = pygame.font.SysFont("arial", 22, italic=True)

text_surface = font_greed.render("GREED", True, ROUGE)
PIXEL_SCALE = 8
small_surface = pygame.transform.scale(
    text_surface,
    (text_surface.get_width() // PIXEL_SCALE,
     text_surface.get_height() // PIXEL_SCALE)
)

alpha_title = 0
title_y_start = HEIGHT // 2
title_y_target = HEIGHT // 2 - 120
current_title_y = title_y_start
slide_duration = 1200
slide_start_time = None

def ease_cos(t):
    return (1 - math.cos(math.pi * t)) / 4

crash_played = False

# --- GESTION DES ÉTATS DU MENU ---
STATE_INTRO = "intro"
STATE_CHOICE = "choice"
current_state = STATE_INTRO

running = True
while running:
    current_time = pygame.time.get_ticks()
    elapsed_seconds = (current_time - start_time) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and elapsed_seconds >= 8:
            if current_state == STATE_INTRO:
                current_state = STATE_CHOICE
                if not crash_played:
                    try:
                        crash_sound.play()
                    except: pass
                    crash_played = True
            
            # --- LOGIQUE DE SÉLECTION ---
            elif current_state == STATE_CHOICE:
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    # Lancement Solo
                    game = Game()
                    game.run()
                    # Si on quitte le solo, on redimensionne le menu
                    screen = pygame.display.set_mode((WIDTH, HEIGHT))
                    
                elif event.key == pygame.K_2 or event.key == pygame.K_KP2:
                    # Lancement Multijoueur
                    run_multiplayer()
                    # Au retour (après avoir fait ECHAP), on remet la taille du menu
                    screen = pygame.display.set_mode((WIDTH, HEIGHT))
                    pygame.display.set_caption("GREED - Menu")

    screen.fill(NOIR)

    if current_state == STATE_INTRO:
        if alpha_title < 255:
            alpha_title += 2

        if elapsed_seconds >= 8 and slide_start_time is None:
            slide_start_time = current_time

        if slide_start_time:
            t = (current_time - slide_start_time) / slide_duration
            t = max(0, min(t, 1))
            smooth_t = ease_cos(t)
            current_title_y = title_y_start + (title_y_target - title_y_start) * smooth_t

        pixel_text = pygame.transform.scale(
            small_surface,
            (small_surface.get_width() * PIXEL_SCALE,
             small_surface.get_height() * PIXEL_SCALE)
        )
        pixel_text.set_alpha(alpha_title)
        screen.blit(pixel_text, pixel_text.get_rect(center=(WIDTH // 2, current_title_y)))

        if elapsed_seconds >= 8:
            action = font_action.render("Appuyez sur une touche pour continuer", True, BLANC)
            screen.blit(action, action.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100)))

    elif current_state == STATE_CHOICE:
        # NOUVEL ÉCRAN DE SÉLECTION
        title = font_question.render("MODE DE JEU", True, ROUGE)
        opt1 = font_action.render("[1] MODE SOLO (HISTOIRE)", True, BLANC)
        opt2 = font_action.render("[2] MODE MULTIJOUEUR (ONLINE)", True, BLANC)
        
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50)))
        screen.blit(opt1, opt1.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
        screen.blit(opt2, opt2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
