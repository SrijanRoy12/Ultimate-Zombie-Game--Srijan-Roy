import pygame
import random
import sys
import math
import os
from pygame import gfxdraw
from pygame.locals import *

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen setup
WIDTH, HEIGHT = 1024, 768
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🧟 ULTIMATE ZOMBIE ESCAPE 💀")

# Game states
MENU = 0
PLAYING = 1
GAME_OVER = 2
VICTORY = 3
PAUSED = 4
USERNAME = 5
ACCESS_GRANTED = 6
INSTALLATION = 7
INSTRUCTIONS = 8

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (230, 50, 50)
GREEN = (50, 230, 50)
BLUE = (50, 50, 230)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
DARK_GRAY = (40, 40, 40)
BLOOD_RED = (136, 8, 8)
NEON_BLUE = (0, 200, 255)
NEON_GREEN = (57, 255, 20)

# Load assets
def load_image(name, scale=1, colorkey=None):
    try:
        image = pygame.image.load(f"assets/{name}.png").convert_alpha()
        if scale != 1:
            size = image.get_size()
            image = pygame.transform.scale(image, (int(size[0] * scale), int(size[1] * scale)))
        return image
    except:
        print(f"Couldn't load image: assets/{name}.png")
        image = pygame.Surface((50, 50), pygame.SRCALPHA)
        if "player" in name:
            image.fill(RED)
        elif "zombie" in name:
            image.fill(GREEN)
        elif "bullet" in name:
            pygame.draw.circle(image, ORANGE, (25, 25), 10)
        else:
            image.fill(YELLOW)
        return image

def load_sound(name):
    try:
        return pygame.mixer.Sound(f"assets/sounds/{name}.wav")
    except:
        print(f"Couldn't load sound: assets/sounds/{name}.wav")
        return pygame.mixer.Sound(buffer=bytearray(1000))

def load_assets():
    assets = {
        "player": load_image("player", 0.5),
        "zombie_normal": load_image("zombie1", 0.4),
        "zombie_fast": load_image("zombie2", 0.35),
        "zombie_tank": load_image("zombie3", 0.5),
        "bullet": load_image("bullet", 0.2),
        "health_pack": load_image("health", 0.3),
        "ammo_pack": load_image("ammo", 0.3),
        "speed_pack": load_image("speed", 0.3),
        "score_pack": load_image("score", 0.3),
        "background": load_image("background", 1),
        
        "sounds": {
            "collect": load_sound("collect"),
            "shoot": load_sound("shoot"),
            "hit": load_sound("hit"),
            "zombie_death": load_sound("zombie_death"),
            "dash": load_sound("dash"),
            "victory": load_sound("victory"),
            "game_over": load_sound("game_over"),
            "weapon_switch": load_sound("weapon_switch"),
            "reload": load_sound("reload"),
            "typing": load_sound("typing"),
            "access_granted": load_sound("access_granted"),
            "menu_select": load_sound("menu_select")
        }
    }
    
    if assets["background"]:
        assets["background"] = pygame.transform.scale(assets["background"], (WIDTH, HEIGHT))
        darken = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        darken.fill((0, 0, 0, 128))
        assets["background"].blit(darken, (0, 0))
    else:
        assets["background"] = pygame.Surface((WIDTH, HEIGHT))
        assets["background"].fill(DARK_GRAY)
    
    return assets

class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def add_particles(self, pos, color, count=10, speed=2, lifespan=30, size_range=(2, 5)):
        for _ in range(count):
            angle = random.uniform(0, math.pi*2)
            velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
            self.particles.append({
                'pos': [pos[0], pos[1]],
                'vel': velocity,
                'color': color,
                'life': lifespan,
                'max_life': lifespan,
                'size': random.randint(*size_range)
            })
    
    def update(self):
        for particle in self.particles[:]:
            particle['pos'][0] += particle['vel'][0]
            particle['pos'][1] += particle['vel'][1]
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, surface):
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            color = (*particle['color'][:3], alpha)
            size = particle['size']
            pos = (int(particle['pos'][0]), int(particle['pos'][1]))
            pygame.gfxdraw.filled_circle(surface, pos[0], pos[1], size, color)

