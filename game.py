import pygame
import sys
import numpy as np
import math
import random

# Initialize pygame
pygame.init()

# Constants - ADJUSTED FOR BETTER SPACING
SCREEN_WIDTH, SCREEN_HEIGHT = 900, 750  # Taller screen for more space
BOARD_SIZE = 550  # Slightly smaller board
GRID_SIZE = 8
CELL_SIZE = BOARD_SIZE // GRID_SIZE
FPS = 60
BOARD_MARGIN_TOP = 100  # More space at top
BOARD_MARGIN_LEFT = (SCREEN_WIDTH - BOARD_SIZE) // 2  # Center horizontally

# Modern Vibrant Colors
BG_COLOR = (15, 15, 25)  # Darker background
ACCENT_COLOR = (255, 75, 145)  # Hot pink
SECONDARY_ACCENT = (0, 195, 255)  # Bright cyan
TERTIARY_ACCENT = (130, 255, 100)  # Neon green
PLAYER1_COLOR = (255, 70, 120)  # Vibrant pink
PLAYER2_COLOR = (30, 200, 255)  # Electric blue
GRID_COLOR = (50, 50, 70)  # Subtle grid
GRID_HIGHLIGHT = (70, 70, 100)  # Highlighted grid cells
UI_TEXT = (240, 240, 255)  # Bright text
UI_BG = (30, 30, 40, 180)  # Semi-transparent UI background

# Try to load modern fonts
try:
    FONT_FAMILY = "Arial"
    FONT_LARGE = pygame.font.SysFont(FONT_FAMILY, 48, bold=True)
    FONT_MEDIUM = pygame.font.SysFont(FONT_FAMILY, 32, bold=True)
    FONT_SMALL = pygame.font.SysFont(FONT_FAMILY, 24)
    FONT_EMOJI = pygame.font.SysFont("Arial", 36)
except:
    FONT_LARGE = pygame.font.Font(None, 48)
    FONT_MEDIUM = pygame.font.Font(None, 32)
    FONT_SMALL = pygame.font.Font(None, 24)
    FONT_EMOJI = pygame.font.Font(None, 36)

