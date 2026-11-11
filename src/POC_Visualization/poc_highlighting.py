import pygame
import math
import sys

pygame.init()

# --------------------------------------------------
# WINDOW SETTINGS
# --------------------------------------------------

WIDTH, HEIGHT = 1000, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Magic-8 - 3D Cube Explorer")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 26)

BACKGROUND = (25, 25, 35)
WHITE = (240, 240, 240)
YELLOW = (255, 230, 0)
PLANE_COLOR = (245, 175, 45)
GREEN = (100, 230, 130)
RED = (255, 100, 100)

CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

# --------------------------------------------------
# CUBE SETTINGS
# --------------------------------------------------

CUBE_SIZE = 8
SCALE = 55
DISTANCE = 18

# 1 = cube exists, 0 = empty
voxels = [
    [
        [1 for z in range(CUBE_SIZE)]
        for y in range(CUBE_SIZE)
    ]
    for x in range(CUBE_SIZE)
]

# Each individual cube has its own integer value.
# None means that no value has been entered yet.
cube_values = [
    [
        [None for z in range(CUBE_SIZE)]
        for y in range(CUBE_SIZE)
    ]
    for x in range(CUBE_SIZE)
]

# Currently selected cell
selected = [0, 0, 0]

# None = normal mode
# 0 = X plane
# 1 = Y plane
# 2 = Z plane
active_plane = None

# Value editing settings
editing_value = False
value_input = ""
value_error = ""

angle_x = -0.45
angle_y = 0.55

ROTATION_SPEED = 0.04
MOUSE_SENSITIVITY = 0.01

dragging = False
last_mouse_x = 0
last_mouse_y = 0

# --------------------------------------------------
# FACE DEFINITIONS
# --------------------------------------------------

FACE_DEFINITIONS = [
    (
        [(0.5, -0.5, -0.5),
         (0.5, 0.5, -0.5),
         (0.5, 0.5, 0.5),
         (0.5, -0.5, 0.5)],
        (1, 0, 0),
        (220, 80, 80)
    ),
    (
        [(-0.5, -0.5, 0.5),
         (-0.5, 0.5, 0.5),
         (-0.5, 0.5, -0.5),
         (-0.5, -0.5, -0.5)],
        (-1, 0, 0),
        (80, 180, 220)
    ),
    (
        [(-0.5, 0.5, -0.5),
         (-0.5, 0.5, 0.5),
         (0.5, 0.5, 0.5),
         (0.5, 0.5, -0.5)],
        (0, 1, 0),
        (100, 200, 120)
    ),
    (
        [(-0.5, -0.5, 0.5),
         (-0.5, -0.5, -0.5),
         (0.5, -0.5, -0.5),
         (0.5, -0.5, 0.5)],
        (0, -1, 0),
        (220, 190, 80)
    ),
    (
        [(-0.5, -0.5, 0.5),
         (0.5, -0.5, 0.5),
         (0.5, 0.5, 0.5),
         (-0.5, 0.5, 0.5)],
        (0, 0, 1),
        (150, 100, 220)
    ),
    (
        [(0.5, -0.5, -0.5),
         (-0.5, -0.5, -0.5),
         (-0.5, 0.5, -0.5),
         (0.5, 0.5, -0.5)],
        (0, 0, -1),
        (100, 180, 180)
    )
]

# --------------------------------------------------
# ROTATION
# --------------------------------------------------

def rotate_point(point):

    x, y, z = point

    # Rotate around X
    cos_x = math.cos(angle_x)
    sin_x = math.sin(angle_x)

    y1 = y * cos_x - z * sin_x
    z1 = y * sin_x + z * cos_x

    # Rotate around Y
    cos_y = math.cos(angle_y)
    sin_y = math.sin(angle_y)

    x2 = x * cos_y + z1 * sin_y
    z2 = -x * sin_y + z1 * cos_y

    return (x2, y1, z2)


# --------------------------------------------------
# PROJECTION
# --------------------------------------------------

def project(point):

    x, y, z = rotate_point(point)

    denominator = DISTANCE + z

    if denominator <= 0.1:
        return None

    factor = DISTANCE / denominator

    screen_x = CENTER_X + x * SCALE * factor
    screen_y = CENTER_Y - y * SCALE * factor

    return (int(screen_x), int(screen_y))


# --------------------------------------------------
# CELL AND PLANE HELPERS
# --------------------------------------------------

