"""Human-like mouse movement using WindMouse algorithm."""

import math
import random
import time
from typing import Callable, Optional, Tuple

from src.utils.logger import get_logger


def wind_mouse(
    start_x: float,
    start_y: float,
    dest_x: float,
    dest_y: float,
    gravity: float = 9.0,
    wind: float = 3.0,
    max_velocity: float = 15.0,
    target_area: float = 12.0,
    move_callback: Optional[Callable[[int, int], None]] = None,
    sleep_time: Tuple[float, float] = (0.001, 0.003),
) -> None:
    """
    Generate human-like mouse movement using the WindMouse algorithm.

    Models the cursor as an object with inertia acted upon by:
    - Gravity: Constant pull toward destination
    - Wind: Random fluctuating force for natural variation

    Args:
        start_x: Starting X position
        start_y: Starting Y position
        dest_x: Destination X position
        dest_y: Destination Y position
        gravity: Gravitational force toward destination (G_0)
        wind: Wind force magnitude (W_0)
        max_velocity: Maximum velocity cap (M_0)
        target_area: Distance threshold for behavior change (D_0)
        move_callback: Function called for each movement step (x, y)
        sleep_time: (min, max) sleep duration between steps
    """
    sqrt3 = math.sqrt(3)
    sqrt5 = math.sqrt(5)

    current_x = float(start_x)
    current_y = float(start_y)
    velocity_x = 0.0
    velocity_y = 0.0
    wind_x = 0.0
    wind_y = 0.0

    max_iterations = 10000  # Prevent infinite loops
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        distance = math.hypot(dest_x - current_x, dest_y - current_y)

        if distance < 1:
            break

        # Wind force changes based on distance to target
        if distance >= target_area:
            # Far from target: wind adds random fluctuation
            wind_x = wind_x / sqrt3 + (2 * random.random() - 1) * wind / sqrt5
            wind_y = wind_y / sqrt3 + (2 * random.random() - 1) * wind / sqrt5
        else:
            # Near target: wind dampens for precision
            wind_x /= sqrt3
            wind_y /= sqrt3

        # Gravity pulls toward destination
        gravity_x = gravity * (dest_x - current_x) / distance
        gravity_y = gravity * (dest_y - current_y) / distance

        # Update velocity
        velocity_x += wind_x + gravity_x
        velocity_y += wind_y + gravity_y

        # Limit velocity
        velocity_mag = math.hypot(velocity_x, velocity_y)
        if velocity_mag > max_velocity:
            velocity_clamp = max_velocity / 2 + random.random() * max_velocity / 2
            velocity_x = velocity_x / velocity_mag * velocity_clamp
            velocity_y = velocity_y / velocity_mag * velocity_clamp

        # Update position
        current_x += velocity_x
        current_y += velocity_y

        # Execute move
        if move_callback:
            move_callback(int(round(current_x)), int(round(current_y)))

        # Small delay for natural speed
        if sleep_time:
            time.sleep(random.uniform(sleep_time[0], sleep_time[1]))

    # Final move to exact destination
    if move_callback:
        move_callback(int(dest_x), int(dest_y))


def generate_path(
    start_x: float,
    start_y: float,
    dest_x: float,
    dest_y: float,
    **kwargs,
) -> list[Tuple[int, int]]:
    """
    Generate a human-like mouse path without executing moves.

    Args:
        start_x: Starting X position
        start_y: Starting Y position
        dest_x: Destination X position
        dest_y: Destination Y position
        **kwargs: Additional arguments passed to wind_mouse

    Returns:
        List of (x, y) positions along the path
    """
    path = []

    def collect_point(x: int, y: int) -> None:
        path.append((x, y))

    # Generate without sleep for speed
    wind_mouse(
        start_x, start_y, dest_x, dest_y,
        move_callback=collect_point,
        sleep_time=None,
        **kwargs,
    )

    return path


class MouseMover:
    """
    Mouse movement with human-like behavior.

    Wraps the WindMouse algorithm with configurable parameters
    and integrates with input backends.
    """

    def __init__(
        self,
        gravity: float = 9.0,
        wind: float = 3.0,
        max_velocity: float = 15.0,
        target_area: float = 12.0,
        move_delay: Tuple[float, float] = (0.001, 0.003),
    ):
        """
        Initialize mouse mover.

        Args:
            gravity: Pull toward destination
            wind: Random variation magnitude
            max_velocity: Maximum movement speed
            target_area: Distance for precision mode
            move_delay: (min, max) delay between steps
        """
        self.gravity = gravity
        self.wind = wind
        self.max_velocity = max_velocity
        self.target_area = target_area
        self.move_delay = move_delay
        self.log = get_logger()

        # Position tracking
        self._current_x = 0
        self._current_y = 0

        # Movement backend (set by controller)
        self._move_func: Optional[Callable[[int, int], None]] = None

    def set_move_function(self, func: Callable[[int, int], None]) -> None:
        """Set the low-level move function."""
        self._move_func = func

    def set_position(self, x: int, y: int) -> None:
        """Update tracked position without moving."""
        self._current_x = x
        self._current_y = y

    def get_position(self) -> Tuple[int, int]:
        """Get current tracked position."""
        return (self._current_x, self._current_y)

    def move_to(self, x: int, y: int) -> None:
        """
        Move mouse to position with human-like movement.

        Args:
            x: Target X position
            y: Target Y position
        """
        if self._move_func is None:
            self.log.warning("No move function set, cannot move mouse")
            return

        def do_move(mx: int, my: int) -> None:
            self._move_func(mx, my)
            self._current_x = mx
            self._current_y = my

        wind_mouse(
            self._current_x,
            self._current_y,
            x,
            y,
            gravity=self.gravity,
            wind=self.wind,
            max_velocity=self.max_velocity,
            target_area=self.target_area,
            move_callback=do_move,
            sleep_time=self.move_delay,
        )

    def move_relative(self, dx: int, dy: int) -> None:
        """Move relative to current position."""
        self.move_to(self._current_x + dx, self._current_y + dy)
