"""User Interface Module: the window, player input, and on-screen text.

The UI turns the player's input into Round actions (start_task, select_cell,
submit_addition, submit_subtraction) and into changes to the View (rotation,
isolated layer, cursor). Each frame it asks the Renderer to draw the cube,
then draws the task information and the arithmetic on top.

Numbers are shown to the player, and read back from them, in the round's
number base (ruleset.number_base) using number_base.py.

Controls:
    Left mouse drag / arrow keys   Rotate the cube
    Right mouse click              Select the cell under the mouse
    W A S D                        Move the cursor
    SPACE                          Select the cursor's cell
    X / Y / Z                      Isolate a layer across x / y / z (again to show all)
    Q / E                          Previous / next layer
    ENTER                          Start the next task, or submit an answer
"""

import asyncio
import math
import time

import pygame

from magic8_poc.cube import Cube
from magic8_poc.cube_values import CUBE_VALUES
from magic8_poc.game_round import Phase, Round, SelectResult
from magic8_poc.lines import Coord
from magic8_poc.number_base import DIGITS, parse_answer, to_display
from magic8_poc.renderer import RenderedFrame, Renderer, View
from magic8_poc.ruleset import CUBE_SIZE, HALF_LINE_TYPES, TaskType

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 750
FRAMES_PER_SECOND = 60

ROTATION_SPEED = 0.04       # Radians per frame while an arrow key is held
MOUSE_SENSITIVITY = 0.01    # Radians per pixel of mouse drag

# Display colours, named by what they show so the colours can change freely.
TEXT_COLOUR = (240, 240, 240)
HEADING_COLOUR = (255, 230, 0)
SUCCESS_COLOUR = (120, 220, 130)
ERROR_COLOUR = (255, 110, 110)
HINT_COLOUR = (170, 170, 185)
ANSWER_BOX_FILL = (50, 50, 65)

AXIS_NAMES = "xyz"

BASE_NAMES = {2: "binary", 8: "octal", 10: "decimal", 16: "hexadecimal"}

# What the player is asked to find in each type of task.
TASK_DESCRIPTIONS = {
    TaskType.COMPLEMENT: "Find the starter's complement",
    TaskType.HALF_ORTHOGONAL_X: "Find the rest of the starter's half-line along x",
    TaskType.HALF_ORTHOGONAL_Y: "Find the rest of the starter's half-line along y",
    TaskType.HALF_ORTHOGONAL_Z: "Find the rest of the starter's half-line along z",
    TaskType.ORTHOGONAL_X: "Find the rest of the line along x",
    TaskType.ORTHOGONAL_Y: "Find the rest of the line along y",
    TaskType.ORTHOGONAL_Z: "Find the rest of the line along z",
    TaskType.DIAGONAL_XY_SAME: "Find the xy diagonal: x and y increase together",
    TaskType.DIAGONAL_XY_DIFF: "Find the xy diagonal: x increases as y decreases",
    TaskType.DIAGONAL_XZ_SAME: "Find the xz diagonal: x and z increase together",
    TaskType.DIAGONAL_XZ_DIFF: "Find the xz diagonal: x increases as z decreases",
    TaskType.DIAGONAL_YZ_SAME: "Find the yz diagonal: y and z increase together",
    TaskType.DIAGONAL_YZ_DIFF: "Find the yz diagonal: y increases as z decreases",
    TaskType.TRIAGONAL_XYZ_SAME: "Find the triagonal: x, y and z increase together",
    TaskType.TRIAGONAL_XY_SAME_Z_DIFF: "Find the triagonal: x and y increase as z decreases",
    TaskType.TRIAGONAL_XZ_SAME_Y_DIFF: "Find the triagonal: x and z increase as y decreases",
    TaskType.TRIAGONAL_YZ_SAME_X_DIFF: "Find the triagonal: y and z increase as x decreases",
}

# Screen direction of each cursor key (screen y points down).
CURSOR_KEYS = {
    pygame.K_w: (0, -1),
    pygame.K_s: (0, 1),
    pygame.K_a: (-1, 0),
    pygame.K_d: (1, 0),
}