def is_exterior(x, y, z):
    """
    Return True if the cube is on any outer surface.

    This includes:
    - Face cubes
    - Edge cubes
    - Corner cubes

    Interior cubes are not selectable.
    """

    return (
        x == 0 or x == CUBE_SIZE - 1 or
        y == 0 or y == CUBE_SIZE - 1 or
        z == 0 or z == CUBE_SIZE - 1
    )


def get_visible_cells():
    """
    Return the cells that should currently be displayed.

    Normal mode: all cubes.
    Plane mode: only the selected X, Y, or Z plane.
    """

    cells = set()

    for x in range(CUBE_SIZE):
        for y in range(CUBE_SIZE):
            for z in range(CUBE_SIZE):

                if voxels[x][y][z] == 0:
                    continue

                if active_plane is None:
                    cells.add((x, y, z))

                elif active_plane == 0 and x == selected[0]:
                    cells.add((x, y, z))

                elif active_plane == 1 and y == selected[1]:
                    cells.add((x, y, z))

                elif active_plane == 2 and z == selected[2]:
                    cells.add((x, y, z))

    return cells


def is_selectable(cell):

    x, y, z = cell

    if not (0 <= x < CUBE_SIZE
            and 0 <= y < CUBE_SIZE
            and 0 <= z < CUBE_SIZE):
        return False

    if voxels[x][y][z] == 0:
        return False

    # In plane mode, every cell in that plane is selectable.
    if active_plane is not None:
        return cell in get_visible_cells()

    # In normal mode, only exterior cells are selectable.
    return is_exterior(x, y, z)


def cell_center(x, y, z):

    return (
        x - (CUBE_SIZE - 1) / 2,
        y - (CUBE_SIZE - 1) / 2,
        z - (CUBE_SIZE - 1) / 2
    )


# --------------------------------------------------
# GENERATE VISIBLE FACES
# --------------------------------------------------

def generate_faces():

    faces = []

    # Only cells in the current display mode are considered.
    visible_cells = get_visible_cells()

    for x, y, z in visible_cells:

        center = cell_center(x, y, z)

        for corners, normal, normal_color in FACE_DEFINITIONS:

            nx, ny, nz = normal

            neighbor = (
                x + nx,
                y + ny,
                z + nz
            )

            # If the neighboring cell is also being displayed,
            # the shared face is hidden.
            if neighbor in visible_cells:
                continue

            world_vertices = []

            for cx, cy, cz in corners:

                world_vertices.append((
                    center[0] + cx,
                    center[1] + cy,
                    center[2] + cz
                ))

            # In plane mode, highlight every cell in the plane.
            if active_plane is not None:
                color = PLANE_COLOR
            else:
                color = normal_color

            faces.append((
                world_vertices,
                normal,
                color,
                (x, y, z)
            ))

    return faces


# --------------------------------------------------
# DRAW CUBE
# --------------------------------------------------

def draw_cube():

    faces = generate_faces()
    visible_faces = []

    for vertices, normal, color, cell in faces:

        rotated_normal = rotate_point(normal)

        # Backface culling
        if rotated_normal[2] >= 0:
            continue

        rotated_vertices = [
            rotate_point(vertex)
            for vertex in vertices
        ]

        average_depth = sum(
            vertex[2] for vertex in rotated_vertices
        ) / 4

        projected_vertices = [
            project(vertex)
            for vertex in vertices
        ]

        if None in projected_vertices:
            continue

        visible_faces.append((
            average_depth,
            projected_vertices,
            color,
            cell
        ))

    # Draw distant faces first.
    visible_faces.sort(
        key=lambda face: face[0],
        reverse=True
    )

    for depth, points, color, cell in visible_faces:

        pygame.draw.polygon(
            screen,
            color,
            points
        )

        pygame.draw.polygon(
            screen,
            (25, 25, 25),
            points,
            1
        )

    return visible_faces


# --------------------------------------------------
# POINT-IN-POLYGON TEST
# --------------------------------------------------

def point_in_polygon(point, polygon):

    px, py = point
    inside = False

    j = len(polygon) - 1

    for i in range(len(polygon)):

        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if (yi > py) != (yj > py):

            intersection_x = (
                (xj - xi) * (py - yi)
                / (yj - yi)
                + xi
            )

            if px < intersection_x:
                inside = not inside

        j = i

    return inside


# --------------------------------------------------
# RIGHT-CLICK SELECTION
# --------------------------------------------------

