"""Loot detection and pickup system for D2R Bot."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.data.models import Config, DetectedItem, PickitRules
from src.input.controller import InputController
from src.utils.logger import get_logger


class ItemQuality(Enum):
    """Item quality levels (detected by label color)."""
    WHITE = auto()      # Normal/inferior
    GRAY = auto()       # Socketed
    BLUE = auto()       # Magic
    YELLOW = auto()     # Rare
    GREEN = auto()      # Set
    GOLD = auto()       # Unique
    ORANGE = auto()     # Crafted
    UNKNOWN = auto()


# Color ranges for item quality detection (BGR format for OpenCV)
# These are approximate and may need tuning
QUALITY_COLORS = {
    ItemQuality.WHITE: {
        "lower": (200, 200, 200),
        "upper": (255, 255, 255),
    },
    ItemQuality.GRAY: {
        "lower": (100, 100, 100),
        "upper": (180, 180, 180),
    },
    ItemQuality.BLUE: {
        "lower": (200, 100, 0),
        "upper": (255, 180, 100),
    },
    ItemQuality.YELLOW: {
        "lower": (0, 200, 200),
        "upper": (100, 255, 255),
    },
    ItemQuality.GREEN: {
        "lower": (0, 180, 0),
        "upper": (100, 255, 100),
    },
    ItemQuality.GOLD: {
        "lower": (0, 150, 180),
        "upper": (80, 220, 255),
    },
    ItemQuality.ORANGE: {
        "lower": (0, 100, 200),
        "upper": (80, 180, 255),
    },
}


@dataclass
class LootItem:
    """Detected item on ground."""
    position: Tuple[int, int]
    quality: ItemQuality
    name: str = ""
    width: int = 0
    height: int = 0
    should_pickup: bool = False
    confidence: float = 0.0


@dataclass
class LootStats:
    """Statistics for looting."""
    items_scanned: int = 0
    items_picked: int = 0
    items_skipped: int = 0
    gold_picked: int = 0
    last_scan_time: float = 0.0


class LootManager:
    """
    Manages loot detection and pickup.

    Scans screen for item labels, determines quality,
    checks pickit rules, and picks up valid items.
    """

    # Screen regions (1920x1080)
    SCAN_REGION = {
        "x": 200,      # Left boundary
        "y": 100,      # Top boundary
        "width": 1520,  # Scan width
        "height": 780,  # Scan height
    }

    # Item label dimensions (approximate)
    MIN_LABEL_WIDTH = 50
    MAX_LABEL_WIDTH = 400
    MIN_LABEL_HEIGHT = 12
    MAX_LABEL_HEIGHT = 40

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        screen_capture=None,
        pickit_rules: Optional[PickitRules] = None,
    ):
        """
        Initialize loot manager.

        Args:
            config: Bot configuration
            input_ctrl: Input controller
            screen_capture: Screen capture
            pickit_rules: Item pickup rules
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.capture = screen_capture
        self.pickit = pickit_rules or PickitRules()
        self.log = get_logger()

        # State
        self.stats = LootStats()
        self._last_items: List[LootItem] = []

        # Timing
        self.scan_delay: float = 0.1
        self.pickup_delay: float = 0.3
        self.click_delay: float = 0.1

        # Show items key (usually ALT)
        self.show_items_key: str = "alt"

    def scan_for_items(self, screen: np.ndarray = None) -> List[LootItem]:
        """
        Scan screen for item labels.

        Args:
            screen: Screen capture (will grab if not provided)

        Returns:
            List of detected items
        """
        if screen is None:
            if self.capture is None:
                return []
            screen = self.capture.grab()

        items = []

        # In full implementation, would:
        # 1. Crop to scan region
        # 2. Find text-like regions (high contrast horizontal bands)
        # 3. Extract label bounds
        # 4. Detect color/quality
        # 5. OCR for item name (optional)

        # For now, return placeholder
        self.stats.items_scanned = len(items)
        self.stats.last_scan_time = time.time()
        self._last_items = items

        return items

    def detect_quality(self, screen: np.ndarray, position: Tuple[int, int]) -> ItemQuality:
        """
        Detect item quality from label color.

        Args:
            screen: Screen capture
            position: Label position (center)

        Returns:
            Detected item quality
        """
        if screen is None:
            return ItemQuality.UNKNOWN

        x, y = position

        # Sample pixel color at position
        try:
            # Get small region around position
            region = screen[
                max(0, y - 5):min(screen.shape[0], y + 5),
                max(0, x - 20):min(screen.shape[1], x + 20),
            ]

            if region.size == 0:
                return ItemQuality.UNKNOWN

            # Get average color (BGR)
            avg_color = region.mean(axis=(0, 1))

            # Match to quality
            return self._match_quality_color(tuple(avg_color))

        except Exception as e:
            self.log.debug(f"Quality detection error: {e}")
            return ItemQuality.UNKNOWN

    def _match_quality_color(self, color: Tuple[float, float, float]) -> ItemQuality:
        """
        Match BGR color to item quality.

        Args:
            color: BGR color tuple

        Returns:
            Matched quality
        """
        b, g, r = color

        # Check gold first (most valuable)
        if r > 180 and g > 150 and g < 220 and b < 80:
            return ItemQuality.GOLD

        # Check set (green)
        if g > 180 and r < 100 and b < 100:
            return ItemQuality.GREEN

        # Check unique (gold/tan)
        if r > 200 and g > 180 and g < 220 and b < 100:
            return ItemQuality.GOLD

        # Check rare (yellow)
        if r > 200 and g > 200 and b < 100:
            return ItemQuality.YELLOW

        # Check magic (blue)
        if b > 200 and r < 100 and g < 180:
            return ItemQuality.BLUE

        # Check gray (socketed)
        if abs(r - g) < 30 and abs(g - b) < 30 and 100 < r < 180:
            return ItemQuality.GRAY

        # Check white
        if r > 200 and g > 200 and b > 200:
            return ItemQuality.WHITE

        return ItemQuality.UNKNOWN

    def should_pickup(self, item: LootItem) -> bool:
        """
        Check if item should be picked up based on pickit rules.

        Args:
            item: Detected item

        Returns:
            True if should pickup
        """
        item_name_lower = item.name.lower()

        # Always pick up gold
        if "gold" in item_name_lower:
            return True

        # Check name-based rules first (high priority)
        for pattern in self.pickit.always_pickup:
            if pattern.lower() in item_name_lower:
                return True

        for pattern in self.pickit.never_pickup:
            if pattern.lower() in item_name_lower:
                return False

        # Check quality-based rules
        quality = item.quality

        if quality == ItemQuality.GOLD:  # Unique
            return self.pickit.pickup_uniques

        if quality == ItemQuality.GREEN:  # Set
            return self.pickit.pickup_sets

        if quality == ItemQuality.YELLOW:  # Rare
            return self.pickit.pickup_rares

        if quality == ItemQuality.BLUE:  # Magic
            return self.pickit.pickup_magic

        if quality == ItemQuality.WHITE:
            return self.pickit.pickup_white

        if quality == ItemQuality.GRAY:  # Socketed
            return self.pickit.pickup_socketed

        return False

    def pickup_item(self, item: LootItem) -> bool:
        """
        Pick up a specific item.

        Args:
            item: Item to pick up

        Returns:
            True if pickup attempted
        """
        self.log.info(f"Picking up {item.quality.name} item at {item.position}")

        # Click on item
        x, y = item.position
        self.input.click(x, y)
        time.sleep(self.pickup_delay)

        self.stats.items_picked += 1
        return True

    def pickup_all_valid(self, screen: np.ndarray = None) -> int:
        """
        Scan and pick up all valid items.

        Args:
            screen: Screen capture

        Returns:
            Number of items picked up
        """
        # Show item labels
        self.input.key_down(self.show_items_key)
        time.sleep(0.2)

        try:
            items = self.scan_for_items(screen)
            picked = 0

            for item in items:
                if self.should_pickup(item):
                    item.should_pickup = True
                    if self.pickup_item(item):
                        picked += 1
                        time.sleep(self.click_delay)
                else:
                    self.stats.items_skipped += 1

            return picked

        finally:
            self.input.key_up(self.show_items_key)

    def quick_loot(self, positions: List[Tuple[int, int]]) -> int:
        """
        Quick loot at specific positions without full scan.

        Args:
            positions: Positions to click

        Returns:
            Number of clicks
        """
        self.input.key_down(self.show_items_key)
        time.sleep(0.1)

        try:
            count = 0
            for x, y in positions:
                self.input.click(x, y)
                time.sleep(self.click_delay)
                count += 1

            return count

        finally:
            self.input.key_up(self.show_items_key)

    def pickup_gold(self) -> None:
        """Pick up gold by clicking rapidly in loot area."""
        self.log.info("Picking up gold")

        # Click several times in corpse area
        center = (960, 400)  # Approximate corpse position
        offsets = [
            (0, 0), (-30, 0), (30, 0),
            (0, -30), (0, 30),
        ]

        for dx, dy in offsets:
            self.input.click(center[0] + dx, center[1] + dy)
            time.sleep(0.05)

    def get_last_items(self) -> List[LootItem]:
        """Get items from last scan."""
        return self._last_items.copy()

    def get_stats(self) -> LootStats:
        """Get looting statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = LootStats()

    def set_pickit_rules(self, rules: PickitRules) -> None:
        """Update pickit rules."""
        self.pickit = rules
        self.log.info("Pickit rules updated")


class ItemFilter:
    """
    Filters items based on complex rules.

    Extends basic pickit with stat-based filtering.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize item filter."""
        self.config = config or Config()
        self.log = get_logger()

        # Stat requirements
        self.min_stats: Dict[str, int] = {}  # e.g., {"strength": 100}
        self.required_mods: List[str] = []  # e.g., ["faster cast rate"]

    def add_stat_requirement(self, stat: str, min_value: int) -> None:
        """Add minimum stat requirement."""
        self.min_stats[stat] = min_value

    def add_required_mod(self, mod: str) -> None:
        """Add required modifier."""
        self.required_mods.append(mod.lower())

    def passes_filter(self, item: DetectedItem) -> bool:
        """
        Check if item passes filter.

        Args:
            item: Detected item with stats

        Returns:
            True if passes all requirements
        """
        # Check quality first (quick filter)
        if item.quality not in ["unique", "set", "rare"]:
            return False

        # Would check stats here if we had OCR
        # For now, pass all quality items
        return True

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.min_stats.clear()
        self.required_mods.clear()
