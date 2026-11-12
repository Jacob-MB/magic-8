"""Game state and game rules for Magic-8.

Run this file to start the game. UI input is translated into controller
methods; the renderer only reads controller state and draws it.
"""

import math
import time

import pygame

from cube import CubeGrid


class GameController:
    def __init__(self, size: int = 8) -> None:
        self.cube = CubeGrid(size=size)
        self.selected = [0, 0, 0]
        self.active_plane = None  # None, 0 (X), 1 (Y), or 2 (Z)

        self.angle_x = -0.45
        self.angle_y = 0.55
        self.rotation_speed = 0.04
        self.mouse_sensitivity = 0.01

        self.editing_value = False
        self.value_input = ""
        self.value_error = ""
        self.last_answer_correct = None

        self.start_time = time.perf_counter()
        self.elapsed_time = 0.0
        self.running = True

        # Rendering output is delivered here so the UI never needs to know
        # about the Renderer object.
        self.renderer = None
        self.rendered_surface = None
        self.visible_faces = []
        self.projected_centers = {}

    @property
    def size(self) -> int:
        return self.cube.size

    def get_elapsed_time(self) -> float:
        if self.running:
            return time.perf_counter() - self.start_time
        return self.elapsed_time

    def is_exterior(self, cell):
        return self.cube.is_exterior(cell)

    def get_visible_cells(self):
        cells = set()
        for cell in self.cube.all_cells():
            if self.active_plane is None:
                cells.add(cell)
            elif cell[self.active_plane] == self.selected[self.active_plane]:
                cells.add(cell)
        return cells

    def is_selectable(self, cell) -> bool:
        if not self.cube.in_bounds(cell):
            return False
        if self.active_plane is not None:
            return cell in self.get_visible_cells()
        return self.is_exterior(cell)

    def select_cell(self, cell) -> None:
        if self.is_selectable(cell):
            self.selected[:] = cell

    def submit_value(self, text: str | None = None) -> bool:
        """Check an entered base-8 answer."""

        if text is None:
            text = self.value_input

        if not text or any(digit not in "01234567" for digit in text):
            self.value_error = "Enter a valid base-8 number."
            self.last_answer_correct = False
            return False

        if len(text) > 4:
            self.value_error = "Values cannot exceed 4 digits."
            self.last_answer_correct = False
            return False

        answer = int(text, 8)

        tile = self.cube.get(*self.selected)

        if tile.check_answer(answer):
            self.value_error = "Correct!"
            self.last_answer_correct = True
            self.editing_value = False
            self.value_input = ""
            return True

        self.value_error = "Incorrect value. Try again."
        self.last_answer_correct = False
        return False

    def begin_value_entry(self) -> None:
        self.editing_value = True
        self.value_input = ""
        self.value_error = ""
        self.last_answer_correct = None

    def cancel_value_entry(self) -> None:
        self.editing_value = False
        self.value_input = ""
        self.value_error = ""

    def handle_value_key(self, event) -> None:
        if event.key == pygame.K_RETURN:
            self.submit_value()
        elif event.key == pygame.K_ESCAPE:
            self.cancel_value_entry()
        elif event.key == pygame.K_BACKSPACE:
            self.value_input = self.value_input[:-1]
            self.value_error = ""
        elif event.unicode in "01234567" and len(self.value_input) < 4:
            self.value_input += event.unicode
            self.value_error = ""

    def rotate(self, dx: float, dy: float) -> None:
        self.angle_y += dx * self.mouse_sensitivity
        self.angle_x += dy * self.mouse_sensitivity

    def rotate_keys(self, keys) -> None:
        if self.editing_value:
            return
        if keys[pygame.K_LEFT]:
            self.angle_y -= self.rotation_speed
        if keys[pygame.K_RIGHT]:
            self.angle_y += self.rotation_speed
        if keys[pygame.K_UP]:
            self.angle_x -= self.rotation_speed
        if keys[pygame.K_DOWN]:
            self.angle_x += self.rotation_speed

    def toggle_plane(self, axis: int) -> None:
        self.active_plane = None if self.active_plane == axis else axis
        if not self.is_selectable(tuple(self.selected)):
            visible = sorted(self.get_visible_cells())
            if visible:
                self.selected[:] = visible[0]

    def move_plane(self, direction: int) -> None:
        if self.active_plane is None:
            return
        new_position = self.selected[self.active_plane] + direction
        if 0 <= new_position < self.size:
            self.selected[self.active_plane] = new_position

    def move_selection(self, direction: str) -> None:
        """Move to the selectable neighbour most aligned on the last rendered screen."""
        x, y, z = self.selected
        screen_directions = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
        dx_screen, dy_screen = screen_directions[direction]
        current_screen = self.projected_centers.get(tuple(self.selected))
        if current_screen is None:
            return

        if self.active_plane == 0:
            neighbors = [(x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)]
        elif self.active_plane == 1:
            neighbors = [(x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)]
        elif self.active_plane == 2:
            neighbors = [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)]
        else:
            neighbors = [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)]

        best_neighbor = None
        best_score = -float("inf")
        for neighbor in neighbors:
            if not self.is_selectable(neighbor):
                continue
            neighbor_screen = self.projected_centers.get(neighbor)
            if neighbor_screen is None:
                continue
            dx = neighbor_screen[0] - current_screen[0]
            dy = neighbor_screen[1] - current_screen[1]
            distance = math.hypot(dx, dy)
            if distance < 0.5:
                continue
            alignment = (dx / distance) * dx_screen + (dy / distance) * dy_screen
            if alignment > best_score and alignment > 0:
                best_score, best_neighbor = alignment, neighbor
        if best_neighbor is not None:
            self.selected[:] = best_neighbor

    @staticmethod
    def _point_in_polygon(point, polygon) -> bool:
        """Return whether a screen point lies inside a rendered face polygon."""
        px, py = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if (yi > py) != (yj > py):
                intersection_x = (xj - xi) * (py - yi) / (yj - yi) + xi
                if px < intersection_x:
                    inside = not inside
            j = i
        return inside

    def select_cell_at_position(self, position) -> None:
        """Select the front-most selectable cell at a screen position.

        The renderer supplies face polygons; the UI only supplies mouse
        coordinates and does not need to import or call the renderer.
        """
        for depth, polygon, color, cell in reversed(self.visible_faces):
            if self._point_in_polygon(position, polygon) and self.is_selectable(cell):
                self.select_cell(cell)
                return

    def set_renderer(self, renderer) -> None:
        """Attach an object that implements render(game_state)."""
        self.renderer = renderer

    def refresh_render(self) -> None:
        """Ask the renderer for a frame and retain its output for the UI."""
        if self.renderer is None:
            return
        frame = self.renderer.render(self)
        self.rendered_surface = frame["surface"]
        self.visible_faces = frame["visible_faces"]
        self.projected_centers = frame["projected_centers"]

    def get_rendered_surface(self):
        """Return the most recently rendered screen for the UI to display."""
        return self.rendered_surface

    def cell_center(self, x, y, z):
        middle = (self.size - 1) / 2
        return (x - middle, y - middle, z - middle)


def run_game() -> None:
    # Imports are local so the controller does not require the UI or renderer
    # modules merely to provide its game-state functionality.
    from renderer import Renderer
    from ui import GameUI

    pygame.init()
    controller = GameController(size=8)
    renderer = Renderer(1000, 750)
    ui = GameUI(1000, 750)

    controller.set_renderer(renderer)
    ui.run(controller)

    pygame.quit()


if __name__ == "__main__":
    run_game()