# Letters, not numbers, so they never clash with typing an answer.
LAYER_KEYS = {pygame.K_x: 0, pygame.K_y: 1, pygame.K_z: 2}


class GameUI:
    """Runs one round in a window."""

    def __init__(self, game_round: Round) -> None:
        self.round = game_round
        self.base = game_round.ruleset.number_base

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Magic-8 - Proof of Concept")
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.text_font = pygame.font.Font(None, 26)
        self.heading_font = pygame.font.Font(None, 34)
        self.answer_font = pygame.font.Font(None, 40)

        # Start looking at the continuous plane's layer through the starter,
        # since the starter may be inside the cube.
        layer_axis = game_round.continuous_plane.off_plane_axis
        self.view = View(layer_axis=layer_axis,
                         layer_index=game_round.starter[layer_axis],
                         cursor=game_round.starter)

        self.frame: RenderedFrame | None = None
        self.answer_text = ""
        self.message = ""
        self.message_is_error = False
        self.dragging = False
        self.last_mouse_position = (0, 0)
        self.start_time: float | None = None
        self.finish_time: float | None = None
        self.running = True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run until the window is closed.

        The loop is async and yields every frame so the same code runs in
        the browser (pygbag) as well as on the desktop.
        """
        while self.running:
            self.clock.tick(FRAMES_PER_SECOND)

            for event in pygame.event.get():
                self.handle_event(event)
            self.rotate_from_held_keys(pygame.key.get_pressed())

            self.frame = self.renderer.render(self.round, self.view)
            self.screen.blit(self.frame.surface, (0, 0))
            self.draw_panels()
            pygame.display.flip()

            await asyncio.sleep(0)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.dragging = True
                self.last_mouse_position = event.pos
            elif event.button == 3 and self.frame is not None:
                cell = self.frame.cell_at(event.pos)
                if cell is not None:
                    self.view.cursor = cell
                    self.select(cell)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            change_x = event.pos[0] - self.last_mouse_position[0]
            change_y = event.pos[1] - self.last_mouse_position[1]
            self.view.angle_y += change_x * MOUSE_SENSITIVITY
            self.view.angle_x += change_y * MOUSE_SENSITIVITY
            self.last_mouse_position = event.pos

        elif event.type == pygame.KEYDOWN:
            # While answering, only the answer keys go to the answer box.
            # Every other key still moves the view, so the player can look
            # around the cube for the numbers they need.
            if self.is_answering() and self.is_answer_key(event):
                self.handle_answer_key(event)
            else:
                self.handle_command_key(event)

    def is_answer_key(self, event) -> bool:
        """Return True for Enter, Backspace, or a digit of the round's base."""
        if event.key == pygame.K_RETURN or event.key == pygame.K_BACKSPACE:
            return True
        return bool(event.unicode) and event.unicode.upper() in DIGITS[:self.base]

    def handle_command_key(self, event) -> None:
        """Keys that select cells, start tasks, and move the view."""
        if event.key == pygame.K_RETURN:
            self.start_next_task()
        elif event.key == pygame.K_SPACE:
            self.select(self.view.cursor)
        elif event.key in CURSOR_KEYS:
            self.move_cursor(CURSOR_KEYS[event.key])
        elif event.key in LAYER_KEYS:
            self.toggle_layer(LAYER_KEYS[event.key])
        elif event.key == pygame.K_k:
            self.show_ghost()
        elif event.key == pygame.K_q:
            self.move_layer(-1)
        elif event.key == pygame.K_e:
            self.move_layer(1)
        elif event.key == pygame.K_l:
            self.starting_pos()

    def handle_answer_key(self, event) -> None:
        """Keys used while the player is typing the addition or subtraction."""
        if event.key == pygame.K_RETURN:
            self.submit_answer()
        elif event.key == pygame.K_BACKSPACE:
            self.answer_text = self.answer_text[:-1]
        else:
            self.answer_text += event.unicode.upper()

    def rotate_from_held_keys(self, keys) -> None:
        if keys[pygame.K_LEFT]:
            self.view.angle_y -= ROTATION_SPEED
        if keys[pygame.K_RIGHT]:
            self.view.angle_y += ROTATION_SPEED
        if keys[pygame.K_UP]:
            self.view.angle_x -= ROTATION_SPEED
        if keys[pygame.K_DOWN]:
            self.view.angle_x += ROTATION_SPEED

    # ------------------------------------------------------------------
    # Round actions
    # ------------------------------------------------------------------

    def is_answering(self) -> bool:
        return self.round.phase in (Phase.ADDING, Phase.SUBTRACTING)

    def start_next_task(self) -> None:
        if not self.round.start_task():
            return
        if self.start_time is None:
            self.start_time = time.perf_counter()
        self.answer_text = ""
        self.show_message("", is_error=False)

    def select(self, cell: Coord) -> None:
        result = self.round.select_cell(cell)
        if result is SelectResult.INCORRECT:
            self.show_message("That cell is not on the line.", is_error=True)
        elif result is SelectResult.CORRECT:
            if self.round.phase is Phase.SELECTING:
                self.show_message("Correct!", is_error=False)
            else:
                self.show_message("All cells found! Now do the arithmetic.", is_error=False)

    def submit_answer(self) -> None:
        answer = parse_answer(self.answer_text, self.base)
        if answer is None:
            self.show_message(f"Type a number in {self.base_name()} first.", is_error=True)
            return

        if self.round.phase is Phase.ADDING:
            if self.round.submit_addition(answer):
                self.answer_text = ""
                self.show_message("Correct! Now subtract.", is_error=False)
            else:
                self.show_message("Not quite. Check your addition.", is_error=True)
            return

        if self.round.submit_subtraction(answer):
            self.answer_text = ""
            if self.round.phase is Phase.ROUND_COMPLETE:
                self.finish_time = time.perf_counter()
            self.show_message("Correct! The line's numbers are now shown.", is_error=False)
        else:
            self.show_message("Not quite. Check your subtraction.", is_error=True)

    def show_message(self, text: str, is_error: bool) -> None:
        self.message = text
        self.message_is_error = is_error

    # ------------------------------------------------------------------
    # View changes
    # ------------------------------------------------------------------

    def is_selectable(self, cell: Coord) -> bool:
        """Cells the cursor may move to: those the player can see."""
        for coordinate in cell:
            if coordinate < 0 or coordinate >= CUBE_SIZE:
                return False

        if self.view.layer_axis is not None:
            return cell[self.view.layer_axis] == self.view.layer_index

        # With the whole cube shown, only the outside cells can be seen.
        for coordinate in cell:
            if coordinate == 0 or coordinate == CUBE_SIZE - 1:
                return True
        return False

    def toggle_layer(self, axis: int) -> None:
        if self.view.layer_axis == axis:
            # Show the whole cube again. If the cursor is now hidden inside
            # the cube, move it out to the nearest side.
            self.view.layer_axis = None
            if not self.is_selectable(self.view.cursor):
                self.view.cursor = self.nearest_outside_cell(self.view.cursor)
        else:
            self.view.layer_axis = axis
            self.view.layer_index = self.view.cursor[axis]

    def show_ghost(self) -> None:
        #show the whole cube
        self.round._ghost = not self.round._ghost

    def move_layer(self, step: int) -> None:
        if self.view.layer_axis is None:
            return
        new_index = self.view.layer_index + step
        if new_index < 0 or new_index >= CUBE_SIZE:
            return
        self.view.layer_index = new_index

        # Keep the cursor in the shown layer.
        cursor = list(self.view.cursor)
        cursor[self.view.layer_axis] = new_index
        self.view.cursor = tuple(cursor)

    def starting_pos (self) -> None:
        game_round = self.round
        layer_axis = game_round.continuous_plane.off_plane_axis
        self.view = View(layer_axis=layer_axis,
                        layer_index=game_round.starter[layer_axis],
                        cursor=game_round.starter)

        # Keep the cursor in the shown layer.
        self.view.cursor = game_round.starter

    @staticmethod
    def nearest_outside_cell(cell: Coord) -> Coord:
        """Move the cell to the nearest side of the cube along one axis."""
        best_axis = 0
        best_distance = CUBE_SIZE
        for axis in range(3):
            distance = min(cell[axis], CUBE_SIZE - 1 - cell[axis])
            if distance < best_distance:
                best_axis = axis
                best_distance = distance

        moved = list(cell)
        if cell[best_axis] < CUBE_SIZE / 2:
            moved[best_axis] = 0
        else:
            moved[best_axis] = CUBE_SIZE - 1
        return tuple(moved)

    def move_cursor(self, screen_direction: tuple[int, int]) -> None:
        """Move the cursor to the neighbouring cell that best matches the
        key's direction on screen, since the cube may be rotated."""
        if self.frame is None:
            return
        current = self.frame.screen_position(self.view.cursor)
        if current is None:
            return

        x, y, z = self.view.cursor
        neighbours = [(x + 1, y, z), (x - 1, y, z),
                      (x, y + 1, z), (x, y - 1, z),
                      (x, y, z + 1), (x, y, z - 1)]

        best_cell = None
        best_alignment = 0.0
        for neighbour in neighbours:
            if not self.is_selectable(neighbour):
                continue
            position = self.frame.screen_position(neighbour)
            if position is None:
                continue

            change_x = position[0] - current[0]
            change_y = position[1] - current[1]
            distance = math.hypot(change_x, change_y)
            if distance < 0.5:
                continue

            # How closely the move points along the key's direction (1 is exact).
            alignment = (change_x * screen_direction[0] + change_y * screen_direction[1]) / distance
            if alignment > best_alignment:
                best_alignment = alignment
                best_cell = neighbour

        if best_cell is not None:
            self.view.cursor = best_cell

    # ------------------------------------------------------------------
    # Text panels
    # ------------------------------------------------------------------

    def base_name(self) -> str:
        return BASE_NAMES.get(self.base, f"base {self.base}")

    def show(self, number: int) -> str:
        """Write a number in the round's base."""
        return to_display(number, self.base)

    def elapsed_seconds(self) -> int:
        if self.start_time is None:
            return 0
        if self.finish_time is not None:
            return int(self.finish_time - self.start_time)
        return int(time.perf_counter() - self.start_time)

    def draw_text(self, text: str, position, colour=TEXT_COLOUR, font=None) -> None:
        if font is None:
            font = self.text_font
        self.screen.blit(font.render(text, True, colour), position)

    def draw_text_right(self, text: str, right_x: int, y: int, colour=TEXT_COLOUR, font=None) -> None:
        """Draw text so that it ends at right_x, for lining up digits."""
        if font is None:
            font = self.text_font
        surface = font.render(text, True, colour)
        self.screen.blit(surface, (right_x - surface.get_width(), y))

    def draw_panels(self) -> None:
        self.draw_task_panel()
        self.draw_view_panel()
        self.draw_timer()
        if self.is_answering():
            self.draw_answer_box()
        self.draw_controls()

    def draw_task_panel(self) -> None:
        """Top left: the task, its progress, and what to do next."""
        game_round = self.round
        tasks_per_round = game_round.ruleset.tasks_per_round
        phase = game_round.phase
        x = 20
        y = 20

        if phase is Phase.READY:
            self.draw_text("Magic-8 round", (x, y), HEADING_COLOUR, self.heading_font)
            y += 36
            self.draw_text(f"Starter {game_round.starter} = "
                           f"{self.show(game_round.value_at(game_round.starter))}", (x, y))
            y += 27
            self.draw_text("Press ENTER to start task 1.", (x, y))
        else:
            self.draw_text(f"Task {game_round.task_number} of {tasks_per_round}",
                           (x, y), HEADING_COLOUR, self.heading_font)
            y += 36
            self.draw_text(TASK_DESCRIPTIONS[game_round.current_task_type], (x, y))
            y += 27
            self.draw_text(f"Starter {game_round.starter} = "
                           f"{self.show(game_round.value_at(game_round.starter))}", (x, y))
            y += 27

            found = len(game_round.correct_cells)
            needed = len(game_round.target_cells)
            self.draw_text(f"Cells found: {found} / {needed}", (x, y))
            y += 27

            if phase is Phase.SELECTING:
                self.draw_text("Select the cells with SPACE or right click.", (x, y), HINT_COLOUR)
            elif phase is Phase.ADDING or phase is Phase.SUBTRACTING:
                self.draw_text(f"Type your answer in {self.base_name()}, then press ENTER.", (x, y), HINT_COLOUR)
            elif phase is Phase.TASK_COMPLETE:
                self.draw_text(f"Press ENTER to start task {game_round.task_number + 1}.", (x, y), HINT_COLOUR)
            elif phase is Phase.ROUND_COMPLETE:
                self.draw_text("All tasks complete. Well done!", (x, y), SUCCESS_COLOUR)

        if self.message:
            y += 33
            colour = ERROR_COLOUR if self.message_is_error else SUCCESS_COLOUR
            self.draw_text(self.message, (x, y), colour)

    def draw_view_panel(self) -> None:
        """Bottom left: what part of the cube is shown and the cursor cell."""
        x = 20
        y = WINDOW_HEIGHT - 75
        plane_name = ""
        for axis in self.round.continuous_plane.axes:
            plane_name += AXIS_NAMES[axis]
        self.draw_text(f"Continuous plane: {plane_name}", (x, y))

        if self.view.layer_axis is None:
            layer_text = "Layer: whole cube"
        else:
            axis_name = AXIS_NAMES[self.view.layer_axis]
            layer_text = f"Layer: {axis_name} = {self.view.layer_index}"
        self.draw_text(layer_text, (x, y + 25), HEADING_COLOUR if self.view.layer_axis is not None else TEXT_COLOUR)
        self.draw_text(f"Cursor: {self.view.cursor}", (x, y + 50))

    def draw_timer(self) -> None:
        minutes, seconds = divmod(self.elapsed_seconds(), 60)
        self.draw_text_right(f"Time: {minutes:02d}:{seconds:02d}", WINDOW_WIDTH - 25, 20,
                             HEADING_COLOUR, self.heading_font)

    def answer_prompt(self) -> str:
        """What the player should work out, in words only. The numbers to
        add are shown in their cells, and the player must remember the magic
        sum, so the prompt gives no numbers away."""
        game_round = self.round
        if game_round.phase is Phase.ADDING:
            return "Add the numbers shown on the line"

        task_type = game_round.current_task_type
        if task_type is TaskType.COMPLEMENT:
            return "Subtract the starter from the complement sum"
        if task_type in HALF_LINE_TYPES:
            return "Subtract your sum from the half-line sum"
        return "Subtract your sum from the full-line sum"

    def draw_answer_box(self) -> None:
        """Top right: one box with the prompt and the player's typed answer."""
        box_width = 440
        box_height = 100
        box_x = WINDOW_WIDTH - box_width - 20
        box_y = 60

        box = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, ANSWER_BOX_FILL, box, border_radius=8)
        pygame.draw.rect(self.screen, TEXT_COLOUR, box, 2, border_radius=8)

        self.draw_text(self.answer_prompt(), (box_x + 15, box_y + 15))
        self.draw_text(self.answer_text + "_", (box_x + 15, box_y + 50), HEADING_COLOUR, self.answer_font)

    def draw_controls(self) -> None:
        """Bottom right: a short reminder of the controls."""
        lines = [
            "Drag / arrows: rotate",
            "WASD: move cursor   SPACE: select",
            "X Y Z: layer   Q / E: change layer",
            "K: show additional layers",
            "L: return to starter",
            "ENTER: start task / submit",
        ]
        y = WINDOW_HEIGHT - 25 * len(lines) - 10
        for line in lines:
            self.draw_text_right(line, WINDOW_WIDTH - 20, y, HINT_COLOUR)
            y += 25


async def main() -> None:
    """Play the PoC's fixed round."""
    pygame.init()
    game_round = Round(Cube(CUBE_VALUES))
    await GameUI(game_round).run()
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
