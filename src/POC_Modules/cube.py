"""Cube data model for Magic-8.

Each CubeTile stores its correct puzzle value and whether that value has been
revealed. CubeGrid owns the 8 x 8 x 8 collection of tiles.
"""

from dataclasses import dataclass
from typing import Callable, Optional


CUBE_SIZE = 8


@dataclass
class CubeTile:
    """One cell in the 8 x 8 x 8 cube."""

    value: int
    shown: bool = False

    def check_answer(self, answer: int) -> bool:
        """Reveal this tile if answer matches its stored correct value."""
        if answer == self.value:
            self.shown = True
            return True
        return False


class CubeGrid:
    """Stores the 512 CubeTile objects, indexed as tiles[x][y][z]."""

    def __init__(
        self,
        size: int = CUBE_SIZE,
        value_factory: Optional[Callable[[int, int, int], int]] = None,
    ) -> None:
        self.size = size
        if value_factory is None:
            # Placeholder puzzle data: replace this with the intended puzzle
            # solution when the actual Magic-8 cube values have been defined.
            value_factory = lambda x, y, z: (x + y + z) % 4096

        self.tiles = [
            [
                [CubeTile(int(value_factory(x, y, z))) for z in range(size)]
                for y in range(size)
            ]
            for x in range(size)
        ]

    def get(self, x: int, y: int, z: int) -> CubeTile:
        if not self.in_bounds((x, y, z)):
            raise IndexError(f"Cube coordinate {(x, y, z)} is out of bounds")
        return self.tiles[x][y][z]

    def in_bounds(self, cell: tuple[int, int, int]) -> bool:
        return all(0 <= coordinate < self.size for coordinate in cell)

    def is_exterior(self, cell: tuple[int, int, int]) -> bool:
        x, y, z = cell
        last = self.size - 1
        return x in (0, last) or y in (0, last) or z in (0, last)

    def all_cells(self):
        for x in range(self.size):
            for y in range(self.size):
                for z in range(self.size):
                    yield (x, y, z)

    def revealed_count(self) -> int:
        return sum(self.get(*cell).shown for cell in self.all_cells())
