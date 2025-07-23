import sys
import os
import numpy as np
import random
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QGridLayout, QLabel, QSpinBox, QDialog, QFormLayout, QSpacerItem, QSizePolicy, QMessageBox
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QIcon
from player_snake import PlayerSnake

GRID_SIZE = 80
GAME_AREA_SIZE = 400  # px, area game tetap

class Egg:
    def __init__(self, x, y, hatch_cycle, is_food=False, is_player=False):
        self.x = x
        self.y = y
        self.hatch_cycle = hatch_cycle
        self.is_food = is_food
        self.is_player = is_player

class Snake:
    def __init__(self, body, direction, born_cycle, hungry=False, turn_interval=30, tangled_die_cycles=30, food_attract_radius=5, egg_attract_radius=5, shading_interval=300):
        self.body = body
        self.direction = direction
        self.born_cycle = born_cycle
        self.last_lay = born_cycle
        self.steps_since_dir_change = 0
        self.turn_interval = turn_interval
        self.hungry = hungry
        self.ate = False
        self.tangled_cycles = 0
        self.tangled_die_cycles = tangled_die_cycles
        self.food_attract_radius = food_attract_radius
        self.egg_attract_radius = egg_attract_radius
        self.last_head = self.head()
        self.shading_interval = shading_interval
        self.last_shading = born_cycle

    def head(self):
        return self.body[0]

    def move(self, food_positions, egg_positions):
        self.steps_since_dir_change += 1
        head_x, head_y = self.head()
        nearest_food = None
        min_food_dist = None
        for fx, fy in food_positions:
            dist = abs(head_x - fx) + abs(head_y - fy)
            if dist <= self.food_attract_radius:
                if min_food_dist is None or dist < min_food_dist:
                    min_food_dist = dist
                    nearest_food = (fx, fy)
        nearest_egg = None
        min_egg_dist = None
        for ex, ey in egg_positions:
            dist = abs(head_x - ex) + abs(head_y - ey)
            if dist <= self.egg_attract_radius:
                if min_egg_dist is None or dist < min_egg_dist:
                    min_egg_dist = dist
                    nearest_egg = (ex, ey)
        moved = False
        target = None
        if nearest_food:
            target = nearest_food
        elif nearest_egg:
            target = nearest_egg
        if target:
            dx = np.sign(target[0] - head_x)
            dy = np.sign(target[1] - head_y)
            preferred_dirs = []
            if dx != 0:
                preferred_dirs.append((dx, 0))
            if dy != 0:
                preferred_dirs.append((0, dy))
            if dx != 0 and dy != 0:
                preferred_dirs.append((dx, dy))
            possible_dirs = preferred_dirs + [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)]
            for ddx, ddy in possible_dirs:
                new_head = (head_x + ddx, head_y + ddy)
                if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                    self.direction = (ddx, ddy)
                    self.body = [new_head] + self.body[:-1]
                    self.steps_since_dir_change = 0
                    moved = True
                    break
        if not moved:
            if self.steps_since_dir_change >= self.turn_interval:
                possible_dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(1,-1),(-1,1)]
                random.shuffle(possible_dirs)
                for dx, dy in possible_dirs:
                    new_head = (head_x + dx, head_y + dy)
                    if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                        self.direction = (dx, dy)
                        self.steps_since_dir_change = 0
                        self.body = [new_head] + self.body[:-1]
                        moved = True
                        break
                if not moved:
                    self.bounce()
                    dx, dy = self.direction
                    new_head = (head_x + dx, head_y + dy)
                    if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                        self.body = [new_head] + self.body[:-1]
                        self.steps_since_dir_change = 0
                        moved = True
            if not moved:
                dx, dy = self.direction
                new_head = (head_x + dx, head_y + dy)
                if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                    self.body = [new_head] + self.body[:-1]
                    moved = True
                else:
                    self.bounce()
                    dx, dy = self.direction
                    new_head = (head_x + dx, head_y + dy)
                    if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                        self.body = [new_head] + self.body[:-1]
                        moved = True
        if self.head() == self.last_head:
            self.tangled_cycles += 1
        else:
            self.tangled_cycles = 0
        self.last_head = self.head()

    def grow_by(self, extra_body_len):
        dx, dy = self.direction
        for _ in range(extra_body_len):
            possible_dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(1,-1),(-1,1)]
            random.shuffle(possible_dirs)
            for ddx, ddy in possible_dirs:
                new_head = (self.body[0][0] + ddx, self.body[0][1] + ddy)
                if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                    self.direction = (ddx, ddy)
                    self.body = [new_head] + self.body
                    break
            else:
                self.bounce()
                dx, dy = self.direction
                new_head = (self.body[0][0] + dx, self.body[0][1] + dy)
                if 0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE and new_head not in self.body:
                    self.body = [new_head] + self.body

    def bounce(self):
        if not self.body:
            return
        dx, dy = self.direction
        x, y = self.body[0]
        if x <= 0 or x >= GRID_SIZE-1:
            dx = -dx
        if y <= 0 or y >= GRID_SIZE-1:
            dy = -dy
        self.direction = (dx, dy)

    def shade_skin(self, current_cycle, eggs):
        if self.shading_interval <= 0 or len(self.body) < 2:
            return
        if current_cycle - self.last_shading >= self.shading_interval:
            tail = self.body[-1]
            eggs.append(Egg(tail[0], tail[1], 0, is_food=True))
            self.last_shading = current_cycle

