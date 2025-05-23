import pygame
import sys
import numpy as np
import math
import random
import time
import asyncio
from typing import Optional, Tuple, List, Dict, Any

# Initialize pygame
pygame.init()

# Constants - EXPANDED FOR BETTER SPACING
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 900  # Much larger screen for better spacing
BOARD_SIZE = 600  # Slightly larger board for better visibility
GRID_SIZE = 8
CELL_SIZE = BOARD_SIZE // GRID_SIZE
FPS = 60
BOARD_MARGIN_TOP = 180  # Much more space at top
BOARD_MARGIN_LEFT = (SCREEN_WIDTH - BOARD_SIZE) // 2  # Center horizontally

# Modern Vibrant Colors with better contrast
BG_COLOR = (12, 12, 20)  # Darker background
ACCENT_COLOR = (255, 75, 145)  # Hot pink
SECONDARY_ACCENT = (0, 195, 255)  # Bright cyan
TERTIARY_ACCENT = (130, 255, 100)  # Neon green
PLAYER1_COLOR = (255, 70, 120)  # Vibrant pink
PLAYER2_COLOR = (30, 200, 255)  # Electric blue
GRID_COLOR = (50, 50, 70)  # Subtle grid
GRID_HIGHLIGHT = (80, 80, 120)  # More visible highlighted grid cells
UI_TEXT = (240, 240, 255)  # Bright text
UI_BG = (30, 30, 45, 200)  # More opaque UI background for better readability

# Try to load modern fonts
try:
    FONT_FAMILY = "Arial"
    FONT_LARGE = pygame.font.SysFont(FONT_FAMILY, 56, bold=True)
    FONT_MEDIUM = pygame.font.SysFont(FONT_FAMILY, 36, bold=True)
    FONT_SMALL = pygame.font.SysFont(FONT_FAMILY, 28)
    FONT_EMOJI = pygame.font.SysFont("Arial", 42)
except:
    FONT_LARGE = pygame.font.Font(None, 56)
    FONT_MEDIUM = pygame.font.Font(None, 36)
    FONT_SMALL = pygame.font.Font(None, 28)
    FONT_EMOJI = pygame.font.Font(None, 42)

# Initialize screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("✨ LLM Battle Arena ✨")
clock = pygame.time.Clock()

# Game state
board = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)
current_player = 1
animations = []
particles = []
hover_cell = None
game_over = False
winner = None
flash_alpha = 0
messages = []

# LLM Battle specific variables
llm_names = {1: "LLM 1", 2: "LLM 2"}  # Will be set by the battle runner
llm_thinking = False
thinking_start_time = 0
thinking_dots = 0
move_delay = 1.0  # Seconds between moves for better visualization
last_move_time = 0
battle_stats = {"wins": {1: 0, 2: 0}, "ties": 0, "games": 0}
current_game = 1
total_games = 1
auto_restart = False
auto_restart_delay = 3.0  # Seconds before auto-restarting
game_end_time = 0

# Try to load sounds
try:
    place_sound = pygame.mixer.Sound("place.wav")
    capture_sound = pygame.mixer.Sound("capture.wav")
    game_over_sound = pygame.mixer.Sound("gameover.wav")
    pygame.mixer.music.set_volume(0.5)
except:
    place_sound = capture_sound = game_over_sound = None


class Message:
    def __init__(self, text, color=UI_TEXT, duration=120, size="medium"):
        if size == "large":
            self.font = FONT_LARGE
        elif size == "small":
            self.font = FONT_SMALL
        else:
            self.font = FONT_MEDIUM

        self.text = text
        self.color = color
        self.duration = duration
        self.age = 0
        self.y = SCREEN_HEIGHT + 50
        self.target_y = SCREEN_HEIGHT - 150  # Lower position for better visibility

    def update(self):
        self.age += 1
        # Animate in
        if self.age < 20:
            self.y = self.y - (self.y - self.target_y) * 0.2
        # Hold
        elif self.age < self.duration - 20:
            self.y = self.target_y
        # Animate out
        else:
            self.y += 5

        return self.age >= self.duration

    def draw(self):
        # Create text surface
        text_surf = self.font.render(self.text, True, self.color)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, self.y))

        # Create background
        padding = 30  # More padding for better spacing
        bg_rect = pygame.Rect(
            text_rect.left - padding,
            text_rect.top - padding//2,
            text_rect.width + padding*2,
            text_rect.height + padding
        )

        # Draw rounded background with more pronounced shadow
        shadow_rect = bg_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=20)
        pygame.draw.rect(screen, UI_BG, bg_rect, border_radius=20)

        # Draw accent border with thicker line
        pygame.draw.rect(
            screen,
            PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR,
            bg_rect,
            width=3,
            border_radius=20
        )

        # Draw text
        screen.blit(text_surf, text_rect)


