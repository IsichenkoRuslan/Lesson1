import math
import random
import sys
from dataclasses import dataclass

import pygame

# ------------------------------------------------------------
# BALL ARENA — небольшая аркадная игра на Pygame
# Управление: WASD / стрелки — толчок, SPACE — способность, P — пауза
# ------------------------------------------------------------

pygame.init()
pygame.display.set_caption("Ball Arena")

WIDTH, HEIGHT = 1100, 760
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
CLOCK = pygame.time.Clock()
FPS = 60

FONT = pygame.font.SysFont("arial", 22)
SMALL = pygame.font.SysFont("arial", 16)
MEDIUM = pygame.font.SysFont("arial", 30, bold=True)
BIG = pygame.font.SysFont("arial", 54, bold=True)

BG = (13, 18, 32)
PANEL = (24, 32, 52)
PANEL_LIGHT = (33, 44, 69)
WHITE = (240, 245, 255)
MUTED = (157, 171, 198)
GREEN = (77, 220, 145)
RED = (255, 91, 105)
ARENA = pygame.Rect(60, 135, 980, 535)

COLORS = [
    (70, 165, 255),
    (255, 92, 112),
    (93, 224, 151),
    (190, 115, 255),
    (255, 190, 75),
    (70, 220, 220),
    (255, 125, 215),
    (220, 230, 245),
]
COLOR_NAMES = ["Синий", "Красный", "Зелёный", "Фиолетовый", "Оранжевый", "Бирюзовый", "Розовый", "Серебряный"]

ABILITIES = {
    "turbo": {
        "name": "ТУРБО",
        "description": "Резко ускоряет шарик на 2.5 секунды.",
        "cooldown": 8.0,
        "short": "Ускорение",
    },
    "heavy": {
        "name": "ТЯЖЁЛЫЙ УДАР",
        "description": "Столкновения наносят в 2 раза больше урона.",
        "cooldown": 9.0,
        "short": "Больше урона",
    },
    "shield": {
        "name": "ЭНЕРГОЩИТ",
        "description": "На 3 секунды полностью защищает от урона.",
        "cooldown": 10.0,
        "short": "Защита",
    },
    "projectile": {
        "name": "ЭНЕРГОСНАРЯД",
        "description": "Стреляет снарядом, который наносит 22 урона.",
        "cooldown": 4.0,
        "short": "Выстрел",
    },
    "mine": {
        "name": "МИНА",
        "description": "Оставляет мину: попадание противника наносит 26 урона.",
        "cooldown": 9.0,
        "short": "Ловушка",
    },
    "heal": {
        "name": "РЕГЕНЕРАЦИЯ",
        "description": "Восстанавливает 22 единицы здоровья.",
        "cooldown": 12.0,
        "short": "Лечение",
    },
    "freeze": {
        "name": "ЗАМОРОЗКА",
        "description": "Замедляет противника на 2.5 секунды.",
        "cooldown": 11.0,
        "short": "Замедление",
    },
}
ABILITY_ORDER = list(ABILITIES.keys())


def clamp(value, low, high):
    return max(low, min(high, value))


def draw_text(surface, text, font, color, center):
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=center))


def draw_text_left(surface, text, font, color, pos):
    surface.blit(font.render(text, True, color), pos)


def brighten(color, amount=35):
    return tuple(min(255, c + amount) for c in color)


def draw_panel(surface, rect, color=PANEL, border=(55, 70, 103), radius=18, width=2):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def draw_background(surface):
    surface.fill(BG)
    # Ненавязчивый фон из точек и линий.
    for x in range(25, WIDTH, 55):
        for y in range(20, HEIGHT, 55):
            pygame.draw.circle(surface, (25, 34, 55), (x, y), 1)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple
    radius: int = 4

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.vx *= 0.985
        self.vy *= 0.985

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha_radius = max(1, int(self.radius * min(1.0, self.life * 3)))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), alpha_radius)


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: tuple
    life: float = 0.8

    def update(self, dt):
        self.y -= 34 * dt
        self.life -= dt

    def draw(self, surface):
        if self.life > 0:
            image = SMALL.render(self.text, True, self.color)
            image.set_alpha(int(255 * clamp(self.life / 0.8, 0, 1)))
            surface.blit(image, image.get_rect(center=(int(self.x), int(self.y))))