class Game:
    def __init__(self):
        self.reset()
        self.hatch_cycles = 30
        self.lay_interval = 120
        self.hungry_die_cycles = 300
        self.turn_interval = 30
        self.tangled_die_cycles = 30
        self.food_attract_radius = 5
        self.egg_attract_radius = 5
        self.cell_size = GAME_AREA_SIZE // GRID_SIZE
        self.shading_interval = 300
        self.max_snake_length = 0
        self.total_eggs = 0
        self.total_food = 0
        self.stats_head = 0
        self.stats_body = 0
        self.stats_egg = 0
        self.stats_food_legend = 0
        self.stats_player_body = 0
        self.stats_player_head = 0
        self.player_alive = True
        self.player_max_length = 0
        self.player_survive_cycles = 0

    def reset(self):
        self.cycle = 0
        self.eggs = []
        self.snakes = []
        self.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.uint8)
        self.stats_snakes = 0
        self.stats_eggs = 0
        self.max_snake_length = 0
        self.total_eggs = 0
        self.total_food = 0
        self.stats_head = 0
        self.stats_body = 0
        self.stats_egg = 0
        self.stats_food_legend = 0
        self.stats_player_body = 0
        self.stats_player_head = 0
        self.player_alive = True
        self.player_max_length = 0
        self.player_survive_cycles = 0

    def add_egg(self, x, y, is_player=False):
        for egg in self.eggs:
            if egg.x == x and egg.y == y:
                if not egg.is_food:
                    egg.is_food = True
                return
        self.eggs.append(Egg(x, y, self.cycle + self.hatch_cycles, is_player=is_player))
        self.grid[x, y] = 2 if not is_player else 5
        self.total_eggs += 1

    def add_food(self, x, y):
        for egg in self.eggs:
            if egg.x == x and egg.y == y:
                egg.is_food = True
                return
        self.eggs.append(Egg(x, y, 0, is_food=True))
        self.grid[x, y] = 4
        self.total_food += 1

    def add_snake(self, body, direction, hungry=False, is_player=False):
        valid_body = [(x, y) for x, y in body if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE]
        if len(valid_body) >= 3:
            if is_player:
                snake = PlayerSnake(valid_body, direction, self.cycle, hungry=hungry, turn_interval=self.turn_interval, tangled_die_cycles=self.tangled_die_cycles, food_attract_radius=self.food_attract_radius, egg_attract_radius=self.egg_attract_radius, shading_interval=self.shading_interval)
            else:
                snake = Snake(valid_body, direction, self.cycle, hungry=hungry, turn_interval=self.turn_interval, tangled_die_cycles=self.tangled_die_cycles, food_attract_radius=self.food_attract_radius, egg_attract_radius=self.egg_attract_radius, shading_interval=self.shading_interval)
            self.snakes.append(snake)
            for x, y in valid_body:
                self.grid[x, y] = 1
            if len(valid_body) > self.max_snake_length:
                self.max_snake_length = len(valid_body)

    def update(self):
        self.cycle += 1
        self.grid[:] = 0
        new_snakes = []
        remaining_eggs = []
        for egg in self.eggs:
            if egg.is_food:
                remaining_eggs.append(egg)
                continue
            if self.cycle >= egg.hatch_cycle:
                dir = random.choice([(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)])
                body = [(egg.x, egg.y)]
                for i in range(1,3):
                    nx, ny = egg.x + dir[0]*i, egg.y + dir[1]*i
                    if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                        body.append((nx, ny))
                if len(body) == 3:
                    if egg.is_player:
                        new_snake = PlayerSnake(body, dir, self.cycle, hungry=True, turn_interval=self.turn_interval, tangled_die_cycles=self.tangled_die_cycles, food_attract_radius=self.food_attract_radius, egg_attract_radius=self.egg_attract_radius, shading_interval=self.shading_interval)
                    else:
                        new_snake = Snake(body, dir, self.cycle, hungry=True, turn_interval=self.turn_interval, tangled_die_cycles=self.tangled_die_cycles, food_attract_radius=self.food_attract_radius, egg_attract_radius=self.egg_attract_radius, shading_interval=self.shading_interval)
                    new_snakes.append(new_snake)
                    if len(body) > self.max_snake_length:
                        self.max_snake_length = len(body)
            else:
                remaining_eggs.append(egg)
        self.eggs = remaining_eggs
        self.snakes += new_snakes

        eggs_to_add = []
        eaten_positions = set()
        food_positions = [(egg.x, egg.y) for egg in self.eggs if egg.is_food]
        egg_positions = [(egg.x, egg.y) for egg in self.eggs if not egg.is_food]
        player_snake = None
        for snake in self.snakes:
            if isinstance(snake, PlayerSnake):
                player_snake = snake
                break
        for snake in self.snakes:
            if len(snake.body) >= 3:
                snake.turn_interval = self.turn_interval
                snake.tangled_die_cycles = self.tangled_die_cycles
                snake.food_attract_radius = self.food_attract_radius
                snake.egg_attract_radius = self.egg_attract_radius
                snake.shading_interval = self.shading_interval
                snake.bounce()
                if isinstance(snake, PlayerSnake):
                    snake.move(food_positions, egg_positions, self.player_direction)
                else:
                    snake.move(food_positions, egg_positions)
                snake.shade_skin(self.cycle, eggs_to_add)
                if len(snake.body) > self.max_snake_length:
                    self.max_snake_length = len(snake.body)
        self.snakes = [snake for snake in self.snakes if len(snake.body) >= 3]
        head_positions = {}
        for idx, snake in enumerate(self.snakes):
            if snake.body:
                pos = snake.head()
                if pos in head_positions:
                    head_positions[pos].append(idx)
                else:
                    head_positions[pos] = [idx]
        eaten_snakes = set()
        player_eaten = False
        for pos, idxs in head_positions.items():
            if len(idxs) > 1:
                eater = random.choice(idxs)
                for idx in idxs:
                    if idx != eater and self.snakes[idx].body:
                        # Check if player snake is eaten
                        if isinstance(self.snakes[idx], PlayerSnake):
                            player_eaten = True
                            self.player_alive = False
                            self.player_survive_cycles = self.cycle - self.snakes[idx].born_cycle
                            self.player_max_length = max(self.player_max_length, len(self.snakes[idx].body))
                        self.snakes[eater].grow_by(len(self.snakes[idx].body))
                        self.snakes[eater].ate = True
                        self.snakes[idx].body = []
                        eaten_snakes.add(idx)
        for snake in self.snakes:
            if not snake.body:
                continue
            for egg in self.eggs:
                if (egg.x, egg.y) == snake.head() and not egg.is_food:
                    snake.grow_by(1)
                    snake.ate = True
                    eaten_positions.add((egg.x, egg.y))
                if (egg.x, egg.y) == snake.head() and egg.is_food:
                    snake.grow_by(1)
                    snake.ate = True
                    egg.is_food = False
                    eaten_positions.add((egg.x, egg.y))
                    self.total_food += 1
        snakes_to_remove = set()
        for i, snake in enumerate(self.snakes):
            if not snake.body:
                continue
            for j, other in enumerate(self.snakes):
                if i == j or not other.body:
                    continue
                if snake.head() in other.body:
                    eaten_length = len(other.body)
                    # Check if player snake is eaten
                    if isinstance(other, PlayerSnake):
                        player_eaten = True
                        self.player_alive = False
                        self.player_survive_cycles = self.cycle - other.born_cycle
                        self.player_max_length = max(self.player_max_length, len(other.body))
                    snake.grow_by(eaten_length)
                    snake.ate = True
                    other.body = []
                    snakes_to_remove.add(j)
        self.snakes = [snake for idx, snake in enumerate(self.snakes) if len(snake.body) >= 3 and idx not in snakes_to_remove and snake.tangled_cycles <= snake.tangled_die_cycles]
        self.snakes = [snake for snake in self.snakes if not (snake.hungry and not snake.ate and self.cycle - snake.born_cycle > self.hungry_die_cycles)]
        self.snakes = [snake for snake in self.snakes if not (isinstance(snake, PlayerSnake) and snake.hungry and not snake.ate and self.cycle - snake.born_cycle > self.hungry_die_cycles)]
        for snake in self.snakes:
            if snake.hungry and snake.ate:
                snake.hungry = False
            snake.ate = False
        for snake in self.snakes:
            if not snake.body:
                continue
            if not isinstance(snake, PlayerSnake):
                if len(snake.body) > 3 and self.cycle - snake.last_lay >= self.lay_interval:
                    tail = snake.body[-1]
                    if 0 <= tail[0] < GRID_SIZE and 0 <= tail[1] < GRID_SIZE:
                        eggs_to_add.append(Egg(tail[0], tail[1], self.cycle + self.hatch_cycles, is_player=False))
                        self.total_eggs += 1
                    snake.last_lay = self.cycle
        self.eggs = [egg for egg in self.eggs if (egg.x, egg.y) not in eaten_positions]
        self.eggs += eggs_to_add
        for egg in self.eggs:
            if 0 <= egg.x < GRID_SIZE and 0 <= egg.y < GRID_SIZE:
                if egg.is_food:
                    self.grid[egg.x, egg.y] = 4
                elif egg.is_player:
                    self.grid[egg.x, egg.y] = 5
                else:
                    self.grid[egg.x, egg.y] = 2
        for snake in self.snakes:
            for idx, (x, y) in enumerate(snake.body):
                if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
                    if isinstance(snake, PlayerSnake):
                        if idx == 0:
                            self.grid[x, y] = 6  # kepala oranye
                        else:
                            self.grid[x, y] = 5  # badan biru
                    else:
                        if idx == 0:
                            self.grid[x, y] = 3
                        else:
                            self.grid[x, y] = 1
        self.stats_snakes = len(self.snakes)
        self.stats_eggs = len([egg for egg in self.eggs if not egg.is_food])
        self.stats_food = len([egg for egg in self.eggs if egg.is_food])
        self.stats_head = int(np.count_nonzero(self.grid == 3)) + int(np.count_nonzero(self.grid == 6))
        self.stats_body = int(np.count_nonzero(self.grid == 1)) + int(np.count_nonzero(self.grid == 5))
        self.stats_egg = int(np.count_nonzero(self.grid == 2))
        self.stats_food_legend = int(np.count_nonzero(self.grid == 4))
        self.stats_player_body = int(np.count_nonzero(self.grid == 5))
        self.stats_player_head = int(np.count_nonzero(self.grid == 6))
        # Track player snake stats
        if player_snake and len(player_snake.body) > self.player_max_length:
            self.player_max_length = len(player_snake.body)
        if player_snake and self.player_alive:
            self.player_survive_cycles = self.cycle - player_snake.born_cycle
        self.player_eaten = player_eaten

