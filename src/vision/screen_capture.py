"""Screen capture module using mss for fast screenshots."""

import time
from typing import Optional, Tuple

import numpy as np
from mss import mss
import cv2

from src.utils.logger import get_logger

# Try to import Windows-specific modules
try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class ScreenCapture:
    """
    Fast screen capture with caching.

    Uses mss for efficient screen capture and caches frames
    to avoid redundant captures within the cache duration.
    """

    # Default cache duration in seconds (40ms = 1 frame at 25fps)
    DEFAULT_CACHE_DURATION = 0.040

    def __init__(
        self,
        window_title: str = "Diablo II: Resurrected",
        cache_duration: float = DEFAULT_CACHE_DURATION,
    ):
        """
        Initialize screen capture.

        Args:
            window_title: Title of the game window to capture
            cache_duration: How long to cache frames (seconds)
        """
        self.window_title = window_title
        self.cache_duration = cache_duration
        self.sct = mss()
        self.log = get_logger()

        # Cache state
        self._cached_frame: Optional[np.ndarray] = None
        self._cache_time: float = 0

        # Window state
        self._window_rect: Optional[Tuple[int, int, int, int]] = None
        self._last_window_check: float = 0
        self._window_check_interval: float = 1.0  # Check window position every 1s

    def _find_window(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the game window position.

        Returns:
            Tuple of (left, top, width, height) or None if not found
        """
        if not HAS_WIN32:
            # On non-Windows, return None (will use full screen)
            return None

        try:
            hwnd = win32gui.FindWindow(None, self.window_title)
            if hwnd == 0:
                return None

            # Get window rectangle
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            return (left, top, width, height)

        except Exception as e:
            self.log.warning(f"Error finding window: {e}")
            return None

    def _get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get window rectangle with caching.

        Returns:
            Tuple of (left, top, width, height) or None
        """
        current_time = time.time()

        # Check if we need to refresh window position
        if current_time - self._last_window_check > self._window_check_interval:
            self._window_rect = self._find_window()
            self._last_window_check = current_time

        return self._window_rect

    def _build_monitor(
        self, region: Optional[Tuple[int, int, int, int]] = None
    ) -> dict:
        """
        Build monitor dict for mss capture.

        Args:
            region: Optional (left, top, width, height) region

        Returns:
            Monitor dict for mss
        """
        if region:
            return {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3],
            }

        # Try to use game window
        window_rect = self._get_window_rect()
        if window_rect:
            return {
                "left": window_rect[0],
                "top": window_rect[1],
                "width": window_rect[2],
                "height": window_rect[3],
            }

        # Fall back to primary monitor
        return self.sct.monitors[1]

    def grab(self, use_cache: bool = True) -> np.ndarray:
        """
        Capture the game screen.

        Args:
            use_cache: Whether to use cached frame if available

        Returns:
            Screenshot as numpy array (BGR format for OpenCV)
        """
        current_time = time.time()

        # Return cached frame if still valid
        if (
            use_cache
            and self._cached_frame is not None
            and (current_time - self._cache_time) < self.cache_duration
        ):
            return self._cached_frame

        # Capture new frame
        monitor = self._build_monitor()
        screenshot = self.sct.grab(monitor)

        # Convert to numpy array (BGRA -> BGR)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Update cache
        self._cached_frame = frame
        self._cache_time = current_time

        return frame

    def grab_region(
        self,
        region: Tuple[int, int, int, int],
        use_cache: bool = False,
    ) -> np.ndarray:
        """
        Capture a specific region of the screen.

        Args:
            region: Tuple of (left, top, width, height)
            use_cache: Whether to use cached frame (default False for regions)

        Returns:
            Screenshot region as numpy array (BGR format)
        """
        monitor = self._build_monitor(region)
        screenshot = self.sct.grab(monitor)

        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        return frame

    def grab_game_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        """
        Capture a region relative to the game window.

        Args:
            x: X offset from game window left
            y: Y offset from game window top
            width: Region width
            height: Region height

        Returns:
            Screenshot region as numpy array (BGR format)
        """
        window_rect = self._get_window_rect()

        if window_rect:
            # Offset by window position
            abs_x = window_rect[0] + x
            abs_y = window_rect[1] + y
        else:
            # No window found, use absolute coordinates
            abs_x = x
            abs_y = y

        return self.grab_region((abs_x, abs_y, width, height))

    def is_game_running(self) -> bool:
        """
        Check if the game window is found.

        Returns:
            True if game window is detected
        """
        if not HAS_WIN32:
            # Can't detect on non-Windows, assume running
            self.log.debug("Window detection not available (non-Windows)")
            return True

        window_rect = self._find_window()
        return window_rect is not None

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the current game window position.

        Returns:
            Tuple of (left, top, width, height) or None if not found
        """
        return self._get_window_rect()

    def invalidate_cache(self) -> None:
        """Force the next grab() to capture a new frame."""
        self._cached_frame = None
        self._cache_time = 0

    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Get the dimensions of captured frames.

        Returns:
            Tuple of (width, height)
        """
        frame = self.grab()
        return (frame.shape[1], frame.shape[0])