class Ball:
    def __init__(self, x, y, color, ability, label, direction):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.ability = ability
        self.label = label
        self.radius = 31
        self.max_hp = 100
        self.hp = 100.0
        self.base_speed = 205.0
        angle = direction + random.uniform(-0.28, 0.28)
        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed
        self.cooldown = 0.0
        self.boost_timer = 0.0
        self.power_timer = 0.0
        self.shield_timer = 0.0
        self.slow_timer = 0.0
        self.ability_flash = 0.0
        self.push_cooldown = 0.0

    def update_timers(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        self.power_timer = max(0.0, self.power_timer - dt)
        self.shield_timer = max(0.0, self.shield_timer - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.ability_flash = max(0.0, self.ability_flash - dt)
        self.push_cooldown = max(0.0, self.push_cooldown - dt)

        if self.boost_timer > 0:
            self.boost_timer = max(0.0, self.boost_timer - dt)
            if self.boost_timer == 0:
                speed = math.hypot(self.vx, self.vy)
                if speed > 0:
                    self.vx = self.vx / speed * self.base_speed
                    self.vy = self.vy / speed * self.base_speed

    def update(self, dt, arena):
        move_factor = 0.55 if self.slow_timer > 0 else 1.0
        self.x += self.vx * move_factor * dt
        self.y += self.vy * move_factor * dt

        if self.x - self.radius < arena.left:
            self.x = arena.left + self.radius
            self.vx = abs(self.vx)
        elif self.x + self.radius > arena.right:
            self.x = arena.right - self.radius
            self.vx = -abs(self.vx)

        if self.y - self.radius < arena.top:
            self.y = arena.top + self.radius
            self.vy = abs(self.vy)
        elif self.y + self.radius > arena.bottom:
            self.y = arena.bottom - self.radius
            self.vy = -abs(self.vy)

        speed = math.hypot(self.vx, self.vy)
        max_speed = 390 if self.boost_timer > 0 else 315
        min_speed = 135
        if speed > max_speed:
            self.vx = self.vx / speed * max_speed
            self.vy = self.vy / speed * max_speed
        elif 0 < speed < min_speed:
            self.vx = self.vx / speed * min_speed
            self.vy = self.vy / speed * min_speed

    def take_damage(self, amount):
        if self.shield_timer > 0:
            return 0
        actual = min(self.hp, amount)
        self.hp = max(0.0, self.hp - amount)
        return actual

    def use_ability(self, opponent, projectiles, mines, particles, floating_texts):
        if self.cooldown > 0:
            return False

        ability = self.ability
        self.cooldown = ABILITIES[ability]["cooldown"]
        self.ability_flash = 0.5
        floating_texts.append(FloatingText(self.x, self.y - 44, ABILITIES[ability]["name"], self.color))

        if ability == "turbo":
            self.boost_timer = 2.5
            speed = math.hypot(self.vx, self.vy)
            if speed > 0:
                self.vx = self.vx / speed * min(390, speed * 1.75)
                self.vy = self.vy / speed * min(390, speed * 1.75)
            for _ in range(12):
                particles.append(Particle(self.x, self.y, random.uniform(-110, 110), random.uniform(-110, 110), 0.45, self.color, 5))

        elif ability == "heavy":
            self.power_timer = 4.0
            for _ in range(9):
                particles.append(Particle(self.x, self.y, random.uniform(-90, 90), random.uniform(-90, 90), 0.45, (255, 190, 75), 5))

        elif ability == "shield":
            self.shield_timer = 3.0

        elif ability == "projectile":
            dx, dy = opponent.x - self.x, opponent.y - self.y
            distance = max(1.0, math.hypot(dx, dy))
            speed = 510.0
            projectiles.append(Projectile(self, self.x, self.y, dx / distance * speed, dy / distance * speed, 22))

        elif ability == "mine":
            speed = max(1.0, math.hypot(self.vx, self.vy))
            # Мина появляется немного позади движущегося шарика.
            mx = self.x - self.vx / speed * 48
            my = self.y - self.vy / speed * 48
            mines.append(Mine(self, mx, my))
            for _ in range(8):
                particles.append(Particle(mx, my, random.uniform(-70, 70), random.uniform(-70, 70), 0.4, (255, 150, 75), 4))

        elif ability == "heal":
            healed = min(22.0, self.max_hp - self.hp)
            self.hp = min(self.max_hp, self.hp + 22.0)
            floating_texts.append(FloatingText(self.x, self.y - 62, f"+{int(healed)} HP", GREEN))
            for _ in range(14):
                particles.append(Particle(self.x, self.y, random.uniform(-100, 100), random.uniform(-100, 100), 0.6, GREEN, 5))

        elif ability == "freeze":
            opponent.slow_timer = 2.5
            dealt = opponent.take_damage(4)
            floating_texts.append(FloatingText(opponent.x, opponent.y - 42, f"-{int(dealt)}", (120, 210, 255)))
            for _ in range(12):
                particles.append(Particle(opponent.x, opponent.y, random.uniform(-100, 100), random.uniform(-100, 100), 0.55, (130, 210, 255), 5))

        return True

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        # Тень и внешний обод.
        pygame.draw.circle(surface, (5, 8, 16), (cx + 5, cy + 7), self.radius + 2)
        pygame.draw.circle(surface, brighten(self.color, 15), (cx, cy), self.radius + 2)
        pygame.draw.circle(surface, self.color, (cx, cy), self.radius - 2)
        pygame.draw.circle(surface, brighten(self.color, 55), (cx - 10, cy - 11), 8)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 12, cy - 13), 3)

        if self.power_timer > 0:
            pygame.draw.circle(surface, (255, 196, 75), (cx, cy), self.radius + 8, 3)
        if self.shield_timer > 0:
            pygame.draw.circle(surface, (120, 220, 255), (cx, cy), self.radius + 12, 4)
        if self.boost_timer > 0:
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), self.radius + 5, 2)

        label = SMALL.render(self.label, True, WHITE)
        surface.blit(label, label.get_rect(center=(cx, cy + self.radius + 17)))


