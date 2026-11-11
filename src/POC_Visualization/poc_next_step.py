import pygame
import math
import sys

pygame.init()

# --------------------------------------------------
# WINDOW SETTINGS
# --------------------------------------------------

WIDTH, HEIGHT = 1000, 750

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Magic-8 - 3D Cube")

clock = pygame.time.Clock()

# --------------------------------------------------
# CUBE SETTINGS
# --------------------------------------------------

CUBE_SIZE = 8

# Create an 8 x 8 x 8 array containing 512 cubes
# 1 = cube exists, 0 = empty space

voxels = [
    [
        [1 for z in range(CUBE_SIZE)]
        for y in range(CUBE_SIZE)
    ]
    for x in range(CUBE_SIZE)
]

# --------------------------------------------------
# ROTATION SETTINGS
# --------------------------------------------------

angle_x = -0.45
angle_y = 0.55

rotation_speed = 0.08
mouse_sensitivity = 0.01

dragging = False
last_mouse_x = 0
last_mouse_y = 0

# --------------------------------------------------
# PROJECTION SETTINGS
# --------------------------------------------------

scale = 55
distance = 18

center_x = WIDTH // 2
center_y = HEIGHT // 2

# --------------------------------------------------
# FACE COLOURS
# --------------------------------------------------

FACE_COLORS = {
    (-1, 0, 0): (65, 110, 190),   # Left
    ( 1, 0, 0): (90, 140, 220),   # Right

    (0, -1, 0): (70, 170, 140),   # Top
    (0,  1, 0): (45, 120, 100),   # Bottom

    (0, 0, -1): (60, 160, 220),   # Front
    (0, 0,  1): (35, 90, 150)     # Back
}

GRID_COLOR = (15, 25, 40)


# --------------------------------------------------
# ROTATE A 3D POINT
# --------------------------------------------------

def rotate_vertex(vertex, angle_x, angle_y):

    x, y, z = vertex

    # Rotate around X axis

    y1 = y * math.cos(angle_x) - z * math.sin(angle_x)
    z1 = y * math.sin(angle_x) + z * math.cos(angle_x)

    # Rotate around Y axis

    x2 = x * math.cos(angle_y) + z1 * math.sin(angle_y)
    z2 = -x * math.sin(angle_y) + z1 * math.cos(angle_y)

    return x2, y1, z2


# --------------------------------------------------
# PROJECT 3D POINT ONTO 2D SCREEN
# --------------------------------------------------

def project_vertex(vertex):

    x, y, z = vertex

    factor = distance / (distance + z)

    screen_x = int(center_x + x * scale * factor)
    screen_y = int(center_y + y * scale * factor)

    return screen_x, screen_y


# --------------------------------------------------
# GENERATE EXPOSED FACES OF THE 8x8x8 CUBE
# --------------------------------------------------

def generate_faces():

    faces = []

    half = CUBE_SIZE / 2

    for x in range(CUBE_SIZE):

        for y in range(CUBE_SIZE):

            for z in range(CUBE_SIZE):

                # Skip empty positions
                if voxels[x][y][z] == 0:
                    continue

                # Coordinates of this small cube

                x0 = x - half
                x1 = x0 + 1

                y0 = y - half
                y1 = y0 + 1

                z0 = z - half
                z1 = z0 + 1

                # Check all six neighboring positions.
                # Only generate faces that are exposed.

                # LEFT (-X)
                if x == 0 or voxels[x-1][y][z] == 0:

                    faces.append((
                        [
                            (x0, y0, z0),
                            (x0, y1, z0),
                            (x0, y1, z1),
                            (x0, y0, z1)
                        ],
                        (-1, 0, 0)
                    ))

                # RIGHT (+X)
                if x == CUBE_SIZE-1 or voxels[x+1][y][z] == 0:

                    faces.append((
                        [
                            (x1, y0, z0),
                            (x1, y1, z0),
                            (x1, y1, z1),
                            (x1, y0, z1)
                        ],
                        (1, 0, 0)
                    ))

                # TOP (-Y)
                if y == 0 or voxels[x][y-1][z] == 0:

                    faces.append((
                        [
                            (x0, y0, z0),
                            (x1, y0, z0),
                            (x1, y0, z1),
                            (x0, y0, z1)
                        ],
                        (0, -1, 0)
                    ))

                # BOTTOM (+Y)
                if y == CUBE_SIZE-1 or voxels[x][y+1][z] == 0:

                    faces.append((
                        [
                            (x0, y1, z0),
                            (x1, y1, z0),
                            (x1, y1, z1),
                            (x0, y1, z1)
                        ],
                        (0, 1, 0)
                    ))

                # FRONT (-Z)
                if z == 0 or voxels[x][y][z-1] == 0:

                    faces.append((
                        [
                            (x0, y0, z0),
                            (x1, y0, z0),
                            (x1, y1, z0),
                            (x0, y1, z0)
                        ],
                        (0, 0, -1)
                    ))

                # BACK (+Z)
                if z == CUBE_SIZE-1 or voxels[x][y][z+1] == 0:

                    faces.append((
                        [
                            (x0, y0, z1),
                            (x1, y0, z1),
                            (x1, y1, z1),
                            (x0, y1, z1)
                        ],
                        (0, 0, 1)
                    ))

    return faces


