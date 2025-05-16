import pygame
import sys
import numpy as np
import random
import math
from pygame import gfxdraw
from collections import deque
# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
GRID_SIZE = 8  # Default size
CELL_SIZE = 70
MARGIN_TOP = 100
MARGIN_SIDE = 50
PLAYER_COLORS = [(255, 50, 50, 200), (50, 50, 255, 200)]  # RGBA colors
BACKGROUND_COLOR = (28, 40, 51)
GRID_COLOR = (50, 70, 80)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (100, 150, 200, 100)
FPS = 60
MIN_MOVES_TO_WIN = 2  # Minimum moves before game can end

class OrbParticle:
    def __init__(self, x, y, color, size=5):
        self.x = x
        self.y = y 
        self.color = color
        self.size = random.randint(3, size)
        self.lifetime = random.randint(20, 40)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.speed_x = math.cos(angle) * speed
        self.speed_y = math.sin(angle) * speed
        self.alpha = 255
        
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.lifetime -= 1
        self.alpha = max(0, int(255 * (self.lifetime / 40)))
        
    def draw(self, surface):
        if self.lifetime > 0:
            color = (*self.color[:3], self.alpha)
            pygame.gfxdraw.filled_circle(surface, int(self.x), int(self.y), self.size, color)
            pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), self.size, color)

class Orb:
    def __init__(self, x, y, player, count=1):
        self.x = x
        self.y = y
        self.player = player
        self.count = count
        self.animation_progress = 0  # For pop-in animation
        self.particles = []
        self.exploding = False  # Flag to track if this orb is currently exploding
        
    def update(self):
        # Update animation
        if self.animation_progress < 1:
            self.animation_progress = min(1, self.animation_progress + 0.1)
            
        # Update particles
        for particle in self.particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                self.particles.remove(particle)
    
    def draw(self, surface):
        # Draw particles first (behind the orb)
        for particle in self.particles:
            particle.draw(surface)
            
        # Calculate animated size
        anim_size = self.animation_progress * 15
        
        # Draw the orb
        color = (*PLAYER_COLORS[self.player-1][:3], 255)
        pygame.gfxdraw.filled_circle(surface, int(self.x), int(self.y), int(anim_size), color)
        pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), int(anim_size), color)
        
        # Draw electrons based on count
        if self.count >= 1:
            self.draw_electron(surface, self.x, self.y, 8)
        if self.count >= 2:
            angle = (pygame.time.get_ticks() / 500) % (2 * math.pi)  # Rotating animation
            self.draw_electron(surface, 
                             self.x + math.cos(angle) * 20 * self.animation_progress, 
                             self.y + math.sin(angle) * 20 * self.animation_progress, 
                             6)
        if self.count >= 3:
            angle2 = angle + (2 * math.pi / 3)
            self.draw_electron(surface,
                             self.x + math.cos(angle2) * 20 * self.animation_progress,
                             self.y + math.sin(angle2) * 20 * self.animation_progress,
                             6)
        if self.count >= 4:
            angle3 = angle + (4 * math.pi / 3)
            self.draw_electron(surface,
                             self.x + math.cos(angle3) * 20 * self.animation_progress,
                             self.y + math.sin(angle3) * 20 * self.animation_progress,
                             6)
    
    def draw_electron(self, surface, x, y, size):
        pygame.gfxdraw.filled_circle(surface, int(x), int(y), size, (255, 255, 255, 200))
        pygame.gfxdraw.aacircle(surface, int(x), int(y), size, (255, 255, 255, 200))

