"""Gameplay logic for one round of tasks.

The Round class is a state machine. It has no loop of its own: the game loop
in the UI module calls its action methods when the player does something,
then reads its state to decide what to draw.

All numbers going in and out of the Round are plain integers. Showing them
to the player in their number base (and reading the player's answers) is the
UI's job, using number_base.py.

A task goes through these phases:

    SELECTING  -> the player clicks cells until every target cell is found
    ADDING     -> (all but the complement task) the player adds the starter
                  and extra numbers
    SUBTRACTING-> the player subtracts from the magic constant
    TASK_COMPLETE, or ROUND_COMPLETE after the last task
"""

from enum import Enum

from magic8_poc.cube import Cube
from magic8_poc.fixed_round import (CONTINUOUS_PLANE, STARTER, TASKS,
                                    TaskConfig)
from magic8_poc.lines import Coord, Plane, TaskSolver
from magic8_poc.ruleset import STANDARD_RULESET, Ruleset, TaskType


class Phase(Enum):
    """Where the round is up to."""

    READY = 1           # Round created, waiting for the first START
    SELECTING = 2       # Player is finding the task's target cells
    ADDING = 3          # Player is adding the numbers in the column
    SUBTRACTING = 4     # Player is subtracting from the magic constant
    TASK_COMPLETE = 5   # Task finished, waiting for START on the next task
    ROUND_COMPLETE = 6  # All of the round's tasks finished


class SelectResult(Enum):
    """What happened when the player selected a cell."""

    CORRECT = 1    # The cell is a target cell; it is marked correct
    INCORRECT = 2  # The cell is not a target cell; it is marked incorrect
    IGNORED = 3    # Not accepted right now (wrong phase, or already correct)


