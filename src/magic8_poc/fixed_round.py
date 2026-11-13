"""The hardcoded round used by the proof of concept.

The final game chooses the continuous plane, starter, and lines at random. For
the PoC every round is the same, so these values never change.
"""

from dataclasses import dataclass

from magic8_poc.lines import Coord, Plane
from magic8_poc.ruleset import TaskType


@dataclass(frozen=True)
class TaskConfig:
    """One task in a round.

    task_type: The line (or complement) the player must complete.
    extra_count: How many numbers from the line, besides the starter, the
        player adds together before the subtraction step. Task 1 has none.
    """

    task_type: TaskType
    extra_count: int


# The x and y axes form the continuous plane, so z is the axis not in the
# plane. The task list below is written to match this plane.
CONTINUOUS_PLANE = Plane.XY

# Chosen so that the task 8 triagonal is split (it wraps around the cube).
STARTER: Coord = (2, 5, 1)

TASKS: list[TaskConfig] = [
    # Task 1: the starter's complement.
    TaskConfig(TaskType.COMPLEMENT, extra_count=0),
    # Task 2: half-orthogonal on an axis of the continuous plane.
    TaskConfig(TaskType.HALF_ORTHOGONAL_X, extra_count=1),
    # Task 3: orthogonal on the axis not in the plane.
    TaskConfig(TaskType.ORTHOGONAL_Z, extra_count=2),
    # Task 4: diagonal using both axes of the plane.
    TaskConfig(TaskType.DIAGONAL_XY_SAME, extra_count=2),
    # Task 5: diagonal using one plane axis (x) and the off-plane axis.
    TaskConfig(TaskType.DIAGONAL_XZ_SAME, extra_count=2),
    # Task 6: diagonal using the other plane axis (y) and the off-plane axis.
    TaskConfig(TaskType.DIAGONAL_YZ_DIFF, extra_count=2),
    # Task 7: a triagonal.
    TaskConfig(TaskType.TRIAGONAL_XYZ_SAME, extra_count=2),
    # Task 8: a split triagonal different from task 7.
    TaskConfig(TaskType.TRIAGONAL_XY_SAME_Z_DIFF, extra_count=2),
]
