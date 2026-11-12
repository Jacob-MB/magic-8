"""All drawing and 3D projection for Magic-8.

Renderer draws onto its own off-screen Surface and returns the frame plus
selection geometry to the game controller. It does not process input or
modify game state.
"""

import math
import pygame


class Renderer:
    BACKGROUND = (25, 25, 35)
    WHITE = (240, 240, 240)
    YELLOW = (255, 230, 0)
    PLANE_COLOR = (245, 175, 45)
    RED = (255, 100, 100)

    FACE_DEFINITIONS = [
        ([(.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5), (.5, -.5, .5)], (1, 0, 0), (220, 80, 80)),
        ([(-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5), (-.5, -.5, -.5)], (-1, 0, 0), (80, 180, 220)),
        ([(-.5, .5, -.5), (-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5)], (0, 1, 0), (100, 200, 120)),
        ([(-.5, -.5, .5), (-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5)], (0, -1, 0), (220, 190, 80)),
        ([(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)], (0, 0, 1), (150, 100, 220)),
        ([(.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5)], (0, 0, -1), (100, 180, 180)),
    ]

    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.surface = pygame.Surface((width, height))
        self.center_x, self.center_y = width // 2, height // 2
        self.scale = 55
        self.distance = 18
        self.font = pygame.font.SysFont(None, 26)
        self.value_font = pygame.font.SysFont(None, 22, bold=True)
        self.last_visible_faces = []

    def rotate_point(self, point, game):
        x, y, z = point
        cx, sx = math.cos(game.angle_x), math.sin(game.angle_x)
        y1, z1 = y * cx - z * sx, y * sx + z * cx
        cy, sy = math.cos(game.angle_y), math.sin(game.angle_y)
        return (x * cy + z1 * sy, y1, -x * sy + z1 * cy)

    def project(self, point, game):
        x, y, z = self.rotate_point(point, game)
        denominator = self.distance + z
        if denominator <= 0.1:
            return None
        factor = self.distance / denominator
        return (int(self.center_x + x * self.scale * factor), int(self.center_y - y * self.scale * factor))

    @staticmethod
    def point_in_polygon(point, polygon):
        px, py = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if (yi > py) != (yj > py):
                intersection_x = (xj - xi) * (py - yi) / (yj - yi) + xi
                if px < intersection_x:
                    inside = not inside
            j = i
        return inside

    def generate_faces(self, game):
        faces = []
        visible_cells = game.get_visible_cells()
        for x, y, z in visible_cells:
            center = game.cell_center(x, y, z)
            for corners, normal, normal_color in self.FACE_DEFINITIONS:
                neighbor = (x + normal[0], y + normal[1], z + normal[2])
                if neighbor in visible_cells:
                    continue
                vertices = [(center[0] + cx, center[1] + cy, center[2] + cz) for cx, cy, cz in corners]
                color = self.PLANE_COLOR if game.active_plane is not None else normal_color
                faces.append((vertices, normal, color, (x, y, z)))
        return faces

    def draw_cube(self, game):
        visible_faces = []
        for vertices, normal, color, cell in self.generate_faces(game):
            if self.rotate_point(normal, game)[2] >= 0:
                continue
            rotated = [self.rotate_point(vertex, game) for vertex in vertices]
            average_depth = sum(vertex[2] for vertex in rotated) / 4
            projected = [self.project(vertex, game) for vertex in vertices]
            if None not in projected:
                visible_faces.append((average_depth, projected, color, cell))
        visible_faces.sort(key=lambda face: face[0], reverse=True)
        self.last_visible_faces = visible_faces
        for depth, points, color, cell in visible_faces:
            pygame.draw.polygon(self.surface, color, points)
            pygame.draw.polygon(self.surface, (25, 25, 25), points, 1)
        return visible_faces

    def draw_cube_values(self, game, visible_faces):
        cell_faces = {}
        for depth, polygon, color, cell in visible_faces:
            tile = game.cube.get(*cell)
            if not tile.shown:
                continue
            cell_faces.setdefault(cell, []).append((depth, polygon, tile.value))

        for cell, faces in cell_faces.items():
            faces.sort(key=lambda face: face[0])
            for depth, polygon, value in faces:
                center_x = sum(point[0] for point in polygon) / len(polygon)
                center_y = sum(point[1] for point in polygon) / len(polygon)
                center = (center_x, center_y)
                occluded = False
                for other_depth, other_polygon, other_color, other_cell in visible_faces:
                    if other_cell != cell and other_depth < depth and self.point_in_polygon(center, other_polygon):
                        occluded = True
                        break
                if occluded:
                    continue
                octal_value = format(value, "o")

                text = self.value_font.render(octal_value, True, self.WHITE)
                rect = text.get_rect(center=(int(center_x), int(center_y)))
                outline = self.value_font.render(str(value), True, (20, 20, 20))
                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    self.surface.blit(outline, (rect.x + ox, rect.y + oy))
                self.surface.blit(text, rect)
                break

    def draw_selection(self, game):
        center = game.cell_center(*game.selected)
        corners = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
                   (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
        projected = [self.project((center[0] + c[0], center[1] + c[1], center[2] + c[2]), game) for c in corners]
        for start, end in edges:
            if projected[start] is not None and projected[end] is not None:
                pygame.draw.line(self.surface, self.YELLOW, projected[start], projected[end], 4)
        marker = self.project(center, game)
        if marker is not None:
            pygame.draw.circle(self.surface, self.YELLOW, marker, 5)

    def draw_information(self, game):
        if game.active_plane is None:
            plane_text = "Plane mode: OFF"
        else:
            name = "XYZ"[game.active_plane]
            plane_text = f"Plane mode: {name} ({name} = {game.selected[game.active_plane]})"
        tile = game.cube.get(*game.selected)
        value_text = f"Selected value: {tile.value if tile.shown else 'Hidden'}"
        elapsed = game.get_elapsed_time()
        minutes, seconds = divmod(int(elapsed), 60)
        timer_text = f"Time: {minutes:02d}:{seconds:02d}"
        instructions = [
            "Left mouse drag: Rotate cube", "Right mouse click: Select cell",
            "Arrow keys: Rotate cube", "W A S D: Move selection",
            "ENTER: Guess selected cube value", "1: Toggle X plane | 2: Toggle Y plane | 3: Toggle Z plane",
            plane_text, f"Selected cell: {tuple(game.selected)}", value_text,
            f"Revealed: {game.cube.revealed_count()}/{game.size ** 3}",
            "Q / E: Previous / next parallel plane", f"Dimensions: {game.size} x {game.size} x {game.size}",
        ]
        for i, message in enumerate(instructions):
            color = self.YELLOW if i == 6 and game.active_plane is not None else self.WHITE
            self.surface.blit(self.font.render(message, True, color), (20, 20 + i * 27))
        timer_surface = pygame.font.SysFont(None, 34, bold=True).render(timer_text, True, self.YELLOW)
        self.surface.blit(timer_surface, (self.width - timer_surface.get_width() - 25, 20))

    def draw_value_prompt(self, game):
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.surface.blit(overlay, (0, 0))
        box_width, box_height = 450, 220
        box_x, box_y = (self.width - box_width) // 2, (self.height - box_height) // 2
        pygame.draw.rect(self.surface, (50, 50, 65), (box_x, box_y, box_width, box_height), border_radius=10)
        pygame.draw.rect(self.surface, self.WHITE, (box_x, box_y, box_width, box_height), 2, border_radius=10)
        prompt_font = pygame.font.SysFont(None, 36)
        input_font = pygame.font.SysFont(None, 32)
        lines = [
            (prompt_font, f"Guess value for cube {tuple(game.selected)}:", self.WHITE, 25),
            (input_font, game.value_input + "|", self.YELLOW, 85),
            (self.font, "Enter: Submit    Esc: Cancel", self.WHITE, 130),
        ]
        for font, message, color, offset in lines:
            self.surface.blit(font.render(message, True, color), (box_x + 25, box_y + offset))
        if game.value_error:
            self.surface.blit(self.font.render(game.value_error, True, self.RED), (box_x + 25, box_y + 175))

    def render(self, game):
        """Render one frame and return it, plus input geometry, to the controller."""
        self.surface.fill(self.BACKGROUND)
        visible_faces = self.draw_cube(game)
        self.draw_cube_values(game, visible_faces)
        self.draw_selection(game)
        self.draw_information(game)
        if game.editing_value:
            self.draw_value_prompt(game)

        # Cache projected cell centres so controller navigation does not need
        # to call renderer.project() or receive a renderer callback.
        projected_centers = {
            cell: self.project(game.cell_center(*cell), game)
            for cell in game.get_visible_cells()
        }

        return {
            "surface": self.surface,
            "visible_faces": visible_faces,
            "projected_centers": projected_centers,
        }