class Projectile:
    def __init__(self, owner, x, y, vx, vy, damage):
        self.owner = owner
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.radius = 9
        self.life = 2.3

    def update(self, dt, arena, target, particles, floating_texts):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

        if math.hypot(self.x - target.x, self.y - target.y) < self.radius + target.radius:
            dealt = target.take_damage(self.damage)
            floating_texts.append(FloatingText(target.x, target.y - 42, f"-{int(dealt)}", RED))
            for _ in range(12):
                particles.append(Particle(self.x, self.y, random.uniform(-120, 120), random.uniform(-120, 120), 0.45, self.owner.color, 5))
            # Небольшой толчок от попадания.
            dx, dy = target.x - self.x, target.y - self.y
            length = max(1.0, math.hypot(dx, dy))
            target.vx += dx / length * 100
            target.vy += dy / length * 100
            return False

        if (self.life <= 0 or self.x < arena.left or self.x > arena.right or
                self.y < arena.top or self.y > arena.bottom):
            return False
        return True

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius + 4)
        pygame.draw.circle(surface, self.owner.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x - 3), int(self.y - 3)), 3)


class Mine:
    def __init__(self, owner, x, y):
        self.owner = owner
        self.x = float(x)
        self.y = float(y)
        self.radius = 13
        self.life = 10.0
        self.pulse = 0.0

    def update(self, dt, target, particles, floating_texts):
        self.life -= dt
        self.pulse += dt * 5
        if math.hypot(self.x - target.x, self.y - target.y) < self.radius + target.radius + 5:
            dealt = target.take_damage(26)
            floating_texts.append(FloatingText(target.x, target.y - 48, f"-{int(dealt)}", RED))
            dx, dy = target.x - self.x, target.y - self.y
            length = max(1.0, math.hypot(dx, dy))
            target.vx += dx / length * 190
            target.vy += dy / length * 190
            for _ in range(22):
                particles.append(Particle(self.x, self.y, random.uniform(-190, 190), random.uniform(-190, 190), 0.65, (255, 145, 75), 6))
            return False
        return self.life > 0

    def draw(self, surface):
        pulse_radius = self.radius + int((math.sin(self.pulse) + 1) * 2)
        pygame.draw.circle(surface, (255, 120, 80), (int(self.x), int(self.y)), pulse_radius + 4, 2)
        pygame.draw.circle(surface, (105, 43, 42), (int(self.x), int(self.y)), pulse_radius)
        pygame.draw.circle(surface, (255, 190, 100), (int(self.x), int(self.y)), 4)