class ChainReactionGame:
    def __init__(self, player1_name="Player 1", player2_name="Player 2", grid_size=8, timer=60):
        self.player_names = [player1_name, player2_name]
        self.grid_size = grid_size
        self.current_player = 0
        self.game_over = False
        self.winner = None
        self.grid = np.empty((grid_size, grid_size), dtype=object)  # Stores Orb objects
        self.grid.fill(None)
        self.timer = timer
        self.player_timers = [timer, timer]
        self.last_time_update = pygame.time.get_ticks()
        self.hovered_cell = None
        self.explosion_particles = []
        self.move_count = 0  # Track total moves made
        self.player_moves = [0, 0]
        self.explosion_queue = deque()  # Queue for processing chain reactions
        self.processing_explosions = False  # Flag to track if we're mid-chain reaction
        
        # Initialize screen
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Chain Reaction: {player1_name} vs {player2_name}")
        self.clock = pygame.time.Clock()
        
        # Load fonts
        self.font_large = pygame.font.SysFont("Arial", 32)
        self.font_medium = pygame.font.SysFont("Arial", 24)
    
    def update(self):
        """Update the game state, animations, chain reactions, etc."""
        # Update timers
        self.update_timers()
        
        # Process explosion queue (chain reactions)
        self.process_explosions()
        
        # Update orbs
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.grid[row, col] is not None:
                    self.grid[row, col].update()
        
        # Update explosion particles
        for particle in self.explosion_particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                self.explosion_particles.remove(particle)

    def process_explosions(self):
        """Process pending explosions from the queue"""
        # Process up to 3 explosions per frame for smooth visuals
        explosions_this_frame = 0
        while self.explosion_queue and explosions_this_frame < 3:
            row, col = self.explosion_queue.popleft()
            if self.grid[row, col] is not None:
                self.explode_cell(row, col)
                explosions_this_frame += 1
                
        # If queue is empty and we were processing explosions, check for game end
        if not self.explosion_queue and self.processing_explosions:
            self.processing_explosions = False
            self.check_winner()
            if not self.game_over:
                self.switch_player()
                
    def get_critical_mass(self, row, col):
        """Return critical mass for cell position"""
        if (row == 0 or row == self.grid_size-1) and (col == 0 or col == self.grid_size-1):
            return 2  # Corner
        elif row == 0 or row == self.grid_size-1 or col == 0 or col == self.grid_size-1:
            return 3  # Edge
        return 4  # Center
    
    def is_valid_move(self, row, col):
        """Check if move is valid for current player"""
        # Can't move during chain reactions
        if self.processing_explosions:
            return False
            
        # Check if coordinates are within grid bounds
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return False
            
        # After first move from each player, can only place in own cells or empty cells
        cell = self.grid[row, col]
        
        # Empty cell is always valid
        if cell is None:
            return True
            
        # Can only add to your own orbs
        return cell.player == self.current_player + 1
    
    def make_move(self, row, col):
        """Place an orb and handle chain reactions"""
        if not self.is_valid_move(row, col) or self.game_over:
            return False
        
        cell_x = MARGIN_SIDE + col * CELL_SIZE + CELL_SIZE // 2
        cell_y = MARGIN_TOP + row * CELL_SIZE + CELL_SIZE // 2
        
        # Add or update orb
        if self.grid[row, col] is None:
            self.grid[row, col] = Orb(cell_x, cell_y, self.current_player + 1, 1)
        else:
            # Always set player to current player when adding to existing orb
            self.grid[row, col].player = self.current_player + 1
            self.grid[row, col].count += 1
            # Create particle effect when adding to existing orb
            for _ in range(5):
                self.grid[row, col].particles.append(
                    OrbParticle(cell_x, cell_y, PLAYER_COLORS[self.current_player]))
        
        # Increment move counter
        self.move_count += 1
        self.player_moves[self.current_player] += 1

        # Check for explosion
        critical_mass = self.get_critical_mass(row, col)
        if self.grid[row, col].count >= critical_mass:
            # Add to explosion queue instead of processing immediately
            self.explosion_queue.append((row, col))
            self.processing_explosions = True
            # Don't switch player yet - wait until chain reaction finishes
        else:
            # No explosion, switch player immediately
            self.switch_player()
            self.last_time_update = pygame.time.get_ticks()
        
        return True
    
    def explode_cell(self, row, col):
        """Handle single cell explosion and add adjacent cells to queue if needed"""
        orb = self.grid[row, col]
        if orb is None or orb.exploding:
            return
            
        # Mark as exploding to prevent duplicate explosions
        orb.exploding = True
        
        player = orb.player
        count = orb.count
        
        # Create explosion particles
        for _ in range(count * 8):
            self.explosion_particles.append(
                OrbParticle(orb.x, orb.y, PLAYER_COLORS[player - 1], 7))

        # Remove the exploded orb
        self.grid[row, col] = None

        # Distribute orbs to adjacent cells
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < self.grid_size and 0 <= new_col < self.grid_size:
                x = MARGIN_SIDE + new_col * CELL_SIZE + CELL_SIZE // 2
                y = MARGIN_TOP + new_row * CELL_SIZE + CELL_SIZE // 2

                if self.grid[new_row, new_col] is None:
                    self.grid[new_row, new_col] = Orb(x, y, player, 1)
                else:
                    # When adding to an existing orb, always capture it for the current player
                    current_orb = self.grid[new_row, new_col]
                    if current_orb.player != player:
                        current_orb.player = player
                        current_orb.count += 1
                        current_orb.animation_progress = 0.5  # Start with some animation progress for smoother visuals
                    else:
                        current_orb.count += 1

                    # Add some visual particles
                    for _ in range(3):
                        self.grid[new_row, new_col].particles.append(
                            OrbParticle(x, y, PLAYER_COLORS[player - 1]))

                # Check if this newly affected cell should now explode
                new_critical_mass = self.get_critical_mass(new_row, new_col)
                if (self.grid[new_row, new_col] is not None and 
                    self.grid[new_row, new_col].count >= new_critical_mass):
                    self.explosion_queue.append((new_row, new_col))
    
    def switch_player(self):
        """Switch to next player"""
        self.current_player = (self.current_player + 1) % 2
        
        # After switching, check if current player has any valid moves
        has_valid_moves = False
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.is_valid_move(r, c):
                    has_valid_moves = True
                    break
            if has_valid_moves:
                break
                
        if not has_valid_moves:
            # If no valid moves, switch back and declare other player winner
            self.current_player = (self.current_player + 1) % 2
            self.game_over = True
            self.winner = self.current_player
    
    def check_winner(self):
        """Check if only one player remains (after minimum moves)"""
        if self.move_count < MIN_MOVES_TO_WIN:
            return  # Don't check for winner until minimum moves have been made
            
        active_players = set()
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                orb = self.grid[row, col]
                if orb is not None:
                    active_players.add(orb.player)
        
        if len(active_players) == 1 and self.move_count >= MIN_MOVES_TO_WIN:
            self.game_over = True
            self.winner = list(active_players)[0] - 1
        elif len(active_players) == 0 and self.move_count > 0:
            self.game_over = True
            self.winner = None  # Draw
    
    def update_timers(self):
        current_time = pygame.time.get_ticks()
        if not self.game_over and not self.processing_explosions and current_time - self.last_time_update >= 1000:
            self.player_timers[self.current_player] -= 1
            self.last_time_update = current_time
            if self.player_timers[self.current_player] <= 0:
                self.game_over = True
                self.winner = 1 - self.current_player  # Other player wins
    
    def draw(self):
        """Draw the game state"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # Draw grid background
        grid_rect = pygame.Rect(MARGIN_SIDE, MARGIN_TOP, 
                               self.grid_size * CELL_SIZE, self.grid_size * CELL_SIZE)
        pygame.draw.rect(self.screen, (40, 60, 70), grid_rect)
        
        # Draw grid lines
        for i in range(self.grid_size + 1):
            # Horizontal lines
            y = MARGIN_TOP + i * CELL_SIZE
            pygame.draw.line(self.screen, GRID_COLOR, (MARGIN_SIDE, y), 
                           (MARGIN_SIDE + self.grid_size * CELL_SIZE, y), 2)
            # Vertical lines
            x = MARGIN_SIDE + i * CELL_SIZE
            pygame.draw.line(self.screen, GRID_COLOR, (x, MARGIN_TOP), 
                           (x, MARGIN_TOP + self.grid_size * CELL_SIZE), 2)
        
        # Highlight hovered cell
        if self.hovered_cell and not self.game_over and not self.processing_explosions:
            row, col = self.hovered_cell
            highlight_rect = pygame.Rect(
                MARGIN_SIDE + col * CELL_SIZE, 
                MARGIN_TOP + row * CELL_SIZE, 
                CELL_SIZE, CELL_SIZE
            )
            highlight_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(HIGHLIGHT_COLOR)
            self.screen.blit(highlight_surface, highlight_rect)
        
        # Update and draw all orbs
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.grid[row, col] is not None:
                    self.grid[row, col].draw(self.screen)
        
        # Draw explosion particles
        for particle in self.explosion_particles[:]:
            particle.draw(self.screen)
        
        # Draw UI
        self.draw_ui()
        
        # Draw game over overlay if needed
        if self.game_over:
            self.draw_game_over()
        
        pygame.display.flip()
    
    def draw_ui(self):
        """Draw player info and game status"""
        # Draw right panel background
        panel_rect = pygame.Rect(MARGIN_SIDE + self.grid_size * CELL_SIZE, 0, 
                                SCREEN_WIDTH - (MARGIN_SIDE + self.grid_size * CELL_SIZE), SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, (40, 50, 60), panel_rect)
        
        # Draw player info
        for i in range(2):
            self.draw_player_info(i, 50 + i * 100)
        
        # Draw current turn indicator
        turn_text = "Current Turn:"
        turn_surface = self.font_medium.render(turn_text, True, TEXT_COLOR)
        self.screen.blit(turn_surface, (panel_rect.x + 20, 220))
        
        player_name = self.player_names[self.current_player]
        name_surface = self.font_large.render(player_name, True, PLAYER_COLORS[self.current_player][:3])
        self.screen.blit(name_surface, (panel_rect.x + 20, 250))
        
        # Draw timers
        timer_text = f"Time Left: {self.player_timers[self.current_player]}s"
        timer_surface = self.font_medium.render(timer_text, True, TEXT_COLOR)
        self.screen.blit(timer_surface, (panel_rect.x + 20, 300))
        
        # Draw chain reaction indicator
        if self.processing_explosions:
            chain_text = "Chain Reaction in Progress..."
            chain_surface = self.font_medium.render(chain_text, True, (255, 200, 0))
            self.screen.blit(chain_surface, (panel_rect.x + 20, 350))
    
    def draw_player_info(self, player_num, y_pos):
        """Draw player name, color and timer"""
        panel_x = MARGIN_SIDE + self.grid_size * CELL_SIZE + 20
        
        # Draw player color indicator
        pygame.draw.rect(self.screen, PLAYER_COLORS[player_num][:3], 
                        (panel_x, y_pos, 30, 30), border_radius=15)
        pygame.draw.rect(self.screen, TEXT_COLOR, 
                        (panel_x, y_pos, 30, 30), 2, border_radius=15)
        
        # Draw player name
        name_surface = self.font_medium.render(self.player_names[player_num], True, TEXT_COLOR)
        self.screen.blit(name_surface, (panel_x + 40, y_pos))
        
        # Draw timer
        timer_text = f"Time: {self.player_timers[player_num]}s"
        timer_surface = self.font_medium.render(timer_text, True, TEXT_COLOR)
        self.screen.blit(timer_surface, (panel_x + 40, y_pos + 25))
    
    def draw_game_over(self):
        """Draw game over overlay"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        if self.winner is not None:
            # Winner announcement
            winner_text = f"{self.player_names[self.winner]} Wins!"
            winner_surface = self.font_large.render(winner_text, True, PLAYER_COLORS[self.winner][:3])
            winner_rect = winner_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
            self.screen.blit(winner_surface, winner_rect)
        else:
            # Draw announcement
            draw_text = "Game Ended in Draw!"
            draw_surface = self.font_large.render(draw_text, True, TEXT_COLOR)
            draw_rect = draw_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
            self.screen.blit(draw_surface, draw_rect)
        
        # Play again prompt
        again_text = "Click anywhere to play again"
        again_surface = self.font_medium.render(again_text, True, TEXT_COLOR)
        again_rect = again_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30))
        self.screen.blit(again_surface, again_rect)
    
    def handle_click(self, pos):
        """Handle mouse click"""
        x, y = pos
        
        # Check if click is in grid
        if (MARGIN_SIDE <= x < MARGIN_SIDE + self.grid_size * CELL_SIZE and
            MARGIN_TOP <= y < MARGIN_TOP + self.grid_size * CELL_SIZE):
            col = (x - MARGIN_SIDE) // CELL_SIZE
            row = (y - MARGIN_TOP) // CELL_SIZE
            return self.make_move(row, col)
        
        # If game over, any click resets
        elif self.game_over:
            self.__init__(self.player_names[0], self.player_names[1], self.grid_size, self.timer)
            return True
            
        return False
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            
            # Update hovered cell
            self.hovered_cell = None
            if not self.processing_explosions:  # Don't highlight during chain reactions
                if (MARGIN_SIDE <= mouse_pos[0] < MARGIN_SIDE + self.grid_size * CELL_SIZE and
                    MARGIN_TOP <= mouse_pos[1] < MARGIN_TOP + self.grid_size * CELL_SIZE):
                    col = (mouse_pos[0] - MARGIN_SIDE) // CELL_SIZE
                    row = (mouse_pos[1] - MARGIN_TOP) // CELL_SIZE
                    if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                        self.hovered_cell = (row, col)
            
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
            
            # Update game state
            self.update()
            
            # Drawing
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    # Get command line arguments or use defaults
    player1_name = sys.argv[1] if len(sys.argv) > 1 else "Player 1"
    player2_name = sys.argv[2] if len(sys.argv) > 2 else "Player 2"
    grid_size = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    timer = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    game = ChainReactionGame(player1_name, player2_name, grid_size, timer)
    game.run()