class GameWidget(QWidget):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.setFixedSize(GAME_AREA_SIZE, GAME_AREA_SIZE)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        cell_size = GAME_AREA_SIZE // GRID_SIZE
        self.game.cell_size = cell_size
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                val = self.game.grid[x, y]
                if val == 1:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(51,204,51))
                elif val == 2:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(255,255,0))
                elif val == 3:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(255,0,0))
                elif val == 4:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(128,128,128))
                elif val == 5:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(0,0,255))
                elif val == 6:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, QColor(255,128,0))
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, GAME_AREA_SIZE - 1, GAME_AREA_SIZE - 1)

    def mousePressEvent(self, event):
        cell_size = GAME_AREA_SIZE // GRID_SIZE
        x = int(event.position().x() // cell_size)
        y = int(event.position().y() // cell_size)
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            if event.button() == Qt.LeftButton:
                found = False
                for egg in self.game.eggs:
                    if egg.x == x and egg.y == y:
                        if not egg.is_food:
                            egg.is_food = True
                        found = True
                        break
                if not found:
                    self.game.add_egg(x, y)
            elif event.button() == Qt.RightButton:
                self.game.add_food(x, y)
            self.update()

class SettingsDialog(QDialog):
    def __init__(self, parent, game):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.game = game
        self.layout = QFormLayout(self)
        self.spin_hatch = QSpinBox()
        self.spin_hatch.setRange(1, 999)
        self.spin_hatch.setValue(game.hatch_cycles)
        self.spin_lay = QSpinBox()
        self.spin_lay.setRange(1, 999)
        self.spin_lay.setValue(game.lay_interval)
        self.spin_hungry = QSpinBox()
        self.spin_hungry.setRange(1, 999)
        self.spin_hungry.setValue(game.hungry_die_cycles)
        self.spin_turn = QSpinBox()
        self.spin_turn.setRange(1, 999)
        self.spin_turn.setValue(game.turn_interval)
        self.spin_tangled = QSpinBox()
        self.spin_tangled.setRange(1, 999)
        self.spin_tangled.setValue(game.tangled_die_cycles)
        self.spin_food_radius = QSpinBox()
        self.spin_food_radius.setRange(1, 30)
        self.spin_food_radius.setValue(game.food_attract_radius)
        self.spin_egg_radius = QSpinBox()
        self.spin_egg_radius.setRange(1, 30)
        self.spin_egg_radius.setValue(game.egg_attract_radius)
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(10, 2000)
        self.spin_speed.setValue(parent.spin_speed.value())
        self.spin_speed.setSuffix(" ms")
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 200)
        self.spin_grid_size.setValue(GRID_SIZE)
        self.spin_shading = QSpinBox()
        self.spin_shading.setRange(1, 9999)
        self.spin_shading.setValue(game.shading_interval)
        self.layout.addRow("Egg hatch cycles", self.spin_hatch)
        self.layout.addRow("Egg lay interval", self.spin_lay)
        self.layout.addRow("Hungry dies after cycles", self.spin_hungry)
        self.layout.addRow("Snake turn interval", self.spin_turn)
        self.layout.addRow("Tangled dies after cycles", self.spin_tangled)
        self.layout.addRow("Food attract radius", self.spin_food_radius)
        self.layout.addRow("Egg attract radius", self.spin_egg_radius)
        self.layout.addRow("Cycle speed", self.spin_speed)
        self.layout.addRow("Grid size", self.spin_grid_size)
        self.layout.addRow("Snake shading interval", self.spin_shading)
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        self.layout.addRow(btn_ok)

    def apply_settings(self):
        self.game.hatch_cycles = self.spin_hatch.value()
        self.game.lay_interval = self.spin_lay.value()
        self.game.hungry_die_cycles = self.spin_hungry.value()
        self.game.turn_interval = self.spin_turn.value()
        self.game.tangled_die_cycles = self.spin_tangled.value()
        self.game.food_attract_radius = self.spin_food_radius.value()
        self.game.egg_attract_radius = self.spin_egg_radius.value()
        global GRID_SIZE
        GRID_SIZE = self.spin_grid_size.value()
        self.game.cell_size = GAME_AREA_SIZE // GRID_SIZE
        self.game.shading_interval = self.spin_shading.value()
        self.game.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.uint8)