class Particle:
    def __init__(self, x, y, color, style="circle"):
        self.x = x
        self.y = y
        self.color = color
        self.style = style
        self.size = random.randint(4, 10)  # Larger particles
        self.speed_x = random.uniform(-3.5, 3.5)  # Faster movement
        self.speed_y = random.uniform(-3.5, 3.5)
        self.life = random.randint(40, 80)  # Longer life
        self.max_life = self.life
        self.rotation = random.randint(0, 360)
        self.rot_speed = random.uniform(-6, 6)  # Faster rotation

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.life -= 1
        self.rotation += self.rot_speed
        self.speed_x *= 0.95
        self.speed_y *= 0.95
        return self.life <= 0

    def draw(self):
        # Fade out based on remaining life
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color[:3], alpha) if len(self.color) == 4 else (*self.color, alpha)

        if self.style == "circle":
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (self.size, self.size), self.size)
            screen.blit(surf, (self.x - self.size, self.y - self.size))
        elif self.style == "square":
            surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            surf.fill(color)
            rotated = pygame.transform.rotate(surf, self.rotation)
            screen.blit(rotated, (self.x - rotated.get_width()//2, self.y - rotated.get_height()//2))
        elif self.style == "triangle":
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            points = [
                (self.size, 0),
                (0, self.size * 2),
                (self.size * 2, self.size * 2)
            ]
            pygame.draw.polygon(surf, color, points)
            rotated = pygame.transform.rotate(surf, self.rotation)
            screen.blit(rotated, (self.x - rotated.get_width()//2, self.y - rotated.get_height()//2))


class Animation:
    def __init__(self, row, col, player, animation_type="place"):
        self.row = row
        self.col = col
        self.player = player
        self.progress = 0
        self.type = animation_type
        self.max_progress = 20
        self.color = PLAYER1_COLOR if player == 1 else PLAYER2_COLOR

    def update(self):
        self.progress += 1
        return self.progress >= self.max_progress

    def draw(self):
        x = BOARD_MARGIN_LEFT + self.col * CELL_SIZE + CELL_SIZE // 2
        y = BOARD_MARGIN_TOP + self.row * CELL_SIZE + CELL_SIZE // 2
        progress_ratio = self.progress / self.max_progress

        if self.type == "place":
            # Growing circle animation with enhanced glow
            radius = int(CELL_SIZE // 2.5 * min(1, progress_ratio * 1.2))

            # Glow effect with more layers
            for i in range(4):  # More glow layers
                glow_size = radius + 6 + i*3  # Larger glow
                glow_alpha = 120 - i*25  # More visible glow
                glow_color = (*self.color[:3], glow_alpha)
                glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
                screen.blit(glow_surf, (x-glow_size, y-glow_size))

            # Main piece
            pygame.draw.circle(screen, self.color, (x, y), radius)

            # Highlight effect
            if radius > 5:
                highlight_pos = (x - radius//3, y - radius//3)
                highlight_size = radius // 2
                pygame.draw.circle(screen, (255, 255, 255, 180), highlight_pos, highlight_size)

        elif self.type == "capture":
            # Shrinking circle with enhanced glow
            reverse_progress = 1.0 - progress_ratio
            radius = int(CELL_SIZE // 2.5 * reverse_progress)

            # Glow effect that expands
            glow_size = int(CELL_SIZE // 2.5 + progress_ratio * 15)  # Larger expansion
            glow_alpha = int(120 * (1 - progress_ratio))  # More visible
            glow_color = (*self.color[:3], glow_alpha)
            glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
            screen.blit(glow_surf, (x-glow_size, y-glow_size))

            # Main piece
            pygame.draw.circle(screen, self.color, (x, y), radius)


def create_particles(x, y, color, count=30, styles=None):  # More particles
    if styles is None:
        styles = ["circle", "square", "triangle"]

    for _ in range(count):
        style = random.choice(styles)
        particles.append(Particle(x, y, color, style))


def draw_board_background():
    """Draw the modern game board background."""
    # Main board with enhanced gradient
    surf = pygame.Surface((BOARD_SIZE + 30, BOARD_SIZE + 30), pygame.SRCALPHA)  # Larger surface

    # Create gradient background with more contrast
    for i in range(BOARD_SIZE + 30):
        # Calculate gradient color with more vibrance
        ratio = i / (BOARD_SIZE + 30)
        r = int(35 + ratio * 25)
        g = int(35 + ratio * 25)
        b = int(55 + ratio * 20)
        color = (r, g, b, 255)

        # Draw horizontal line with calculated color
        pygame.draw.line(surf, color, (0, i), (BOARD_SIZE + 30, i))

    # Add rounded corners and border
    pygame.draw.rect(
        surf,
        (0, 0, 0, 0),
        (0, 0, BOARD_SIZE + 30, BOARD_SIZE + 30),
        border_radius=25  # More rounded corners
    )

    # Draw border with player color and thicker line
    border_color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
    pygame.draw.rect(
        surf,
        border_color,
        (0, 0, BOARD_SIZE + 30, BOARD_SIZE + 30),
        width=4,  # Thicker border
        border_radius=25
    )

    # Add enhanced glow along the border
    glow_surf = pygame.Surface((BOARD_SIZE + 60, BOARD_SIZE + 60), pygame.SRCALPHA)  # Larger glow
    for i in range(15):  # More glow layers
        glow_alpha = 18 - i * 1.2  # More visible glow
        glow_color = (*border_color[:3], glow_alpha)
        pygame.draw.rect(
            glow_surf,
            glow_color,
            (i, i, BOARD_SIZE + 60 - i*2, BOARD_SIZE + 60 - i*2),
            width=1,
            border_radius=25 + i
        )

    # Add shadow for depth
    shadow_surf = pygame.Surface((BOARD_SIZE + 30, BOARD_SIZE + 30), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(5, 5, BOARD_SIZE + 30, BOARD_SIZE + 30)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 60), shadow_rect, border_radius=25)

    # Blit the surfaces to the screen
    screen.blit(shadow_surf, (BOARD_MARGIN_LEFT - 15, BOARD_MARGIN_TOP - 15))
    screen.blit(glow_surf, (BOARD_MARGIN_LEFT - 30, BOARD_MARGIN_TOP - 30))
    screen.blit(surf, (BOARD_MARGIN_LEFT - 15, BOARD_MARGIN_TOP - 15))


def draw_grid():
    """Draw the grid lines on the board with a modern look."""
    for i in range(GRID_SIZE + 1):
        # Choose color - highlight every other line with more contrast
        color = GRID_HIGHLIGHT if i % 2 == 0 else GRID_COLOR

        # Vertical lines
        pygame.draw.line(
            screen,
            color,
            (BOARD_MARGIN_LEFT + i * CELL_SIZE, BOARD_MARGIN_TOP),
            (BOARD_MARGIN_LEFT + i * CELL_SIZE, BOARD_MARGIN_TOP + BOARD_SIZE),
            2 if i == 0 or i == GRID_SIZE else 1
        )

        # Horizontal lines
        pygame.draw.line(
            screen,
            color,
            (BOARD_MARGIN_LEFT, BOARD_MARGIN_TOP + i * CELL_SIZE),
            (BOARD_MARGIN_LEFT + BOARD_SIZE, BOARD_MARGIN_TOP + i * CELL_SIZE),
            2 if i == 0 or i == GRID_SIZE else 1
        )


def draw_pieces():
    """Draw the pieces on the board with enhanced modern styling."""
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            if board[row, col] != 0:
                x = BOARD_MARGIN_LEFT + col * CELL_SIZE + CELL_SIZE // 2
                y = BOARD_MARGIN_TOP + row * CELL_SIZE + CELL_SIZE // 2
                color = PLAYER1_COLOR if board[row, col] == 1 else PLAYER2_COLOR

                # Enhanced glow effect
                for i in range(4):  # More glow layers
                    glow_size = CELL_SIZE // 2.5 + 3 + i*2.5  # Larger glow
                    glow_alpha = 90 - i*20  # More visible
                    glow_color = (*color[:3], glow_alpha)
                    glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
                    screen.blit(glow_surf, (x-glow_size, y-glow_size))

                # Main piece with slightly larger size
                pygame.draw.circle(screen, color, (x, y), CELL_SIZE // 2.3)  # Slightly larger

                # Enhanced highlight/shine effect
                highlight_pos = (x - CELL_SIZE//7, y - CELL_SIZE//7)
                highlight_size = CELL_SIZE // 4.5  # Larger highlight
                pygame.draw.circle(screen, (255, 255, 255, 180), highlight_pos, highlight_size)


def draw_thinking_indicator():
    """Draw an enhanced indicator when an LLM is thinking."""
    if llm_thinking:
        # Calculate elapsed time and update dots animation
        elapsed = time.time() - thinking_start_time
        global thinking_dots
        if int(elapsed * 2) % 2 == 0 and thinking_dots < 3:
            thinking_dots = (thinking_dots + 1) % 4
        
        # Create thinking text with animated dots
        dots = "." * thinking_dots
        thinking_text = f"{llm_names[current_player]} thinking{dots}"
        
        # Render text with enhanced pulsing effect
        pulse = (math.sin(elapsed * 4) + 1) / 2  # 0 to 1 pulsing
        alpha = int(180 + pulse * 75)  # 180-255 alpha
        color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
        text_color = (*color[:3], alpha)
        
        text_surf = FONT_MEDIUM.render(thinking_text, True, text_color)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, BOARD_MARGIN_TOP - 60))  # More space
        
        # Draw with enhanced glow effect
        glow_surf = pygame.Surface((text_rect.width + 40, text_rect.height + 30), pygame.SRCALPHA)  # Larger glow
        glow_color = (*color[:3], 50 + int(pulse * 40))  # More visible
        pygame.draw.rect(glow_surf, glow_color, (0, 0, text_rect.width + 40, text_rect.height + 30), 
                         border_radius=20)  # More rounded
        screen.blit(glow_surf, (text_rect.x - 20, text_rect.y - 15))
        screen.blit(text_surf, text_rect)


def draw_ui():
    """Draw the modern UI elements with improved spacing."""
    # IMPROVED SPACING FOR TOP UI
    player1_count, player2_count = count_pieces()

    # Top UI container with much more space
    top_ui_margin = 40  # More space from top of screen
    pill_width = 250  # Wider for LLM names
    pill_height = 70  # Taller for better visibility
    spacing = 50  # More space between elements

    # Calculate positions to center all elements
    total_width = (pill_width * 3) + (spacing * 2)
    left_start = (SCREEN_WIDTH - total_width) // 2

    # Player 1 pill with shadow for depth
    shadow_rect = pygame.Rect(left_start + 4, top_ui_margin + 4, pill_width, pill_height)
    pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=35)
    
    p1_rect = pygame.Rect(left_start, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, p1_rect, border_radius=35)
    pygame.draw.rect(
        screen,
        PLAYER1_COLOR,
        p1_rect,
        width=4 if current_player == 1 else 2,  # Thicker border for current player
        border_radius=35
    )

    # Player 1 avatar/circle with larger size
    pygame.draw.circle(screen, PLAYER1_COLOR, (left_start + 45, top_ui_margin + pill_height//2), 25)

    # Player 1 text with better positioning
    p1_text = FONT_MEDIUM.render(f"{llm_names[1]}: {player1_count}", True, UI_TEXT)
    screen.blit(p1_text, (left_start + 80, top_ui_margin + pill_height//2 - p1_text.get_height()//2))

    # Turn indicator - center with shadow
    turn_x = left_start + pill_width + spacing
    shadow_rect = pygame.Rect(turn_x + 4, top_ui_margin + 4, pill_width, pill_height)
    pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=35)
    
    turn_rect = pygame.Rect(turn_x, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, turn_rect, border_radius=35)
    turn_color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
    pygame.draw.rect(screen, turn_color, turn_rect, width=4, border_radius=35)  # Thicker border

    # Turn text with better centering
    turn_text = FONT_MEDIUM.render(f"GAME {current_game}/{total_games}", True, UI_TEXT)
    turn_text_rect = turn_text.get_rect(center=(turn_x + pill_width//2, top_ui_margin + pill_height//2))
    screen.blit(turn_text, turn_text_rect)

    # Player 2 pill with shadow
    p2_x = turn_x + pill_width + spacing
    shadow_rect = pygame.Rect(p2_x + 4, top_ui_margin + 4, pill_width, pill_height)
    pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=35)
    
    p2_rect = pygame.Rect(p2_x, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, p2_rect, border_radius=35)
    pygame.draw.rect(
        screen,
        PLAYER2_COLOR,
        p2_rect,
        width=4 if current_player == 2 else 2,  # Thicker border for current player
        border_radius=35
    )

    # Player 2 avatar/circle with larger size
    pygame.draw.circle(screen, PLAYER2_COLOR, (p2_x + 45, top_ui_margin + pill_height//2), 25)

    # Player 2 text with better positioning
    p2_text = FONT_MEDIUM.render(f"{llm_names[2]}: {player2_count}", True, UI_TEXT)
    screen.blit(p2_text, (p2_x + 80, top_ui_margin + pill_height//2 - p2_text.get_height()//2))

    # Bottom status bar with much more spacing
    bottom_y = BOARD_MARGIN_TOP + BOARD_SIZE + 40  # More space below board
    
    # Add shadow for depth
    shadow_rect = pygame.Rect(
        BOARD_MARGIN_LEFT + 4,
        bottom_y + 4,
        BOARD_SIZE,
        60  # Taller for better visibility
    )
    pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=30)
    
    bottom_rect = pygame.Rect(
        BOARD_MARGIN_LEFT,
        bottom_y,
        BOARD_SIZE,
        60
    )
    pygame.draw.rect(screen, UI_BG, bottom_rect, border_radius=30)

    # Game status message with larger font
    if not game_over:
        status_text = FONT_MEDIUM.render(
            f"{llm_names[current_player]}'s Turn",
            True,
            turn_color
        )
    else:
        if winner:
            win_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR
            status_text = FONT_MEDIUM.render(
                f"{llm_names[winner]} WINS! 🎉",
                True,
                win_color
            )
        else:
            status_text = FONT_MEDIUM.render("TIE GAME! 🤝", True, UI_TEXT)

    status_rect = status_text.get_rect(center=(SCREEN_WIDTH//2, bottom_y + 30))
    screen.blit(status_text, status_rect)

    # Draw battle stats with more space and shadow
    stats_y = bottom_y + 80  # More space between elements
    
    # Add shadow
    shadow_rect = pygame.Rect(
        BOARD_MARGIN_LEFT + 4,
        stats_y + 4,
        BOARD_SIZE,
        60  # Taller
    )
    pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=30)
    
    stats_rect = pygame.Rect(
        BOARD_MARGIN_LEFT,
        stats_y,
        BOARD_SIZE,
        60
    )
    pygame.draw.rect(screen, UI_BG, stats_rect, border_radius=30)
    
    # More detailed stats with better formatting
    stats_text = FONT_SMALL.render(
        f"Battle Stats: {llm_names[1]} {battle_stats['wins'][1]} - {battle_stats['wins'][2]} {llm_names[2]} (Ties: {battle_stats['ties']})",
        True,
        UI_TEXT
    )
    stats_rect = stats_text.get_rect(center=(SCREEN_WIDTH//2, stats_y + 30))
    screen.blit(stats_text, stats_rect)
# Game over overlay with improved design
    if game_over:
        # Semi-transparent overlay with gradient
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(SCREEN_HEIGHT):
            alpha = min(180, int(180 * (y / SCREEN_HEIGHT * 1.5)))
            pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))
        screen.blit(overlay, (0, 0))

        # Main game over container with larger size
        go_width, go_height = 550, 400  # Much larger container
        go_rect = pygame.Rect(
            (SCREEN_WIDTH - go_width)//2,
            (SCREEN_HEIGHT - go_height)//2,
            go_width,
            go_height
        )

        # Add shadow for depth
        shadow_rect = go_rect.copy()
        shadow_rect.x += 8
        shadow_rect.y += 8
        pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=35)

        pygame.draw.rect(screen, UI_BG, go_rect, border_radius=35)

        # Border with winner color or neutral and thicker line
        border_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR if winner == 2 else UI_TEXT
        pygame.draw.rect(screen, border_color, go_rect, width=5, border_radius=35)  # Thicker border

        # Game over text with much more spacing
        if winner:
            win_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR
            win_emoji = "🏆"
            go_text1 = FONT_LARGE.render(f"{win_emoji} GAME OVER {win_emoji}", True, UI_TEXT)
            go_text2 = FONT_LARGE.render(
                f"{llm_names[winner]} WINS!",
                True,
                win_color
            )
        else:
            go_text1 = FONT_LARGE.render("🤝 GAME OVER 🤝", True, UI_TEXT)
            go_text2 = FONT_LARGE.render("IT'S A TIE!", True, UI_TEXT)

        # Position text with much better spacing
        go_text1_rect = go_text1.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        go_text2_rect = go_text2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
        screen.blit(go_text1, go_text1_rect)
        screen.blit(go_text2, go_text2_rect)

        # Final scores with larger font
        score_text = FONT_MEDIUM.render(f"{llm_names[1]}: {player1_count} • {llm_names[2]}: {player2_count}", True, UI_TEXT)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        screen.blit(score_text, score_rect)

        # Auto-restart countdown or button with better styling
        if auto_restart:
            time_left = max(0, auto_restart_delay - (time.time() - game_end_time))
            restart_text = FONT_MEDIUM.render(f"Next game in {time_left:.1f}s", True, TERTIARY_ACCENT)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 140))
            screen.blit(restart_text, restart_rect)
        else:
            # Restart button with enhanced styling
            restart_rect = pygame.Rect(
                (SCREEN_WIDTH - 280)//2,  # Wider button
                (SCREEN_HEIGHT)//2 + 130,
                280,
                70  # Taller button
            )

            # Add button shadow for depth
            shadow_rect = restart_rect.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=35)

            # Button background with gradient
            button_surf = pygame.Surface((280, 70), pygame.SRCALPHA)
            for i in range(70):
                # Calculate gradient color
                ratio = i / 70
                r = int(40 + ratio * 10)
                g = int(40 + ratio * 10)
                b = int(60 + ratio * 10)
                color = (r, g, b, 255)
                pygame.draw.line(button_surf, color, (0, i), (280, i))

            # Apply rounded corners to button
            pygame.draw.rect(button_surf, (0, 0, 0, 0), (0, 0, 280, 70), border_radius=35)
            screen.blit(button_surf, restart_rect)

            # Button border with glow
            pygame.draw.rect(screen, TERTIARY_ACCENT, restart_rect, width=3, border_radius=35)

            # Button text with icon
            restart_text = FONT_MEDIUM.render("⚡ Next Battle", True, UI_TEXT)
            restart_rect2 = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 165))
            screen.blit(restart_text, restart_rect2)

            # Add subtle pulsing effect to button
            pulse = (math.sin(time.time() * 3) + 1) / 2  # 0 to 1 pulsing
            glow_size = int(5 + pulse * 5)
            glow_surf = pygame.Surface((restart_rect.width + glow_size*2, restart_rect.height + glow_size*2), pygame.SRCALPHA)
            glow_alpha = int(40 + pulse * 40)
            glow_color = (*TERTIARY_ACCENT[:3], glow_alpha)
            pygame.draw.rect(
                glow_surf,
                glow_color,
                (0, 0, restart_rect.width + glow_size*2, restart_rect.height + glow_size*2),
                border_radius=35 + glow_size
            )
            screen.blit(glow_surf, (restart_rect.x - glow_size, restart_rect.y - glow_size))


def get_valid_moves():
    """Get all valid moves on the current board."""
    valid_moves = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            if is_valid_move(row, col):
                valid_moves.append((row, col))
    return valid_moves


def is_valid_move(row, col):
    """Check if a move is valid (cell is empty and within bounds)."""
    return 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE and board[row, col] == 0


def make_move(row, col, player):
    """Place a piece on the board and capture adjacent pieces."""
    global flash_alpha
    board[row, col] = player
    animations.append(Animation(row, col, player, "place"))

    # Create particles
    piece_x = BOARD_MARGIN_LEFT + col * CELL_SIZE + CELL_SIZE // 2
    piece_y = BOARD_MARGIN_TOP + row * CELL_SIZE + CELL_SIZE // 2
    color = PLAYER1_COLOR if player == 1 else PLAYER2_COLOR
    create_particles(piece_x, piece_y, color, count=35)  # More particles

    # Flash effect
    flash_alpha = 80  # Slightly stronger flash

    # Play sound
    if place_sound:
        place_sound.play()

    # Add message
    messages.append(Message(f"🎮 {llm_names[player]} placed at ({row}, {col})",
                           PLAYER1_COLOR if player == 1 else PLAYER2_COLOR))

    # Capture adjacent pieces
    captures = 0
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
    for dr, dc in directions:
        r, c = row + dr, col + dc
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and board[r, c] != 0 and board[r, c] != player:
            board[r, c] = player  # Capture
            animations.append(Animation(r, c, player, "capture"))
            captures += 1

            # Create capture particles
            cap_x = BOARD_MARGIN_LEFT + c * CELL_SIZE + CELL_SIZE // 2
            cap_y = BOARD_MARGIN_TOP + r * CELL_SIZE + CELL_SIZE // 2
            create_particles(cap_x, cap_y, color, count=20)  # More particles

    # Play capture sound if captures happened
    if captures > 0 and capture_sound:
        capture_sound.play()
        messages.append(Message(f"⚔️ {llm_names[player]} captured {captures} pieces!",
                               PLAYER1_COLOR if player == 1 else PLAYER2_COLOR))


def is_board_full():
    """Check if the board is full."""
    return np.all(board != 0)


def count_pieces():
    """Count the number of pieces for each player."""
    player1_count = np.sum(board == 1)
    player2_count = np.sum(board == 2)
    return player1_count, player2_count


def reset_game():
    """Reset the game to its initial state."""
    global board, current_player, animations, particles, game_over, winner, flash_alpha, messages
    board = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)
    current_player = 1
    animations = []
    particles = []
    messages = []
    game_over = False
    winner = None
    flash_alpha = 0
    messages.append(Message(f"🎮 Battle {current_game}/{total_games} Started!", TERTIARY_ACCENT, size="large"))
    messages.append(Message(f"{llm_names[1]} vs {llm_names[2]}", UI_TEXT))


def draw_background_gradient():
    """Draw a cooler gradient background with stars."""
    # Create background gradient
    bg_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Enhanced gradient from darker at top to slightly lighter at bottom
    for y in range(SCREEN_HEIGHT):
        ratio = y / SCREEN_HEIGHT
        r = int(12 + ratio * 10)
        g = int(12 + ratio * 10)
        b = int(20 + ratio * 15)
        pygame.draw.line(bg_surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    # Add more stars with different sizes/brightness for depth
    for _ in range(150):  # More stars
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT)
        size = random.randint(1, 4)  # Larger stars
        brightness = random.randint(130, 255)
        color = (brightness, brightness, brightness)
        pygame.draw.circle(bg_surf, color, (x, y), size)

        # Add glow to some stars
        if random.random() < 0.3:  # 30% of stars get glow
            glow_size = size * 2
            glow_alpha = 50
            glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
            glow_color = (brightness, brightness, brightness, glow_alpha)
            pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
            bg_surf.blit(glow_surf, (x-glow_size, y-glow_size))

    # Add subtle nebula-like effects in the background
    for _ in range(5):
        nebula_x = random.randint(0, SCREEN_WIDTH)
        nebula_y = random.randint(0, SCREEN_HEIGHT)
        nebula_size = random.randint(100, 300)
        nebula_color = random.choice([
            (30, 0, 50, 10),  # Purple
            (0, 20, 40, 10),  # Blue
            (40, 0, 40, 10),  # Magenta
        ])

        nebula_surf = pygame.Surface((nebula_size*2, nebula_size*2), pygame.SRCALPHA)
        pygame.draw.circle(nebula_surf, nebula_color, (nebula_size, nebula_size), nebula_size)
        bg_surf.blit(nebula_surf, (nebula_x-nebula_size, nebula_y-nebula_size))

    # Blit the background
    screen.blit(bg_surf, (0, 0))


def check_game_over():
    """Check if the game is over and determine the winner."""
    global game_over, winner, game_end_time, battle_stats

    if is_board_full():
        game_over = True
        game_end_time = time.time()
        player1_count, player2_count = count_pieces()

        # Determine winner
        if player1_count > player2_count:
            winner = 1
            battle_stats["wins"][1] += 1
            messages.append(Message(f"🏆 {llm_names[1]} WINS!", PLAYER1_COLOR, size="large"))
        elif player2_count > player1_count:
            winner = 2
            battle_stats["wins"][2] += 1
            messages.append(Message(f"🏆 {llm_names[2]} WINS!", PLAYER2_COLOR, size="large"))
        else:
            winner = None
            battle_stats["ties"] += 1
            messages.append(Message("🤝 IT'S A TIE!", UI_TEXT, size="large"))

        battle_stats["games"] += 1

        # Create victory particles - more particles and across the screen
        for _ in range(20):  # More particles
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT // 2)
            color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR if winner == 2 else TERTIARY_ACCENT
            create_particles(x, y, color, count=30)

        # Play game over sound
        if game_over_sound:
            game_over_sound.play()

        return True
    return False


def get_board_state():
    """Get the current board state as a dictionary for LLM agents."""
    return {
        "board": board.tolist(),
        "current_player": current_player,
        "valid_moves": get_valid_moves(),
        "player1_count": np.sum(board == 1),
        "player2_count": np.sum(board == 2),
    }


def set_llm_names(p1_name, p2_name):
    """Set the names of the LLM agents."""
    global llm_names
    llm_names = {1: p1_name, 2: p2_name}


def set_tournament_config(current, total, auto=False, delay=3.0):
    """Configure tournament settings."""
    global current_game, total_games, auto_restart, auto_restart_delay
    current_game = current
    total_games = total
    auto_restart = auto
    auto_restart_delay = delay


def start_thinking():
    """Indicate that an LLM is thinking."""
    global llm_thinking, thinking_start_time, thinking_dots
    llm_thinking = True
    thinking_start_time = time.time()
    thinking_dots = 0


def stop_thinking():
    """Stop the thinking indicator."""
    global llm_thinking
    llm_thinking = False


async def run_game_loop(get_llm_move_func):
    """Run the game loop with LLM agents making moves.

    Args:
        get_llm_move_func: Async function that takes (player, board_state) and returns (row, col)
    """
    global current_player, game_over, winner, flash_alpha, last_move_time, current_game

    running = True
    reset_game()

    while running:
        # Apply background
        draw_background_gradient()

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False  # Signal to stop the tournament

            # Handle mouse clicks for restart button
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_over and not auto_restart:
                # Check if restart button was clicked
                restart_rect = pygame.Rect(
                    (SCREEN_WIDTH - 280)//2,
                    (SCREEN_HEIGHT)//2 + 130,
                    280,
                    70
                )
                if restart_rect.collidepoint(event.pos):
                    current_game += 1
                    reset_game()

        # Auto-restart logic
        if game_over and auto_restart and time.time() - game_end_time >= auto_restart_delay:
            current_game += 1
            reset_game()

        # Get LLM move if it's time
        current_time = time.time()
        if not game_over and not llm_thinking and current_time - last_move_time >= move_delay:
            # Start thinking animation
            start_thinking()

            # Get board state for LLM
            board_state = get_board_state()

            # Get move from LLM (non-blocking)
            try:
                row, col = await get_llm_move_func(current_player, board_state)

                # Validate move
                if is_valid_move(row, col):
                    # Stop thinking animation
                    stop_thinking()

                    # Make the move
                    make_move(row, col, current_player)
                    last_move_time = time.time()

                    # Switch player
                    current_player = 3 - current_player

                    # Check for game over
                    check_game_over()
                else:
                    # Invalid move, try again with random valid move
                    valid_moves = get_valid_moves()
                    if valid_moves:
                        row, col = random.choice(valid_moves)
                        messages.append(Message(f"⚠️ {llm_names[current_player]} made invalid move, using random",
                                              (255, 180, 0)))
                        stop_thinking()
                        make_move(row, col, current_player)
                        last_move_time = time.time()
                        current_player = 3 - current_player
                        check_game_over()
            except Exception as e:
                # Handle errors in LLM response
                messages.append(Message(f"⚠️ Error: {str(e)[:30]}...", (255, 100, 100)))
                stop_thinking()

                # Make random move
                valid_moves = get_valid_moves()
                if valid_moves:
                    row, col = random.choice(valid_moves)
                    make_move(row, col, current_player)
                    last_move_time = time.time()
                    current_player = 3 - current_player
                    check_game_over()

        # Draw game elements
        draw_board_background()
        draw_grid()
        draw_pieces()
        draw_thinking_indicator()

        # Update and draw animations
        for anim in animations[:]:
            if anim.update():
                animations.remove(anim)
            else:
                anim.draw()

        # Update and draw particles
        for particle in particles[:]:
            if particle.update():
                particles.remove(particle)
            else:
                particle.draw()

        # Flash effect
        if flash_alpha > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            color = PLAYER1_COLOR if current_player == 2 else PLAYER2_COLOR  # Previous player's color
            flash_surf.fill((*color[:3], flash_alpha))
            screen.blit(flash_surf, (0, 0))
            flash_alpha = max(0, flash_alpha - 5)

        # Draw UI
        draw_ui()

        # Update and draw messages
        for msg in messages[:]:
            if msg.update():
                messages.remove(msg)
            else:
                msg.draw()

        pygame.display.flip()
        clock.tick(FPS)

        # Process a few pygame events to keep UI responsive
        await asyncio.sleep(0.01)

    pygame.quit()
    return False  # Signal to stop the tournament


def init_game():
    """Initialize the game for the first time."""
    global last_move_time
    last_move_time = time.time()
    reset_game()


if __name__ == "__main__":
    # This is just for testing the UI directly
    set_llm_names("Groq Claude", "Google Gemini")
    set_tournament_config(1, 5, auto=True)
    init_game()

    # Mock LLM move function for testing
    async def mock_llm_move(player, board_state):
        # Simulate thinking time
        await asyncio.sleep(2)
        valid_moves = board_state["valid_moves"]
        if valid_moves:
            return random.choice(valid_moves)
        return (0, 0)  # Should never happen if we check for game over

    # Run the game loop
    asyncio.run(run_game_loop(mock_llm_move))