# Initialize screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("✨ Gen Z Strategy Game ✨")
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
        self.target_y = SCREEN_HEIGHT - 120  # Lower position

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
        padding = 25  # More padding
        bg_rect = pygame.Rect(
            text_rect.left - padding,
            text_rect.top - padding//2,
            text_rect.width + padding*2,
            text_rect.height + padding
        )

        # Draw rounded background
        pygame.draw.rect(screen, UI_BG, bg_rect, border_radius=20)

        # Draw accent border
        pygame.draw.rect(
            screen,
            ACCENT_COLOR if current_player == 1 else SECONDARY_ACCENT,
            bg_rect,
            width=2,
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
        self.size = random.randint(3, 8)
        self.speed_x = random.uniform(-3, 3)
        self.speed_y = random.uniform(-3, 3)
        self.life = random.randint(30, 60)
        self.max_life = self.life
        self.rotation = random.randint(0, 360)
        self.rot_speed = random.uniform(-5, 5)

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
            # Growing circle animation with glow
            radius = int(CELL_SIZE // 2.5 * min(1, progress_ratio * 1.2))

            # Glow effect
            for i in range(3):
                glow_size = radius + 5 + i*2
                glow_alpha = 100 - i*30
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
                pygame.draw.circle(screen, (255, 255, 255, 150), highlight_pos, highlight_size)

        elif self.type == "capture":
            # Shrinking circle with glow
            reverse_progress = 1.0 - progress_ratio
            radius = int(CELL_SIZE // 2.5 * reverse_progress)

            # Glow effect that expands
            glow_size = int(CELL_SIZE // 2.5 + progress_ratio * 10)
            glow_alpha = int(100 * (1 - progress_ratio))
            glow_color = (*self.color[:3], glow_alpha)
            glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
            screen.blit(glow_surf, (x-glow_size, y-glow_size))

            # Main piece
            pygame.draw.circle(screen, self.color, (x, y), radius)


def create_particles(x, y, color, count=25, styles=None):
    if styles is None:
        styles = ["circle", "square", "triangle"]

    for _ in range(count):
        style = random.choice(styles)
        particles.append(Particle(x, y, color, style))


def draw_board_background():
    """Draw the modern game board background."""
    # Main board with gradient
    surf = pygame.Surface((BOARD_SIZE + 20, BOARD_SIZE + 20), pygame.SRCALPHA)

    # Create gradient background
    for i in range(BOARD_SIZE + 20):
        # Calculate gradient color
        ratio = i / (BOARD_SIZE + 20)
        r = int(35 + ratio * 20)
        g = int(35 + ratio * 20)
        b = int(50 + ratio * 15)
        color = (r, g, b, 255)

        # Draw horizontal line with calculated color
        pygame.draw.line(surf, color, (0, i), (BOARD_SIZE + 20, i))

    # Add rounded corners and border
    pygame.draw.rect(
        surf,
        (0, 0, 0, 0),
        (0, 0, BOARD_SIZE + 20, BOARD_SIZE + 20),
        border_radius=20
    )

    # Draw border with player color
    border_color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
    pygame.draw.rect(
        surf,
        border_color,
        (0, 0, BOARD_SIZE + 20, BOARD_SIZE + 20),
        width=3,
        border_radius=20
    )

    # Add subtle glow along the border
    glow_surf = pygame.Surface((BOARD_SIZE + 40, BOARD_SIZE + 40), pygame.SRCALPHA)
    for i in range(10):
        glow_alpha = 15 - i * 1.5
        glow_color = (*border_color[:3], glow_alpha)
        pygame.draw.rect(
            glow_surf,
            glow_color,
            (i, i, BOARD_SIZE + 40 - i*2, BOARD_SIZE + 40 - i*2),
            width=1,
            border_radius=20 + i
        )

    # Blit the surfaces to the screen
    screen.blit(glow_surf, (BOARD_MARGIN_LEFT - 20, BOARD_MARGIN_TOP - 20))
    screen.blit(surf, (BOARD_MARGIN_LEFT - 10, BOARD_MARGIN_TOP - 10))


def draw_grid():
    """Draw the grid lines on the board with a modern look."""
    for i in range(GRID_SIZE + 1):
        # Choose color - highlight every other line
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
    """Draw the pieces on the board with modern styling."""
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            if board[row, col] != 0:
                x = BOARD_MARGIN_LEFT + col * CELL_SIZE + CELL_SIZE // 2
                y = BOARD_MARGIN_TOP + row * CELL_SIZE + CELL_SIZE // 2
                color = PLAYER1_COLOR if board[row, col] == 1 else PLAYER2_COLOR

                # Glow effect
                for i in range(3):
                    glow_size = CELL_SIZE // 2.5 + 2 + i*2
                    glow_alpha = 80 - i*25
                    glow_color = (*color[:3], glow_alpha)
                    glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
                    screen.blit(glow_surf, (x-glow_size, y-glow_size))

                # Main piece
                pygame.draw.circle(screen, color, (x, y), CELL_SIZE // 2.5)

                # Highlight/shine effect
                highlight_pos = (x - CELL_SIZE//8, y - CELL_SIZE//8)
                highlight_size = CELL_SIZE // 5
                pygame.draw.circle(screen, (255, 255, 255, 150), highlight_pos, highlight_size)


def draw_hover_highlight():
    """Highlight the cell being hovered over."""
    if hover_cell and not game_over:
        row, col = hover_cell
        if is_valid_move(row, col):
            color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
            x = BOARD_MARGIN_LEFT + col * CELL_SIZE
            y = BOARD_MARGIN_TOP + row * CELL_SIZE

            # Draw semi-transparent hover effect
            hover_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            hover_surf.fill((*color[:3], 40))
            screen.blit(hover_surf, (x, y))

            # Draw border
            pygame.draw.rect(
                screen,
                (*color[:3], 120),
                (x, y, CELL_SIZE, CELL_SIZE),
                width=2,
                border_radius=5
            )


def draw_ui():
    """Draw the modern UI elements."""
    # IMPROVED SPACING FOR TOP UI
    player1_count, player2_count = count_pieces()

    # Top UI container for better alignment
    top_ui_margin = 25  # Space from top of screen
    pill_width = 170
    pill_height = 60
    spacing = 30  # Space between elements

    # Calculate positions to center all elements
    total_width = (pill_width * 3) + (spacing * 2)
    left_start = (SCREEN_WIDTH - total_width) // 2

    # Player 1 pill
    p1_rect = pygame.Rect(left_start, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, p1_rect, border_radius=30)
    pygame.draw.rect(
        screen,
        PLAYER1_COLOR,
        p1_rect,
        width=3 if current_player == 1 else 1,
        border_radius=30
    )

    # Player 1 avatar/circle
    pygame.draw.circle(screen, PLAYER1_COLOR, (left_start + 35, top_ui_margin + pill_height//2), 20)

    # Player 1 text
    p1_text = FONT_MEDIUM.render(f"YOU: {player1_count}", True, UI_TEXT)
    screen.blit(p1_text, (left_start + 60, top_ui_margin + 15))

    # Turn indicator - center
    turn_x = left_start + pill_width + spacing
    turn_rect = pygame.Rect(turn_x, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, turn_rect, border_radius=30)
    turn_color = PLAYER1_COLOR if current_player == 1 else PLAYER2_COLOR
    pygame.draw.rect(screen, turn_color, turn_rect, width=3, border_radius=30)

    # Turn text
    turn_text = FONT_MEDIUM.render("TURN", True, UI_TEXT)
    turn_text_rect = turn_text.get_rect(center=(turn_x + pill_width//2, top_ui_margin + pill_height//2))
    screen.blit(turn_text, turn_text_rect)

    # Player 2 pill
    p2_rect = pygame.Rect(turn_x + pill_width + spacing, top_ui_margin, pill_width, pill_height)
    pygame.draw.rect(screen, UI_BG, p2_rect, border_radius=30)
    pygame.draw.rect(
        screen,
        PLAYER2_COLOR,
        p2_rect,
        width=3 if current_player == 2 else 1,
        border_radius=30
    )

    # Player 2 avatar/circle
    pygame.draw.circle(screen, PLAYER2_COLOR, (turn_x + pill_width + spacing + 35, top_ui_margin + pill_height//2), 20)

    # Player 2 text
    p2_text = FONT_MEDIUM.render(f"CPU: {player2_count}", True, UI_TEXT)
    screen.blit(p2_text, (turn_x + pill_width + spacing + 60, top_ui_margin + 15))

    # Bottom status bar with proper spacing
    bottom_y = BOARD_MARGIN_TOP + BOARD_SIZE + 25
    bottom_rect = pygame.Rect(
        BOARD_MARGIN_LEFT,
        bottom_y,
        BOARD_SIZE,
        50
    )
    pygame.draw.rect(screen, UI_BG, bottom_rect, border_radius=25)

    # Game status message
    if not game_over:
        status_text = FONT_MEDIUM.render(
            f"{'Your' if current_player == 1 else 'CPU'} Move",
            True,
            turn_color
        )
    else:
        if winner:
            win_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR
            status_text = FONT_MEDIUM.render(
                f"{'YOU' if winner == 1 else 'CPU'} WIN! 🎉",
                True,
                win_color
            )
        else:
            status_text = FONT_MEDIUM.render("TIE GAME! 🤝", True, UI_TEXT)

    status_rect = status_text.get_rect(center=(SCREEN_WIDTH//2, bottom_y + 25))
    screen.blit(status_text, status_rect)

    # Game over overlay
    if game_over:
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Main game over container
        go_width, go_height = 450, 300  # Larger container
        go_rect = pygame.Rect(
            (SCREEN_WIDTH - go_width)//2,
            (SCREEN_HEIGHT - go_height)//2,
            go_width,
            go_height
        )
        pygame.draw.rect(screen, UI_BG, go_rect, border_radius=25)

        # Border with winner color or neutral
        border_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR if winner == 2 else UI_TEXT
        pygame.draw.rect(screen, border_color, go_rect, width=4, border_radius=25)

        # Game over text with more spacing
        if winner:
            win_color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR
            win_emoji = "🏆" if winner == 1 else "🤖"
            go_text1 = FONT_LARGE.render(f"{win_emoji} GAME OVER {win_emoji}", True, UI_TEXT)
            go_text2 = FONT_LARGE.render(
                f"{'YOU' if winner == 1 else 'CPU'} WIN!",
                True,
                win_color
            )
        else:
            go_text1 = FONT_LARGE.render("🤝 GAME OVER 🤝", True, UI_TEXT)
            go_text2 = FONT_LARGE.render("IT'S A TIE!", True, UI_TEXT)

        # Position text with better spacing
        go_text1_rect = go_text1.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 70))
        go_text2_rect = go_text2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 10))
        screen.blit(go_text1, go_text1_rect)
        screen.blit(go_text2, go_text2_rect)

        # Final scores
        score_text = FONT_MEDIUM.render(f"YOU: {player1_count} • CPU: {player2_count}", True, UI_TEXT)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        screen.blit(score_text, score_rect)

        # Restart button with better positioning
        restart_rect = pygame.Rect(
            (SCREEN_WIDTH - 220)//2,
            (SCREEN_HEIGHT)//2 + 110,
            220,
            60
        )
        pygame.draw.rect(screen, (40, 40, 60), restart_rect, border_radius=30)
        pygame.draw.rect(screen, TERTIARY_ACCENT, restart_rect, width=3, border_radius=30)

        restart_text = FONT_MEDIUM.render("Play Again", True, UI_TEXT)
        restart_rect2 = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 140))
        screen.blit(restart_text, restart_rect2)


def update_hover():
    """Update the hover cell based on mouse position."""
    global hover_cell
    pos = pygame.mouse.get_pos()
    cell = get_cell_from_mouse(pos)
    hover_cell = cell


def get_cell_from_mouse(pos):
    """Get the grid cell (row, col) from the mouse position."""
    x, y = pos
    if (x < BOARD_MARGIN_LEFT or x >= BOARD_MARGIN_LEFT + BOARD_SIZE or
        y < BOARD_MARGIN_TOP or y >= BOARD_MARGIN_TOP + BOARD_SIZE):
        return None

    x -= BOARD_MARGIN_LEFT
    y -= BOARD_MARGIN_TOP
    row = y // CELL_SIZE
    col = x // CELL_SIZE

    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
        return (row, col)
    return None


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
    create_particles(piece_x, piece_y, color, count=30)

    # Flash effect
    flash_alpha = 70

    # Play sound
    if place_sound:
        place_sound.play()

    # Add message
    if player == 1:
        messages.append(Message("⚡ You placed a piece!", PLAYER1_COLOR))
    else:
        messages.append(Message("💻 CPU placed a piece!", PLAYER2_COLOR))

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
            create_particles(cap_x, cap_y, color, count=15)

    # Play capture sound if captures happened
    if captures > 0 and capture_sound:
        capture_sound.play()
        if player == 1:
            messages.append(Message(f"🔥 You captured {captures} pieces!", PLAYER1_COLOR))
        else:
            messages.append(Message(f"⚔️ CPU captured {captures} pieces!", PLAYER2_COLOR))


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
    messages.append(Message("🎮 Game Started! Your Turn!", TERTIARY_ACCENT, size="large"))


def draw_background_gradient():
    """Draw a cooler gradient background with stars."""
    # Create background gradient
    bg_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Gradient from darker at top to slightly lighter at bottom
    for y in range(SCREEN_HEIGHT):
        ratio = y / SCREEN_HEIGHT
        r = int(15 + ratio * 8)
        g = int(15 + ratio * 8)
        b = int(25 + ratio * 10)
        pygame.draw.line(bg_surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    # Add stars with different sizes/brightness
    for _ in range(100):
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT)
        size = random.randint(1, 3)
        brightness = random.randint(120, 255)
        color = (brightness, brightness, brightness)
        pygame.draw.circle(bg_surf, color, (x, y), size)

    # Blit the background
    screen.blit(bg_surf, (0, 0))


def main():
    global current_player, game_over, winner, flash_alpha
    running = True

    # Add initial messages
    messages.append(Message("🎮 Welcome to the Game!", TERTIARY_ACCENT, size="large"))
    messages.append(Message("✨ Place pieces to capture opponents!", UI_TEXT))

    while running:
        # Apply background
        draw_background_gradient()

        # Update hover cell
        update_hover()

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle mouse clicks
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_over:
                    # Check if restart button was clicked
                    restart_rect = pygame.Rect(
                        (SCREEN_WIDTH - 220)//2,
                        (SCREEN_HEIGHT)//2 + 110,
                        220,
                        60
                    )
                    if restart_rect.collidepoint(event.pos):
                        reset_game()
                else:
                    # Handle game move
                    cell = get_cell_from_mouse(event.pos)
                    if cell:
                        row, col = cell
                        if is_valid_move(row, col):
                            make_move(row, col, current_player)
                            current_player = 3 - current_player  # Switch player

        # Draw game elements
        draw_board_background()
        draw_grid()
        draw_hover_highlight()
        draw_pieces()

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

        # Check for game over
        if not game_over and is_board_full():
            game_over = True
            player1_count, player2_count = count_pieces()

            # Determine winner
            if player1_count > player2_count:
                winner = 1
                messages.append(Message("🏆 YOU WIN! CONGRATULATIONS!", PLAYER1_COLOR, size="large"))
            elif player2_count > player1_count:
                winner = 2
                messages.append(Message("😿 CPU WINS! BETTER LUCK NEXT TIME!", PLAYER2_COLOR, size="large"))
            else:
                winner = None
                messages.append(Message("🤝 IT'S A TIE! WELL PLAYED!", UI_TEXT, size="large"))

            # Create victory particles
            for _ in range(10):
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT // 2)
                color = PLAYER1_COLOR if winner == 1 else PLAYER2_COLOR if winner == 2 else TERTIARY_ACCENT
                create_particles(x, y, color, count=20)

            # Play game over sound
            if game_over_sound:
                game_over_sound.play()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()