def select_cube_at_position(mouse_position, visible_faces):

    # Check frontmost faces first.
    for depth, polygon, color, cell in reversed(visible_faces):

        if point_in_polygon(mouse_position, polygon):

            if is_selectable(cell):

                selected[0] = cell[0]
                selected[1] = cell[1]
                selected[2] = cell[2]

                return


# --------------------------------------------------
# DRAW SELECTED CELL OUTLINE
# --------------------------------------------------

def draw_selection():

    x, y, z = selected

    center = cell_center(x, y, z)

    corners = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5)
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    projected = []

    for corner in corners:

        world_point = (
            center[0] + corner[0],
            center[1] + corner[1],
            center[2] + corner[2]
        )

        projected.append(project(world_point))

    for start, end in edges:

        if (
            projected[start] is not None
            and projected[end] is not None
        ):

            pygame.draw.line(
                screen,
                YELLOW,
                projected[start],
                projected[end],
                4
            )

    marker = project(center)

    if marker is not None:

        pygame.draw.circle(
            screen,
            YELLOW,
            marker,
            5
        )

# --------------------------------------------------
# DRAW ALL VISIBLE CUBE VALUES
# --------------------------------------------------

def draw_cube_values(visible_faces):

    value_font = pygame.font.SysFont(None, 22, bold=True)

    # Store the visible faces belonging to each cube.
    cell_faces = {}

    for depth, polygon, color, cell in visible_faces:

        x, y, z = cell
        value = cube_values[x][y][z]

        # Ignore empty cubes.
        if value is None:
            continue

        if cell not in cell_faces:
            cell_faces[cell] = []

        cell_faces[cell].append(
            (depth, polygon, value)
        )

    # Draw one value per cube.
    for cell, faces in cell_faces.items():

        # Try the closest visible face first.
        faces.sort(key=lambda face: face[0])

        for depth, polygon, value in faces:

            # Find the center of this visible face.
            center_x = sum(point[0] for point in polygon) / len(polygon)
            center_y = sum(point[1] for point in polygon) / len(polygon)

            center = (center_x, center_y)

            # Check whether another cube's face covers
            # the center of this face.
            occluded = False

            for other_depth, other_polygon, other_color, other_cell in visible_faces:

                if other_cell == cell:
                    continue

                # Smaller depth means closer to the camera.
                if other_depth < depth:

                    if point_in_polygon(center, other_polygon):
                        occluded = True
                        break

            if occluded:
                continue

            # Create the value text.
            text = value_font.render(
                str(value),
                True,
                WHITE
            )

            text_rect = text.get_rect(
                center=(int(center_x), int(center_y))
            )

            # Add a dark outline to improve readability.
            for offset_x, offset_y in [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1)
            ]:

                outline = value_font.render(
                    str(value),
                    True,
                    (20, 20, 20)
                )

                screen.blit(
                    outline,
                    (
                        text_rect.x + offset_x,
                        text_rect.y + offset_y
                    )
                )

            screen.blit(text, text_rect)

            # One value is enough for this cube.
            break


# --------------------------------------------------
# DRAW SELECTED CUBE VALUE
# --------------------------------------------------

def draw_selected_value():

    x, y, z = selected

    value = cube_values[x][y][z]

    if value is None:
        display_text = "Empty"
    else:
        display_text = str(value)

    center = cell_center(x, y, z)
    position = project(center)

    if position is not None:

        value_font = pygame.font.SysFont(None, 28)

        text = value_font.render(
            display_text,
            True,
            WHITE
        )

        text_rect = text.get_rect(center=position)

        screen.blit(text, text_rect)


# --------------------------------------------------
# VALUE ENTRY PROMPT
# --------------------------------------------------

