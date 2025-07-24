import sys
import os
import numpy as np
import random
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QDialog, QFormLayout, QSizePolicy, QGridLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QIcon

DEFAULT_GRID_SIZE = 40
DEFAULT_GAME_AREA_SIZE = 400
DEFAULT_CYCLE_SPEED = 50
DEFAULT_INCU_CYCLES = 20
DEFAULT_HUNGER_CYCLES = 40
DEFAULT_TURN_INTERVAL = 10
DEFAULT_FOOD_ATTRACT_RADIUS = 5
DEFAULT_LAY_EGG_INTERVAL = 50

COLOR_NEUTRAL = QColor(128, 128, 128)
COLOR_WEAPON = QColor(255, 0, 0)
COLOR_LEG = QColor(0, 0, 255)
COLOR_EYE = QColor(0, 255, 0)
COLOR_FOOD = QColor(255, 255, 0)
COLOR_EGG = QColor(200, 200, 200)

DIRECTIONS = [(1,0), (0,1), (-1,0), (0,-1)]  # right, down, left, up

class Egg:
    def __init__(self, x, y, incubate_cycles):
        self.x = x
        self.y = y
        self.incubate_cycles = incubate_cycles
        self.born_cycle = None
        self.hatched = False

class Creature:
    def __init__(self, x, y, hunger_cycles, turn_interval, food_attract_radius, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL):
        self.neutral = (x, y)
        self.direction_idx = random.randint(0, 3)
        self.direction = DIRECTIONS[self.direction_idx]
        self.cells = {'neutral': [(x, y)]}
        self.hunger_cycles = hunger_cycles
        self.turn_interval = turn_interval
        self.food_attract_radius = food_attract_radius
        self.born_cycle = 0
        self.hunger = hunger_cycles
        self.steps_since_turn = 0
        self.has_weapon = False
        self.has_leg = False
        self.has_eye = False
        self.alive = True
        self.last_lay_cycle = 0
        self.lay_egg_interval = lay_egg_interval

    def rotate(self):
        # Rotasi random, bukan hanya melingkar
        self.direction_idx = random.randint(0, 3)
        self.direction = DIRECTIONS[self.direction_idx]
        self._update_attached_cells()

    def _update_attached_cells(self):
        tx, ty = self.neutral
        dx, dy = self.direction
        if self.has_weapon:
            self.cells['weapon'] = [(tx + dx, ty + dy)]
        if self.has_leg:
            self.cells['leg'] = [(tx - dx, ty - dy)]
        if self.has_eye:
            ex, ey = -dy, dx
            self.cells['eye'] = [(tx + ex, ty + ey)]

    def move(self, grid_size, food_positions, eggs, creatures, current_cycle, food_list):
        speed = 1 + (1 if self.has_leg else 0)
        for _ in range(speed):
            self.steps_since_turn += 1
            head_x, head_y = self.neutral
            nearest_target = None
            min_dist = None
            # Gabungkan food dan egg yang belum hatched sebagai target
            egg_targets = [(egg.x, egg.y) for egg in eggs if not egg.hatched]
            all_targets = set(food_positions) | set(egg_targets)
            for tx, ty in all_targets:
                dist = abs(head_x - tx) + abs(head_y - ty)
                if dist <= self.food_attract_radius:
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        nearest_target = (tx, ty)
            # Mata: jika ada food/egg di arah mata, neutral akan bergerak ke arah itu
            if self.has_eye:
                eye_pos = self.cells['eye'][0]
                ex, ey = eye_pos
                dx_eye = ex - head_x
                dy_eye = ey - head_y
                if dx_eye != 0 or dy_eye != 0:
                    found_target = None
                    for step in range(1, grid_size):
                        tx = ex + dx_eye * step
                        ty = ey + dy_eye * step
                        if 0 <= tx < grid_size and 0 <= ty < grid_size:
                            if (tx, ty) in all_targets:
                                found_target = (dx_eye, dy_eye)
                                break
                        else:
                            break
                    if found_target:
                        # Neutral bergerak ke arah eye
                        nx, ny = self.neutral
                        tx, ty = nx + dx_eye, ny + dy_eye
                        if 0 <= tx < grid_size and 0 <= ty < grid_size:
                            self.direction = (dx_eye, dy_eye)
                            self.direction_idx = DIRECTIONS.index(self.direction) if self.direction in DIRECTIONS else self.direction_idx
                            self.neutral = (tx, ty)
                            self.cells['neutral'] = [self.neutral]
                            self._update_attached_cells()
                            continue
            elif nearest_target:
                dx = np.sign(nearest_target[0] - head_x)
                dy = np.sign(nearest_target[1] - head_y)
                for idx, (ddx, ddy) in enumerate(DIRECTIONS):
                    if (dx, dy) == (ddx, ddy):
                        self.direction_idx = idx
                        self.direction = DIRECTIONS[self.direction_idx]
                        break
            if self.steps_since_turn >= self.turn_interval:
                self.rotate()
                self.steps_since_turn = 0
            dx, dy = self.direction
            nx, ny = self.neutral
            tx, ty = nx + dx, ny + dy
            if 0 <= tx < grid_size and 0 <= ty < grid_size:
                self.neutral = (tx, ty)
                self.cells['neutral'] = [self.neutral]
                self._update_attached_cells()
            if self.has_weapon:
                for wx, wy in self.cells['weapon']:
                    for c in creatures:
                        if c is not self and c.alive:
                            if (wx, wy) in c.all_cells():
                                c.alive = False
            for egg in eggs:
                if not egg.hatched and (egg.x, egg.y) == self.neutral:
                    self.eat_and_grow()
                    egg.hatched = True
            for idx, (fx, fy) in enumerate(food_list):
                if (fx, fy) == self.neutral:
                    self.eat_and_grow()
                    food_list.pop(idx)
                    break
            if self.cell_count() > 4:
                self.alive = False
        if self.feature_count() == 3 and current_cycle - self.last_lay_cycle >= self.lay_egg_interval:
            tx, ty = self.neutral
            self.last_lay_cycle = current_cycle
            return Egg(tx, ty, self.hunger_cycles)
        return None

    def eat_and_grow(self):
        self.hunger = self.hunger_cycles
        if self.feature_count() < 3:
            self.grow('random')

    def grow(self, part):
        if self.feature_count() >= 3:
            return
        options = []
        if not self.has_weapon:
            options.append('weapon')
        if not self.has_leg:
            options.append('leg')
        if not self.has_eye:
            options.append('eye')
        if options:
            chosen = random.choice(options)
            if chosen == 'weapon' and not self.has_weapon:
                self.has_weapon = True
            elif chosen == 'leg' and not self.has_leg:
                self.has_leg = True
            elif chosen == 'eye' and not self.has_eye:
                self.has_eye = True
            self._update_attached_cells()

    def cell_count(self):
        count = 0
        for v in self.cells.values():
            count += len(v)
        return count

    def feature_count(self):
        count = 0
        if self.has_weapon:
            count += 1
        if self.has_leg:
            count += 1
        if self.has_eye:
            count += 1
        return count

    def all_cells(self):
        result = []
        for v in self.cells.values():
            result.extend(v)
        return result

