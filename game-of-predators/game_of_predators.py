import sys
import os
import numpy as np
import random
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QDialog, QFormLayout, QSizePolicy, QGridLayout, QSpacerItem, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QIcon

DEFAULT_GRID_SIZE = 100
DEFAULT_GAME_AREA_SIZE = 400
DEFAULT_CYCLE_SPEED = 25
DEFAULT_INCU_CYCLES = 20
DEFAULT_HUNGER_CYCLES = 200
DEFAULT_TURN_INTERVAL = 10
DEFAULT_FOOD_ATTRACT_RADIUS = 20
DEFAULT_LAY_EGG_INTERVAL = 50
DEFAULT_MATURITY_CYCLES = 300
DEFAULT_RARITY = 0.5

COLOR_NEUTRAL = QColor(128, 128, 128)
COLOR_WEAPON = QColor(255, 0, 0)
COLOR_LEG = QColor(0, 0, 255)
COLOR_EYE = QColor(0, 255, 0)
COLOR_FOOD = QColor(255, 255, 0)
COLOR_EGG = QColor(200, 200, 200)
COLOR_OLD = QColor(128, 0, 128)

DIRECTIONS = [
    (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)
]

class Egg:
    def __init__(self, x, y, incubate_cycles):
        self.x = x
        self.y = y
        self.incubate_cycles = incubate_cycles
        self.born_cycle = None
        self.hatched = False

class Creature:
    def __init__(self, x, y, hunger_cycles, turn_interval, food_attract_radius, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL, maturity_cycles=DEFAULT_MATURITY_CYCLES, rarity=DEFAULT_RARITY, game=None):
        self.neutral = (x, y)
        self.direction_idx = random.randint(0, 7)
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
        self.age = 0
        self.maturity_cycles = maturity_cycles
        self.is_old = False
        self.old_since = None
        self.last_feature_loss_age = None
        self.rarity = rarity
        self.game = game

    def rotate(self):
        self.direction_idx = random.randint(0, 7)
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
            ex, ey = dy, -dx
            self.cells['eye'] = [(tx + ex, ty + ey)]

    def maybe_lose_feature(self):
        if not self.is_old:
            return
        if self.last_feature_loss_age is not None:
            if self.age - self.last_feature_loss_age < self.maturity_cycles:
                return
        features = []
        if self.has_weapon:
            features.append('weapon')
        if self.has_leg:
            features.append('leg')
        if self.has_eye:
            features.append('eye')
        if not features:
            return
        max_prob = 0.8
        min_prob = 0.05
        old_age = self.age - self.maturity_cycles
        prob = min_prob + min(max_prob - min_prob, old_age / (self.maturity_cycles * 2))
        if random.random() < prob:
            lost = random.choice(features)
            if lost == 'weapon':
                self.has_weapon = False
                self.cells.pop('weapon', None)
            elif lost == 'leg':
                self.has_leg = False
                self.cells.pop('leg', None)
            elif lost == 'eye':
                self.has_eye = False
                self.cells.pop('eye', None)
            self.last_feature_loss_age = self.age

    def move(self, grid_size, food_positions, eggs, creatures, current_cycle, food_list):
        self.age += 1
        if not self.is_old and self.age >= self.maturity_cycles:
            self.is_old = True
            self.old_since = self.age
        if self.is_old:
            self.maybe_lose_feature()
        speed = 1 + (1 if self.has_leg else 0)
        for _ in range(speed):
            self.steps_since_turn += 1
            head_x, head_y = self.neutral
            nearest_target = None
            min_dist = None
            egg_targets = [(egg.x, egg.y) for egg in eggs if not egg.hatched]
            all_targets = set(food_positions) | set(egg_targets)
            for tx, ty in all_targets:
                dist = abs(head_x - tx) + abs(head_y - ty)
                if dist <= self.food_attract_radius:
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        nearest_target = (tx, ty)
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
                        nx, ny = self.neutral
                        tx, ty = nx + dx_eye, ny + dy_eye
                        if 0 <= tx < grid_size and 0 <= ty < grid_size:
                            if (dx_eye, dy_eye) in DIRECTIONS:
                                self.direction_idx = DIRECTIONS.index((dx_eye, dy_eye))
                                self.direction = DIRECTIONS[self.direction_idx]
                            self.neutral = (tx, ty)
                            self.cells['neutral'] = [self.neutral]
                            self._update_attached_cells()
                            continue
            elif nearest_target:
                dx = np.sign(nearest_target[0] - head_x)
                dy = np.sign(nearest_target[1] - head_y)
                if (dx, dy) in DIRECTIONS:
                    self.direction_idx = DIRECTIONS.index((dx, dy))
                    self.direction = DIRECTIONS[self.direction_idx]
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
            rarity_factor = self.rarity
            if self.game:
                total_cells = self.game.grid_size * self.game.grid_size
                food_count = len(self.game.food)
                egg_count = len([egg for egg in self.game.eggs if not egg.hatched])
                abundance = (food_count + egg_count) / max(1, total_cells)
                rarity_factor = min(1.0, max(0.0, self.rarity + abundance * 0.8 - 0.2))
            if random.random() > rarity_factor:
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
    def __init__(self, grid_size=DEFAULT_GRID_SIZE, incubate_cycles=DEFAULT_INCU_CYCLES, hunger_cycles=DEFAULT_HUNGER_CYCLES, turn_interval=DEFAULT_TURN_INTERVAL, food_attract_radius=DEFAULT_FOOD_ATTRACT_RADIUS, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL, maturity_cycles=DEFAULT_MATURITY_CYCLES, rarity=DEFAULT_RARITY):
        self.grid_size = grid_size
        self.cell_size = DEFAULT_GAME_AREA_SIZE // self.grid_size
        self.incubate_cycles = incubate_cycles
        self.hunger_cycles = hunger_cycles
        self.turn_interval = turn_interval
        self.food_attract_radius = food_attract_radius
        self.lay_egg_interval = lay_egg_interval
        self.maturity_cycles = maturity_cycles
        self.rarity = rarity
        self.reset()
        self.max_creature_age = 0

    def reset(self):
        self.eggs = []
        self.creatures = []
        self.food = []
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
        self.cycle = 0
        self.max_creature_age = 0

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
                        if getattr(creature, "is_old", False):
                            self.grid[cell[0], cell[1]] = 8
                        else:
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
                    maturity_cycles = self.maturity_cycles
                    rarity = self.rarity
                    self.creatures.append(Creature(egg.x, egg.y, hunger, turn, food_radius, lay_interval, maturity_cycles, rarity, self))
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
        for creature in self.creatures:
            if creature.age > self.max_creature_age:
                self.max_creature_age = creature.age
        self.update_grid()

