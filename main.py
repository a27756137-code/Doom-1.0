import pygame
import math
import random

pygame.init()

# Настройка полноэкранного режима
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", int(HEIGHT * 0.035), bold=True)
big_font = pygame.font.SysFont("Arial", int(HEIGHT * 0.08), bold=True)

# Карта: 1 - красный кирпич, 2 - техно-стена, 3 - колонна с неоном, 0 - пол
MAP = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 1],
    [1, 0, 3, 3, 0, 0, 0, 0, 2, 2, 0, 1],
    [1, 0, 3, 0, 0, 1, 0, 0, 0, 2, 0, 1],
    [1, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 1],
    [1, 1, 0, 1, 2, 0, 0, 0, 3, 3, 0, 1],
    [1, 0, 0, 1, 0, 0, 3, 0, 0, 3, 0, 1],
    [1, 0, 2, 0, 0, 1, 1, 1, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]
TILE = 64
TEX_SIZE = 64

# Генерация процедурных текстур стен (без внешних картинок)
def create_textures():
    textures = {}
    
    # 1: Кровавый кирпич
    t1 = pygame.Surface((TEX_SIZE, TEX_SIZE))
    t1.fill((45, 20, 20)) # Раствор между кирпичами
    for row in range(4):
        y = row * 16
        offset = 16 if row % 2 == 1 else 0
        for col in range(-1, 3):
            x = col * 32 + offset
            shade = random.randint(130, 175)
            pygame.draw.rect(t1, (shade, int(shade * 0.25), int(shade * 0.2)), (x + 2, y + 2, 28, 12))
            pygame.draw.line(t1, (min(255, shade + 35), 50, 40), (x + 2, y + 2), (x + 29, y + 2))
    textures[1] = t1

    # 2: Металлическая обшивка
    t2 = pygame.Surface((TEX_SIZE, TEX_SIZE))
    t2.fill((70, 80, 95))
    pygame.draw.rect(t2, (40, 45, 55), (0, 0, TEX_SIZE, TEX_SIZE), 3)
    pygame.draw.line(t2, (50, 55, 65), (0, 32), (TEX_SIZE, 32), 3)
    for rx in [8, 56]:
        for ry in [8, 24, 40, 56]:
            pygame.draw.circle(t2, (130, 140, 155), (rx, ry), 2)
    textures[2] = t2

    # 3: Техно-стена с неоновым свечением
    t3 = t2.copy()
    pygame.draw.rect(t3, (20, 90, 40), (22, 6, 20, 52))
    pygame.draw.rect(t3, (50, 255, 100), (26, 10, 12, 44))
    textures[3] = t3

    return textures

TEXTURES = create_textures()

