import pygame
import sys
import math

pygame.init()
pygame.mixer.init()

# 🎵 Musique d'intro
pygame.mixer.music.load("intro_mixkit.mp3")
pygame.mixer.music.set_volume(0.6)
pygame.mixer.music.play()

# 🔊 Son crash
crash_sound = pygame.mixer.Sound("crash.mp3")
crash_sound.set_volume(0.8)

# Fenêtre
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GREED")

clock = pygame.time.Clock()
NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
ROUGE = (180, 0, 0)

# Temps
start_time = pygame.time.get_ticks()

# Polices
font_greed = pygame.font.SysFont("arial", 125, bold=True)
font_question = pygame.font.SysFont("arial", 30)
font_action = pygame.font.SysFont("arial", 22, italic=True)

# Texte GREED
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

transition = False
fade_alpha = 0
fade_speed = 3
fade_phase = "black"
#unicité
crash_played = False  

running = True
while running:
    current_time = pygame.time.get_ticks()
    elapsed_seconds = (current_time - start_time) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if (
            event.type == pygame.KEYDOWN
            and elapsed_seconds >= 8
            and not transition
        ):
            transition = True
            fade_alpha = 0
            fade_phase = "black"

            if not crash_played:
                crash_sound.play()
                crash_played = True

    screen.fill(NOIR)

 
    if not transition:
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
            question = font_question.render("Êtes-vous prêts ?", True, BLANC)
            action = font_action.render("Appuyez sur une touche pour lancer", True, BLANC)

            screen.blit(question, question.get_rect(center=(WIDTH // 2, current_title_y + 100)))
            screen.blit(action, action.get_rect(center=(WIDTH // 2, current_title_y + 140)))


    else:
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.set_alpha(fade_alpha)

        if fade_phase == "black":
            fade_surface.fill(NOIR)
            fade_alpha += fade_speed
            if fade_alpha >= 255:
                fade_alpha = 0
                fade_phase = "white"

        elif fade_phase == "white":
            fade_surface.fill(BLANC)
            fade_alpha += fade_speed
            if fade_alpha >= 255:
                running = False  

        screen.blit(fade_surface, (0, 0))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