def draw_value_prompt():

    # Dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))

    screen.blit(overlay, (0, 0))

    prompt_font = pygame.font.SysFont(None, 36)
    input_font = pygame.font.SysFont(None, 32)

    # Prompt box dimensions
    box_width = 450
    box_height = 200

    box_x = (WIDTH - box_width) // 2
    box_y = (HEIGHT - box_height) // 2

    pygame.draw.rect(
        screen,
        (50, 50, 65),
        (box_x, box_y, box_width, box_height),
        border_radius=10
    )

    pygame.draw.rect(
        screen,
        WHITE,
        (box_x, box_y, box_width, box_height),
        2,
        border_radius=10
    )

    # Prompt title
    title = prompt_font.render(
        f"Enter value for cube {tuple(selected)}:",
        True,
        WHITE
    )

    screen.blit(
        title,
        (box_x + 25, box_y + 25)
    )

    # Input text
    input_text = input_font.render(
        value_input + "|",
        True,
        YELLOW
    )

    screen.blit(
        input_text,
        (box_x + 25, box_y + 85)
    )

    # Instructions
    instructions = font.render(
        "ENTER: Save     ESC: Cancel",
        True,
        WHITE
    )

    screen.blit(
        instructions,
        (box_x + 25, box_y + 130)
    )

    # Error message
    if value_error:

        error_text = font.render(
            value_error,
            True,
            RED
        )

        screen.blit(
            error_text,
            (box_x + 25, box_y + 165)
        )


# --------------------------------------------------
# WASD NAVIGATION
# --------------------------------------------------

def move_selection(direction):

    x, y, z = selected

    screen_directions = {
        "w": (0, -1),
        "s": (0, 1),
        "a": (-1, 0),
        "d": (1, 0)
    }

    dx_screen, dy_screen = screen_directions[direction]

    current_center = cell_center(x, y, z)
    current_screen = project(current_center)

    if current_screen is None:
        return

    # Find the possible neighboring cells.
    if active_plane == 0:
        # X is fixed. Move through the Y-Z plane.
        neighbors = [
            (x, y + 1, z),
            (x, y - 1, z),
            (x, y, z + 1),
            (x, y, z - 1)
        ]

    elif active_plane == 1:
        # Y is fixed. Move through the X-Z plane.
        neighbors = [
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y, z + 1),
            (x, y, z - 1)
        ]

    elif active_plane == 2:
        # Z is fixed. Move through the X-Y plane.
        neighbors = [
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y + 1, z),
            (x, y - 1, z)
        ]

    else:
        # Normal mode: exterior cells only.
        neighbors = [
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y + 1, z),
            (x, y - 1, z),
            (x, y, z + 1),
            (x, y, z - 1)
        ]

    best_neighbor = None
    best_score = -float("inf")

    for neighbor in neighbors:

        if not is_selectable(neighbor):
            continue

        nx, ny, nz = neighbor

        neighbor_screen = project(
            cell_center(nx, ny, nz)
        )

        if neighbor_screen is None:
            continue

        dx = neighbor_screen[0] - current_screen[0]
        dy = neighbor_screen[1] - current_screen[1]

        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.5:
            continue

        dx /= distance
        dy /= distance

        alignment = (
            dx * dx_screen
            + dy * dy_screen
        )

        if alignment <= 0:
            continue

        if alignment > best_score:

            best_score = alignment
            best_neighbor = neighbor

    if best_neighbor is not None:

        selected[0] = best_neighbor[0]
        selected[1] = best_neighbor[1]
        selected[2] = best_neighbor[2]


# --------------------------------------------------
# TOGGLE PLANES
# --------------------------------------------------

def toggle_plane(axis):

    global active_plane

    if active_plane == axis:
        # Pressing the same number again turns plane mode off.
        active_plane = None

    else:
        active_plane = axis

    # Ensure selection remains valid after switching modes.
    if not is_selectable(tuple(selected)):

        visible_cells = get_visible_cells()

        if visible_cells:
            first_cell = sorted(visible_cells)[0]

            selected[0] = first_cell[0]
            selected[1] = first_cell[1]
            selected[2] = first_cell[2]


# --------------------------------------------------
# INFORMATION DISPLAY
# --------------------------------------------------

def draw_information():

    if active_plane is None:
        plane_text = "Plane mode: OFF"
    else:
        plane_names = ["X", "Y", "Z"]
        plane_text = (
            f"Plane mode: {plane_names[active_plane]} "
            f"({plane_names[active_plane]} = "
            f"{selected[active_plane]})"
        )

    x, y, z = selected
    selected_value = cube_values[x][y][z]

    if selected_value is None:
        value_text = "Selected value: Empty"
    else:
        value_text = f"Selected value: {selected_value}"

    instructions = [
        "Left mouse drag: Rotate cube",
        "Right mouse click: Select cell",
        "Arrow keys: Rotate cube",
        "W A S D: Move selection",
        "ENTER: Edit selected cube value",
        "1: Toggle X plane | 2: Toggle Y plane | 3: Toggle Z plane",
        plane_text,
        f"Selected cell: {tuple(selected)}",
        value_text,
        "Dimensions: 8 x 8 x 8 | Total cubes: 512"
    ]

    for i, message in enumerate(instructions):

        color = (
            YELLOW
            if i == 6 and active_plane is not None
            else WHITE
        )

        text = font.render(
            message,
            True,
            color
        )

        screen.blit(
            text,
            (20, 20 + i * 27)
        )