# --------------------------------------------------
# DRAW THE ENTIRE 8x8x8 CUBE
# --------------------------------------------------

def draw_cube():

    visible_faces = []

    faces = generate_faces()

    for vertices, normal in faces:

        # Rotate face vertices

        rotated = [
            rotate_vertex(v, angle_x, angle_y)
            for v in vertices
        ]

        # Rotate face normal

        rotated_normal = rotate_vertex(
            normal, angle_x, angle_y
        )

        # Backface culling:
        # Do not draw faces pointing away from camera

        if rotated_normal[2] >= 0:
            continue

        # Calculate average depth for sorting

        average_depth = sum(
            vertex[2] for vertex in rotated
        ) / len(rotated)

        # Project vertices onto screen

        projected = [
            project_vertex(v)
            for v in rotated
        ]

        color = FACE_COLORS[normal]

        visible_faces.append((
            average_depth,
            projected,
            color
        ))

    # Draw farthest faces first
    visible_faces.sort(
        key=lambda face: face[0],
        reverse=True
    )

    # Draw opaque faces

    for depth, points, color in visible_faces:

        pygame.draw.polygon(
            screen,
            color,
            points
        )

        # Draw grid lines separating individual cubes

        pygame.draw.polygon(
            screen,
            GRID_COLOR,
            points,
            2
        )


# --------------------------------------------------
# MAIN GAME LOOP
# --------------------------------------------------

font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 23)

running = True

while running:

    screen.fill((25, 25, 35))

    # ----------------------------------------------
    # HANDLE EVENTS
    # ----------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # Start mouse dragging

        elif event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                dragging = True

                last_mouse_x, last_mouse_y = event.pos

        # Stop mouse dragging

        elif event.type == pygame.MOUSEBUTTONUP:

            if event.button == 1:

                dragging = False

        # Mouse movement

        elif event.type == pygame.MOUSEMOTION:

            if dragging:

                mouse_x, mouse_y = event.pos

                dx = mouse_x - last_mouse_x
                dy = mouse_y - last_mouse_y

                angle_y += dx * mouse_sensitivity
                angle_x += dy * mouse_sensitivity

                last_mouse_x = mouse_x
                last_mouse_y = mouse_y

    # ----------------------------------------------
    # KEYBOARD CONTROLS
    # ----------------------------------------------

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        angle_y -= rotation_speed

    if keys[pygame.K_RIGHT]:
        angle_y += rotation_speed

    if keys[pygame.K_UP]:
        angle_x -= rotation_speed

    if keys[pygame.K_DOWN]:
        angle_x += rotation_speed

    # ----------------------------------------------
    # DRAW CUBE
    # ----------------------------------------------

    draw_cube()

    # ----------------------------------------------
    # DISPLAY INFORMATION
    # ----------------------------------------------

    title = font.render(
        "Magic-8: 3D Cube",
        True,
        (255, 255, 255)
    )

    instructions = small_font.render(
        "Arrow Keys: Rotate | Left Click + Drag: Rotate",
        True,
        (220, 220, 220)
    )

    cube_info = small_font.render(
        "Dimensions: 8 x 8 x 8 | Total Cubes: 512",
        True,
        (180, 200, 220)
    )

    screen.blit(title, (20, 20))
    screen.blit(instructions, (20, 55))
    screen.blit(cube_info, (20, 85))

    pygame.display.flip()

    clock.tick(60)


# --------------------------------------------------
# EXIT
# --------------------------------------------------

pygame.quit()
sys.exit()
