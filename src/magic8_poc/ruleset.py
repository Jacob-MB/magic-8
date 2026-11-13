"""Ruleset Module: the rules of a gameplay round.

This module holds the rules from Dr. Rapoport's game: the cube order, the
number of tasks in a round, the line types a task can use, the magic sums
each line type adds up to, and how many extra numbers a task may add.
Other modules ask this module about the rules instead of writing them into
their own logic, so a rule change only needs to be made here.

All values are plain integers. Showing them in octal is the job of the
number base translation module.
"""

from enum import Enum

# Number of cells along each edge of the cube.
CUBE_SIZE = 8

# Number of tasks in a round.
TASKS_PER_ROUND = 8

# Magic sums, written in octal to match the rules.
COMPLEMENT_SUM = 0o1001  # A cell plus its complement (513 in decimal)
HALF_LINE_SUM = 0o2002   # The 4 cells of a half-line (1026 in decimal)
LINE_SUM = 0o4004        # The 8 cells of a full line (2052 in decimal)


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


def line_sum(task_type: TaskType) -> int:
    """Return the magic sum that the starter and a task's cells add up to.

    This is also the number the player subtracts from in the task.
    """
    if task_type is TaskType.COMPLEMENT:
        return COMPLEMENT_SUM
    if task_type in HALF_LINE_TYPES:
        return HALF_LINE_SUM
    return LINE_SUM


def has_addition_step(task_type: TaskType) -> bool:
    """Return True if the player adds numbers before subtracting.

    The complement task goes straight to subtraction, since the player
    subtracts the starter alone from 1001 (octal).
    """
    return task_type is not TaskType.COMPLEMENT


def allowed_extra_counts(task_type: TaskType) -> range:
    """Return how many extra numbers the player may add in a task.

    The limit depends on the kind of line (FR_ChooseExtra), and always
    leaves at least one of the line's numbers for the player to find
    through the subtraction:
        complement: 0 (there is no addition step)
        half-line (3 other cells): 1 to 2
        full line (7 other cells): 1 to 5
    """
    if task_type is TaskType.COMPLEMENT:
        return range(0, 1)
    if task_type in HALF_LINE_TYPES:
        return range(1, 3)
    return range(1, 6)