class Game:
    def __init__(self, grid_size=DEFAULT_GRID_SIZE, incubate_cycles=DEFAULT_INCU_CYCLES, hunger_cycles=DEFAULT_HUNGER_CYCLES, turn_interval=DEFAULT_TURN_INTERVAL, food_attract_radius=DEFAULT_FOOD_ATTRACT_RADIUS, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL):
        self.grid_size = grid_size
        self.cell_size = DEFAULT_GAME_AREA_SIZE // self.grid_size
        self.incubate_cycles = incubate_cycles
        self.hunger_cycles = hunger_cycles
        self.turn_interval = turn_interval
        self.food_attract_radius = food_attract_radius
        self.lay_egg_interval = lay_egg_interval
        self.reset()

    def reset(self):
        self.eggs = []
        self.creatures = []
        self.food = []
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
        self.cycle = 0

    def add_egg(self, x, y):
        for egg in self.eggs:
            if egg.x == x and egg.y == y:
                return
        self.eggs.append(Egg(x, y, self.incubate_cycles))

    def add_food(self, x, y):
        if (x, y) not in self.food:
            self.food.append((x, y))

    def update_grid(self):
        self.grid[:] = 0
        for egg in self.eggs:
            if not egg.hatched:
                if 0 <= egg.x < self.grid_size and 0 <= egg.y < self.grid_size:
                    self.grid[egg.x, egg.y] = 2
        for fx, fy in self.food:
            if 0 <= fx < self.grid_size and 0 <= fy < self.grid_size:
                self.grid[fx, fy] = 3
        for creature in self.creatures:
            if creature.alive:
                for cell in creature.cells.get('neutral', []):
                    if 0 <= cell[0] < self.grid_size and 0 <= cell[1] < self.grid_size:
                        self.grid[cell[0], cell[1]] = 4
                for cell in creature.cells.get('weapon', []):
                    if 0 <= cell[0] < self.grid_size and 0 <= cell[1] < self.grid_size:
                        self.grid[cell[0], cell[1]] = 5
                for cell in creature.cells.get('leg', []):
                    if 0 <= cell[0] < self.grid_size and 0 <= cell[1] < self.grid_size:
                        self.grid[cell[0], cell[1]] = 6
                for cell in creature.cells.get('eye', []):
                    if 0 <= cell[0] < self.grid_size and 0 <= cell[1] < self.grid_size:
                        self.grid[cell[0], cell[1]] = 7

    def step(self):
        self.cycle += 1
        for egg in self.eggs:
            if not egg.hatched:
                if egg.born_cycle is None:
                    egg.born_cycle = self.cycle
                if self.cycle - egg.born_cycle >= egg.incubate_cycles:
                    egg.hatched = True
                    hunger = self.hunger_cycles
                    turn = self.turn_interval
                    food_radius = self.food_attract_radius
                    lay_interval = self.lay_egg_interval
                    self.creatures.append(Creature(egg.x, egg.y, hunger, turn, food_radius, lay_interval))
        food_positions = set(self.food)
        new_eggs = []
        food_list = self.food
        for creature in self.creatures:
            if creature.alive:
                egg_laid = creature.move(self.grid_size, food_positions, self.eggs, self.creatures, self.cycle, food_list)
                if egg_laid:
                    new_eggs.append(egg_laid)
                creature.hunger -= 1
                if creature.hunger <= 0:
                    creature.alive = False
        for creature in self.creatures:
            if not creature.alive:
                for cell in creature.all_cells():
                    if 0 <= cell[0] < self.grid_size and 0 <= cell[1] < self.grid_size:
                        self.food.append(cell)
        self.creatures = [c for c in self.creatures if c.alive]
        self.eggs += new_eggs
        self.update_grid()