class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Guide")
        layout = QVBoxLayout(self)
        guide_text = (
            "Game of Snakes - Mechanics & Tips\n\n"
            "1. Click on the grid to place an egg (yellow).\n"
            "2. Click again on an egg to turn it into food (grey). Snakes can eat food to grow.\n"
            "3. Right-click on the grid to add food directly (grey).\n"
            "4. Click 'Player' to spawn a player egg (blue) at a random location. Player snake can be controlled with ASWD keys. Only one player snake allowed.\n"
            "5. Eggs hatch into snakes of length 3 after 'Egg hatch cycles'.\n"
            "6. Snakes of length 3 cannot lay eggs. Only longer snakes can lay eggs every 'Egg lay interval'.\n"
            "7. If all snakes die and only eggs/food remain, the game ends.\n"
            "8. Hungry snakes must eat within 'Hungry dies after cycles' or they die. This also applies to player snake.\n"
            "9. Snakes change direction every 'Snake turn interval' cycles.\n"
            "10. If a snake's head does not move for more than 'Tangled dies after cycles', it dies.\n"
            "11. Snakes bounce off walls and can eat eggs, food, or other snakes to grow.\n"
            "12. Tips: Place eggs strategically, avoid tangling, and keep snakes fed to survive!"
        )
        label = QLabel(guide_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game of Snakes")
        self.game = Game()
        self.widget = GameWidget(self.game)
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
        self.running = False
        self.player_direction = None

        self.label_cycle = QLabel("Cycle: 0")
        self.label_time = QLabel("Time: 00:00:00")
        self.label_snakes = QLabel("Snakes: 0")
        self.label_eggs = QLabel("Eggs: 0")
        self.label_food = QLabel("Food: 0")

        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(10, 2000)
        self.spin_speed.setValue(50)
        self.spin_speed.setSuffix(" ms")
        self.spin_speed.valueChanged.connect(self.update_speed)

        btn_start = QPushButton("Start/Stop")
        btn_start.clicked.connect(self.toggle)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_game)
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self.show_settings)
        btn_guide = QPushButton("Guide")
        btn_guide.clicked.connect(self.show_guide)
        btn_player = QPushButton("Player")
        btn_player.clicked.connect(self.spawn_player_egg)

        top_layout = QHBoxLayout()
        top_layout.addWidget(btn_start)
        top_layout.addWidget(btn_clear)
        top_layout.addWidget(btn_settings)
        top_layout.addWidget(btn_guide)
        top_layout.addWidget(btn_player)
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.label_cycle)
        stats_layout.addWidget(self.label_time)
        stats_layout.addWidget(self.label_snakes)
        stats_layout.addWidget(self.label_eggs)
        stats_layout.addWidget(self.label_food)

        legend_grid = QGridLayout()
        legend_grid.setSpacing(1)
        legend_grid.setContentsMargins(0,0,0,0)
        legend_grid.addWidget(self._legend_label("#FF0000", f"Head ({self.game.stats_head})"), 0, 0)
        legend_grid.addWidget(self._legend_label("#33CC33", f"Body ({self.game.stats_body})"), 0, 1)
        legend_grid.addWidget(self._legend_label("#FFFF00", f"Egg ({self.game.stats_egg})"), 0, 2)
        legend_grid.addWidget(self._legend_label("#808080", f"Food ({self.game.stats_food_legend})"), 1, 0)
        legend_grid.addWidget(self._legend_label("#0000FF", f"Player Body ({self.game.stats_player_body})"), 1, 1)
        legend_grid.addWidget(self._legend_label("#FF8000", f"Player Head ({self.game.stats_player_head})"), 1, 2)

        explanation = (
            "Game of Snakes is a simulation of snake evolution on a grid. "
            "Place eggs, manage food, and let snakes survive and reproduce. "
            "Strategic placement of eggs and food is crucial for the survival of the snake population."
        )
        self.explanation_label = QLabel(explanation)
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setMinimumWidth(320)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addLayout(stats_layout)
        layout.addLayout(legend_grid)
        center_layout = QHBoxLayout()
        center_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        center_layout.addWidget(self.widget)
        center_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(center_layout)
        layout.addWidget(self.explanation_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setFixedSize(GAME_AREA_SIZE + 20, GAME_AREA_SIZE + 200)

    def _legend_label(self, color, text):
        color_box = QLabel()
        color_box.setFixedSize(8, 8)
        color_box.setStyleSheet(f"background-color: {color}; border: 1px solid #333;")
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 9px; margin-left: 2px;")
        layout = QHBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(color_box)
        layout.addWidget(lbl)
        w = QWidget()
        w.setLayout(layout)
        w._legend_lbl = lbl
        return w

    def spawn_player_egg(self):
        for snake in self.game.snakes:
            if isinstance(snake, PlayerSnake):
                return
        for egg in self.game.eggs:
            if egg.is_player:
                return
        while True:
            x = random.randint(0, GRID_SIZE-1)
            y = random.randint(0, GRID_SIZE-1)
            if self.game.grid[x, y] == 0:
                break
        self.game.add_egg(x, y, is_player=True)
        self.widget.update()

    def keyPressEvent(self, event):
        key = event.key()
        # Support WASD and Arrow keys for player movement
        if key == Qt.Key_W or key == Qt.Key_Up:
            self.player_direction = (0, -1)
        elif key == Qt.Key_S or key == Qt.Key_Down:
            self.player_direction = (0, 1)
        elif key == Qt.Key_A or key == Qt.Key_Left:
            self.player_direction = (-1, 0)
        elif key == Qt.Key_D or key == Qt.Key_Right:
            self.player_direction = (1, 0)

    def show_settings(self):
        dialog = SettingsDialog(self, self.game)
        if dialog.exec():
            dialog.apply_settings()
            self.spin_speed.setValue(dialog.spin_speed.value())
            self.update_speed()
            self.widget.setFixedSize(GAME_AREA_SIZE, GAME_AREA_SIZE)
            self.setFixedSize(GAME_AREA_SIZE + 20, GAME_AREA_SIZE + 200)
            self.widget.update()

    def show_guide(self):
        dialog = GuideDialog(self)
        dialog.exec()

    def update_speed(self):
        if self.running:
            self.timer.setInterval(self.spin_speed.value())

    def toggle(self):
        if self.running:
            self.timer.stop()
        else:
            self.timer.start(self.spin_speed.value())
        self.running = not self.running

    def format_time(self, cycles, ms_per_cycle):
        total_ms = cycles * ms_per_cycle
        total_seconds = total_ms // 1000
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def show_game_over_stats(self):
        cycles = self.game.cycle
        duration = self.format_time(cycles, self.spin_speed.value())
        total_eggs = self.game.total_eggs
        total_food = self.game.total_food
        max_snake_length = self.game.max_snake_length
        stats_text = (
            f"Game Over!\n\n"
            f"Cycles: {cycles}\n"
            f"Duration: {duration}\n"
            f"Total eggs: {total_eggs}\n"
            f"Total food eaten: {total_food}\n"
            f"Longest snake length: {max_snake_length}\n"
        )
        QMessageBox.information(self, "Extinction - Game Over", stats_text)

    def show_player_game_over(self):
        duration = self.format_time(self.game.player_survive_cycles, self.spin_speed.value())
        stats_text = (
            f"Player Snake Eaten!\n\n"
            f"Survived: {self.game.player_survive_cycles} cycles\n"
            f"Duration: {duration}\n"
            f"Longest length: {self.game.player_max_length}\n"
        )
        QMessageBox.information(self, "Game Over - Player Eaten", stats_text)

    def next_step(self):
        self.game.player_direction = self.player_direction
        self.game.update()
        self.label_cycle.setText(f"Cycle: {self.game.cycle}")
        self.label_time.setText(f"Time: {self.format_time(self.game.cycle, self.spin_speed.value())}")
        self.label_snakes.setText(f"Snakes: {self.game.stats_snakes}")
        self.label_eggs.setText(f"Eggs: {self.game.stats_eggs}")
        self.label_food.setText(f"Food: {self.game.stats_food}")
        self._update_legend_labels()
        self.widget.update()
        eggs_pending = any(not egg.is_food for egg in self.game.eggs)
        # Show game over if player is eaten
        if hasattr(self.game, "player_eaten") and self.game.player_eaten:
            if self.running:
                self.timer.stop()
                self.running = False
            self.show_player_game_over()
            self.game.player_eaten = False
        # Show game over if all snakes extinct
        elif self.game.stats_snakes == 0 and not eggs_pending:
            if self.running:
                self.timer.stop()
                self.running = False
            self.show_game_over_stats()

    def clear_game(self):
        self.game.reset()
        self.label_cycle.setText("Cycle: 0")
        self.label_time.setText("Time: 00:00:00")
        self.label_snakes.setText("Snakes: 0")
        self.label_eggs.setText("Eggs: 0")
        self.label_food.setText("Food: 0")
        self._update_legend_labels()
        self.widget.update()

    def _update_legend_labels(self):
        legend_widgets = [
            (self.game.stats_head, 0, 0, "Head"),
            (self.game.stats_body, 0, 1, "Body"),
            (self.game.stats_egg, 0, 2, "Egg"),
            (self.game.stats_food_legend, 1, 0, "Food"),
            (self.game.stats_player_body, 1, 1, "Player Body"),
            (self.game.stats_player_head, 1, 2, "Player Head"),
        ]
        for count, row, col, label in legend_widgets:
            widget = self.centralWidget().layout().itemAt(2).layout().itemAtPosition(row, col).widget()
            widget._legend_lbl.setText(f"{label} ({count})")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GameOfSnakes.App")
    icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "Game of Snakes.ico")
    app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())