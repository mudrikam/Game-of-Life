from PySide6.QtCore import Qt
import random

class PlayerSnake:
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

    def move(self, food_positions, egg_positions, player_direction=None):
        self.steps_since_dir_change += 1
        head_x, head_y = self.head()
        moved = False
        if player_direction:
            dx, dy = player_direction
            new_head = (head_x + dx, head_y + dy)
            if 0 <= new_head[0] < 80 and 0 <= new_head[1] < 80 and new_head not in self.body:
                self.direction = (dx, dy)
                self.body = [new_head] + self.body[:-1]
                self.steps_since_dir_change = 0
                moved = True
        if not moved:
            dx, dy = self.direction
            new_head = (head_x + dx, head_y + dy)
            if 0 <= new_head[0] < 80 and 0 <= new_head[1] < 80 and new_head not in self.body:
                self.body = [new_head] + self.body[:-1]
                moved = True
            else:
                self.bounce()
                dx, dy = self.direction
                new_head = (head_x + dx, head_y + dy)
                if 0 <= new_head[0] < 80 and 0 <= new_head[1] < 80 and new_head not in self.body:
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
                if 0 <= new_head[0] < 80 and 0 <= new_head[1] < 80 and new_head not in self.body:
                    self.direction = (ddx, ddy)
                    self.body = [new_head] + self.body
                    break
            else:
                self.bounce()
                dx, dy = self.direction
                new_head = (self.body[0][0] + dx, self.body[0][1] + dy)
                if 0 <= new_head[0] < 80 and 0 <= new_head[1] < 80 and new_head not in self.body:
                    self.body = [new_head] + self.body

    def bounce(self):
        if not self.body:
            return
        dx, dy = self.direction
        x, y = self.body[0]
        if x <= 0 or x >= 79:
            dx = -dx
        if y <= 0 or y >= 79:
            dy = -dy
        self.direction = (dx, dy)

    def shade_skin(self, current_cycle, eggs):
        return