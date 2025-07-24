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
DEFAULT_food_radius = 20
DEFAULT_LAY_EGG_INTERVAL = 10
DEFAULT_MATURITY_CYCLES = 100
DEFAULT_RARITY = 0.5
DEFAULT_RECRUIT_RADIUS = 2

COLOR_NEUTRAL = QColor(128, 128, 128)
COLOR_WEAPON = QColor(255, 0, 0)
COLOR_LEG = QColor(0, 0, 255)
COLOR_EYE = QColor(0, 255, 0)
COLOR_FOOD = QColor(255, 255, 0)
COLOR_EGG = QColor(200, 200, 200)
COLOR_OLD = QColor(128, 0, 128)
COLOR_NUCLEUS = QColor(255, 128, 0)

DIRECTIONS = [
    (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)
]

COOP_ATTACH_DIRS = DIRECTIONS

DEFAULT_IDLE_LIMIT = 10

class Egg:
    def __init__(self, x, y, incubate_cycles):
        self.x = x
        self.y = y
        self.incubate_cycles = incubate_cycles
        self.born_cycle = None
        self.hatched = False

class Creature:
    def __init__(self, x, y, hunger_cycles, turn_interval, food_radius, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL, maturity_cycles=DEFAULT_MATURITY_CYCLES, rarity=DEFAULT_RARITY, game=None, recruit_radius=DEFAULT_RECRUIT_RADIUS):
        self.neutral = (x, y)
        self.direction_idx = random.randint(0, 7)
        self.direction = DIRECTIONS[self.direction_idx]
        self.cells = {'neutral': [(x, y)]}
        self.hunger_cycles = hunger_cycles
        self.turn_interval = turn_interval
        self.food_radius = food_radius
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
        self.coop_group = None
        self.last_coop_cycle = -1
        self.coop_leader = None
        self.recruit_radius = recruit_radius
        self.is_nucleus = False
        self.last_position = self.neutral
        self.idle_counter = 0
        self.idle_limit = getattr(game, "idle_limit", DEFAULT_IDLE_LIMIT) if game else DEFAULT_IDLE_LIMIT

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

    def can_cooperate_with(self, other, creatures):
        if not self.alive or not other.alive:
            return False
        if not (self.is_old or other.is_old):
            return False
        if self.coop_group and other.coop_group and self.coop_group is not other.coop_group:
            if any(c.is_nucleus for c in self.coop_group) and any(c.is_nucleus for c in other.coop_group):
                pass
            else:
                return False
        elif (self.coop_group and any(c.is_nucleus for c in self.coop_group)) or (other.coop_group and any(c.is_nucleus for c in other.coop_group)):
            if self.coop_group is not None and other.coop_group is not None and self.coop_group is not other.coop_group:
                return False
        if self.coop_group is not None and other.coop_group is not None and self.coop_group is other.coop_group:
            return False
        x1, y1 = self.neutral
        x2, y2 = other.neutral
        if max(abs(x1 - x2), abs(y1 - y2)) <= self.recruit_radius:
            return True
        return False

    def try_cooperate(self, other, coop_probability, current_cycle, creatures):
        if not self.can_cooperate_with(other, creatures):
            return False
        if self.coop_group and other.coop_group and self.coop_group is not other.coop_group:
            if any(c.is_nucleus for c in self.coop_group) and any(c.is_nucleus for c in other.coop_group):
                recruiter = None
                for c in self.coop_group:
                    if c.is_nucleus:
                        recruiter = c
                        break
                if recruiter is None:
                    recruiter = self
                coop_chance = coop_probability
                if random.random() < coop_chance:
                    merged = self.coop_group | other.coop_group
                    nucleus = recruiter
                    for member in merged:
                        member.coop_group = merged
                        member.coop_leader = nucleus
                        member.last_coop_cycle = current_cycle
                        member.is_nucleus = (member is nucleus)
                        # Reset group hunger for all
                        if hasattr(member, "group_hunger"):
                            delattr(member, "group_hunger")
                    self._enforce_group_features(merged)
                    return True
                return False
        # Single-to-group or single-to-single
        if self.is_nucleus or other.is_nucleus:
            recruiter = self if self.is_nucleus else other if other.is_nucleus else self if self.is_old else other
        else:
            recruiter = self if self.is_old else other if other.is_old else None
        if recruiter is None:
            return False
        joined = False
        if self.is_old and other.is_old:
            coop_chance = 1.0
        else:
            coop_chance = coop_probability
        if random.random() < coop_chance:
            self._pending_coop = True
            other._pending_coop = True
            if self.coop_group and other.coop_group:
                merged = self.coop_group | other.coop_group
            elif self.coop_group:
                merged = self.coop_group | set([other])
            elif other.coop_group:
                merged = other.coop_group | set([self])
            else:
                merged = set([self, other])
            nucleus = None
            for m in merged:
                if m.is_nucleus:
                    nucleus = m
                    break
            if not nucleus:
                recruiter.is_nucleus = True
                nucleus = recruiter
            for member in merged:
                member.coop_group = merged
                member.coop_leader = nucleus
                member.last_coop_cycle = current_cycle
                member.is_nucleus = (member is nucleus)
                # Reset group hunger for all
                if hasattr(member, "group_hunger"):
                    delattr(member, "group_hunger")
            self.attach_to_coop_group_outermost(other, merged, creatures)
            self._enforce_group_features(merged)
            joined = True
        return joined

    def _enforce_group_features(self, group):
        weapon_owner = None
        leg_owner = None
        eye_owner = None
        for member in group:
            if member.has_weapon and weapon_owner is None:
                weapon_owner = member
            elif member.has_weapon:
                member.has_weapon = False
                member.cells.pop('weapon', None)
            if member.has_leg and leg_owner is None:
                leg_owner = member
            elif member.has_leg:
                member.has_leg = False
                member.cells.pop('leg', None)
            if member.has_eye and eye_owner is None:
                eye_owner = member
            elif member.has_eye:
                member.has_eye = False
                member.cells.pop('eye', None)
        for member in group:
            member._update_attached_cells()

    def attach_to_coop_group_outermost(self, other, group, creatures):
        group_cells = {c.neutral for c in group}
        occupied = group_cells | {c.neutral for c in creatures if c.alive and c not in group}
        possible = set()
        for gx, gy in group_cells:
            for dx, dy in COOP_ATTACH_DIRS:
                nx, ny = gx + dx, gy + dy
                if (nx, ny) not in occupied and 0 <= nx < (self.game.grid_size if self.game else 100) and 0 <= ny < (self.game.grid_size if self.game else 100):
                    possible.add((nx, ny))
        if possible:
            pos = random.choice(list(possible))
            other.neutral = pos
            other.cells['neutral'] = [pos]
            other._update_attached_cells()
        else:
            self.attach_to_coop_group(other)

    def attach_to_coop_group(self, other):
        group = self.coop_group if self.coop_group else set([self])
        group_cells = [c.neutral for c in group]
        possible = set()
        for gx, gy in group_cells:
            for dx, dy in COOP_ATTACH_DIRS:
                nx, ny = gx + dx, gy + dy
                if (nx, ny) not in group_cells:
                    possible.add((nx, ny))
        if possible:
            pos = random.choice(list(possible))
            other.neutral = pos
            other.cells['neutral'] = [pos]
            other._update_attached_cells()

    def move_coop_group(self, grid_size, food_positions, eggs, creatures, current_cycle, food_list, coop_probability):
        if not self.is_nucleus:
            return None
        group = [c for c in self.coop_group if c.alive]
        leader = self
        group_size = len(group)
        if not hasattr(leader, "group_hunger") or getattr(leader, "_last_group_size", None) != group_size:
            leader.group_hunger = leader.hunger_cycles * group_size
            leader._last_group_size = group_size
        if len(group) == 1 and leader.is_nucleus:
            leader.alive = False
            return None
        leader.group_hunger -= 1
        if leader.group_hunger <= 0:
            for member in group:
                member.alive = False
            return None
        for member in group:
            member.hunger -= 1
            if member.hunger <= 0:
                member.alive = False
        for member in group:
            member.age += 1
            if not member.is_old and member.age >= member.maturity_cycles:
                member.is_old = True
                member.old_since = member.age
            if member.is_old:
                member.maybe_lose_feature()
        speed = 1 + (1 if leader.has_leg else 0)
        for _ in range(speed):
            leader.steps_since_turn += 1
            head_x, head_y = leader.neutral
            nearest_target = None
            min_dist = None
            egg_targets = [(egg.x, egg.y) for egg in eggs if not egg.hatched]
            all_targets = set(food_positions) | set(egg_targets)
            for tx, ty in all_targets:
                dist = abs(head_x - tx) + abs(head_y - ty)
                if dist <= leader.food_radius:
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        nearest_target = (tx, ty)
            if leader.has_eye:
                eye_pos = leader.cells['eye'][0]
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
                        nx, ny = leader.neutral
                        tx, ty = nx + dx_eye, ny + dy_eye
                        if 0 <= tx < grid_size and 0 <= ty < grid_size:
                            if (dx_eye, dy_eye) in DIRECTIONS:
                                leader.direction_idx = DIRECTIONS.index((dx_eye, dy_eye))
                                leader.direction = DIRECTIONS[leader.direction_idx]
                            leader.neutral = (tx, ty)
                            leader.cells['neutral'] = [leader.neutral]
                            leader._update_attached_cells()
                            if leader.last_position != leader.neutral:
                                leader.idle_counter = 0
                                leader.last_position = leader.neutral
                            else:
                                leader.idle_counter += 1
                            continue
            elif nearest_target:
                dx = np.sign(nearest_target[0] - head_x)
                dy = np.sign(nearest_target[1] - head_y)
                if (dx, dy) in DIRECTIONS:
                    leader.direction_idx = DIRECTIONS.index((dx, dy))
                    leader.direction = DIRECTIONS[leader.direction_idx]
            if leader.steps_since_turn >= leader.turn_interval:
                leader.rotate()
                leader.steps_since_turn = 0
            dx, dy = leader.direction
            nx, ny = leader.neutral
            tx, ty = nx + dx, ny + dy
            if 0 <= tx < grid_size and 0 <= ty < grid_size:
                leader.neutral = (tx, ty)
                leader.cells['neutral'] = [leader.neutral]
                leader._update_attached_cells()
                if leader.last_position != leader.neutral:
                    leader.idle_counter = 0
                    leader.last_position = leader.neutral
                else:
                    leader.idle_counter += 1
            else:
                leader.rotate()
                leader.idle_counter += 1
                continue
            self.recruit_nearby(leader, creatures, coop_probability, current_cycle)
            if leader.has_weapon:
                weapon_cells = set(leader.cells.get('weapon', []))
                for c in creatures:
                    if c is not leader and c.alive and (leader.coop_group is None or c.coop_group is None or leader.coop_group != c.coop_group):
                        kill = False
                        if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('leg', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('eye', [])):
                            kill = True
                        if getattr(c, "is_old", False):
                            if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                                kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('weapon', [])):
                            kill = False
                        if kill and not (getattr(leader, "_pending_coop", False) and getattr(c, "_pending_coop", False)):
                            c.alive = False
            if hasattr(leader, "_pending_coop"):
                del leader._pending_coop
            for egg in eggs:
                if not egg.hatched and (egg.x, egg.y) == leader.neutral:
                    self._group_eat_and_grow(group)
                    egg.hatched = True
            for idx, (fx, fy) in enumerate(food_list):
                if (fx, fy) == leader.neutral:
                    self._group_eat_and_grow(group)
                    food_list.pop(idx)
                    break
            if leader.cell_count() > 4:
                leader.alive = False
            if leader.idle_counter >= leader.idle_limit:
                leader.alive = False
        if leader.alive:
            members = [m for m in group if m is not leader]
            queue = [leader.neutral]
            visited = set(queue)
            assign_idx = 0
            while queue and assign_idx < len(members):
                cx, cy = queue.pop(0)
                for dx, dy in COOP_ATTACH_DIRS:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size and (nx, ny) not in visited:
                        members[assign_idx].neutral = (nx, ny)
                        members[assign_idx].cells['neutral'] = [(nx, ny)]
                        members[assign_idx]._update_attached_cells()
                        members[assign_idx].steps_since_turn = leader.steps_since_turn
                        members[assign_idx].direction_idx = leader.direction_idx
                        members[assign_idx].direction = leader.direction
                        if members[assign_idx].last_position != (nx, ny):
                            members[assign_idx].idle_counter = 0
                            members[assign_idx].last_position = (nx, ny)
                        else:
                            members[assign_idx].idle_counter += 1
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        assign_idx += 1
                        if assign_idx >= len(members):
                            break
        self._enforce_group_features(group)
        for member in group:
            self.recruit_nearby(member, creatures, coop_probability, current_cycle)
            if member.has_weapon:
                weapon_cells = set(member.cells.get('weapon', []))
                for c in creatures:
                    if c is not member and c.alive and (member.coop_group is None or c.coop_group is None or member.coop_group != c.coop_group):
                        kill = False
                        if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('leg', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('eye', [])):
                            kill = True
                        if getattr(c, "is_old", False):
                            if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                                kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('weapon', [])):
                            kill = False
                        if kill and not (getattr(member, "_pending_coop", False) and getattr(c, "_pending_coop", False)):
                            c.alive = False
            if hasattr(member, "_pending_coop"):
                del member._pending_coop
            for egg in eggs:
                if not egg.hatched and (egg.x, egg.y) == member.neutral:
                    self._group_eat_and_grow(group)
                    egg.hatched = True
            for idx, (fx, fy) in enumerate(food_list):
                if (fx, fy) == member.neutral:
                    self._group_eat_and_grow(group)
                    food_list.pop(idx)
                    break
            if member.cell_count() > 4:
                member.alive = False
            if member.idle_counter >= member.idle_limit:
                member.alive = False
        if leader.feature_count() == 3 and current_cycle - leader.last_lay_cycle >= leader.lay_egg_interval:
            tx, ty = leader.neutral
            leader.last_lay_cycle = current_cycle
            return Egg(tx, ty, leader.hunger_cycles)
        return None

    def _group_eat_and_grow(self, group):
        for member in group:
            if member.feature_count() < 3:
                rarity_factor = member.rarity
                if member.game:
                    total_cells = member.game.grid_size * member.game.grid_size
                    food_count = len(member.game.food)
                    egg_count = len([egg for egg in member.game.eggs if not egg.hatched])
                    abundance = (food_count + egg_count) / max(1, total_cells)
                    rarity_factor = min(1.0, max(0.0, member.rarity + abundance * 0.8 - 0.2))
                if rarity_factor == 0.0 or random.random() > rarity_factor:
                    member.grow('random')
            member.hunger += member.hunger_cycles

    def move(self, grid_size, food_positions, eggs, creatures, current_cycle, food_list, coop_probability):
        if self.coop_group and self.is_nucleus:
            return self.move_coop_group(grid_size, food_positions, eggs, creatures, current_cycle, food_list, coop_probability)
        elif self.coop_group:
            return None
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
                if dist <= self.food_radius:
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
                            if self.last_position != self.neutral:
                                self.idle_counter = 0
                                self.last_position = self.neutral
                            else:
                                self.idle_counter += 1
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
                if self.last_position != self.neutral:
                    self.idle_counter = 0
                    self.last_position = self.neutral
                else:
                    self.idle_counter += 1
            else:
                self.rotate()
                self.idle_counter += 1
                continue
            self.recruit_nearby(self, creatures, coop_probability, current_cycle)
            if self.has_weapon:
                weapon_cells = set(self.cells.get('weapon', []))
                for c in creatures:
                    if c is not self and c.alive and (self.coop_group is None or c.coop_group is None or self.coop_group != c.coop_group):
                        kill = False
                        if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('leg', [])):
                            kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('eye', [])):
                            kill = True
                        if getattr(c, "is_old", False):
                            if any(cell in weapon_cells for cell in c.cells.get('neutral', [])):
                                kill = True
                        if any(cell in weapon_cells for cell in c.cells.get('weapon', [])):
                            kill = False
                        if kill and not (getattr(self, "_pending_coop", False) and getattr(c, "_pending_coop", False)):
                            c.alive = False
            if hasattr(self, "_pending_coop"):
                del self._pending_coop
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
            if self.idle_counter >= self.idle_limit:
                self.alive = False
        if self.feature_count() == 3 and current_cycle - self.last_lay_cycle >= self.lay_egg_interval:
            tx, ty = self.neutral
            self.last_lay_cycle = current_cycle
            return Egg(tx, ty, self.hunger_cycles)
        return None

    def recruit_nearby(self, self_creature, creatures, coop_probability, current_cycle):
        # Try to recruit any other group or single nearby
        for other in creatures:
            if other is self_creature:
                continue
            if not other.alive:
                continue
            if self_creature.coop_group is not None and other.coop_group is not None and self_creature.coop_group is other.coop_group:
                continue
            if self_creature.can_cooperate_with(other, creatures):
                self_creature.try_cooperate(other, coop_probability, current_cycle, creatures)

    def eat_and_grow(self):
        if self.coop_group:
            group = [c for c in self.coop_group if c.alive]
            self._group_eat_and_grow(group)
        else:
            if self.feature_count() < 3:
                rarity_factor = self.rarity
                if self.game:
                    total_cells = self.game.grid_size * self.game.grid_size
                    food_count = len(self.game.food)
                    egg_count = len([egg for egg in self.game.eggs if not egg.hatched])
                    abundance = (food_count + egg_count) / max(1, total_cells)
                    rarity_factor = min(1.0, max(0.0, self.rarity + abundance * 0.8 - 0.2))
                if rarity_factor == 0.0 or random.random() > rarity_factor:
                    self.grow('random')
            self.hunger += self.hunger_cycles

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
            if part == 'random':
                chosen = random.choice(options)
            else:
                chosen = part
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
    def __init__(self, grid_size=DEFAULT_GRID_SIZE, incubate_cycles=DEFAULT_INCU_CYCLES, hunger_cycles=DEFAULT_HUNGER_CYCLES, turn_interval=DEFAULT_TURN_INTERVAL, food_radius=DEFAULT_food_radius, lay_egg_interval=DEFAULT_LAY_EGG_INTERVAL, maturity_cycles=DEFAULT_MATURITY_CYCLES, rarity=DEFAULT_RARITY, recruit_radius=DEFAULT_RECRUIT_RADIUS):
        self.grid_size = grid_size
        self.cell_size = DEFAULT_GAME_AREA_SIZE // self.grid_size
        self.incubate_cycles = incubate_cycles
        self.hunger_cycles = hunger_cycles
        self.turn_interval = turn_interval
        self.food_radius = food_radius
        self.lay_egg_interval = lay_egg_interval
        self.maturity_cycles = maturity_cycles
        self.rarity = rarity
        self.recruit_radius = recruit_radius
        self.idle_limit = DEFAULT_IDLE_LIMIT
        self.reset()
        self.max_creature_age = 0
        self.last_coop_probability = 0.0

    def reset(self):
        self.eggs = []
        self.creatures = []
        self.food = []
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
        self.cycle = 0
        self.max_creature_age = 0
        self.last_coop_probability = 0.0

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
                        if getattr(creature, "is_nucleus", False):
                            self.grid[cell[0], cell[1]] = 9
                        elif getattr(creature, "is_old", False):
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
        total_cells = self.grid_size * self.grid_size
        food_count = len(self.food)
        egg_count = len([egg for egg in self.eggs if not egg.hatched])
        if total_cells == 0:
            abundance = 1.0
        else:
            abundance = min(1.0, max(0.0, (food_count + egg_count) / total_cells))
        if abundance >= 0.5:
            coop_probability = 0.0
        else:
            coop_probability = 1.0 - (abundance * 2.0)
        self.last_coop_probability = coop_probability
        for egg in self.eggs:
            if not egg.hatched:
                if egg.born_cycle is None:
                    egg.born_cycle = self.cycle
                if self.cycle - egg.born_cycle >= egg.incubate_cycles:
                    egg.hatched = True
                    hunger = self.hunger_cycles
                    turn = self.turn_interval
                    food_radius = self.food_radius
                    lay_interval = self.lay_egg_interval
                    maturity_cycles = self.maturity_cycles
                    rarity = self.rarity
                    recruit_radius = self.recruit_radius
                    self.creatures.append(Creature(egg.x, egg.y, hunger, turn, food_radius, lay_interval, maturity_cycles, rarity, self, recruit_radius))
        food_positions = set(self.food)
        new_eggs = []
        food_list = self.food
        for creature in self.creatures:
            if creature.alive:
                egg_laid = creature.move(self.grid_size, food_positions, self.eggs, self.creatures, self.cycle, food_list, coop_probability)
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
            "12. Cooperation: Old cells can cooperate to extend hunger if food/egg is rare.\n"
            "13. Use Settings to adjust parameters.\n"
            "14. Nucleus (orange): The first recruiter and only one per group. All group members share hunger and will cluster together."
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
                elif val == 9:
                    painter.fillRect(x*cell_size, y*cell_size, cell_size, cell_size, COLOR_NUCLEUS)
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, DEFAULT_GAME_AREA_SIZE - 1, DEFAULT_GAME_AREA_SIZE - 1)

    def mousePressEvent(self, event):
        cell_size = DEFAULT_GAME_AREA_SIZE // self.game.grid_size
        x = int(event.position().x() // cell_size)
        y = int(event.position().y() // cell_size)
        if 0 <= x < self.game.grid_size and 0 <= y < self.game.grid_size:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ControlModifier:
                self.spawn_dummy_coop(x, y)
                self.game.update_grid()
                self.update()
                if self.main_window:
                    self.main_window.update_egg_count()
                    self.main_window.update_food_count()
                return
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

    def spawn_dummy_coop(self, x, y):
        if any(c.neutral == (x, y) for c in self.game.creatures):
            return
        c1 = Creature(x, y, self.game.hunger_cycles, self.game.turn_interval, self.game.food_radius, self.game.lay_egg_interval, self.game.maturity_cycles, self.game.rarity, self.game)
        c2_dir = random.choice(DIRECTIONS)
        x2, y2 = x + c2_dir[0], y + c2_dir[1]
        if not (0 <= x2 < self.game.grid_size and 0 <= y2 < self.game.grid_size):
            return
        if any(c.neutral == (x2, y2) for c in self.game.creatures):
            return
        c2 = Creature(x2, y2, self.game.hunger_cycles, self.game.turn_interval, self.game.food_radius, self.game.lay_egg_interval, self.game.maturity_cycles, self.game.rarity, self.game)
        c1.is_old = True
        c2.is_old = False
        c1.age = c1.maturity_cycles
        c2.age = 0
        coop_set = set([c1, c2])
        for c in coop_set:
            c.coop_group = coop_set
            c.coop_leader = c1
            c.last_coop_cycle = self.game.cycle
            c.is_nucleus = False
        c1.is_nucleus = True
        self.game.creatures.append(c1)
        self.game.creatures.append(c2)

class SettingsDialog(QDialog):
    def __init__(self, parent, game, cycle_speed):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.game = game
        self.layout = QFormLayout(self)
        self.spin_grid_size = QSpinBox()
        self.spin_grid_size.setRange(10, 300)  # Ubah batas maksimum dari 100 menjadi 300
        self.spin_grid_size.setValue(self.game.grid_size)
        self.spin_cycle_speed = QSpinBox()
        self.spin_cycle_speed.setRange(10, 2000)
        self.spin_cycle_speed.setValue(cycle_speed)
        self.spin_cycle_speed.setSuffix(" ms")
        self.spin_incubate = QSpinBox()
        self.spin_incubate.setRange(1, 500)
        self.spin_incubate.setValue(self.game.incubate_cycles)
        self.spin_hunger = QSpinBox()
        self.spin_hunger.setRange(1, 500)
        self.spin_hunger.setValue(self.game.hunger_cycles)
        self.spin_turn = QSpinBox()
        self.spin_turn.setRange(1, 500)
        self.spin_turn.setValue(self.game.turn_interval)
        self.spin_food_radius = QSpinBox()
        self.spin_food_radius.setRange(1, 500)
        self.spin_food_radius.setValue(self.game.food_radius)
        self.spin_lay_egg = QSpinBox()
        self.spin_lay_egg.setRange(1, 500)
        self.spin_lay_egg.setValue(self.game.lay_egg_interval)
        self.spin_maturity = QSpinBox()
        self.spin_maturity.setRange(1, 1000)
        self.spin_maturity.setValue(self.game.maturity_cycles)
        self.spin_rarity = QSpinBox()
        self.spin_rarity.setRange(0, 100)
        self.spin_rarity.setValue(int(self.game.rarity * 100))
        self.spin_rarity.setSuffix(" %")
        self.spin_recruit_radius = QSpinBox()
        self.spin_recruit_radius.setRange(1, 10)
        self.spin_recruit_radius.setValue(getattr(self.game, "recruit_radius", DEFAULT_RECRUIT_RADIUS))
        self.layout.addRow("Grid size", self.spin_grid_size)
        self.layout.addRow("Cycle speed", self.spin_cycle_speed)
        self.layout.addRow("Egg incubate cycles", self.spin_incubate)
        self.layout.addRow("Creature hunger cycles", self.spin_hunger)
        self.layout.addRow("Creature turn interval", self.spin_turn)
        self.layout.addRow("Food attract radius", self.spin_food_radius)
        self.layout.addRow("Lay egg interval", self.spin_lay_egg)
        self.layout.addRow("Maturity cycles (old age)", self.spin_maturity)
        self.layout.addRow("Feature rarity (higher = rarer)", self.spin_rarity)
        self.layout.addRow("Recruit radius", self.spin_recruit_radius)
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
        recruit_radius = self.spin_recruit_radius.value()
        grid_size_changed = (self.game.grid_size != grid_size)
        self.game.grid_size = grid_size
        self.game.cell_size = DEFAULT_GAME_AREA_SIZE // grid_size
        self.game.incubate_cycles = incubate_cycles
        self.game.hunger_cycles = hunger_cycles
        self.game.turn_interval = turn_interval
        self.game.food_radius = food_radius
        self.game.lay_egg_interval = lay_egg_interval
        self.game.maturity_cycles = maturity_cycles
        self.game.rarity = rarity
        self.game.recruit_radius = recruit_radius
        for creature in getattr(self.game, "creatures", []):
            creature.hunger_cycles = hunger_cycles
            creature.turn_interval = turn_interval
            creature.food_radius = food_radius
            creature.lay_egg_interval = lay_egg_interval
            creature.maturity_cycles = maturity_cycles
            creature.rarity = rarity
            creature.game = self.game
            creature.recruit_radius = recruit_radius
        if grid_size_changed:
            self.game.reset()
        return grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval, maturity_cycles, rarity, recruit_radius

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
        self.label_coop = QLabel("Coop Prob: 0%")
        self.label_max_hunger = QLabel("Hunger: 0")

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
        stats_layout.addWidget(self.label_coop)
        stats_layout.addWidget(self.label_max_hunger)

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
        legend_grid.addWidget(self._legend_label(COLOR_NUCLEUS, "Nucleus (first recruiter, only one per group)"), 2, 1)

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
        self.label_coop.setText("Coop Prob: 0%")
        self.label_max_hunger.setText("Hunger: 0")

    def update_egg_count(self):
        eggs = [egg for egg in self.game.eggs if not egg.hatched]
        self.label_eggs.setText(f"Eggs: {len(eggs)}")

    def update_food_count(self):
        self.label_food.setText(f"Food: {len(self.game.food)}")

    def showEvent(self, event):
        super().showEvent(event)
        self.update_egg_count()
        self.update_food_count()
        self.update_coop_prob()
        self.update_max_hunger()

    def update_coop_prob(self):
        prob = int(round(self.game.last_coop_probability * 100))
        self.label_coop.setText(f"Coop Prob: {prob}%")

    def update_max_hunger(self):
        max_hunger = 0
        for c in self.game.creatures:
            if c.alive and c.hunger > max_hunger:
                max_hunger = c.hunger
        self.label_max_hunger.setText(f"Hunger: {max_hunger}")

    def show_settings(self):
        dialog = SettingsDialog(self, self.game, self.cycle_speed)
        if dialog.exec():
            grid_size, cycle_speed, incubate_cycles, hunger_cycles, turn_interval, food_radius, lay_egg_interval, maturity_cycles, rarity, recruit_radius = dialog.apply_settings()
            self.cycle_speed = cycle_speed
            self.widget.setFixedSize(DEFAULT_GAME_AREA_SIZE, DEFAULT_GAME_AREA_SIZE)
            self.setFixedSize(DEFAULT_GAME_AREA_SIZE + 40, DEFAULT_GAME_AREA_SIZE + 180)
            self.timer.setInterval(self.cycle_speed)
            self.widget.update()
            self.update_coop_prob()
            self.update_max_hunger()

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
        coop_prob = int(round(self.game.last_coop_probability * 100))
        max_hunger = 0
        for c in self.game.creatures:
            if c.hunger > max_hunger:
                max_hunger = c.hunger
        stats_text = (
            f"Population Extinct!\n\n"
            f"Cycles: {cycles}\n"
            f"Time: {duration}\n"
            f"Oldest organism age: {max_age}\n"
            f"Coop probability: {coop_prob}%\n"
            f"Hunger: {max_hunger}\n"
        )
        QMessageBox.information(self, "Population Extinct", stats_text)

    def next_step(self):
        self.game.step()
        self.label_cycle.setText(f"Cycle: {self.game.cycle}")
        self.label_time.setText(f"Time: {self.format_time(self.game.cycle, self.cycle_speed)}")
        self.update_egg_count()
        self.update_food_count()
        self.update_coop_prob()
        self.update_max_hunger()
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