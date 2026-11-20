"""Rendering Module: draws the 3D cube and the round state as a 2D view.

The renderer reads the round (through Round's read-only properties) and the
view settings chosen by the player (rotation, isolated layer, cursor). It
draws onto its own off-screen surface and returns it as a RenderedFrame. It
never changes the round or the view, and never handles input.

How the 3D cube is projected is this module's secret. The UI turns a mouse
position into a cell, or a cell into a screen position, only through
RenderedFrame.cell_at and RenderedFrame.screen_position.
"""

import math
from dataclasses import dataclass, field

import pygame

from magic8_poc.game_round import Round
from magic8_poc.lines import Coord
from magic8_poc.number_base import to_display
from magic8_poc.ruleset import CUBE_SIZE

# Display colours, named by what they show so the colours can change freely.
BACKGROUND_COLOUR = (25, 25, 35)
HIDDEN_FILL = (120, 130, 150)
LAYER_FILL = (150, 140, 110)
STARTER_FILL = (235, 190, 60)
CORRECT_FILL = (80, 180, 100)
INCORRECT_FILL = (200, 80, 80)
FACE_EDGE_COLOUR = (25, 25, 25)
CURSOR_COLOUR = (255, 230, 0)
NUMBER_TEXT_COLOUR = (240, 240, 240)
NUMBER_OUTLINE_COLOUR = (20, 20, 20)

# Each face of a unit cell: its four corners (relative to the cell centre),
# its outward normal, and how bright it is drawn so the player can tell the
# cube's sides apart.
FACE_DEFINITIONS = [
    ([(.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5), (.5, -.5, .5)], (1, 0, 0), 0.85),
    ([(-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5), (-.5, -.5, -.5)], (-1, 0, 0), 0.85),
    ([(-.5, .5, -.5), (-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5)], (0, 1, 0), 1.0),
    ([(-.5, -.5, .5), (-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5)], (0, -1, 0), 0.6),
    ([(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)], (0, 0, 1), 0.7),
    ([(.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5)], (0, 0, -1), 0.95),
]

# Corners and edges of a unit cell, used to outline the cursor.
CELL_CORNERS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
                (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
CELL_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
              (0, 4), (1, 5), (2, 6), (3, 7)]


@dataclass
class View:
    """How the player is looking at the cube. The UI changes it from input.

    Attributes:
        angle_x: Rotation about the screen's horizontal axis, in radians.
        angle_y: Rotation about the screen's vertical axis, in radians.
        layer_axis: The axis of the isolated layer (0 = x, 1 = y, 2 = z),
            or None to show the whole cube.
        layer_index: Which layer along layer_axis is shown.
        cursor: The cell the keyboard cursor is on.
    """

    angle_x: float = -0.45
    angle_y: float = 0.55
    layer_axis: int | None = None
    layer_index: int = 0
    cursor: Coord = (0, 0, 0)

    def visible_cells(self) -> set[Coord]:
        """Cells drawn in this view: the whole cube, or one layer of it."""
        cells = set()
        for x in range(CUBE_SIZE):
            for y in range(CUBE_SIZE):
                for z in range(CUBE_SIZE):
                    cell = (x, y, z)
                    if self.layer_axis is None or cell[self.layer_axis] == self.layer_index:
                        cells.add(cell)
        return cells


@dataclass
class DrawnFace:
    """One cell face as drawn on screen."""

    depth: float                     # Distance from the viewer; larger is further
    polygon: list[tuple[int, int]]   # Screen corners
    cell: Coord
    fill: tuple[int, int, int]


