"""Main input controller combining mouse and keyboard."""

import random
import time
from typing import Optional, Tuple

from src.input.mouse import MouseMover
from src.input.keyboard import KeyboardController
from src.utils.logger import get_logger

# Try to import platform-specific input library
try:
    import pydirectinput
    pydirectinput.FAILSAFE = False
    HAS_PYDIRECTINPUT = True
except ImportError:
    HAS_PYDIRECTINPUT = False

# Fallback to pyautogui for non-Windows
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except (ImportError, Exception):
    # pyautogui can fail on headless/Wayland systems
    HAS_PYAUTOGUI = False


class InputController:
    """
    Unified input controller for mouse and keyboard.

    Combines MouseMover and KeyboardController with the appropriate
    backend (pydirectinput on Windows, pyautogui otherwise).
    """

    def __init__(
        self,
        human_like: bool = True,
        mouse_speed: str = "normal",
        click_delay: Tuple[float, float] = (0.05, 0.15),
    ):
        """
        Initialize input controller.

        Args:
            human_like: Enable human-like movement and timing
            mouse_speed: 'slow', 'normal', or 'fast'
            click_delay: (min, max) delay after clicks
        """
        self.human_like = human_like
        self.click_delay = click_delay
        self.log = get_logger()

        # Initialize components
        self.mouse = MouseMover(**self._get_mouse_params(mouse_speed))
        self.keyboard = KeyboardController()

        # Setup backend
        self._setup_backend()

    def _get_mouse_params(self, speed: str) -> dict:
        """Get mouse parameters based on speed setting."""
        params = {
            "slow": {
                "gravity": 6.0,
                "wind": 2.0,
                "max_velocity": 10.0,
                "move_delay": (0.002, 0.005),
            },
            "normal": {
                "gravity": 9.0,
                "wind": 3.0,
                "max_velocity": 15.0,
                "move_delay": (0.001, 0.003),
            },
            "fast": {
                "gravity": 12.0,
                "wind": 4.0,
                "max_velocity": 20.0,
                "move_delay": (0.0005, 0.002),
            },
        }
        return params.get(speed, params["normal"])

    def _setup_backend(self) -> None:
        """Configure the input backend based on available libraries."""
        if HAS_PYDIRECTINPUT:
            self.log.info("Using pydirectinput backend (Windows)")
            self._backend = "pydirectinput"

            # Set mouse functions
            self.mouse.set_move_function(pydirectinput.moveTo)

            # Set keyboard functions
            self.keyboard.set_key_functions(
                key_down=pydirectinput.keyDown,
                key_up=pydirectinput.keyUp,
                press=pydirectinput.press,
            )

            # Store click functions
            self._click = pydirectinput.click
            self._mouse_down = pydirectinput.mouseDown
            self._mouse_up = pydirectinput.mouseUp
            self._get_position = pydirectinput.position

        elif HAS_PYAUTOGUI:
            self.log.info("Using pyautogui backend (fallback)")
            self._backend = "pyautogui"

            self.mouse.set_move_function(lambda x, y: pyautogui.moveTo(x, y, _pause=False))

            self.keyboard.set_key_functions(
                key_down=pyautogui.keyDown,
                key_up=pyautogui.keyUp,
                press=pyautogui.press,
            )

            self._click = pyautogui.click
            self._mouse_down = pyautogui.mouseDown
            self._mouse_up = pyautogui.mouseUp
            self._get_position = pyautogui.position

        else:
            self.log.warning("No input backend available - input disabled")
            self._backend = None
            self._click = None
            self._mouse_down = None
            self._mouse_up = None
            self._get_position = None

        # Sync initial position if possible
        if self._get_position:
            try:
                pos = self._get_position()
                self.mouse.set_position(pos[0], pos[1])
            except Exception:
                pass

    def _random_delay(self, delay_range: Tuple[float, float]) -> None:
        """Sleep for random duration within range."""
        time.sleep(random.uniform(delay_range[0], delay_range[1]))

    # ========== Mouse Methods ==========

    def move_to(self, x: int, y: int) -> None:
        """
        Move mouse to position.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
        """
        if self.human_like:
            self.mouse.move_to(x, y)
        elif self._backend == "pydirectinput":
            pydirectinput.moveTo(x, y)
        elif self._backend == "pyautogui":
            pyautogui.moveTo(x, y, _pause=False)

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> None:
        """
        Click at position (or current position if not specified).

        Args:
            x: X coordinate (optional)
            y: Y coordinate (optional)
            button: 'left', 'right', or 'middle'
        """
        if x is not None and y is not None:
            self.move_to(x, y)
            self._random_delay((0.02, 0.05))

        if self._click:
            self._click(button=button)

        if self.human_like:
            self._random_delay(self.click_delay)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Right-click at position."""
        self.click(x, y, button="right")

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Double-click at position."""
        self.click(x, y)
        self._random_delay((0.05, 0.1))
        self.click(button="left")

    def mouse_down(self, button: str = "left") -> None:
        """Press mouse button down."""
        if self._mouse_down:
            self._mouse_down(button=button)

    def mouse_up(self, button: str = "left") -> None:
        """Release mouse button."""
        if self._mouse_up:
            self._mouse_up(button=button)

    def drag(self, start: Tuple[int, int], end: Tuple[int, int], button: str = "left") -> None:
        """
        Drag from start to end position.

        Args:
            start: Starting (x, y) position
            end: Ending (x, y) position
            button: Mouse button to hold
        """
        self.move_to(start[0], start[1])
        self._random_delay((0.05, 0.1))
        self.mouse_down(button)
        self._random_delay((0.02, 0.05))
        self.move_to(end[0], end[1])
        self._random_delay((0.02, 0.05))
        self.mouse_up(button)

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if self._get_position:
            return self._get_position()
        return self.mouse.get_position()

    # ========== Keyboard Methods ==========

    def press(self, key: str) -> None:
        """Press a key."""
        self.keyboard.press(key)

    def hold_key(self, key: str, duration: float) -> None:
        """Hold a key for duration."""
        self.keyboard.hold(key, duration)

    def key_down(self, key: str) -> None:
        """Press key down without releasing."""
        self.keyboard.key_down(key)

    def key_up(self, key: str) -> None:
        """Release held key."""
        self.keyboard.key_up(key)

    def type_text(self, text: str) -> None:
        """Type text with human-like delays."""
        self.keyboard.type_text(text)

    def press_combo(self, *keys: str) -> None:
        """Press key combination."""
        self.keyboard.press_combo(*keys)

    # ========== Game-Specific Methods ==========

    def cast_skill(self, skill_key: str, target: Optional[Tuple[int, int]] = None) -> None:
        """
        Cast a skill, optionally at a target location.

        Args:
            skill_key: Hotkey for the skill
            target: Optional (x, y) target position
        """
        # Press skill key
        self.keyboard.press(skill_key)
        self._random_delay((0.02, 0.05))

        if target:
            # Cast at target location
            self.click(target[0], target[1], button="left")
        else:
            # Cast at current location / self-cast
            self.click(button="right")

    def cast_at_cursor(self, skill_key: str) -> None:
        """Cast skill at current cursor position."""
        self.keyboard.press(skill_key)
        self._random_delay((0.02, 0.05))
        self.click(button="right")

    def use_potion(self, slot: int) -> None:
        """
        Use potion from belt slot.

        Args:
            slot: Belt slot number (1-4)
        """
        if 1 <= slot <= 4:
            self.keyboard.press(str(slot))

    def open_inventory(self) -> None:
        """Open inventory screen."""
        self.keyboard.press("i")

    def close_ui(self) -> None:
        """Close any open UI (escape key)."""
        self.keyboard.press("escape")

    def interact(self) -> None:
        """Interact with object/NPC (default: left click)."""
        self.click(button="left")

    def show_items(self, hold: bool = True) -> None:
        """
        Show/hide item labels on ground.

        Args:
            hold: If True, holds Alt key. If False, releases it.
        """
        if hold:
            self.keyboard.key_down("alt")
        else:
            self.keyboard.key_up("alt")