class GameWidget(QWidget):
    def __init__(self, game, main_window=None):
        super().__init__()
        self.game = game
        self.main_window = main_window
        self.setFixedSize(DEFAULT_GAME_AREA_SIZE, DEFAULT_GAME_AREA_SIZE)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        cell_size = DEFAULT_GAME_AREA_SIZE // self.game.grid_size
        for x in range(self.game.grid_size):
            for y in range(self.game.grid_size):
                val = self.game.grid[x, y]
                if val == 2:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_EGG)
                elif val == 3:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_FOOD)
                elif val == 4:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_NEUTRAL)
                elif val == 5:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_WEAPON)
                elif val == 6:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_LEG)
                elif val == 7:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_EYE)
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, DEFAULT_GAME_AREA_SIZE - 1, DEFAULT_GAME_AREA_SIZE - 1)

    def mousePressEvent(self, event):
        cell_size = DEFAULT_GAME_AREA_SIZE // self.game.grid_size
        x = int(event.position().x() // cell_size)
        y = int(event.position().y() // cell_size)
        if 0 <= x < self.game.grid_size and 0 <= y < self.game.grid_size:
            if event.button() == Qt.LeftButton:
                self.game.add_egg(x, y)
                self.game.update_grid()
                self.update()
                if self.main_window:
                    self.main_window.update_egg_count()
            elif event.button() == Qt.RightButton:
                self.game.add_food(x, y)
                self.game.update_grid()
                self.update()
                if self.main_window:
                    self.main_window.update_food_count()

class SettingsDialog(QDialog):
    def __init__(self, parent, game, cycle_speed):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.game = game
        self.layout = QFormLayout(self)
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 100)
        self.spin_grid_size.setValue(self.game.grid_size)
        self.spin_cycle_speed = QSpinBox()
        self.spin_cycle_speed.setRange(10, 2000)
        self.spin_cycle_speed.setValue(cycle_speed)
        self.spin_cycle_speed.setSuffix(" ms")
        self.spin_incubate = QSpinBox()
        self.spin_incubate.setRange(1, 100)
        self.spin_incubate.setValue(self.game.incubate_cycles)
        self.spin_hunger = QSpinBox()
        self.spin_hunger.setRange(1, 200)
        self.spin_hunger.setValue(self.game.hunger_cycles)
        self.spin_turn = QSpinBox()
        self.spin_turn.setRange(1, 50)
        self.spin_turn.setValue(self.game.turn_interval)
        self.spin_food_radius = QSpinBox()
        self.spin_food_radius.setRange(1, 40)
        self.spin_food_radius.setValue(self.game.food_attract_radius)
        self.spin_lay_egg = QSpinBox()
        self.spin_lay_egg.setRange(1, 200)
        self.spin_lay_egg.setValue(DEFAULT_LAY_EGG_INTERVAL)
        self.layout.addRow("Grid size", self.spin_grid_size)
        self.layout.addRow("Cycle speed", self.spin_cycle_speed)
        self.layout.addRow("Egg incubate cycles", self.spin_incubate)
        self.layout.addRow("Creature hunger cycles", self.spin_hunger)
        self.layout.addRow("Creature turn interval", self.spin_turn)
        self.layout.addRow("Food attract radius", self.spin_food_radius)
        self.layout.addRow("Lay egg interval", self.spin_lay_egg)
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        self.layout.addRow(btn_ok)

    def apply_settings(self):
        grid_size = self.spin_grid_size.value()
        cycle_speed = self.spin_cycle_speed.value()
        incubate_cycles = self.spin_incubate.value()
        hunger_cycles = self.spin_hunger.value()
        turn_interval = self.spin_turn.value()
        food_radius = self.spin_food_radius.value()
        lay_egg_interval = self.spin_lay_egg.value()
        return grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game of Predators")
        self.game = Game()
        self.cycle_speed = DEFAULT_CYCLE_SPEED
        self.widget = GameWidget(self.game, self)
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
        self.running = False

        btn_start = QPushButton("Start/Stop")
        btn_start.clicked.connect(self.toggle)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_game)
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self.show_settings)

        self.label_cycle = QLabel("Cycle: 0")
        self.label_eggs = QLabel("Eggs: 0")
        self.label_food = QLabel("Food: 0")

        top_layout = QHBoxLayout()
        top_layout.addWidget(btn_start)
        top_layout.addWidget(btn_clear)
        top_layout.addWidget(btn_settings)
        top_layout.addWidget(self.label_cycle)
        top_layout.addWidget(self.label_eggs)
        top_layout.addWidget(self.label_food)

        legend_grid = QGridLayout()
        legend_grid.setSpacing(1)
        legend_grid.setContentsMargins(0,0,0,0)
        legend_grid.addWidget(self._legend_label(COLOR_EGG, "Egg (incubate)"), 0, 0)
        legend_grid.addWidget(self._legend_label(COLOR_FOOD, "Food"), 0, 1)
        legend_grid.addWidget(self._legend_label(COLOR_NEUTRAL, "Neutral (creature)"), 0, 2)
        legend_grid.addWidget(self._legend_label(COLOR_WEAPON, "Weapon (kill, turns to food)"), 1, 0)
        legend_grid.addWidget(self._legend_label(COLOR_LEG, "Leg (speed +1)"), 1, 1)
        legend_grid.addWidget(self._legend_label(COLOR_EYE, "Eye (see food, turn)"), 1, 2)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addLayout(legend_grid)
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.widget)
        layout.addLayout(center_layout)

        explanation = (
            "Game of Predators (prototype):\n"
        )
        self.explanation_label = QLabel(explanation)
        self.explanation_label.setWordWrap(True)
        layout.addWidget(self.explanation_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setFixedSize(DEFAULT_GAME_AREA_SIZE + 40, DEFAULT_GAME_AREA_SIZE + 180)

    def _legend_label(self, color, text):
        color_box = QLabel()
        color_box.setFixedSize(12, 12)
        color_box.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #333;")
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 10px; margin-left: 2px;")
        layout = QHBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(color_box)
        layout.addWidget(lbl)
        w = QWidget()
        w.setLayout(layout)
        return w

    def clear_game(self):
        self.game.reset()
        self.widget.update()
        self.update_egg_count()
        self.update_food_count()
        self.label_cycle.setText("Cycle: 0")

    def update_egg_count(self):
        eggs = [egg for egg in self.game.eggs if not egg.hatched]
        self.label_eggs.setText(f"Eggs: {len(eggs)}")

    def update_food_count(self):
        self.label_food.setText(f"Food: {len(self.game.food)}")

    def showEvent(self, event):
        super().showEvent(event)
        self.update_egg_count()
        self.update_food_count()

    def show_settings(self):
        dialog = SettingsDialog(self, self.game, self.cycle_speed)
        if dialog.exec():
            grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval = dialog.apply_settings()
            self.cycle_speed = cycle_speed
            self.game = Game(grid_size, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval)
            self.widget.game = self.game
            self.widget.setFixedSize(DEFAULT_GAME_AREA_SIZE, DEFAULT_GAME_AREA_SIZE)
            self.setFixedSize(DEFAULT_GAME_AREA_SIZE + 40, DEFAULT_GAME_AREA_SIZE + 180)
            self.clear_game()
            self.timer.setInterval(self.cycle_speed)

    def toggle(self):
        if self.running:
            self.timer.stop()
        else:
            self.timer.start(self.cycle_speed)
        self.running = not self.running

    def next_step(self):
        self.game.step()
        self.label_cycle.setText(f"Cycle: {self.game.cycle}")
        self.update_egg_count()
        self.update_food_count()
        self.widget.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GameOfPredators.App")
    icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "Game of Predators.ico")
    app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