@dataclass
class RenderedFrame:
    """A drawn frame, plus what the UI needs to map the screen to cells."""

    surface: pygame.Surface
    faces: list[DrawnFace]                                    # Drawn back to front
    cell_centres: dict[Coord, tuple[int, int]] = field(default_factory=dict)

    def cell_at(self, point: tuple[int, int]) -> Coord | None:
        """Return the front-most drawn cell under a screen point, if any."""
        # Faces are stored back to front, so check them front to back.
        for face in reversed(self.faces):
            if _point_in_polygon(point, face.polygon):
                return face.cell
        return None

    def screen_position(self, cell: Coord) -> tuple[int, int] | None:
        """Return where a visible cell's centre was drawn, if it was drawn."""
        return self.cell_centres.get(cell)


class Renderer:
    """Draws frames of a fixed size."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height))
        self.centre_x = width // 2
        self.centre_y = height // 2
        self.scale = 55
        self.distance = 18
        # Font(None) is pygame's built-in font, which also works in the
        # browser build (system fonts are not available there).
        self.number_font = pygame.font.Font(None, 24)

    def render(self, game_round: Round, view: View) -> RenderedFrame:
        """Draw one frame of the cube for the round and view."""
        self.surface.fill(BACKGROUND_COLOUR)

        visible_cells = view.visible_cells()
        faces = self._draw_cube(game_round, view, visible_cells)
        self._draw_numbers(game_round, faces)
        self._draw_cursor(view)

        cell_centres = {}
        for cell in visible_cells:
            position = self._project(self._cell_centre(cell), view)
            if position is not None:
                cell_centres[cell] = position

        return RenderedFrame(self.surface, faces, cell_centres)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    @staticmethod
    def _cell_centre(cell: Coord) -> tuple[float, float, float]:
        """Position of a cell's centre, with the cube centred on the origin."""
        middle = (CUBE_SIZE - 1) / 2
        x, y, z = cell
        return (x - middle, y - middle, z - middle)

    @staticmethod
    def _rotate(point, view: View) -> tuple[float, float, float]:
        x, y, z = point

        # Rotate about the x axis.
        cos_x = math.cos(view.angle_x)
        sin_x = math.sin(view.angle_x)
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x

        # Then rotate about the y axis.
        cos_y = math.cos(view.angle_y)
        sin_y = math.sin(view.angle_y)
        return (x * cos_y + z1 * sin_y, y1, -x * sin_y + z1 * cos_y)

    def _project(self, point, view: View) -> tuple[int, int] | None:
        """Project a 3D point to the screen, or None if it is behind the viewer."""
        x, y, z = self._rotate(point, view)
        denominator = self.distance + z
        if denominator <= 0.1:
            return None
        factor = self.distance / denominator
        screen_x = int(self.centre_x + x * self.scale * factor)
        screen_y = int(self.centre_y - y * self.scale * factor)
        return (screen_x, screen_y)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    @staticmethod
    def _cell_fill(game_round: Round, cell: Coord, layer_isolated: bool):
        """Base fill colour of a cell, from its state in the round."""
        if cell == game_round.starter:
            return STARTER_FILL
        if cell in game_round.incorrect_cells:
            return INCORRECT_FILL
        if cell in game_round.correct_cells:
            return CORRECT_FILL
        if layer_isolated:
            return LAYER_FILL
        return HIDDEN_FILL

    def _draw_cube(self, game_round: Round, view: View, visible_cells):
        """Draw every outward-facing face of the visible cells, back to front."""
        layer_isolated = view.layer_axis is not None
        faces = []
        for cell in visible_cells:
            centre = self._cell_centre(cell)
            base_fill = self._cell_fill(game_round, cell, layer_isolated)

            for corners, normal, brightness in FACE_DEFINITIONS:
                # Skip faces hidden against a neighbouring visible cell.
                neighbour = (cell[0] + normal[0], cell[1] + normal[1], cell[2] + normal[2])
                if neighbour in visible_cells:
                    continue

                # Skip faces pointing away from the viewer.
                if self._rotate(normal, view)[2] >= 0:
                    continue

                vertices = []
                for corner_x, corner_y, corner_z in corners:
                    vertices.append((centre[0] + corner_x, centre[1] + corner_y, centre[2] + corner_z))

                polygon = []
                depth_total = 0.0
                for vertex in vertices:
                    depth_total += self._rotate(vertex, view)[2]
                    polygon.append(self._project(vertex, view))
                if None in polygon:
                    continue

                fill = (int(base_fill[0] * brightness),
                        int(base_fill[1] * brightness),
                        int(base_fill[2] * brightness))
                faces.append(DrawnFace(depth_total / len(vertices), polygon, cell, fill))

        # Painter's algorithm: draw the furthest faces first.
        faces.sort(key=lambda face: face.depth, reverse=True)
        for face in faces:
            pygame.draw.polygon(self.surface, face.fill, face.polygon)
            pygame.draw.polygon(self.surface, FACE_EDGE_COLOUR, face.polygon, 1)
        return faces

    def _draw_numbers(self, game_round: Round, faces: list[DrawnFace]) -> None:
        """Write each revealed cell's number on its nearest unblocked face."""
        base = game_round.ruleset.number_base
        revealed = game_round.revealed_cells

        # Group the drawn faces of each revealed cell.
        faces_by_cell: dict[Coord, list[DrawnFace]] = {}
        for face in faces:
            if face.cell in revealed:
                faces_by_cell.setdefault(face.cell, []).append(face)

        for cell, cell_faces in faces_by_cell.items():
            # Try the nearest face first.
            cell_faces.sort(key=lambda face: face.depth)
            for face in cell_faces:
                centre = _polygon_centre(face.polygon)
                if self._is_covered(face, centre, faces):
                    continue
                self._draw_number(to_display(game_round.value_at(cell), base), centre)
                break

    @staticmethod
    def _is_covered(face: DrawnFace, point, faces: list[DrawnFace]) -> bool:
        """Return True if another cell's nearer face is drawn over the point."""
        for other in faces:
            if other.cell != face.cell and other.depth < face.depth:
                if _point_in_polygon(point, other.polygon):
                    return True
        return False

    def _draw_number(self, text: str, centre) -> None:
        """Draw outlined text so it reads on any fill colour."""
        label = self.number_font.render(text, True, NUMBER_TEXT_COLOUR)
        outline = self.number_font.render(text, True, NUMBER_OUTLINE_COLOUR)
        rect = label.get_rect(center=(int(centre[0]), int(centre[1])))
        for offset_x, offset_y in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            self.surface.blit(outline, (rect.x + offset_x, rect.y + offset_y))
        self.surface.blit(label, rect)

    def _draw_cursor(self, view: View) -> None:
        """Outline the cursor cell."""
        centre = self._cell_centre(view.cursor)
        corners = []
        for corner_x, corner_y, corner_z in CELL_CORNERS:
            point = (centre[0] + corner_x, centre[1] + corner_y, centre[2] + corner_z)
            corners.append(self._project(point, view))

        for start, end in CELL_EDGES:
            if corners[start] is not None and corners[end] is not None:
                pygame.draw.line(self.surface, CURSOR_COLOUR, corners[start], corners[end], 3)


def _polygon_centre(polygon) -> tuple[float, float]:
    total_x = 0
    total_y = 0
    for x, y in polygon:
        total_x += x
        total_y += y
    return (total_x / len(polygon), total_y / len(polygon))


def _point_in_polygon(point, polygon) -> bool:
    """Return whether a screen point lies inside a polygon (ray casting)."""
    point_x, point_y = point
    inside = False
    previous = len(polygon) - 1
    for current in range(len(polygon)):
        x_current, y_current = polygon[current]
        x_previous, y_previous = polygon[previous]
        if (y_current > point_y) != (y_previous > point_y):
            crossing_x = (x_previous - x_current) * (point_y - y_current) / (y_previous - y_current) + x_current
            if point_x < crossing_x:
                inside = not inside
        previous = current
    return inside