# --------------------------------------------------
# VALUE INPUT HANDLING
# --------------------------------------------------

def handle_value_input(event):
    """
    Handle keyboard input while the value prompt is open.
    """

    global editing_value
    global value_input
    global value_error

    if event.key == pygame.K_RETURN:

        try:
            # Convert the input into an integer.
            new_value = int(value_input)

            x, y, z = selected

            # Save the value in the selected cube.
            cube_values[x][y][z] = new_value

            # Close the prompt.
            editing_value = False
            value_input = ""
            value_error = ""

        except ValueError:

            # Keep the prompt open if the input is invalid.
            value_error = "Please enter a valid integer."

    elif event.key == pygame.K_ESCAPE:

        # Cancel without changing the existing value.
        editing_value = False
        value_input = ""
        value_error = ""

    elif event.key == pygame.K_BACKSPACE:

        value_input = value_input[:-1]
        value_error = ""

    else:

        # Accept numerical digits.
        if event.unicode.isdigit():

            value_input += event.unicode
            value_error = ""

        # Accept a minus sign only at the beginning.
        elif event.unicode == "-" and value_input == "":

            value_input = "-"
            value_error = ""


# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

running = True
visible_faces = []

while running:

    clock.tick(60)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False
            continue

        # ------------------------------------------
        # VALUE ENTRY MODE
        # ------------------------------------------

        if editing_value:

            # Ignore mouse and movement inputs while
            # the value prompt is open.
            if event.type == pygame.KEYDOWN:
                handle_value_input(event)

            continue

        # ------------------------------------------
        # MOUSE INPUT
        # ------------------------------------------

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                dragging = True
                last_mouse_x, last_mouse_y = event.pos

            elif event.button == 3:

                select_cube_at_position(
                    event.pos,
                    visible_faces
                )

        if event.type == pygame.MOUSEBUTTONUP:

            if event.button == 1:
                dragging = False

        if event.type == pygame.MOUSEMOTION and dragging:

            mouse_x, mouse_y = event.pos

            dx = mouse_x - last_mouse_x
            dy = mouse_y - last_mouse_y

            angle_y += dx * MOUSE_SENSITIVITY
            angle_x += dy * MOUSE_SENSITIVITY

            last_mouse_x = mouse_x
            last_mouse_y = mouse_y

        # ------------------------------------------
        # KEYBOARD INPUT
        # ------------------------------------------

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_RETURN:

                # Open the value prompt for the selected cube.
                x, y, z = selected

                current_value = cube_values[x][y][z]

                if current_value is None:
                    value_input = ""
                else:
                    value_input = str(current_value)

                value_error = ""
                editing_value = True

            elif event.key == pygame.K_w:
                move_selection("w")

            elif event.key == pygame.K_s:
                move_selection("s")

            elif event.key == pygame.K_a:
                move_selection("a")

            elif event.key == pygame.K_d:
                move_selection("d")

            # Plane toggles
            elif event.key == pygame.K_1:
                toggle_plane(0)

            elif event.key == pygame.K_2:
                toggle_plane(1)

            elif event.key == pygame.K_3:
                toggle_plane(2)

    # ----------------------------------------------
    # ARROW KEY ROTATION
    # ----------------------------------------------

    if not editing_value:

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            angle_y -= ROTATION_SPEED

        if keys[pygame.K_RIGHT]:
            angle_y += ROTATION_SPEED

        if keys[pygame.K_UP]:
            angle_x -= ROTATION_SPEED

        if keys[pygame.K_DOWN]:
            angle_x += ROTATION_SPEED

    # ----------------------------------------------
    # DRAW EVERYTHING
    # ----------------------------------------------

    screen.fill(BACKGROUND)

    visible_faces = draw_cube()

    # Display values on every visible cube.
    draw_cube_values(visible_faces)

    # Draw the selection highlight on top of the values.
    draw_selection()

    draw_information()

    # Display the input prompt when editing a cube.
    if editing_value:
        draw_value_prompt()

    pygame.display.flip()


pygame.quit()
sys.exit()