# Проверка коллизии с учетом радиуса (ИСПРАВЛЯЕТ ЗАСТРЕВАНИЕ В СТЕНАХ)
def can_move(x, y, radius):
    min_gx = int((x - radius) // TILE)
    max_gx = int((x + radius) // TILE)
    min_gy = int((y - radius) // TILE)
    max_gy = int((y + radius) // TILE)
    
    for gy in range(min_gy, max_gy + 1):
        for gx in range(min_gx, max_gx + 1):
            if 0 <= gy < len(MAP) and 0 <= gx < len(MAP[0]):
                if MAP[gy][gx] > 0:
                    return False
            else:
                return False
    return True

def reset_game():
    global px, py, p_angle, player_hp, enemies, particles, walk_timer, damage_flash
    px, py = 100.0, 100.0
    p_angle = 0.0
    player_hp = 100.0
    walk_timer = 0.0
    damage_flash = 0
    particles = []
    # Враги: [x, y, hp, hit_timer, anim_offset]
    enemies = [
        [300.0, 220.0, 100, 0, 0.0],
        [540.0, 160.0, 100, 0, 1.2],
        [420.0, 360.0, 100, 0, 2.5],
        [160.0, 480.0, 100, 0, 3.8],
        [600.0, 480.0, 100, 0, 5.1],
        [480.0, 280.0, 100, 0, 0.7]
    ]

reset_game()

# Настройки 3D камеры
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 160
DELTA_ANGLE = FOV / NUM_RAYS
SCALE = WIDTH // NUM_RAYS + 1
MAX_DEPTH = 800

# Элементы управления (Джойстик слева + кнопка огня справа)
joy_radius = int(min(WIDTH, HEIGHT) * 0.16)
joy_center = (int(joy_radius * 1.4), HEIGHT - int(joy_radius * 1.4))
btn_fire = pygame.Rect(WIDTH - int(joy_radius * 2.2), HEIGHT - int(joy_radius * 2.2), int(joy_radius * 1.8), int(joy_radius * 1.8))

shoot_anim = 0

# Быстрый алгоритм DDA для идеально ровных стен
def cast_ray(angle):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    if abs(cos_a) < 1e-6: cos_a = 1e-6
    if abs(sin_a) < 1e-6: sin_a = 1e-6

    # Горизонтальные пересечения
    y_hor = (int(py // TILE) * TILE + TILE) if sin_a > 0 else (int(py // TILE) * TILE - 0.0001)
    dy = TILE if sin_a > 0 else -TILE
    depth_hor = (y_hor - py) / sin_a
    x_hor = px + depth_hor * cos_a
    delta_depth = dy / sin_a
    dx = delta_depth * cos_a
    tex_hor = 1

    for _ in range(16):
        gx, gy = int(x_hor // TILE), int(y_hor // TILE)
        if 0 <= gy < len(MAP) and 0 <= gx < len(MAP[0]):
            if MAP[gy][gx] > 0:
                tex_hor = MAP[gy][gx]
                break
        else:
            break
        x_hor += dx
        y_hor += dy
        depth_hor += delta_depth

    # Вертикальные пересечения
    x_vert = (int(px // TILE) * TILE + TILE) if cos_a > 0 else (int(px // TILE) * TILE - 0.0001)
    dx = TILE if cos_a > 0 else -TILE
    depth_vert = (x_vert - px) / cos_a
    y_vert = py + depth_vert * sin_a
    delta_depth = dx / cos_a
    dy = delta_depth * sin_a
    tex_vert = 1

    for _ in range(16):
        gx, gy = int(x_vert // TILE), int(y_vert // TILE)
        if 0 <= gy < len(MAP) and 0 <= gx < len(MAP[0]):
            if MAP[gy][gx] > 0:
                tex_vert = MAP[gy][gx]
                break
        else:
            break
        x_vert += dx
        y_vert += dy
        depth_vert += delta_depth

    if depth_vert < depth_hor:
        return depth_vert, int(y_vert % TILE), tex_vert, True
    else:
        return depth_hor, int(x_hor % TILE), tex_hor, False

def draw_background():
    bands = 28
    h_step = (HEIGHT // 2) // bands + 1
    for i in range(bands):
        c_sky = max(8, 55 - i * 2)
        pygame.draw.rect(screen, (c_sky, 10, 18), (0, i * h_step, WIDTH, h_step))
        c_flr = min(75, 12 + i * 2)
        pygame.draw.rect(screen, (c_flr, c_flr - 2, c_flr + 4), (0, HEIGHT // 2 + i * h_step, WIDTH, h_step))

running = True
while running:
    clock.tick(30)
    fire_pressed = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if player_hp <= 0 or all(e[2] <= 0 for e in enemies):
                reset_game()
            elif btn_fire.collidepoint(event.pos) and shoot_anim == 0:
                fire_pressed = True
                shoot_anim = 7

    # Сенсорный джойстик
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mx, my = pygame.mouse.get_pos()
    moving = False
    joy_pos = joy_center

    if mouse_pressed and player_hp > 0:
        dist_joy = math.hypot(mx - joy_center[0], my - joy_center[1])
        if dist_joy < joy_radius * 2.0 and not btn_fire.collidepoint(mx, my):
            dx_j = (mx - joy_center[0]) / joy_radius
            dy_j = (my - joy_center[1]) / joy_radius
            if dist_joy > joy_radius:
                dx_j *= joy_radius / dist_joy
                dy_j *= joy_radius / dist_joy
            joy_pos = (int(joy_center[0] + dx_j * joy_radius), int(joy_center[1] + dy_j * joy_radius))

            # Поворот и движение с плавным скольжением вдоль стен
            p_angle += dx_j * 0.075
            speed = -dy_j * 5.5
            if abs(speed) > 0.4:
                nx = px + math.cos(p_angle) * speed
                ny = py + math.sin(p_angle) * speed
                p_rad = 16 # Радиус игрока
                if can_move(nx, py, p_rad): px = nx
                if can_move(px, ny, p_rad): py = ny
                moving = True

    walk_timer = (walk_timer + 0.35) if moving else 0.0

    # 1. Отрисовка неба и пола
    draw_background()

    # 2. Отрисовка 3D стен с текстурами
    z_buffer = [MAX_DEPTH] * NUM_RAYS
    cur_angle = p_angle - HALF_FOV
    strip_w = WIDTH // NUM_RAYS

    for ray in range(NUM_RAYS):
        depth, offset, tex_id, is_vert = cast_ray(cur_angle)
        depth *= math.cos(p_angle - cur_angle)
        z_buffer[ray] = depth

        proj_h = min(int((TILE * HEIGHT * 0.85) / (depth + 0.0001)), int(HEIGHT * 1.4))
        tex = TEXTURES.get(tex_id, TEXTURES[1])
        column = tex.subsurface((offset, 0, 1, TEX_SIZE))
        column = pygame.transform.scale(column, (SCALE, proj_h))

        # Затенение дальних и боковых стен для объема
        shade = max(35, min(255, int(255 - depth * 0.35)))
        if is_vert:
            shade = int(shade * 0.8)
        if shade < 245:
            column.fill((shade, shade, shade), special_flags=pygame.BLEND_RGB_MULT)

        screen.blit(column, (ray * strip_w, HEIGHT // 2 - proj_h // 2))
        cur_angle += DELTA_ANGLE

    # 3. Физика и отрисовка демонов (БЕЗ ЗАСТРЕВАНИЯ В СТЕНАХ)
    enemies.sort(key=lambda e: (e[0] - px) ** 2 + (e[1] - py) ** 2, reverse=True)
    e_rad = 18 # Физический радиус моба

    for i, enemy in enumerate(enemies):
        if enemy[2] <= 0:
            continue
        ex, ey, hp, hit_t, anim_o = enemy
        if hit_t > 0:
            enemy[3] -= 1
        enemy[4] += 0.15

        dist = math.hypot(ex - px, ey - py)

        # Движение к игроку + отталкивание от других демонов и стен
        if 38 < dist < 420 and player_hp > 0:
            vx = (px - ex) / dist * 1.8
            vy = (py - ey) / dist * 1.8

            for j, other in enumerate(enemies):
                if i != j and other[2] > 0:
                    od = math.hypot(ex - other[0], ey - other[1])
                    if 0 < od < e_rad * 2.2:
                        vx += (ex - other[0]) / od * 1.2
                        vy += (ey - other[1]) / od * 1.2

            # Независимая проверка осей X и Y заставляет моба скользить вдоль стены
            if can_move(ex + vx, ey, e_rad):
                enemy[0] += vx
            if can_move(enemy[0], ey + vy, e_rad):
                enemy[1] += vy
        elif dist <= 42 and player_hp > 0:
            player_hp -= 0.6
            damage_flash = 5

        dx, dy = enemy[0] - px, enemy[1] - py
        e_angle = math.atan2(dy, dx) - p_angle
        while e_angle > math.pi: e_angle -= 2 * math.pi
        while e_angle < -math.pi: e_angle += 2 * math.pi

        if -HALF_FOV < e_angle < HALF_FOV and dist > 22:
            s_size = min(int((TILE * HEIGHT * 0.68) / dist), HEIGHT)
            sx = int((e_angle + HALF_FOV) / FOV * WIDTH) - s_size // 2
            bounce = int(math.sin(enemy[4]) * (s_size * 0.04))
            sy = HEIGHT // 2 - s_size // 2 + int(s_size * 0.08) + bounce

            c_ray = int((sx + s_size // 2) / strip_w)
            if 0 <= c_ray < NUM_RAYS and dist < z_buffer[c_ray]:
                # Тень
                pygame.draw.ellipse(screen, (10, 10, 12), (sx + s_size // 6, sy + s_size - s_size // 7 - bounce, int(s_size * 0.68), s_size // 5))
                
                # Туловище и броня монстра
                is_hit = enemy[3] > 0
                c_dark = (255, 255, 255) if is_hit else (130, 20, 25)
                c_main = (255, 255, 255) if is_hit else (195, 40, 40)
                
                pygame.draw.ellipse(screen, c_dark, (sx, sy, s_size, int(s_size * 0.92)))
                pygame.draw.ellipse(screen, c_main, (sx + s_size // 10, sy + s_size // 12, int(s_size * 0.8), int(s_size * 0.75)))

                # Изогнутые рога
                pygame.draw.polygon(screen, (220, 200, 175), [(sx + s_size // 5, sy + s_size // 6), (sx - s_size // 10, sy - s_size // 4), (sx + s_size // 3, sy + s_size // 10)])
                pygame.draw.polygon(screen, (220, 200, 175), [(sx + s_size - s_size // 5, sy + s_size // 6), (sx + s_size + s_size // 10, sy - s_size // 4), (sx + s_size - s_size // 3, sy + s_size // 10)])

                # Горящие глаза и пасть с клыками
                ew = max(4, s_size // 6)
                pygame.draw.polygon(screen, (255, 240, 0), [(sx + s_size // 4, sy + s_size // 3), (sx + s_size // 4 + ew, sy + s_size // 3 + ew // 2), (sx + s_size // 4, sy + s_size // 3 + ew)])
                pygame.draw.polygon(screen, (255, 240, 0), [(sx + s_size - s_size // 4, sy + s_size // 3), (sx + s_size - s_size // 4 - ew, sy + s_size // 3 + ew // 2), (sx + s_size - s_size // 4, sy + s_size // 3 + ew)])

                mx_mouth, my_mouth = sx + s_size // 4, sy + int(s_size * 0.58)
                mw, mh = s_size // 2, s_size // 5
                pygame.draw.rect(screen, (45, 5, 10), (mx_mouth, my_mouth, mw, mh), border_radius=4)
                for t in range(3):
                    tx_tooth = mx_mouth + (t + 1) * (mw // 4)
                    pygame.draw.polygon(screen, (240, 240, 220), [(tx_tooth - 3, my_mouth), (tx_tooth + 3, my_mouth), (tx_tooth, my_mouth + mh // 2)])

                # Полоска здоровья
                hp_w = int((s_size * 0.8) * (hp / 100))
                pygame.draw.rect(screen, (40, 0, 0), (sx + s_size // 10, sy - 14, int(s_size * 0.8), 7))
                pygame.draw.rect(screen, (40, 240, 60), (sx + s_size // 10, sy - 14, hp_w, 7))

                # Выстрел и разлет частиц крови/искр
                if fire_pressed and abs(e_angle) < 0.17 and dist < 480:
                    enemy[2] -= 50
                    enemy[3] = 4
                    for _ in range(15):
                        particles.append([
                            sx + s_size // 2, sy + s_size // 2,
                            random.uniform(-9, 9), random.uniform(-9, 4),
                            random.randint(10, 18), (230, random.randint(10, 60), 20)
                        ])

    # 4. Частицы крови и искр
    for p in particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[3] += 0.6 # Гравитация
        p[4] -= 1
        pygame.draw.circle(screen, p[5], (int(p[0]), int(p[1])), max(2, p[4] // 2))
        if p[4] <= 0:
            particles.remove(p)

    # 5. Двустволка с отдачей
    bob_x = int(math.cos(walk_timer) * 14)
    bob_y = int(abs(math.sin(walk_timer)) * 12)
    recoil = shoot_anim * 11
    gx = WIDTH // 2 + bob_x
    gy = HEIGHT - int(HEIGHT * 0.25) + bob_y + recoil

    if shoot_anim > 4:
        pygame.draw.polygon(screen, (255, 150, 20), [(gx - 60, gy - 10), (gx, gy - 100), (gx + 60, gy - 10), (gx + 90, gy + 20), (gx - 90, gy + 20)])
        pygame.draw.circle(screen, (255, 255, 200), (gx, gy - 25), 35)
    if shoot_anim > 0:
        shoot_anim -= 1

    bw, bh = int(WIDTH * 0.045), int(HEIGHT * 0.26)
    pygame.draw.rect(screen, (45, 50, 58), (gx - bw - 2, gy, bw, bh), border_radius=6)
    pygame.draw.rect(screen, (45, 50, 58), (gx + 2, gy, bw, bh), border_radius=6)
    pygame.draw.rect(screen, (110, 120, 135), (gx - bw + 5, gy + 6, 6, bh - 12))
    pygame.draw.rect(screen, (110, 120, 135), (gx + 9, gy + 6, 6, bh - 12))
    pygame.draw.rect(screen, (105, 50, 20), (gx - bw - 8, gy + int(bh * 0.55), bw * 2 + 16, bh), border_radius=8)

    # Прицел
    pygame.draw.circle(screen, (50, 255, 120), (WIDTH // 2, HEIGHT // 2), 10, 2)
    pygame.draw.circle(screen, (50, 255, 120), (WIDTH // 2, HEIGHT // 2), 2)

    # 6. Мини-карта
    mm_s = max(8, int(min(WIDTH, HEIGHT) * 0.022))
    for r_i, row in enumerate(MAP):
        for c_i, val in enumerate(row):
            col = (130, 55, 55) if val > 0 else (25, 25, 30)
            pygame.draw.rect(screen, col, (15 + c_i * mm_s, 15 + r_i * mm_s, mm_s - 1, mm_s - 1))
    pygame.draw.circle(screen, (0, 255, 80), (15 + int(px / TILE * mm_s), 15 + int(py / TILE * mm_s)), 3)
    for e in enemies:
        if e[2] > 0:
            pygame.draw.circle(screen, (255, 40, 40), (15 + int(e[0] / TILE * mm_s), 15 + int(e[1] / TILE * mm_s)), 3)

    # 7. Интерфейс: Джойстик, кнопка выстрела и статистика
    pygame.draw.circle(screen, (50, 55, 65), joy_center, joy_radius)
    pygame.draw.circle(screen, (160, 170, 185), joy_center, joy_radius, 3)
    pygame.draw.circle(screen, (210, 220, 235), joy_pos, int(joy_radius * 0.42))

    pygame.draw.rect(screen, (190, 30, 35), btn_fire, border_radius=50)
    pygame.draw.rect(screen, (255, 130, 130), btn_fire, 4, border_radius=50)
    f_txt = font.render("FIRE", True, (255, 255, 255))
    screen.blit(f_txt, (btn_fire.centerx - f_txt.get_width() // 2, btn_fire.centery - f_txt.get_height() // 2))

    hp_txt = font.render(f"HP: {int(max(0, player_hp))}%", True, (255, 80, 80))
    alive_cnt = sum(1 for e in enemies if e[2] > 0)
    en_txt = font.render(f"ДЕМОНЫ: {alive_cnt}", True, (255, 215, 60))
    screen.blit(hp_txt, (WIDTH - hp_txt.get_width() - 25, 20))
    screen.blit(en_txt, (WIDTH - en_txt.get_width() - 25, 25 + hp_txt.get_height()))

    if damage_flash > 0:
        pygame.draw.rect(screen, (255, 20, 20), (0, 0, WIDTH, HEIGHT), 14)
        damage_flash -= 1

    if player_hp <= 0:
        msg = big_font.render("ТЫ ПОГИБ! (Нажми на экран)", True, (255, 50, 50))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 40))
    elif alive_cnt == 0:
        msg = big_font.render("ПОБЕДА! (Нажми на экран)", True, (60, 255, 90))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 40))

    pygame.display.flip()

pygame.quit()
