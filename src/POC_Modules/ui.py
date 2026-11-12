"""Window management and input handling for Magic-8.

The UI communicates only with GameController. It never imports or calls the
Renderer; the controller supplies the latest rendered surface and handles
screen-position-to-cell selection.
"""

import pygame


class GameUI:
    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Magic-8 - 3D Cube Explorer")
        self.clock = pygame.time.Clock()
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

    def process_event(self, event, controller) -> None:
        """Translate Pygame events into controller calls."""
        if event.type == pygame.QUIT:
            controller.running = False
            return

        if controller.editing_value:
            if event.type == pygame.KEYDOWN:
                controller.handle_value_key(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.dragging = True
                self.last_mouse_x, self.last_mouse_y = event.pos
            elif event.button == 3:
                controller.select_cell_at_position(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mouse_x, mouse_y = event.pos
            dx = mouse_x - self.last_mouse_x
            dy = mouse_y - self.last_mouse_y
            controller.rotate(dx, dy)
            self.last_mouse_x, self.last_mouse_y = mouse_x, mouse_y

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                controller.begin_value_entry()
            elif event.key == pygame.K_w:
                controller.move_selection("w")
            elif event.key == pygame.K_s:
                controller.move_selection("s")
            elif event.key == pygame.K_a:
                controller.move_selection("a")
            elif event.key == pygame.K_d:
                controller.move_selection("d")
            elif event.key == pygame.K_1:
                controller.toggle_plane(0)
            elif event.key == pygame.K_2:
                controller.toggle_plane(1)
            elif event.key == pygame.K_3:
                controller.toggle_plane(2)
            elif event.key == pygame.K_q:
                controller.move_plane(-1)
            elif event.key == pygame.K_e:
                controller.move_plane(1)

    def run(self, controller) -> None:
        """Run the UI loop using only the controller's public interface."""
        while controller.running:
            self.clock.tick(60)

            # Use the geometry from the most recently rendered frame when
            # processing clicks and directional selection input.
            for event in pygame.event.get():
                self.process_event(event, controller)

            if not controller.editing_value:
                controller.rotate_keys(pygame.key.get_pressed())

            # Controller asks its renderer to create a frame, stores it, and
            # then exposes the surface back to this UI.
            controller.refresh_render()
            rendered_surface = controller.get_rendered_surface()
            if rendered_surface is not None:
                self.screen.blit(rendered_surface, (0, 0))
                pygame.display.flip()
