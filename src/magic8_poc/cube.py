"""Cube Representation Module: the numbers in the magic cube.

How the numbers are stored is this module's secret. The rest of the game
reads them only through Cube.value_at, so the storage can change without
affecting other modules.
"""

from magic8_poc.lines import Coord
from magic8_poc.ruleset import CUBE_SIZE

CELL_COUNT = CUBE_SIZE ** 3


class Cube:
    """The 8x8x8 magic cube's numbers. They never change once created."""

    def __init__(self, values: list[list[list[int]]]):
        """Create a cube from nested lists indexed values[x][y][z].

        Raises:
            ValueError: If the values are not 8x8x8, or do not contain each
                number from 1 to 512 exactly once.
        """
        self._check_shape(values)

        # Store a copy so later changes to the caller's lists cannot change
        # the cube.
        self._values: list[list[list[int]]] = []
        for x in range(CUBE_SIZE):
            plane = []
            for y in range(CUBE_SIZE):
                row = list(values[x][y])
                plane.append(row)
            self._values.append(plane)

        self._check_numbers()

    def value_at(self, cell: Coord) -> int:
        """Return the number in a cell."""
        x, y, z = cell
        return self._values[x][y][z]

    def _check_shape(self, values: list[list[list[int]]]) -> None:
        """Check the values are nested CUBE_SIZE x CUBE_SIZE x CUBE_SIZE."""
        message = f"Cube must be {CUBE_SIZE}x{CUBE_SIZE}x{CUBE_SIZE}"

        if len(values) != CUBE_SIZE:
            raise ValueError(message)
        for plane in values:
            if len(plane) != CUBE_SIZE:
                raise ValueError(message)
            for row in plane:
                if len(row) != CUBE_SIZE:
                    raise ValueError(message)

    def _check_numbers(self) -> None:
        """Check every number from 1 to 512 appears exactly once."""
        numbers = []
        for plane in self._values:
            for row in plane:
                numbers.extend(row)

        if sorted(numbers) != list(range(1, CELL_COUNT + 1)):
            raise ValueError(
                f"Cube must contain each number from 1 to {CELL_COUNT} "
                "exactly once")
