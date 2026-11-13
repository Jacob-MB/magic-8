"""Ruleset Module: the rules of a gameplay round.

This module holds the rules from Dr. Rapoport's game. A Ruleset object
holds the rules that a round follows: the number of tasks, the magic sums
each kind of line adds up to, and how many extra numbers a task may add.
Each Round is given a Ruleset, so different rounds (for example, future
game modes) can follow different rules. STANDARD_RULESET holds the rules
of the main game.

The line types (TaskType) and the cube size are the same for every ruleset
and are kept as module-level definitions.

All values are plain integers. Showing them in the player's number base is
the job of number_base.py.
"""

from dataclasses import dataclass
from enum import Enum

# Number of cells along each edge of the cube.
CUBE_SIZE = 8


class TaskType(Enum):
    """Line types that a task can ask the player to complete.

    SAME / DIFF describe whether two axes change in the same direction
    (both increase) or in different directions (one increases while the
    other decreases) along the line. See lines.py for the coordinate
    convention.
    """

    # Task 1
    COMPLEMENT = 1

    # Task 2: the half of the line that holds the starter (coordinates
    # 0-3 or 4-7 on that axis), which always reaches an outer edge.
    HALF_ORTHOGONAL_X = 2
    HALF_ORTHOGONAL_Y = 3
    HALF_ORTHOGONAL_Z = 4

    # Task 3
    ORTHOGONAL_X = 5
    ORTHOGONAL_Y = 6
    ORTHOGONAL_Z = 7

    # Tasks 4, 5 and 6. Continuous vs. split is a matter of where the line
    # sits in the cube, not a different line: see TaskSolver.is_continuous.
    DIAGONAL_XY_SAME = 8
    DIAGONAL_XY_DIFF = 9
    DIAGONAL_XZ_SAME = 10
    DIAGONAL_XZ_DIFF = 11
    DIAGONAL_YZ_SAME = 12
    DIAGONAL_YZ_DIFF = 13

    # Tasks 7 and 8. A triagonal direction is a sign vector (+-1, +-1, +-1)
    # up to negation, so exactly these four pass through any cell.
    TRIAGONAL_XYZ_SAME = 14
    TRIAGONAL_XY_SAME_Z_DIFF = 15
    TRIAGONAL_XZ_SAME_Y_DIFF = 16
    TRIAGONAL_YZ_SAME_X_DIFF = 17


HALF_LINE_TYPES = (
    TaskType.HALF_ORTHOGONAL_X,
    TaskType.HALF_ORTHOGONAL_Y,
    TaskType.HALF_ORTHOGONAL_Z,
)


@dataclass(frozen=True)
class Ruleset:
    """The rules a round follows. A ruleset cannot be changed once created.

    Attributes:
        tasks_per_round: Number of tasks in a round.
        complement_sum: What a cell and its complement add up to.
        half_line_sum: What the 4 cells of a half-line add up to.
        full_line_sum: What the 8 cells of a full line add up to.
        half_line_extra_counts: How many extra numbers a half-line task
            may add.
        full_line_extra_counts: How many extra numbers a full-line task
            may add.
    """

    tasks_per_round: int
    complement_sum: int
    half_line_sum: int
    full_line_sum: int
    half_line_extra_counts: range
    full_line_extra_counts: range

    def line_sum(self, task_type: TaskType) -> int:
        """Return the magic sum that the starter and a task's cells add up to.

        This is also the number the player subtracts from in the task.
        """
        if task_type is TaskType.COMPLEMENT:
            return self.complement_sum
        if task_type in HALF_LINE_TYPES:
            return self.half_line_sum
        return self.full_line_sum

    def has_addition_step(self, task_type: TaskType) -> bool:
        """Return True if the player adds numbers before subtracting.

        The complement task goes straight to subtraction, since the player
        subtracts the starter alone from the complement sum.
        """
        return task_type is not TaskType.COMPLEMENT

    def allowed_extra_counts(self, task_type: TaskType) -> range:
        """Return how many extra numbers the player may add in a task.

        The limit depends on the kind of line (FR_ChooseExtra). The
        complement task has no addition step, so it always allows 0.
        """
        if task_type is TaskType.COMPLEMENT:
            return range(0, 1)
        if task_type in HALF_LINE_TYPES:
            return self.half_line_extra_counts
        return self.full_line_extra_counts


# The rules of the main game. Each extra-count limit leaves at least one of
# the line's numbers for the player to find through the subtraction.
STANDARD_RULESET = Ruleset(
    tasks_per_round=8,
    complement_sum=0o1001,          # 513 in decimal
    half_line_sum=0o2002,           # 1026 in decimal
    full_line_sum=0o4004,           # 2052 in decimal
    half_line_extra_counts=range(1, 3),  # 1 to 2 (3 other cells)
    full_line_extra_counts=range(1, 6),  # 1 to 5 (7 other cells)
)
