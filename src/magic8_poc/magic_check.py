"""Checks that a cube is a most perfect magic cube for a ruleset.

A cube is most perfect when, for the ruleset's magic sums:
    - every cell and its complement add up to the complement sum,
    - every half-line adds up to the half-line sum,
    - every full line adds up to the full-line sum. This covers every
      orthogonal, diagonal and triagonal, whether continuous or split.

Lines are found with TaskSolver, the same geometry the game uses for its
tasks, so this check always agrees with what the player is asked to find.
Cube itself already checks that each number appears exactly once.
"""

from magic8_poc.cube import Cube
from magic8_poc.lines import Coord, TaskSolver
from magic8_poc.number_base import to_display
from magic8_poc.ruleset import CUBE_SIZE, STANDARD_RULESET, Ruleset, TaskType


def find_magic_errors(cube: Cube, ruleset: Ruleset = STANDARD_RULESET) -> list[str]:
    """Return a description of every complement or line with the wrong sum.

    An empty list means the cube is most perfect. Sums in the messages are
    written in the ruleset's number base.
    """
    errors = []

    # Each line passes through several cells, so the same line is found once
    # from each of its cells. Remember the lines already checked (as the set
    # of their cells) so each is checked and reported only once.
    checked_lines: set[frozenset[Coord]] = set()

    for x in range(CUBE_SIZE):
        for y in range(CUBE_SIZE):
            for z in range(CUBE_SIZE):
                solver = TaskSolver((x, y, z))

                for task_type in TaskType:
                    line = solver.get_full_line(task_type)

                    line_key = frozenset(line)
                    if line_key in checked_lines:
                        continue
                    checked_lines.add(line_key)

                    total = 0
                    for cell in line:
                        total += cube.value_at(cell)

                    expected = ruleset.line_sum(task_type)
                    if total != expected:
                        errors.append(
                            f"{task_type.name} through {(x, y, z)} adds up to "
                            f"{to_display(total, ruleset.number_base)}, expected "
                            f"{to_display(expected, ruleset.number_base)}")

    return errors


def is_most_perfect(cube: Cube, ruleset: Ruleset = STANDARD_RULESET) -> bool:
    """Return True if every complement and line has the ruleset's sum."""
    return len(find_magic_errors(cube, ruleset)) == 0
