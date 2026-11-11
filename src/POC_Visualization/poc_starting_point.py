import pygame
import math
import sys

# Initialize Pygame
pygame.init()

# Window settings
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("3D Cube - Pygame")

clock = pygame.time.Clock()

# Cube vertices (x, y, z)
vertices = [
    (-1, -1, -1),
    ( 1, -1, -1),
    ( 1,  1, -1),
    (-1,  1, -1),
    (-1, -1,  1),
    ( 1, -1,  1),
    ( 1,  1,  1),
    (-1,  1,  1)
]

# Edges connecting vertices
edges = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7)
]

# Rotation angles
angle_x = 0
angle_y = 0

# Rotation settings
rotation_speed = 0.08
mouse_sensitivity = 0.01

# Mouse drag settings
dragging = False
last_mouse_x = 0
last_mouse_y = 0

# Projection settings
scale = 150
distance = 4

center_x = WIDTH // 2
center_y = HEIGHT // 2


# Rotate a vertex around X and Y axes
def rotate_vertex(vertex, angle_x, angle_y):

    x, y, z = vertex

    # Rotation around X axis
    y1 = y * math.cos(angle_x) - z * math.sin(angle_x)
    z1 = y * math.sin(angle_x) + z * math.cos(angle_x)

    # Rotation around Y axis
    x2 = x * math.cos(angle_y) + z1 * math.sin(angle_y)
    z2 = -x * math.sin(angle_y) + z1 * math.cos(angle_y)

    return x2, y1, z2


# Convert 3D coordinates into 2D screen coordinates
def project_vertex(vertex):

    x, y, z = vertex

    factor = distance / (distance + z)

    screen_x = int(center_x + x * scale * factor)
    screen_y = int(center_y + y * scale * factor)

    return screen_x, screen_y


# Main game loop
running = True

while running:

    screen.fill((25, 25, 35))

    # Handle events
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # Start dragging
        elif event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:
                dragging = True
                last_mouse_x, last_mouse_y = event.pos

        # Stop dragging
        elif event.type == pygame.MOUSEBUTTONUP:

            if event.button == 1:
                dragging = False

        # Handle mouse movement
        elif event.type == pygame.MOUSEMOTION:

            if dragging:

                mouse_x, mouse_y = event.pos

                dx = mouse_x - last_mouse_x
                dy = mouse_y - last_mouse_y

                # Update cube rotation
                angle_y += dx * mouse_sensitivity
                angle_x += dy * mouse_sensitivity

                last_mouse_x = mouse_x
                last_mouse_y = mouse_y

    # Keyboard controls
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        angle_y -= rotation_speed

    if keys[pygame.K_RIGHT]:
        angle_y += rotation_speed

    if keys[pygame.K_UP]:
        angle_x -= rotation_speed

    if keys[pygame.K_DOWN]:
        angle_x += rotation_speed

    # Rotate cube vertices
    rotated_vertices = []

    for vertex in vertices:

        rotated = rotate_vertex(vertex, angle_x, angle_y)
        rotated_vertices.append(rotated)

    # Project vertices onto 2D screen
    projected_vertices = []

    for vertex in rotated_vertices:

        projected = project_vertex(vertex)
        projected_vertices.append(projected)

    # Draw cube edges
    for edge in edges:

        start = projected_vertices[edge[0]]
        end = projected_vertices[edge[1]]

        pygame.draw.line(
            screen,
            (0, 200, 255),
            start,
            end,
            3
        )

    # Draw cube vertices
    for point in projected_vertices:

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            point,
            5
        )

    # Display instructions
    font = pygame.font.SysFont(None, 28)

    instructions = font.render(
        "Arrow Keys: Rotate | Left Click + Drag: Rotate",
        True,
        (255, 255, 255)
    )

    screen.blit(instructions, (20, 20))

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
sys.exit()