class Weapon:
    def __init__(self, name, damage, fire_rate, ammo, reload_time, spread, bullet_speed, color):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.max_ammo = ammo
        self.ammo = ammo
        self.reload_time = reload_time
        self.spread = spread
        self.bullet_speed = bullet_speed
        self.color = color
        self.reload_timer = 0
        self.fire_timer = 0
    
    def can_fire(self):
        return self.ammo > 0 and self.reload_timer <= 0 and self.fire_timer <= 0
    
    def fire(self, pos, target_pos):
        if not self.can_fire():
            return []
        
        self.ammo -= 1
        self.fire_timer = 60 / self.fire_rate
        
        bullets = []
        angle = math.atan2(target_pos[1] - pos[1], target_pos[0] - pos[0])
        
        for _ in range(1 if "pistol" in self.name else 3 if "shotgun" in self.name else 1):
            bullet_angle = angle + random.uniform(-self.spread, self.spread)
            bullets.append(Bullet(pos[0], pos[1], bullet_angle, self.bullet_speed, self.damage, self.color))
        
        return bullets
    
    def update(self):
        if self.fire_timer > 0:
            self.fire_timer -= 1
        if self.reload_timer > 0:
            self.reload_timer -= 1
    
    def reload(self):
        if self.reload_timer <= 0 and self.ammo < self.max_ammo:
            self.reload_timer = self.reload_time
            return True
        return False
    
    def finish_reload(self):
        self.ammo = self.max_ammo

class Player:
    def __init__(self, assets):
        self.image = assets["player"]
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.speed = 5
        self.base_speed = 5
        self.health = 100
        self.max_health = 100
        self.invincible = False
        self.invincible_timer = 0
        self.dash_cooldown = 0
        self.dashing = False
        self.dash_direction = [0, 0]
        self.dash_timer = 0
        self.score = 0
        self.kills = 0
        self.weapons = [
            Weapon("Pistol", 25, 3, 12, 60, 0.1, 12, YELLOW),
            Weapon("Shotgun", 15, 1, 6, 90, 0.3, 10, ORANGE),
            Weapon("Rifle", 20, 6, 30, 45, 0.05, 15, BLUE)
        ]
        self.current_weapon = 0
    
    def get_weapon(self):
        return self.weapons[self.current_weapon]
    
    def switch_weapon(self, direction):
        self.current_weapon = (self.current_weapon + direction) % len(self.weapons)
        return self.get_weapon()
    
    def dash(self, direction):
        if self.dash_cooldown == 0 and not self.dashing:
            self.dashing = True
            self.dash_timer = 15
            self.dash_direction = direction
            self.dash_cooldown = 60
            return True
        return False
    
    def update(self):
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        
        if self.dashing:
            self.dash_timer -= 1
            self.rect.x += self.dash_direction[0] * 15
            self.rect.y += self.dash_direction[1] * 15
            if self.dash_timer <= 0:
                self.dashing = False
        
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))
        self.rect.y = max(0, min(HEIGHT - self.rect.height, self.rect.y))
        
        if self.invincible and pygame.time.get_ticks() - self.invincible_timer > 1000:
            self.invincible = False
        
        for weapon in self.weapons:
            weapon.update()

class Zombie:
    def __init__(self, x, y, zombie_type, assets):
        self.type = zombie_type
        self.assets = assets
        
        if zombie_type == "fast":
            self.image = assets["zombie_fast"]
            self.speed = random.uniform(2.5, 3.5)
            self.health = 40
            self.damage = 10
            self.knockback_resistance = 0.3
            self.score_value = 150
        elif zombie_type == "tank":
            self.image = assets["zombie_tank"]
            self.speed = random.uniform(0.8, 1.5)
            self.health = 120
            self.damage = 25
            self.knockback_resistance = 0.95
            self.score_value = 250
        else:
            self.image = assets["zombie_normal"]
            self.speed = random.uniform(1.5, 2.5)
            self.health = 60
            self.damage = 15
            self.knockback_resistance = random.uniform(0.5, 0.9)
            self.score_value = 100
        
        self.rect = self.image.get_rect(center=(x, y))
        self.max_health = self.health
        self.wobble_offset = random.uniform(0, 6.28)
    
    def update(self):
        self.wobble_offset += 0.1
        wobble_x = math.sin(self.wobble_offset) * 2
        wobble_y = math.cos(self.wobble_offset * 1.5) * 2
        self.draw_pos = (self.rect.x + wobble_x, self.rect.y + wobble_y)