class Round:
    """One round of tasks around a single starter cell."""

    def __init__(self, cube: Cube, starter: Coord = STARTER,
                 continuous_plane: Plane = CONTINUOUS_PLANE,
                 tasks: list[TaskConfig] = TASKS,
                 ruleset: Ruleset = STANDARD_RULESET, verify: bool = True):
        """Create a round.

        Args:
            cube: The magic cube's numbers.
            starter: The cell whose number is shown from the start.
            continuous_plane: The round's continuous plane. The tasks must
                be chosen to match it.
            tasks: The round's tasks, in order.
            ruleset: The rules this round follows.
            verify: Check each task's line sums before it starts
                (FR_VerifyTask). Turn off only when testing with a cube that
                is not a real magic cube.

        Raises:
            ValueError: If the tasks do not follow the ruleset (wrong number
                of tasks, or an extra count outside the allowed range).
        """
        self._ruleset = ruleset
        self._check_tasks(tasks)

        self._cube = cube
        self._solver = TaskSolver(starter)
        self._continuous_plane = continuous_plane
        self._tasks = tasks
        self._verify = verify

        self._phase = Phase.READY
        self._task_index = -1  # No task has started yet

        # Cells for the current task.
        self._target_cells: list[Coord] = []
        self._correct_cells: set[Coord] = set()
        self._incorrect_cells: set[Coord] = set()
        self._line_revealed = False

    # ------------------------------------------------------------------
    # Actions (called by the game loop)
    # ------------------------------------------------------------------

    def start_task(self) -> bool:
        """Start the next task (the player pressed START).

        Clears the previous task's correct, incorrect and revealed cells; only the
        starter stays shown. Returns False if a task cannot start now.

        Raises:
            ValueError: If verification is on and the task's numbers do not
                add up to the expected magic sum.
        """
        if self._phase not in (Phase.READY, Phase.TASK_COMPLETE):
            return False

        self._task_index += 1
        self._target_cells = self._solver.get_correct_cell_coords(
            self.current_task_type)
        self._correct_cells = set()
        self._incorrect_cells = set()
        self._line_revealed = False

        if self._verify:
            self._check_task_sums()

        self._phase = Phase.SELECTING
        return True

    def select_cell(self, cell: Coord) -> SelectResult:
        """Handle the player selecting a cell.

        A target cell is marked correct and a wrong cell is marked
        incorrect; there is no limit on wrong selections. Selections are
        ignored outside the SELECTING phase, and for the starter or a cell
        that is already marked correct.
        """
        if self._phase is not Phase.SELECTING:
            return SelectResult.IGNORED
        if cell == self.starter or cell in self._correct_cells:
            return SelectResult.IGNORED

        if cell not in self._target_cells:
            self._incorrect_cells.add(cell)
            return SelectResult.INCORRECT

        self._correct_cells.add(cell)

        # Once every target is found, move on to the arithmetic.
        if len(self._correct_cells) == len(self._target_cells):
            if self._ruleset.has_addition_step(self.current_task_type):
                self._phase = Phase.ADDING
            else:
                # Nothing to add (task 1), so go straight to subtraction.
                self._phase = Phase.SUBTRACTING

        return SelectResult.CORRECT

    def submit_addition(self, answer: int) -> bool:
        """Check the player's sum of the addition column.

        Returns True and moves on to subtraction if the answer is correct.
        A wrong answer (or a call outside the ADDING phase) returns False.
        """
        if self._phase is not Phase.ADDING:
            return False

        if answer != self._addition_sum():
            return False

        self._phase = Phase.SUBTRACTING
        return True

    def submit_subtraction(self, answer: int) -> bool:
        """Check the player's answer to the subtraction.

        A correct answer reveals the rest of the line's numbers and finishes
        the task (or the round, after the last task). A wrong answer (or a call
        outside the SUBTRACTING phase) returns False.
        """
        if self._phase is not Phase.SUBTRACTING:
            return False

        expected = self.subtraction_constant - self._addition_sum()
        if answer != expected:
            return False

        self._line_revealed = True

        if self._task_index == len(self._tasks) - 1:
            self._phase = Phase.ROUND_COMPLETE
        else:
            self._phase = Phase.TASK_COMPLETE
        return True

    # ------------------------------------------------------------------
    # Read-only state (used by the renderer and UI)
    # ------------------------------------------------------------------

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def task_number(self) -> int:
        """The current task, counting from 1, or 0 before the first task
        starts."""
        return self._task_index + 1

    @property
    def current_task_type(self) -> TaskType | None:
        if self._task_index < 0:
            return None
        return self._tasks[self._task_index].task_type

    @property
    def starter(self) -> Coord:
        return self._solver.starter

    @property
    def continuous_plane(self) -> Plane:
        """The round's continuous plane (use .axes and .off_plane_axis)."""
        return self._continuous_plane

    @property
    def target_cells(self) -> list[Coord]:
        """The cells the player must find in the current task."""
        # Return a copy so callers cannot change the round's own list.
        return list(self._target_cells)

    @property
    def correct_cells(self) -> set[Coord]:
        """Target cells the player has found so far in the current task."""
        # Return a copy so callers cannot change the round's own set.
        return set(self._correct_cells)

    @property
    def incorrect_cells(self) -> set[Coord]:
        """Wrong cells the player has selected in the current task."""
        # Return a copy so callers cannot change the round's own set.
        return set(self._incorrect_cells)

    @property
    def revealed_cells(self) -> set[Coord]:
        """Cells whose number should be shown.

        The starter is always shown. After a correct subtraction, the whole
        line (or the complement, in task 1) is shown too.
        """
        cells = {self.starter}
        if self._line_revealed:
            cells.update(self._target_cells)
        return cells

    @property
    def addition_values(self) -> list[int]:
        """The numbers in the addition column: the starter, then the extra
        numbers from the line. Empty for task 1 and before the addition step.
        """
        if self._phase in (Phase.READY, Phase.SELECTING):
            return []
        if not self._ruleset.has_addition_step(self.current_task_type):
            return []

        values = []
        for cell in self._addition_cells():
            values.append(self.value_at(cell))
        return values

    @property
    def subtraction_constant(self) -> int:
        """The magic constant the player subtracts from in this task, or 0
        before the first task starts."""
        if self.current_task_type is None:
            return 0
        return self._ruleset.line_sum(self.current_task_type)

    def value_at(self, cell: Coord) -> int:
        """Return the number in a cell."""
        return self._cube.value_at(cell)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _addition_cells(self) -> list[Coord]:
        """The starter, then the first extra_count target cells of the line."""
        extra_count = self._tasks[self._task_index].extra_count
        return [self.starter] + self._target_cells[:extra_count]

    def _addition_sum(self) -> int:
        """The sum the player subtracts from the constant.

        For task 1 this is just the starter, since there is no addition step.
        """
        total = 0
        for cell in self._addition_cells():
            total += self.value_at(cell)
        return total

    def _check_tasks(self, tasks: list[TaskConfig]) -> None:
        """Check the round's tasks follow the ruleset."""
        tasks_per_round = self._ruleset.tasks_per_round
        if len(tasks) != tasks_per_round:
            raise ValueError(
                f"A round needs {tasks_per_round} tasks, got {len(tasks)}")

        for index, task in enumerate(tasks):
            task_number = index + 1
            allowed = self._ruleset.allowed_extra_counts(task.task_type)
            if task.extra_count not in allowed:
                raise ValueError(
                    f"Task {task_number}: extra count {task.extra_count} is "
                    f"not allowed (must be {allowed.start} to "
                    f"{allowed.stop - 1})")

    def _check_task_sums(self) -> None:
        """Check the starter and targets add up to the task's magic sum."""
        total = self.value_at(self.starter)
        for cell in self._target_cells:
            total += self.value_at(cell)

        if total != self.subtraction_constant:
            raise ValueError(
                f"Task {self.task_number} ({self.current_task_type.name}): "
                f"cells sum to {total}, expected {self.subtraction_constant}")