class Game:
    def __init__(self):
        self.state = "menu"
        self.selected_color = 0
        self.selected_ability = "turbo"
        self.player = None
        self.bot = None
        self.projectiles = []
        self.mines = []
        self.particles = []
        self.floating_texts = []
        self.collision_timer = 0.0
        self.ai_timer = 0.7
        self.pause = False
        self.result = ""
        self.winner_color = WHITE
        self.last_push = 0.0
        self.bot_color_index = 1
        self.bot_ability = "heavy"

    def start_battle(self):
        bot_colors = [i for i in range(len(COLORS)) if i != self.selected_color]
        self.bot_color_index = random.choice(bot_colors)
        self.bot_ability = random.choice(ABILITY_ORDER)

        self.player = Ball(ARENA.left + 200, ARENA.centery, COLORS[self.selected_color], self.selected_ability, "ТЫ", 0.0)
        self.bot = Ball(ARENA.right - 200, ARENA.centery, COLORS[self.bot_color_index], self.bot_ability, "БОТ", math.pi)
        self.projectiles = []
        self.mines = []
        self.particles = []
        self.floating_texts = []
        self.collision_timer = 0.0
        self.ai_timer = 0.8
        self.pause = False
        self.result = ""
        self.state = "battle"

    def add_collision_effect(self, x, y, color):
        for _ in range(15):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(45, 180)
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, 0.42, color, 5))

    def handle_ball_collision(self):
        a, b = self.player, self.bot
        dx, dy = b.x - a.x, b.y - a.y
        distance = math.hypot(dx, dy)
        min_distance = a.radius + b.radius
        if distance == 0:
            dx, dy, distance = 1.0, 0.0, 1.0
        if distance >= min_distance:
            return

        nx, ny = dx / distance, dy / distance
        overlap = min_distance - distance
        a.x -= nx * overlap * 0.5
        a.y -= ny * overlap * 0.5
        b.x += nx * overlap * 0.5
        b.y += ny * overlap * 0.5

        relative_vx = b.vx - a.vx
        relative_vy = b.vy - a.vy
        relative_speed = relative_vx * nx + relative_vy * ny
        if relative_speed < 0:
            impulse = -(1.75) * relative_speed / 2
            a.vx -= impulse * nx
            a.vy -= impulse * ny
            b.vx += impulse * nx
            b.vy += impulse * ny

        if self.collision_timer <= 0 and relative_speed < 0:
            impact = abs(relative_speed)
            base_damage = clamp(5 + impact / 37, 5, 15)
            damage_to_bot = base_damage * (2.0 if a.power_timer > 0 else 1.0)
            damage_to_player = base_damage * (2.0 if b.power_timer > 0 else 1.0)
            dealt_bot = b.take_damage(damage_to_bot)
            dealt_player = a.take_damage(damage_to_player)
            if dealt_bot > 0:
                self.floating_texts.append(FloatingText(b.x, b.y - 43, f"-{int(dealt_bot)}", RED))
            if dealt_player > 0:
                self.floating_texts.append(FloatingText(a.x, a.y - 43, f"-{int(dealt_player)}", RED))
            self.add_collision_effect((a.x + b.x) / 2, (a.y + b.y) / 2, (255, 220, 150))
            self.collision_timer = 0.38

    def bot_decision(self, dt):
        self.ai_timer -= dt
        if self.ai_timer > 0:
            return
        self.ai_timer = random.uniform(0.45, 0.95)
        if self.bot.cooldown > 0:
            return

        distance = math.hypot(self.player.x - self.bot.x, self.player.y - self.bot.y)
        ability = self.bot.ability
        use = False
        if ability == "heal":
            use = self.bot.hp < 78
        elif ability == "shield":
            use = self.bot.hp < 70 or random.random() < 0.22
        elif ability == "projectile":
            use = distance > 115 or random.random() < 0.3
        elif ability == "mine":
            use = distance < 320 or random.random() < 0.25
        elif ability == "freeze":
            use = distance < 430 and random.random() < 0.65
        elif ability in ("turbo", "heavy"):
            use = distance < 520 and random.random() < 0.62
        if use:
            self.bot.use_ability(self.player, self.projectiles, self.mines, self.particles, self.floating_texts)

    def update(self, dt):
        if self.state != "battle" or self.pause:
            return

        self.collision_timer = max(0.0, self.collision_timer - dt)
        self.player.update_timers(dt)
        self.bot.update_timers(dt)
        self.player.update(dt, ARENA)
        self.bot.update(dt, ARENA)
        self.handle_ball_collision()
        self.bot_decision(dt)

        active_projectiles = []
        for projectile in self.projectiles:
            target = self.bot if projectile.owner is self.player else self.player
            if projectile.update(dt, ARENA, target, self.particles, self.floating_texts):
                active_projectiles.append(projectile)
        self.projectiles = active_projectiles

        active_mines = []
        for mine in self.mines:
            target = self.bot if mine.owner is self.player else self.player
            if mine.update(dt, target, self.particles, self.floating_texts):
                active_mines.append(mine)
        self.mines = active_mines

        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for floating in self.floating_texts:
            floating.update(dt)
        self.floating_texts = [f for f in self.floating_texts if f.life > 0]

        if self.player.hp <= 0 or self.bot.hp <= 0:
            if self.player.hp <= 0 and self.bot.hp <= 0:
                self.result = "НИЧЬЯ!"
                self.winner_color = WHITE
            elif self.bot.hp <= 0:
                self.result = "ПОБЕДА!"
                self.winner_color = self.player.color
            else:
                self.result = "ПОРАЖЕНИЕ"
                self.winner_color = self.bot.color
            self.state = "result"

    def push_player(self, dx, dy):
        if self.state != "battle" or self.pause or self.player.push_cooldown > 0:
            return
        length = math.hypot(dx, dy)
        if length == 0:
            return
        self.player.vx += dx / length * 115
        self.player.vy += dy / length * 115
        self.player.push_cooldown = 0.12

    def draw_health_bar(self, x, y, width, ball, align_right=False):
        pygame.draw.rect(SCREEN, (45, 54, 75), (x, y, width, 17), border_radius=8)
        fill = int(width * clamp(ball.hp / ball.max_hp, 0, 1))
        if align_right:
            pygame.draw.rect(SCREEN, ball.color, (x + width - fill, y, fill, 17), border_radius=8)
        else:
            pygame.draw.rect(SCREEN, ball.color, (x, y, fill, 17), border_radius=8)
        pygame.draw.rect(SCREEN, (75, 88, 117), (x, y, width, 17), 2, border_radius=8)

    def draw_battle(self):
        draw_background(SCREEN)
        draw_text(SCREEN, "BALL ARENA", MEDIUM, WHITE, (WIDTH // 2, 31))

        # Верхние панели игроков.
        draw_text_left(SCREEN, f"ТЫ  •  {ABILITIES[self.player.ability]['name']}", SMALL, self.player.color, (70, 67))
        draw_text_left(SCREEN, f"БОТ  •  {ABILITIES[self.bot.ability]['name']}", SMALL, self.bot.color, (WIDTH - 350, 67))
        self.draw_health_bar(70, 91, 390, self.player)
        self.draw_health_bar(WIDTH - 460, 91, 390, self.bot, True)
        draw_text(SCREEN, f"{int(self.player.hp)} / 100", SMALL, WHITE, (265, 99))
        draw_text(SCREEN, f"{int(self.bot.hp)} / 100", SMALL, WHITE, (WIDTH - 265, 99))

        pygame.draw.rect(SCREEN, (17, 25, 43), ARENA, border_radius=24)
        pygame.draw.rect(SCREEN, (66, 85, 120), ARENA, 3, border_radius=24)
        # Лёгкая разметка арены.
        for x in range(ARENA.left + 35, ARENA.right, 55):
            pygame.draw.line(SCREEN, (24, 36, 58), (x, ARENA.top + 12), (x, ARENA.bottom - 12), 1)
        for y in range(ARENA.top + 35, ARENA.bottom, 55):
            pygame.draw.line(SCREEN, (24, 36, 58), (ARENA.left + 12, y), (ARENA.right - 12, y), 1)
        pygame.draw.circle(SCREEN, (27, 41, 65), ARENA.center, 88, 2)
        pygame.draw.line(SCREEN, (27, 41, 65), (ARENA.centerx, ARENA.top + 12), (ARENA.centerx, ARENA.bottom - 12), 2)

        for mine in self.mines:
            mine.draw(SCREEN)
        for projectile in self.projectiles:
            projectile.draw(SCREEN)
        for particle in self.particles:
            particle.draw(SCREEN)
        self.player.draw(SCREEN)
        self.bot.draw(SCREEN)
        for floating in self.floating_texts:
            floating.draw(SCREEN)

        ability_name = ABILITIES[self.player.ability]["name"]
        if self.player.cooldown <= 0:
            cooldown_label = "ГОТОВО — SPACE"
            cooldown_color = GREEN
        else:
            cooldown_label = f"Перезарядка: {self.player.cooldown:.1f} сек"
            cooldown_color = MUTED
        draw_text(SCREEN, f"{ability_name}: {cooldown_label}", FONT, cooldown_color, (WIDTH // 2, 706))
        draw_text(SCREEN, "WASD / стрелки — толчок     SPACE — способность     P — пауза", SMALL, MUTED, (WIDTH // 2, 738))

        if self.pause:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 8, 18, 185))
            SCREEN.blit(overlay, (0, 0))
            draw_text(SCREEN, "ПАУЗА", BIG, WHITE, (WIDTH // 2, HEIGHT // 2 - 15))
            draw_text(SCREEN, "Нажми P, чтобы продолжить", FONT, MUTED, (WIDTH // 2, HEIGHT // 2 + 42))

    def draw_menu(self):
        draw_background(SCREEN)
        draw_text(SCREEN, "BALL ARENA", BIG, WHITE, (WIDTH // 2, 55))
        draw_text(SCREEN, "Выбери свой шарик и способность перед боем", FONT, MUTED, (WIDTH // 2, 105))

        left_panel = pygame.Rect(55, 145, 305, 480)
        right_panel = pygame.Rect(385, 145, 660, 480)
        draw_panel(SCREEN, left_panel)
        draw_panel(SCREEN, right_panel)

        draw_text(SCREEN, "ТВОЙ ШАРИК", MEDIUM, WHITE, (left_panel.centerx, 183))
        pygame.draw.circle(SCREEN, COLORS[self.selected_color], (left_panel.centerx, 260), 45)
        pygame.draw.circle(SCREEN, brighten(COLORS[self.selected_color], 55), (left_panel.centerx - 14, 245), 10)
        draw_text(SCREEN, COLOR_NAMES[self.selected_color], FONT, WHITE, (left_panel.centerx, 325))
        draw_text(SCREEN, "Выбери цвет:", SMALL, MUTED, (left_panel.centerx, 375))

        swatch_rects = []
        start_x = left_panel.x + 40
        start_y = 413
        for i, color in enumerate(COLORS):
            row, col = divmod(i, 4)
            cx = start_x + col * 70 + 24
            cy = start_y + row * 70
            rect = pygame.Rect(cx - 23, cy - 23, 46, 46)
            swatch_rects.append(rect)
            pygame.draw.circle(SCREEN, color, (cx, cy), 19)
            if i == self.selected_color:
                pygame.draw.circle(SCREEN, WHITE, (cx, cy), 25, 3)

        draw_text(SCREEN, "Соперник выберет цвет", SMALL, MUTED, (left_panel.centerx, 570))
        draw_text(SCREEN, "и способность случайно", SMALL, MUTED, (left_panel.centerx, 593))

        draw_text(SCREEN, "ВЫБЕРИ СПОСОБНОСТЬ", MEDIUM, WHITE, (right_panel.centerx, 183))
        ability_rects = {}
        card_w, card_h = 302, 91
        for i, key in enumerate(ABILITY_ORDER):
            row, col = divmod(i, 2)
            x = right_panel.x + 18 + col * 318
            y = 215 + row * 99
            rect = pygame.Rect(x, y, card_w, card_h)
            ability_rects[key] = rect
            selected = key == self.selected_ability
            fill = (47, 65, 99) if selected else (29, 39, 61)
            border = self.player_color_for_menu() if selected else (55, 70, 101)
            draw_panel(SCREEN, rect, fill, border, 13, 3 if selected else 1)
            draw_text_left(SCREEN, ABILITIES[key]["name"], SMALL, WHITE if selected else (210, 220, 239), (x + 14, y + 13))
            # Перенос длинных описаний на 2 строки.
            description = ABILITIES[key]["description"]
            words = description.split()
            lines, current = [], ""
            for word in words:
                test = (current + " " + word).strip()
                if SMALL.size(test)[0] > card_w - 28 and current:
                    lines.append(current)
                    current = word
                else:
                    current = test
            if current:
                lines.append(current)
            for j, line in enumerate(lines[:2]):
                draw_text_left(SCREEN, line, SMALL, MUTED, (x + 14, y + 42 + j * 19))

        start_button = pygame.Rect(WIDTH // 2 - 145, 660, 290, 58)
        pygame.draw.rect(SCREEN, (62, 190, 132), start_button, border_radius=18)
        pygame.draw.rect(SCREEN, (125, 245, 185), start_button, 2, border_radius=18)
        draw_text(SCREEN, "НАЧАТЬ БОЙ", MEDIUM, (8, 28, 25), start_button.center)

        self.menu_swatch_rects = swatch_rects
        self.menu_ability_rects = ability_rects
        self.menu_start_rect = start_button

    def player_color_for_menu(self):
        return COLORS[self.selected_color]

    def draw_result(self):
        draw_background(SCREEN)
        draw_text(SCREEN, "BALL ARENA", MEDIUM, MUTED, (WIDTH // 2, 92))
        draw_text(SCREEN, self.result, BIG, self.winner_color, (WIDTH // 2, 235))
        draw_text(SCREEN, f"Твоё здоровье: {int(self.player.hp)} / 100", FONT, WHITE, (WIDTH // 2, 310))
        draw_text(SCREEN, f"Здоровье бота: {int(self.bot.hp)} / 100", FONT, WHITE, (WIDTH // 2, 350))

        # Итоговая информация о выбранных способностях.
        pygame.draw.circle(SCREEN, self.player.color, (WIDTH // 2 - 150, 450), 30)
        pygame.draw.circle(SCREEN, self.bot.color, (WIDTH // 2 + 150, 450), 30)
        draw_text(SCREEN, ABILITIES[self.player.ability]["name"], SMALL, WHITE, (WIDTH // 2 - 150, 500))
        draw_text(SCREEN, ABILITIES[self.bot.ability]["name"], SMALL, WHITE, (WIDTH // 2 + 150, 500))

        again = pygame.Rect(WIDTH // 2 - 155, 565, 310, 58)
        menu = pygame.Rect(WIDTH // 2 - 155, 640, 310, 48)
        pygame.draw.rect(SCREEN, (62, 190, 132), again, border_radius=16)
        pygame.draw.rect(SCREEN, (125, 245, 185), again, 2, border_radius=16)
        draw_text(SCREEN, "ЕЩЁ ОДИН БОЙ", FONT, (8, 28, 25), again.center)
        pygame.draw.rect(SCREEN, PANEL_LIGHT, menu, border_radius=14)
        pygame.draw.rect(SCREEN, (75, 91, 125), menu, 2, border_radius=14)
        draw_text(SCREEN, "В МЕНЮ", FONT, WHITE, menu.center)
        self.result_again_rect = again
        self.result_menu_rect = menu

    def handle_menu_click(self, pos):
        for i, rect in enumerate(self.menu_swatch_rects):
            if rect.collidepoint(pos):
                self.selected_color = i
                return
        for key, rect in self.menu_ability_rects.items():
            if rect.collidepoint(pos):
                self.selected_ability = key
                return
        if self.menu_start_rect.collidepoint(pos):
            self.start_battle()

    def handle_result_click(self, pos):
        if self.result_again_rect.collidepoint(pos):
            self.start_battle()
        elif self.result_menu_rect.collidepoint(pos):
            self.state = "menu"

    def run(self):
        running = True
        while running:
            dt = min(CLOCK.tick(FPS) / 1000.0, 0.035)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        if event.key == pygame.K_RETURN:
                            self.start_battle()
                    elif self.state == "battle":
                        if event.key == pygame.K_p:
                            self.pause = not self.pause
                        elif event.key == pygame.K_SPACE and not self.pause:
                            self.player.use_ability(self.bot, self.projectiles, self.mines, self.particles, self.floating_texts)
                        elif not self.pause:
                            if event.key in (pygame.K_LEFT, pygame.K_a):
                                self.push_player(-1, 0)
                            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                                self.push_player(1, 0)
                            elif event.key in (pygame.K_UP, pygame.K_w):
                                self.push_player(0, -1)
                            elif event.key in (pygame.K_DOWN, pygame.K_s):
                                self.push_player(0, 1)
                    elif self.state == "result":
                        if event.key == pygame.K_RETURN:
                            self.start_battle()
                        elif event.key == pygame.K_m:
                            self.state = "menu"

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "menu":
                        self.handle_menu_click(event.pos)
                    elif self.state == "result":
                        self.handle_result_click(event.pos)

            self.update(dt)

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "battle":
                self.draw_battle()
            elif self.state == "result":
                self.draw_result()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