class Supply:
    def __init__(self, x, y, assets):
        self.type = random.choices(
            ["normal", "health", "speed", "ammo", "score"],
            weights=[0.5, 0.2, 0.1, 0.15, 0.05]
        )[0]
        
        self.assets = assets
        self.images = {
            "normal": assets["score_pack"],
            "health": assets["health_pack"],
            "speed": assets["speed_pack"],
            "ammo": assets["ammo_pack"],
            "score": assets["score_pack"]
        }
        
        self.image = self.images[self.type]
        self.rect = self.image.get_rect(center=(x, y))
        self.bob_offset = random.uniform(0, 6.28)
        self.value = {
            "normal": 1,
            "health": 20,
            "speed": 5,
            "ammo": 10,
            "score": 100
        }[self.type]
    
    def update(self):
        self.bob_offset += 0.05
        self.bob_y = math.sin(self.bob_offset) * 5

class Bullet:
    def __init__(self, x, y, angle, speed, damage, color):
        self.rect = pygame.Rect(x, y, 8, 8)
        self.speed = speed
        self.velocity = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        self.damage = damage
        self.color = color
    
    def update(self):
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        return not (0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT)

class ZombieEscape:
    def __init__(self):
        self.state = USERNAME
        self.assets = load_assets()
        self.player = None
        self.zombies = []
        self.supplies = []
        self.walls = []
        self.bullets = []
        self.particles = ParticleSystem()
        self.blood_particles = ParticleSystem()
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        self.font_outline = pygame.font.Font(None, 80)
        self.time_limit = 180
        self.start_ticks = 0
        self.wave = 1
        self.zombies_to_spawn = 8
        self.zombie_spawn_timer = 0
        self.supply_spawn_timer = 0
        self.username = ""
        self.username_active = True
        self.access_granted_timer = 0
        self.typing_sound_delay = 0
        
        self.generate_maze()
        
        self.menu_items = [
            {"text": "START GAME", "action": self.begin_playing},
            {"text": "HOW TO PLAY", "action": self.show_instructions},
            {"text": "QUIT", "action": self.quit_game}
        ]
        self.selected_item = 0
    
    def generate_maze(self):
        self.walls = []
        for x in range(0, WIDTH, 50):
            self.walls.append(pygame.Rect(x, 0, 50, 50))
            self.walls.append(pygame.Rect(x, HEIGHT-50, 50, 50))
        for y in range(50, HEIGHT-50, 50):
            self.walls.append(pygame.Rect(0, y, 50, 50))
            self.walls.append(pygame.Rect(WIDTH-50, y, 50, 50))
        
        for _ in range(25):
            x = random.randint(1, (WIDTH-100)//50) * 50
            y = random.randint(1, (HEIGHT-100)//50) * 50
            width = random.choice([50, 100, 150])
            height = random.choice([50, 100, 150])
            self.walls.append(pygame.Rect(x, y, width, height))
    
    def draw_username_screen(self):
        win.fill(BLACK)
        
        # Grid pattern
        for x in range(0, WIDTH, 40):
            pygame.draw.line(win, (20, 20, 50), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(win, (20, 20, 50), (0, y), (WIDTH, y), 1)
        
        # Title with outline effect
        title_text = "ENTER YOUR CALLSIGN"
        text_surface = self.font_outline.render(title_text, True, NEON_BLUE)
        outline_surface = self.font_outline.render(title_text, True, BLACK)
        
        for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            win.blit(outline_surface, (WIDTH//2 - outline_surface.get_width()//2 + dx, 
                                     HEIGHT//3 - outline_surface.get_height()//2 + dy))
        
        win.blit(text_surface, (WIDTH//2 - text_surface.get_width()//2, 
                               HEIGHT//3 - text_surface.get_height()//2))
        
        # Input box
        input_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2, 400, 60)
        pygame.draw.rect(win, NEON_BLUE, input_rect, 2)
        
        # Blinking cursor
        if pygame.time.get_ticks() % 1000 < 500 and self.username_active:
            cursor_pos = self.font_medium.size(self.username)[0]
            pygame.draw.line(win, NEON_BLUE, 
                           (input_rect.x + 10 + cursor_pos, input_rect.y + 10),
                           (input_rect.x + 10 + cursor_pos, input_rect.y + 50), 2)
        
        # Render username text
        username_text = self.font_medium.render(self.username, True, NEON_BLUE)
        win.blit(username_text, (input_rect.x + 10, input_rect.y + 10))
        
        # Instructions
        instr = self.font_small.render("Press ENTER to confirm your callsign", True, (200, 200, 255))
        win.blit(instr, (WIDTH//2 - instr.get_width()//2, HEIGHT - 100))
        
        # Play typing sound effect
        if self.typing_sound_delay > 0:
            self.typing_sound_delay -= 1
        elif len(self.username) > 0 and self.username_active:
            self.assets["sounds"]["typing"].play()
            self.typing_sound_delay = 10
    
    def draw_access_granted(self):
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        win.fill((int(10 * pulse), int(20 * pulse), int(30 * pulse)))
        
        scale = 1 + 0.1 * math.sin(pygame.time.get_ticks() * 0.01)
        ag_text = "ACCESS GRANTED"
        text_surface = self.font_outline.render(ag_text, True, NEON_GREEN)
        text_surface = pygame.transform.scale(text_surface, 
            (int(text_surface.get_width() * scale), 
             int(text_surface.get_height() * scale)))
        
        win.blit(text_surface, (WIDTH//2 - text_surface.get_width()//2, 
                               HEIGHT//2 - text_surface.get_height()//2))
        
        welcome_text = self.font_medium.render(f"Welcome, {self.username}!", True, NEON_BLUE)
        win.blit(welcome_text, (WIDTH//2 - welcome_text.get_width()//2, 
                               HEIGHT//2 + text_surface.get_height()//2 + 30))
        
        msg_text = self.font_small.render("Play with your best, survivor!", True, WHITE)
        win.blit(msg_text, (WIDTH//2 - msg_text.get_width()//2, 
                           HEIGHT//2 + text_surface.get_height()//2 + 80))
        
        if self.access_granted_timer > 0:
            countdown = self.font_small.render(f"Starting in {self.access_granted_timer//60 + 1}...", True, WHITE)
            win.blit(countdown, (WIDTH//2 - countdown.get_width()//2, HEIGHT - 100))
            self.access_granted_timer -= 1
        else:
            self.state = MENU
    
    def begin_playing(self):
        self.state = PLAYING
        self.player = Player(self.assets)
        self.zombies = []
        self.supplies = [Supply(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100), self.assets) for _ in range(5)]
        self.bullets = []
        self.wave = 1
        self.zombies_to_spawn = 8
        self.start_ticks = pygame.time.get_ticks()
        self.spawn_zombies(5)
    
    def spawn_zombies(self, count):
        zombie_types = ["normal"] * 7 + ["fast"] * 2 + ["tank"] * 1
        
        for _ in range(count):
            side = random.randint(0, 3)
            if side == 0:
                x, y = random.randint(0, WIDTH), -50
            elif side == 1:
                x, y = WIDTH + 50, random.randint(0, HEIGHT)
            elif side == 2:
                x, y = random.randint(0, WIDTH), HEIGHT + 50
            else:
                x, y = -50, random.randint(0, HEIGHT)
            
            zombie_type = random.choice(zombie_types)
            self.zombies.append(Zombie(x, y, zombie_type, self.assets))
    
    def show_instructions(self):
        self.state = INSTRUCTIONS
    
    def quit_game(self):
        pygame.quit()
        sys.exit()
    
    def draw_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        win.blit(overlay, (0, 0))
        
        title_text = "ULTIMATE ZOMBIE ESCAPE"
        for i, char in enumerate(title_text):
            offset = math.sin(pygame.time.get_ticks() * 0.001 + i * 0.3) * 5
            char_surf = self.font_large.render(char, True, RED if i % 2 else BLOOD_RED)
            win.blit(char_surf, (WIDTH//2 - self.font_large.size(title_text)[0]//2 + i * 35, HEIGHT//4 + offset))
        
        for i, item in enumerate(self.menu_items):
            color = RED if i == self.selected_item else WHITE
            text = self.font_medium.render(item["text"], True, color)
            
            if i == self.selected_item:
                scale = 1 + 0.1 * math.sin(pygame.time.get_ticks() * 0.005)
                text = pygame.transform.scale(text, 
                    (int(text.get_width() * scale), 
                     int(text.get_height() * scale)))
            
            win.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 + i * 60))
        
        instr = self.font_small.render("Use ARROW KEYS to navigate, ENTER to select", True, WHITE)
        win.blit(instr, (WIDTH//2 - instr.get_width()//2, HEIGHT - 50))
        
        zombie_img = self.assets["zombie_normal"]
        win.blit(pygame.transform.flip(zombie_img, True, False), (100, HEIGHT//2))
        win.blit(zombie_img, (WIDTH - 100 - zombie_img.get_width(), HEIGHT//2))
    
    def draw_instructions(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        win.blit(overlay, (0, 0))
        
        title = self.font_large.render("HOW TO PLAY", True, RED)
        win.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        instructions = [
            "Survive for 3 minutes against waves of zombies!",
            "",
            "CONTROLS:",
            "WASD - Move your character",
            "Mouse - Aim and shoot",
            "Left Click - Fire weapon",
            "Space - Dash in movement direction",
            "Q/E - Switch weapons",
            "R - Reload current weapon",
            "ESC - Pause game",
            "",
            "PICKUPS:",
            "Health - Restores 20 HP",
            "Ammo - Adds ammo to all weapons",
            "Speed - Temporarily increases movement speed",
            "Score - Bonus 100 points",
            "",
            "ZOMBIE TYPES:",
            "Normal - Average speed and health",
            "Fast - Quick but fragile",
            "Tank - Slow but tough",
            "",
            "Press any key to return to menu"
        ]
        
        for i, line in enumerate(instructions):
            text = self.font_small.render(line, True, WHITE)
            win.blit(text, (WIDTH//2 - text.get_width()//2, 150 + i * 25))
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
            
            if event.type == pygame.KEYDOWN:
                if self.state == USERNAME:
                    if event.key == pygame.K_RETURN:
                        if len(self.username) > 0:
                            self.assets["sounds"]["access_granted"].play()
                            self.state = ACCESS_GRANTED
                            self.access_granted_timer = 180
                    elif event.key == pygame.K_BACKSPACE:
                        self.username = self.username[:-1]
                    else:
                        if len(self.username) < 15 and event.unicode.isprintable():
                            self.username += event.unicode
                            self.typing_sound_delay = 0
                
                elif self.state == MENU:
                    if event.key == pygame.K_DOWN:
                        self.selected_item = (self.selected_item + 1) % len(self.menu_items)
                        self.assets["sounds"]["menu_select"].play()
                    elif event.key == pygame.K_UP:
                        self.selected_item = (self.selected_item - 1) % len(self.menu_items)
                        self.assets["sounds"]["menu_select"].play()
                    elif event.key == pygame.K_RETURN:
                        self.assets["sounds"]["menu_select"].play()
                        self.menu_items[self.selected_item]["action"]()
                
                elif self.state == PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = PAUSED
                    elif event.key == pygame.K_SPACE:
                        keys = pygame.key.get_pressed()
                        dx, dy = 0, 0
                        if keys[pygame.K_LEFT]: dx = -1
                        if keys[pygame.K_RIGHT]: dx = 1
                        if keys[pygame.K_UP]: dy = -1
                        if keys[pygame.K_DOWN]: dy = 1
                        
                        if dx != 0 or dy != 0:
                            if self.player.dash([dx, dy]):
                                self.assets["sounds"]["dash"].play()
                    elif event.key == pygame.K_r:
                        if self.player.get_weapon().reload():
                            self.assets["sounds"]["reload"].play()
                    elif event.key == pygame.K_q:
                        self.player.switch_weapon(-1)
                        self.assets["sounds"]["weapon_switch"].play()
                    elif event.key == pygame.K_e:
                        self.player.switch_weapon(1)
                        self.assets["sounds"]["weapon_switch"].play()
                
                elif self.state in [PAUSED, GAME_OVER, VICTORY]:
                    if event.key == pygame.K_r:
                        self.begin_playing()
                    elif event.key == pygame.K_ESCAPE and self.state == PAUSED:
                        self.state = PLAYING
                    elif event.key == pygame.K_m:
                        self.state = MENU
                
                elif self.state == INSTRUCTIONS:
                    self.state = MENU
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == PLAYING and event.button == 1:
                    self.shoot(pygame.mouse.get_pos())
    
    def shoot(self, target_pos):
        weapon = self.player.get_weapon()
        
        if not weapon.can_fire():
            if weapon.ammo <= 0:
                if weapon.reload():
                    self.assets["sounds"]["reload"].play()
            return
        
        new_bullets = weapon.fire(self.player.rect.center, target_pos)
        if new_bullets:
            self.assets["sounds"]["shoot"].play()
            self.bullets.extend(new_bullets)
            self.particles.add_particles(self.player.rect.center, (255, 255, 200), 15, 3, 15)
    
    def update(self):
        if self.state != PLAYING:
            return
        
        self.zombie_spawn_timer -= 1
        if self.zombie_spawn_timer <= 0 and len(self.zombies) < 5 + self.wave * 2:
            self.spawn_zombies(1)
            self.zombie_spawn_timer = 60
        
        self.supply_spawn_timer -= 1
        if self.supply_spawn_timer <= 0 and len(self.supplies) < 3 + self.wave:
            self.supplies.append(Supply(
                random.randint(100, WIDTH-100),
                random.randint(100, HEIGHT-100),
                self.assets
            ))
            self.supply_spawn_timer = 300
        
        keys = pygame.key.get_pressed()
        if not self.player.dashing:
            dx, dy = 0, 0
            if keys[pygame.K_LEFT]: dx = -1
            if keys[pygame.K_RIGHT]: dx = 1
            if keys[pygame.K_UP]: dy = -1
            if keys[pygame.K_DOWN]: dy = 1
            
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071
            
            self.player.rect.x += dx * self.player.speed
            self.player.rect.y += dy * self.player.speed
        
        self.player.update()
        
        for zombie in self.zombies:
            dx = self.player.rect.centerx - zombie.rect.centerx
            dy = self.player.rect.centery - zombie.rect.centery
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            
            zombie.rect.x += (dx / dist) * zombie.speed
            zombie.rect.y += (dy / dist) * zombie.speed
            zombie.update()
        
        for bullet in self.bullets[:]:
            if bullet.update():
                self.bullets.remove(bullet)
                continue
            
            for zombie in self.zombies[:]:
                if bullet.rect.colliderect(zombie.rect):
                    zombie.health -= bullet.damage
                    self.blood_particles.add_particles(
                        zombie.rect.center, 
                        BLOOD_RED, 
                        20, 
                        2, 
                        30,
                        size_range=(3, 6) if zombie.type == "tank" else (2, 5)
                    )
                    
                    if zombie.health <= 0:
                        self.assets["sounds"]["zombie_death"].play()
                        self.zombies.remove(zombie)
                        self.player.kills += 1
                        self.player.score += zombie.score_value
                        self.particles.add_particles(zombie.rect.center, GREEN, 30, 3, 40)
                    
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break
        
        for supply in self.supplies[:]:
            supply.update()
            
            if self.player.rect.colliderect(supply.rect):
                self.assets["sounds"]["collect"].play()
                
                if supply.type == "normal":
                    self.player.score += 50
                elif supply.type == "health":
                    self.player.health = min(self.player.max_health, self.player.health + supply.value)
                elif supply.type == "speed":
                    self.player.speed = self.player.base_speed + supply.value
                    pygame.time.set_timer(pygame.USEREVENT, 5000)
                elif supply.type == "ammo":
                    for weapon in self.player.weapons:
                        weapon.ammo = min(weapon.max_ammo, weapon.ammo + supply.value)
                elif supply.type == "score":
                    self.player.score += supply.value
                
                self.particles.add_particles(supply.rect.center, supply.image.get_at((15, 15))[:3], 20, 2, 30)
                self.supplies.remove(supply)
        
        if not self.player.invincible and not self.player.dashing:
            for zombie in self.zombies:
                if self.player.rect.colliderect(zombie.rect):
                    self.assets["sounds"]["hit"].play()
                    
                    self.player.health -= zombie.damage
                    self.player.invincible = True
                    self.player.invincible_timer = pygame.time.get_ticks()
                    
                    dx = self.player.rect.centerx - zombie.rect.centerx
                    dy = self.player.rect.centery - zombie.rect.centery
                    dist = max(1, math.sqrt(dx*dx + dy*dy))
                    knockback = 20 * (1 - zombie.knockback_resistance)
                    self.player.rect.x += (dx / dist) * knockback
                    self.player.rect.y += (dy / dist) * knockback
                    
                    self.blood_particles.add_particles(self.player.rect.center, BLOOD_RED, 30, 3, 40)
                    
                    if self.player.health <= 0:
                        self.state = GAME_OVER
                        self.assets["sounds"]["game_over"].play()
                    break
        
        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000
        if elapsed >= self.time_limit:
            self.state = VICTORY
            self.assets["sounds"]["victory"].play()
        
        self.wave = 1 + int(elapsed / 30)
        
        self.particles.update()
        self.blood_particles.update()
    
    def draw_game(self):
        win.blit(self.assets["background"], (0, 0))
        
        for wall in self.walls:
            wall_surface = pygame.Surface((wall.width, wall.height), pygame.SRCALPHA)
            wall_surface.fill((70, 70, 70, 180))
            win.blit(wall_surface, (wall.x, wall.y))
            pygame.draw.rect(win, (50, 50, 50, 180), wall, 2)
        
        for supply in self.supplies:
            pos = (supply.rect.x, supply.rect.y + supply.bob_y)
            win.blit(supply.image, pos)
            if pygame.time.get_ticks() % 1000 < 500:
                glow = pygame.Surface((supply.rect.width, supply.rect.height), pygame.SRCALPHA)
                alpha = int(100 + 155 * abs(math.sin(pygame.time.get_ticks() * 0.005)))
                color = supply.image.get_at((15, 15))[:3] + (alpha,)
                pygame.draw.rect(glow, color, (0, 0, supply.rect.width, supply.rect.height), 3)
                win.blit(glow, pos)
        
        for bullet in self.bullets:
            pygame.draw.circle(win, bullet.color, bullet.rect.center, 4)
            pygame.draw.circle(win, (min(255, bullet.color[0]+100), min(255, bullet.color[1]+100), min(255, bullet.color[2]+100)), bullet.rect.center, 2)
        
        for zombie in self.zombies:
            win.blit(zombie.image, zombie.draw_pos)
            health_width = int(40 * (zombie.health / zombie.max_health))
            health_color = GREEN if zombie.health > zombie.max_health * 0.6 else YELLOW if zombie.health > zombie.max_health * 0.3 else RED
            pygame.draw.rect(win, health_color, (zombie.draw_pos[0], zombie.draw_pos[1] - 10, health_width, 5))
        
        if self.player.dashing:
            for i in range(1, 6):
                alpha = 255 - i * 40
                size = self.player.rect.width - i * 2
                pos = (
                    self.player.rect.x + i * self.player.dash_direction[0] * 3,
                    self.player.rect.y + i * self.player.dash_direction[1] * 3
                )
                s = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.rect(s, (*RED, alpha), (0, 0, size, size))
                win.blit(s, pos)
        
        if not self.player.invincible or pygame.time.get_ticks() % 200 < 100:
            win.blit(self.player.image, self.player.rect)
        
        self.particles.draw(win)
        self.blood_particles.draw(win)
        self.draw_ui()
    
    def draw_ui(self):
        health_width = int(200 * (self.player.health / self.player.max_health))
        health_color = GREEN if self.player.health > self.player.max_health * 0.6 else YELLOW if self.player.health > self.player.max_health * 0.3 else RED
        pygame.draw.rect(win, health_color, (20, 20, health_width, 25))
        pygame.draw.rect(win, WHITE, (20, 20, 200, 25), 2)
        health_text = self.font_small.render(f"{int(self.player.health)}/{self.player.max_health}", True, WHITE)
        win.blit(health_text, (120 - health_text.get_width()//2, 25 - health_text.get_height()//2))
        
        weapon = self.player.get_weapon()
        weapon_text = self.font_small.render(f"{weapon.name}: {weapon.ammo}/{weapon.max_ammo}", True, weapon.color)
        win.blit(weapon_text, (20, 60))
        
        if weapon.reload_timer > 0:
            reload_width = int(100 * (1 - weapon.reload_timer / weapon.reload_time))
            pygame.draw.rect(win, YELLOW, (20, 90, reload_width, 10))
            pygame.draw.rect(win, WHITE, (20, 90, 100, 10), 1)
        
        score_text = self.font_small.render(f"SCORE: {self.player.score}", True, WHITE)
        win.blit(score_text, (20, 120))
        
        kills_text = self.font_small.render(f"KILLS: {self.player.kills}", True, WHITE)
        win.blit(kills_text, (20, 150))
        
        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000
        time_left = max(0, self.time_limit - elapsed)
        mins, secs = divmod(int(time_left), 60)
        time_text = self.font_small.render(f"TIME: {mins:02d}:{secs:02d}", True, WHITE)
        win.blit(time_text, (WIDTH - 150, 20))
        
        wave_text = self.font_small.render(f"WAVE: {self.wave}", True, WHITE)
        win.blit(wave_text, (WIDTH - 150, 50))
        
        if self.player.dash_cooldown > 0:
            cooldown_width = int(100 * (1 - self.player.dash_cooldown / 60))
            pygame.draw.rect(win, BLUE, (WIDTH - 120, 80, cooldown_width, 10))
            pygame.draw.rect(win, WHITE, (WIDTH - 120, 80, 100, 10), 1)
        
        controls = self.font_small.render("WASD: Move | LMB: Shoot | SPACE: Dash | Q/E: Switch Weapon | R: Reload", True, (200, 200, 200))
        win.blit(controls, (WIDTH//2 - controls.get_width()//2, HEIGHT - 30))
    
    def draw_pause_screen(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        win.blit(overlay, (0, 0))
        
        pause = self.font_large.render("PAUSED", True, WHITE)
        win.blit(pause, (WIDTH//2 - pause.get_width()//2, HEIGHT//2 - 100))
        
        resume = self.font_medium.render("Press ESC to resume", True, WHITE)
        win.blit(resume, (WIDTH//2 - resume.get_width()//2, HEIGHT//2))
        
        restart = self.font_medium.render("Press R to restart", True, WHITE)
        win.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 60))
        
        menu = self.font_medium.render("Press M for menu", True, WHITE)
        win.blit(menu, (WIDTH//2 - menu.get_width()//2, HEIGHT//2 + 120))
    
    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        win.blit(overlay, (0, 0))
        
        game_over = self.font_large.render("GAME OVER", True, RED)
        win.blit(game_over, (WIDTH//2 - game_over.get_width()//2, HEIGHT//2 - 100))
        
        score = self.font_medium.render(f"Final Score: {self.player.score}", True, WHITE)
        win.blit(score, (WIDTH//2 - score.get_width()//2, HEIGHT//2))
        
        kills = self.font_medium.render(f"Zombies Killed: {self.player.kills}", True, WHITE)
        win.blit(kills, (WIDTH//2 - kills.get_width()//2, HEIGHT//2 + 50))
        
        time_survived = (pygame.time.get_ticks() - self.start_ticks) / 1000
        mins, secs = divmod(int(time_survived), 60)
        time_text = self.font_medium.render(f"Time Survived: {mins:02d}:{secs:02d}", True, WHITE)
        win.blit(time_text, (WIDTH//2 - time_text.get_width()//2, HEIGHT//2 + 100))
        
        restart = self.font_medium.render("Press R to restart", True, WHITE)
        win.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 180))
        
        menu = self.font_medium.render("Press M for menu", True, WHITE)
        win.blit(menu, (WIDTH//2 - menu.get_width()//2, HEIGHT//2 + 240))
    
    def draw_victory(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        win.blit(overlay, (0, 0))
        
        victory = self.font_large.render("VICTORY!", True, GREEN)
        win.blit(victory, (WIDTH//2 - victory.get_width()//2, HEIGHT//2 - 100))
        
        score = self.font_medium.render(f"Final Score: {self.player.score}", True, WHITE)
        win.blit(score, (WIDTH//2 - score.get_width()//2, HEIGHT//2))
        
        kills = self.font_medium.render(f"Zombies Killed: {self.player.kills}", True, WHITE)
        win.blit(kills, (WIDTH//2 - kills.get_width()//2, HEIGHT//2 + 50))
        
        time_text = self.font_medium.render("You survived the zombie apocalypse!", True, WHITE)
        win.blit(time_text, (WIDTH//2 - time_text.get_width()//2, HEIGHT//2 + 100))
        
        restart = self.font_medium.render("Press R to restart", True, WHITE)
        win.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 180))
        
        menu = self.font_medium.render("Press M for menu", True, WHITE)
        win.blit(menu, (WIDTH//2 - menu.get_width()//2, HEIGHT//2 + 240))
    
    def draw(self):
        if self.state == USERNAME:
            self.draw_username_screen()
        elif self.state == ACCESS_GRANTED:
            self.draw_access_granted()
        elif self.state == MENU:
            self.draw_menu()
        elif self.state == PLAYING:
            self.draw_game()
        elif self.state == PAUSED:
            self.draw_game()
            self.draw_pause_screen()
        elif self.state == GAME_OVER:
            self.draw_game()
            self.draw_game_over()
        elif self.state == VICTORY:
            self.draw_game()
            self.draw_victory()
        elif self.state == INSTRUCTIONS:
            self.draw_instructions()
    
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    game = ZombieEscape()
    game.run()