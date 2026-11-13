"""Geometry of the task target cells in the 8x8x8 magic cube.

Given a starter cell and a task type, compute the cells the player must
select. All line arithmetic is modulo 8, so broken (split) lines wrap around
the cube's boundaries.
"""

from enum import Enum

CUBE_SIZE = 8
HALF = CUBE_SIZE // 2

Coord = tuple[int, int, int]


class TaskType(Enum):
    """Line types that a task can ask the player to complete.

    Coordinates match the POC renderer (at zero rotation):
        x: 0 -> 7 runs left -> right
        y: 0 -> 7 runs bottom -> top
        z: 0 -> 7 runs front -> back
    Therefore, (0, 0, 0) is the front, bottom, left of the cube.

    SAME / DIFF describe whether two axes change in the same direction
    (both increase) or in different directions (one increases while the
    other decreases) along the line.
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


# Step direction of each full line type.
_DIRECTIONS: dict[TaskType, Coord] = {
    TaskType.ORTHOGONAL_X: (1, 0, 0),
    TaskType.ORTHOGONAL_Y: (0, 1, 0),
    TaskType.ORTHOGONAL_Z: (0, 0, 1),
    TaskType.DIAGONAL_XY_SAME: (1, 1, 0),
    TaskType.DIAGONAL_XY_DIFF: (1, -1, 0),
    TaskType.DIAGONAL_XZ_SAME: (1, 0, 1),
    TaskType.DIAGONAL_XZ_DIFF: (1, 0, -1),
    TaskType.DIAGONAL_YZ_SAME: (0, 1, 1),
    TaskType.DIAGONAL_YZ_DIFF: (0, 1, -1),
    TaskType.TRIAGONAL_XYZ_SAME: (1, 1, 1),
    TaskType.TRIAGONAL_XY_SAME_Z_DIFF: (1, 1, -1),
    TaskType.TRIAGONAL_XZ_SAME_Y_DIFF: (1, -1, 1),
    TaskType.TRIAGONAL_YZ_SAME_X_DIFF: (-1, 1, 1),
}

# Axis index (0 = x, 1 = y, 2 = z) of each half-orthogonal type.
_HALF_AXES: dict[TaskType, int] = {
    TaskType.HALF_ORTHOGONAL_X: 0,
    TaskType.HALF_ORTHOGONAL_Y: 1,
    TaskType.HALF_ORTHOGONAL_Z: 2,
}


class TaskSolver:
    """Computes the target cells of each task type for one starter cell."""

    def __init__(self, starter: Coord):
        if (len(starter) != 3
                or not all(isinstance(c, int) and 0 <= c < CUBE_SIZE
                           for c in starter)):
            raise ValueError(f"Starter must be 3 integers in 0..7, got {starter!r}")
        self.starter: Coord = tuple(starter)

    def get_correct_cell_coords(self, task_type: TaskType) -> list[Coord]:
        """Return the cells the user must select (the starter is excluded)."""
        if task_type is TaskType.COMPLEMENT:
            return [self._get_complement()]
        if task_type in _HALF_AXES:
            return self._get_half_orthogonal(_HALF_AXES[task_type])
        if task_type in _DIRECTIONS:
            return self._get_full_line(_DIRECTIONS[task_type])
        raise ValueError(f"Task type not recognized: {task_type!r}")

    def get_full_line(self, task_type: TaskType) -> list[Coord]:
        """Return the starter followed by the task's target cells."""
        return [self.starter] + self.get_correct_cell_coords(task_type)

    def is_continuous(self, task_type: TaskType) -> bool:
        """Return True if the line stays inside the cube without wrapping.

        Orthogonals and half-orthogonals are always continuous. A diagonal
        or triagonal is continuous only when every changing axis is the same
        number of steps from its starting edge (0 when the axis increases,
        7 when it decreases); otherwise the line is split.
        """
        if task_type is TaskType.COMPLEMENT:
            raise ValueError("A complement is a single cell, not a line")
        if task_type in _HALF_AXES:
            return True
        if task_type not in _DIRECTIONS:
            raise ValueError(f"Task type not recognized: {task_type!r}")

        direction = _DIRECTIONS[task_type]

        # For each axis the line moves along, count how many steps the
        # starter is from the edge where that axis begins.
        steps_from_edge = []
        for axis in range(3):
            step = direction[axis]
            coord = self.starter[axis]

            if step == 0:
                # This axis does not change along the line, so skip it.
                continue

            if step == 1:
                # The axis increases, so the line begins at coordinate 0.
                steps_from_edge.append(coord)
            else:
                # The axis decreases, so the line begins at coordinate 7.
                steps_from_edge.append((CUBE_SIZE - 1) - coord)

        # The line is continuous only if every moving axis is the same
        # number of steps from its starting edge.
        first = steps_from_edge[0]
        for steps in steps_from_edge:
            if steps != first:
                return False
        return True

    def _get_complement(self) -> Coord:
        """Return the starter's complementary cell (task 1).

        The complement is found by moving 4 cells along every axis, wrapping
        around the cube with modulo 8. For example, the complement of
        (1, 2, 3) is (5, 6, 7), and the complement of (6, 0, 5) is (2, 4, 1).
        The starter and its complement always sum to 1001 (octal).
        """
        x, y, z = self.starter

        complement_x = (x + HALF) % CUBE_SIZE
        complement_y = (y + HALF) % CUBE_SIZE
        complement_z = (z + HALF) % CUBE_SIZE
        return (complement_x, complement_y, complement_z)

    def _get_half_orthogonal(self, axis: int) -> list[Coord]:
        """Return the 3 other cells in the starter's half-line (task 2).

        An orthogonal line along one axis is split into two halves:
        coordinates 0-3 and coordinates 4-7 on that axis. The half-line is
        whichever half holds the starter, so it always reaches an outer edge
        of the cube and never wraps around. The 4 cells of a half-line sum
        to 2002 (octal).

        Example: for starter (1, 2, 3) along the x axis, the half-line is
        x = 0..3, so the cells returned are (0, 2, 3), (2, 2, 3), (3, 2, 3).

        Args:
            axis: The axis the half-line runs along (0 = x, 1 = y, 2 = z).
        """
        starter_coord = self.starter[axis]

        # Find the first coordinate of the starter's half: 0 if the starter
        # is in 0-3, or 4 if it is in 4-7.
        if starter_coord < HALF:
            half_start = 0
        else:
            half_start = HALF

        cells = []
        for coord in range(half_start, half_start + HALF):
            # The starter is already known, so it is not a target cell.
            if coord == starter_coord:
                continue

            # Copy the starter and change only the coordinate on this axis.
            cell = list(self.starter)
            cell[axis] = coord
            cells.append(tuple(cell))
        return cells

    def _get_full_line(self, direction: Coord) -> list[Coord]:
        x, y, z = self.starter
        dx, dy, dz = direction

        # Take 7 steps from the starter along the direction. Wrapping with
        # modulo 8 lets a split line continue on the opposite side of the cube.
        cells = []
        for step in range(1, CUBE_SIZE):
            new_x = (x + step * dx) % CUBE_SIZE
            new_y = (y + step * dy) % CUBE_SIZE
            new_z = (z + step * dz) % CUBE_SIZE
            cells.append((new_x, new_y, new_z))
        return cells
