import pygame
from settings import *

class UI():
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)
        self.life_bar = pygame.Rect(10, 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)

        self.xp_bar = pygame.Rect((WIDTH//2)-(HEALTH_BAR_WIDTH//2), 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)

        self.clock_font = pygame.font.Font(UI_FONT, 30)

    def show_bar(self, current, max_amount, bg_rect, color):

        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)

        ratio = current / max_amount
        current_width = bg_rect.width * ratio
        
        current_rect = bg_rect.copy()
        current_rect.width = current_width

        pygame.draw.rect(self.display_surface, color, current_rect)

        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

    def show_clock(self, game_time, day_duration, start_hour=20):
        ratio = game_time / day_duration
        if ratio > 1: ratio = 1

        total_hours = 24
        current_hour_float = start_hour + (total_hours * ratio)
        current_hour = int(current_hour_float % 24)
        current_minute = int((current_hour_float * 60) % 60)

        time_text = f"{current_hour:02d}:{current_minute:02d}"

        text_surf = self.clock_font.render(time_text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(topright=(WIDTH - 20, 10))

        bg_rect = text_rect.inflate(20, 10)
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)
        self.display_surface.blit(text_surf, text_rect)

    def show_inventory(self, inventory):

        slot_size = 50
        padding = 10
        start_x = 20
        start_y = self.display_surface.get_height() - slot_size - 20
        step = 0
        count_font = pygame.font.Font(UI_FONT, 26)

        for item_name, item_amount in inventory.items():

            if item_name == 'xp':
                continue

            x = start_x + (slot_size + padding) * step
            y = start_y

            slot_rect = pygame.Rect(x, y, slot_size, slot_size)

            pygame.draw.rect(self.display_surface, UI_BG_COLOR, slot_rect)

            icon_rect = pygame.Rect(0, 0, slot_size - 10, slot_size - 10)
            icon_rect.center = slot_rect.center

            if item_name == 'gold':
                pygame.draw.rect(self.display_surface, (255, 215, 0), icon_rect)
            elif item_name == 'iron':
                pygame.draw.rect(self.display_surface, (172, 169, 164), icon_rect)
            elif item_name == 'health':
                pygame.draw.rect(self.display_surface, (178, 53, 45), icon_rect)

            amount_surf = count_font.render(str(item_amount), True, (0, 0, 0))
            amount_rect = amount_surf.get_rect(bottomright=slot_rect.bottomright)

            amount_rect.bottom -= 2
            amount_rect.right -= 2

            self.display_surface.blit(amount_surf, amount_rect)
            pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, slot_rect, 3)
            step += 1

    def display(self, player, game_time, day_duration, start_hour=20, show_inventory=True):
        self.show_bar(player.health, player.max_health, self.life_bar, HEALTH_COLOR)
        self.show_bar(player.inventory['xp'], player.xp_to_next_level, self.xp_bar, (93, 179, 103))

        lvl_txt_surf = self.font.render(f"LVL. {player.level}", True, 'white')
        lvl_txt_rect = lvl_txt_surf.get_rect(midleft=(self.xp_bar.right + 10, self.xp_bar.centery))
        self.display_surface.blit(lvl_txt_surf, lvl_txt_rect)

        if show_inventory:
            self.show_inventory(player.inventory)
            
        self.show_clock(game_time, day_duration, start_hour)