"""Keyboard input with human-like timing."""

import random
import time
from typing import Callable, Optional

from src.utils.logger import get_logger


class KeyboardController:
    """
    Keyboard input with human-like timing variation.

    Wraps low-level keyboard functions with configurable delays
    to simulate human typing patterns.
    """

    def __init__(
        self,
        key_delay: tuple[float, float] = (0.03, 0.08),
        hold_duration: tuple[float, float] = (0.05, 0.12),
        variation_percent: float = 15.0,
    ):
        """
        Initialize keyboard controller.

        Args:
            key_delay: (min, max) delay before key press
            hold_duration: (min, max) key hold time
            variation_percent: Random variation percentage
        """
        self.key_delay = key_delay
        self.hold_duration = hold_duration
        self.variation_percent = variation_percent
        self.log = get_logger()

        # Backend functions (set by controller)
        self._key_down_func: Optional[Callable[[str], None]] = None
        self._key_up_func: Optional[Callable[[str], None]] = None
        self._press_func: Optional[Callable[[str], None]] = None

    def set_key_functions(
        self,
        key_down: Callable[[str], None],
        key_up: Callable[[str], None],
        press: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Set low-level keyboard functions."""
        self._key_down_func = key_down
        self._key_up_func = key_up
        self._press_func = press

    def _vary(self, value: float) -> float:
        """Add random variation to a value."""
        variation = value * (self.variation_percent / 100)
        return value + random.uniform(-variation, variation)

    def _random_delay(self, delay_range: tuple[float, float]) -> None:
        """Sleep for a random duration within range."""
        time.sleep(random.uniform(delay_range[0], delay_range[1]))

    def press(self, key: str) -> None:
        """
        Press and release a key with human-like timing.

        Args:
            key: Key to press (e.g., 'a', 'space', 'enter')
        """
        if self._press_func:
            # Use built-in press if available
            self._random_delay(self.key_delay)
            self._press_func(key)
        elif self._key_down_func and self._key_up_func:
            # Manual press/release
            self._random_delay(self.key_delay)
            self._key_down_func(key)
            self._random_delay(self.hold_duration)
            self._key_up_func(key)
        else:
            self.log.warning("No keyboard functions set")

    def hold(self, key: str, duration: float) -> None:
        """
        Hold a key for a specific duration.

        Args:
            key: Key to hold
            duration: Hold duration in seconds
        """
        if not self._key_down_func or not self._key_up_func:
            self.log.warning("No keyboard functions set")
            return

        self._key_down_func(key)
        time.sleep(self._vary(duration))
        self._key_up_func(key)

    def key_down(self, key: str) -> None:
        """Press key down without releasing."""
        if self._key_down_func:
            self._key_down_func(key)
        else:
            self.log.warning("No key_down function set")

    def key_up(self, key: str) -> None:
        """Release a held key."""
        if self._key_up_func:
            self._key_up_func(key)
        else:
            self.log.warning("No key_up function set")

    def type_text(self, text: str, char_delay: tuple[float, float] = (0.02, 0.08)) -> None:
        """
        Type text with human-like character delays.

        Args:
            text: Text to type
            char_delay: (min, max) delay between characters
        """
        for char in text:
            self.press(char)
            self._random_delay(char_delay)

    def press_combo(self, *keys: str, hold_time: float = 0.1) -> None:
        """
        Press a key combination (e.g., Ctrl+C).

        Args:
            keys: Keys to press together
            hold_time: How long to hold the combo
        """
        if not self._key_down_func or not self._key_up_func:
            self.log.warning("No keyboard functions set")
            return

        # Press all keys down
        for key in keys:
            self._key_down_func(key)
            time.sleep(random.uniform(0.01, 0.03))

        # Hold
        time.sleep(self._vary(hold_time))

        # Release in reverse order
        for key in reversed(keys):
            self._key_up_func(key)
            time.sleep(random.uniform(0.01, 0.03))