class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Guide")
        layout = QVBoxLayout(self)
        guide_text = (
            "Game of Predators - Guide\n\n"
            "1. Left click to place an egg (gray).\n"
            "2. Right click to place food (yellow).\n"
            "3. Eggs hatch after N cycles.\n"
            "4. Creatures can eat eggs/food to grow weapon, leg, or eye.\n"
            "5. Weapon (red) kills other creatures.\n"
            "6. Leg (blue) increases speed.\n"
            "7. Eye (green) sees food/egg in its direction and pulls neutral toward it.\n"
            "8. Max organism size is 4 cells, more will die.\n"
            "9. Complete creatures lay eggs every interval.\n"
            "10. Old (purple) creatures may lose features randomly as they age.\n"
            "11. Rarity: If food/egg is abundant, features are rare. If scarce, features are common.\n"
            "12. Use Settings to adjust parameters."
        )
        label = QLabel(guide_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

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
                elif val == 8:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_OLD)
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
        self.spin_maturity = QSpinBox()
        self.spin_maturity.setRange(1, 1000)
        self.spin_maturity.setValue(self.game.maturity_cycles)
        self.spin_rarity = QSpinBox()
        self.spin_rarity.setRange(0, 100)
        self.spin_rarity.setValue(int(self.game.rarity * 100))
        self.spin_rarity.setSuffix(" %")
        self.layout.addRow("Grid size", self.spin_grid_size)
        self.layout.addRow("Cycle speed", self.spin_cycle_speed)
        self.layout.addRow("Egg incubate cycles", self.spin_incubate)
        self.layout.addRow("Creature hunger cycles", self.spin_hunger)
        self.layout.addRow("Creature turn interval", self.spin_turn)
        self.layout.addRow("Food attract radius", self.spin_food_radius)
        self.layout.addRow("Lay egg interval", self.spin_lay_egg)
        self.layout.addRow("Maturity cycles (old age)", self.spin_maturity)
        self.layout.addRow("Feature rarity (higher = rarer)", self.spin_rarity)
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
        maturity_cycles = self.spin_maturity.value()
        rarity = self.spin_rarity.value() / 100.0
        # Update game parameters in place for realtime effect
        self.game.grid_size = grid_size
        self.game.cell_size = DEFAULT_GAME_AREA_SIZE // grid_size
        self.game.incubate_cycles = incubate_cycles
        self.game.hunger_cycles = hunger_cycles
        self.game.turn_interval = turn_interval
        self.game.food_attract_radius = food_radius
        self.game.lay_egg_interval = lay_egg_interval
        self.game.maturity_cycles = maturity_cycles
        self.game.rarity = rarity
        # Update all existing creatures with new parameters
        for creature in getattr(self.game, "creatures", []):
            creature.hunger_cycles = hunger_cycles
            creature.turn_interval = turn_interval
            creature.food_attract_radius = food_radius
            creature.lay_egg_interval = lay_egg_interval
            creature.maturity_cycles = maturity_cycles
            creature.rarity = rarity
            creature.game = self.game
        return grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval, maturity_cycles, rarity

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
        btn_clear = QPushButton("Clear")
        btn_settings = QPushButton("Settings")
        btn_guide = QPushButton("Guide")
        btn_start.clicked.connect(self.toggle)
        btn_clear.clicked.connect(self.clear_game)
        btn_settings.clicked.connect(self.show_settings)
        btn_guide.clicked.connect(self.show_guide)

        self.label_cycle = QLabel("Cycle: 0")
        self.label_time = QLabel("Time: 00:00:00")
        self.label_eggs = QLabel("Eggs: 0")
        self.label_food = QLabel("Food: 0")

        top_layout = QHBoxLayout()
        top_layout.addWidget(btn_start)
        top_layout.addWidget(btn_clear)
        top_layout.addWidget(btn_settings)
        top_layout.addWidget(btn_guide)

        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.label_cycle)
        stats_layout.addWidget(self.label_time)
        stats_layout.addWidget(self.label_eggs)
        stats_layout.addWidget(self.label_food)

        legend_grid = QGridLayout()
        legend_grid.setSpacing(1)
        legend_grid.setContentsMargins(0,0,0,0)
        legend_grid.addWidget(self._legend_label(COLOR_EGG, "Egg (incubate)"), 0, 0)
        legend_grid.addWidget(self._legend_label(COLOR_FOOD, "Food"), 0, 1)
        legend_grid.addWidget(self._legend_label(COLOR_NEUTRAL, "Neutral (creature)"), 0, 2)
        legend_grid.addWidget(self._legend_label(COLOR_WEAPON, "Weapon (kill, turns to food)"), 1, 0)
        legend_grid.addWidget(self._legend_label(COLOR_LEG, "Leg (speed +1)"), 1, 1)
        legend_grid.addWidget(self._legend_label(COLOR_EYE, "Eye (see food/egg, turn)"), 1, 2)
        legend_grid.addWidget(self._legend_label(COLOR_OLD, "Old (may lose features)"), 2, 0)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addLayout(stats_layout)
        layout.addLayout(legend_grid)
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.widget)
        layout.addLayout(center_layout)

        explanation = (
            "Game of Predators:\n"
            "Eggs hatch into creatures that eat, grow, and evolve features.\n"
            "Complete creatures lay eggs; old age may cause feature loss.\n"
            "Rarity: If food/egg is abundant, features are rare. If scarce, features are common.\n"
            "Game ends when all creatures and eggs are gone."
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
        self.label_time.setText("Time: 00:00:00")

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
            grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval, maturity_cycles, rarity = dialog.apply_settings()
            self.cycle_speed = cycle_speed
            self.widget.setFixedSize(DEFAULT_GAME_AREA_SIZE, DEFAULT_GAME_AREA_SIZE)
            self.setFixedSize(DEFAULT_GAME_AREA_SIZE + 40, DEFAULT_GAME_AREA_SIZE + 180)
            self.timer.setInterval(self.cycle_speed)
            self.widget.update()

    def show_guide(self):
        dialog = GuideDialog(self)
        dialog.exec()

    def toggle(self):
        if self.running:
            self.timer.stop()
        else:
            self.timer.start(self.cycle_speed)
        self.running = not self.running

    def format_time(self, cycles, ms_per_cycle):
        total_ms = cycles * ms_per_cycle
        total_seconds = total_ms // 1000
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def show_extinct_dialog(self):
        cycles = self.game.cycle
        duration = self.format_time(cycles, self.cycle_speed)
        max_age = self.game.max_creature_age
        stats_text = (
            f"Population Extinct!\n\n"
            f"Cycles: {cycles}\n"
            f"Time: {duration}\n"
            f"Oldest organism age: {max_age}\n"
        )
        QMessageBox.information(self, "Population Extinct", stats_text)

    def next_step(self):
        self.game.step()
        self.label_cycle.setText(f"Cycle: {self.game.cycle}")
        self.label_time.setText(f"Time: {self.format_time(self.game.cycle, self.cycle_speed)}")
        self.update_egg_count()
        self.update_food_count()
        self.widget.update()
        if len(self.game.creatures) == 0 and len([egg for egg in self.game.eggs if not egg.hatched]) == 0:
            if self.running:
                self.timer.stop()
                self.running = False
            self.show_extinct_dialog()

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