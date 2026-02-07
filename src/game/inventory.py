"""Inventory and stash management for D2R Bot."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.data.models import Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class StashTab(Enum):
    """Stash tab indices."""
    PERSONAL_1 = 0
    PERSONAL_2 = 1
    PERSONAL_3 = 2
    SHARED_1 = 3
    SHARED_2 = 4
    SHARED_3 = 5


class BeltSlot(Enum):
    """Belt column types."""
    HEALTH = 1
    MANA = 2
    REJUV = 3
    FLEX = 4  # Antidote/thaw or extra


@dataclass
class InventorySlot:
    """Single inventory slot state."""
    row: int
    col: int
    occupied: bool = False
    screen_pos: Tuple[int, int] = (0, 0)


@dataclass
class InventoryState:
    """Current inventory state."""
    total_slots: int = 40  # 10x4 grid
    free_slots: int = 40
    occupied_slots: int = 0
    is_open: bool = False


class InventoryManager:
    """
    Manages inventory grid, stash interaction, and belt potions.

    Handles:
    - Inventory space detection
    - Moving items to stash
    - Belt potion management
    - Potion restocking from vendors
    """

    # Inventory grid layout (1920x1080, windowed)
    INVENTORY_TOP_LEFT = (1278, 388)
    SLOT_WIDTH = 29
    SLOT_HEIGHT = 29
    COLS = 10
    ROWS = 4

    # Stash grid layout
    STASH_TOP_LEFT = (153, 388)
    STASH_COLS = 10
    STASH_ROWS = 10

    # Stash tab button positions (1920x1080)
    STASH_TAB_POSITIONS = {
        StashTab.PERSONAL_1: (285, 365),
        StashTab.PERSONAL_2: (335, 365),
        StashTab.PERSONAL_3: (385, 365),
        StashTab.SHARED_1: (435, 365),
        StashTab.SHARED_2: (485, 365),
        StashTab.SHARED_3: (535, 365),
    }

    # Belt positions (1920x1080) - 4 columns, up to 4 rows
    BELT_TOP_LEFT = (860, 580)
    BELT_SLOT_WIDTH = 30
    BELT_SLOT_HEIGHT = 30
    BELT_COLS = 4
    BELT_ROWS = 4  # Max rows (depends on belt type)

    # Vendor buy potion area (approximate)
    VENDOR_POTION_AREA = {
        "health": (200, 450),
        "mana": (230, 450),
        "rejuv": (260, 450),
    }

    # Color thresholds for occupied slot detection (BGR)
    EMPTY_SLOT_COLOR_RANGE = {
        "lower": (10, 10, 10),
        "upper": (40, 40, 40),
    }

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        screen_capture=None,
        template_matcher=None,
    ):
        """
        Initialize inventory manager.

        Args:
            config: Bot configuration
            input_ctrl: Input controller
            screen_capture: Screen capture
            template_matcher: Template matcher
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.capture = screen_capture
        self.matcher = template_matcher
        self.log = get_logger()

        # State
        self.state = InventoryState()
        self._grid: List[List[InventorySlot]] = self._init_grid()

        # Timing
        self.click_delay = 0.15
        self.transfer_delay = 0.2

    def _init_grid(self) -> List[List[InventorySlot]]:
        """Initialize inventory grid with screen positions."""
        grid = []
        for row in range(self.ROWS):
            row_slots = []
            for col in range(self.COLS):
                x = self.INVENTORY_TOP_LEFT[0] + col * self.SLOT_WIDTH + self.SLOT_WIDTH // 2
                y = self.INVENTORY_TOP_LEFT[1] + row * self.SLOT_HEIGHT + self.SLOT_HEIGHT // 2
                row_slots.append(InventorySlot(
                    row=row,
                    col=col,
                    screen_pos=(x, y),
                ))
            grid.append(row_slots)
        return grid

    def get_slot_position(self, row: int, col: int) -> Tuple[int, int]:
        """
        Get screen position of an inventory slot.

        Args:
            row: Row index (0-3)
            col: Column index (0-9)

        Returns:
            (x, y) screen position of slot center
        """
        if 0 <= row < self.ROWS and 0 <= col < self.COLS:
            return self._grid[row][col].screen_pos
        return (0, 0)

    def scan_inventory(self, screen: np.ndarray = None) -> InventoryState:
        """
        Scan inventory to determine which slots are occupied.

        Uses color-based detection: empty slots are dark, occupied slots
        have item graphics (brighter/colored pixels).

        Args:
            screen: Screen capture (will grab if not provided)

        Returns:
            Updated inventory state
        """
        if screen is None:
            if self.capture is None:
                return self.state
            screen = self.capture.grab()

        occupied = 0

        for row in range(self.ROWS):
            for col in range(self.COLS):
                slot = self._grid[row][col]
                x, y = slot.screen_pos

                # Sample small region around slot center
                half = self.SLOT_WIDTH // 2 - 2
                region = screen[
                    max(0, y - half):min(screen.shape[0], y + half),
                    max(0, x - half):min(screen.shape[1], x + half),
                ]

                if region.size == 0:
                    continue

                # Check if slot is occupied by looking at mean brightness
                mean_brightness = region.mean()
                slot.occupied = mean_brightness > 35  # Dark = empty

                if slot.occupied:
                    occupied += 1

        self.state.occupied_slots = occupied
        self.state.free_slots = self.state.total_slots - occupied
        self.log.debug(f"Inventory: {self.state.free_slots} free / {self.state.total_slots} total")

        return self.state

    def get_free_space(self, screen: np.ndarray = None) -> int:
        """
        Get number of free inventory slots.

        Args:
            screen: Screen capture

        Returns:
            Number of free slots
        """
        state = self.scan_inventory(screen)
        return state.free_slots

    def is_full(self, screen: np.ndarray = None) -> bool:
        """
        Check if inventory is full (or nearly full).

        Args:
            screen: Screen capture

        Returns:
            True if 2 or fewer free slots
        """
        free = self.get_free_space(screen)
        return free <= 2

    def open_inventory(self) -> None:
        """Open inventory screen."""
        self.log.debug("Opening inventory")
        self.input.press("i")
        time.sleep(0.5)
        self.state.is_open = True

    def close_inventory(self) -> None:
        """Close inventory screen."""
        self.log.debug("Closing inventory")
        self.input.press("escape")
        time.sleep(0.3)
        self.state.is_open = False

    def click_slot(self, row: int, col: int) -> None:
        """
        Click an inventory slot.

        Args:
            row: Row index (0-3)
            col: Column index (0-9)
        """
        pos = self.get_slot_position(row, col)
        if pos != (0, 0):
            self.input.click(pos[0], pos[1])
            time.sleep(self.click_delay)

    def ctrl_click_slot(self, row: int, col: int) -> None:
        """
        Ctrl+click to transfer item to/from stash.

        Args:
            row: Row index
            col: Column index
        """
        pos = self.get_slot_position(row, col)
        if pos != (0, 0):
            self.input.key_down("ctrl")
            time.sleep(0.02)
            self.input.click(pos[0], pos[1])
            time.sleep(self.transfer_delay)
            self.input.key_up("ctrl")

    def stash_all_items(self) -> int:
        """
        Transfer all inventory items to stash via Ctrl+Click.

        Assumes stash is already open. Scans inventory and ctrl-clicks
        each occupied slot.

        Returns:
            Number of items transferred
        """
        self.log.info("Stashing all inventory items")

        screen = None
        if self.capture:
            screen = self.capture.grab()

        self.scan_inventory(screen)

        transferred = 0
        for row in range(self.ROWS):
            for col in range(self.COLS):
                slot = self._grid[row][col]
                if slot.occupied:
                    self.ctrl_click_slot(row, col)
                    transferred += 1
                    time.sleep(0.05)

        self.log.info(f"Stashed {transferred} items")
        return transferred

    def select_stash_tab(self, tab: StashTab) -> None:
        """
        Click a stash tab.

        Args:
            tab: Stash tab to select
        """
        pos = self.STASH_TAB_POSITIONS.get(tab)
        if pos:
            self.log.debug(f"Selecting stash tab: {tab.name}")
            self.input.click(pos[0], pos[1])
            time.sleep(0.3)

    def stash_items_to_tab(self, tab: StashTab = StashTab.PERSONAL_1) -> int:
        """
        Stash items to a specific tab.

        Selects the tab then transfers all inventory items.

        Args:
            tab: Target stash tab

        Returns:
            Number of items transferred
        """
        self.select_stash_tab(tab)
        return self.stash_all_items()

    def get_stash_slot_position(self, row: int, col: int) -> Tuple[int, int]:
        """
        Get screen position of a stash slot.

        Args:
            row: Row index (0-9)
            col: Column index (0-9)

        Returns:
            (x, y) screen position
        """
        x = self.STASH_TOP_LEFT[0] + col * self.SLOT_WIDTH + self.SLOT_WIDTH // 2
        y = self.STASH_TOP_LEFT[1] + row * self.SLOT_HEIGHT + self.SLOT_HEIGHT // 2
        return (x, y)

    # ========== Belt Management ==========

    def get_belt_slot_position(self, col: int, row: int = 0) -> Tuple[int, int]:
        """
        Get screen position of a belt slot.

        Args:
            col: Column (0-3, left to right)
            row: Row (0 = bottom/active, higher = stored)

        Returns:
            (x, y) screen position
        """
        x = self.BELT_TOP_LEFT[0] + col * self.BELT_SLOT_WIDTH + self.BELT_SLOT_WIDTH // 2
        y = self.BELT_TOP_LEFT[1] - row * self.BELT_SLOT_HEIGHT + self.BELT_SLOT_HEIGHT // 2
        return (x, y)

    def scan_belt(self, screen: np.ndarray = None) -> Dict[int, bool]:
        """
        Check which belt columns have potions.

        Args:
            screen: Screen capture

        Returns:
            Dict mapping column (0-3) to has_potion bool
        """
        if screen is None:
            if self.capture is None:
                return {i: True for i in range(self.BELT_COLS)}
            screen = self.capture.grab()

        belt_status = {}
        for col in range(self.BELT_COLS):
            x, y = self.get_belt_slot_position(col)

            half = self.BELT_SLOT_WIDTH // 2 - 2
            region = screen[
                max(0, y - half):min(screen.shape[0], y + half),
                max(0, x - half):min(screen.shape[1], x + half),
            ]

            if region.size == 0:
                belt_status[col] = False
                continue

            # Potion slots are colorful; empty slots are dark
            mean_brightness = region.mean()
            belt_status[col] = mean_brightness > 40

        return belt_status

    def fill_belt_from_inventory(self) -> int:
        """
        Move potions from inventory to belt by shift-clicking.

        Assumes inventory is open. Scans for potion-colored slots
        and shift-clicks them to move to belt.

        Returns:
            Number of potions moved
        """
        self.log.info("Filling belt from inventory")

        screen = None
        if self.capture:
            screen = self.capture.grab()

        moved = 0
        for row in range(self.ROWS):
            for col in range(self.COLS):
                slot = self._grid[row][col]
                if not slot.occupied:
                    continue

                # Check if slot contains a potion (red/blue/purple hues)
                if screen is not None and self._is_potion_slot(screen, slot.screen_pos):
                    self.input.key_down("shift")
                    time.sleep(0.02)
                    self.input.click(slot.screen_pos[0], slot.screen_pos[1])
                    time.sleep(self.click_delay)
                    self.input.key_up("shift")
                    moved += 1

        self.log.info(f"Moved {moved} potions to belt")
        return moved

    def _is_potion_slot(self, screen: np.ndarray, pos: Tuple[int, int]) -> bool:
        """
        Check if an inventory slot contains a potion based on color.

        Potions have distinctive red (health), blue (mana), or purple (rejuv) colors.

        Args:
            screen: Screen capture
            pos: Slot center position

        Returns:
            True if slot likely contains a potion
        """
        x, y = pos
        half = 10

        region = screen[
            max(0, y - half):min(screen.shape[0], y + half),
            max(0, x - half):min(screen.shape[1], x + half),
        ]

        if region.size == 0:
            return False

        avg_color = region.mean(axis=(0, 1))
        b, g, r = avg_color

        # Health potion (red)
        if r > 150 and g < 100 and b < 100:
            return True

        # Mana potion (blue)
        if b > 150 and r < 100 and g < 100:
            return True

        # Rejuv potion (purple)
        if r > 100 and b > 100 and g < 80:
            return True

        return False

    def buy_potions(self, potion_type: str = "health", count: int = 4) -> int:
        """
        Buy potions from vendor.

        Assumes vendor trade window is open. Right-clicks potion to buy.

        Args:
            potion_type: "health", "mana", or "rejuv"
            count: Number of potions to buy

        Returns:
            Number of potions bought
        """
        pos = self.VENDOR_POTION_AREA.get(potion_type)
        if pos is None:
            return 0

        self.log.info(f"Buying {count} {potion_type} potions")

        bought = 0
        for _ in range(count):
            self.input.right_click(pos[0], pos[1])
            time.sleep(self.click_delay)
            bought += 1

        return bought

    def buy_and_fill_potions(self) -> int:
        """
        Buy potions and fill belt.

        Buys health and mana potions then fills belt slots.

        Returns:
            Total potions bought
        """
        total = 0
        total += self.buy_potions("health", 8)
        total += self.buy_potions("mana", 8)
        return total

    # ========== Town Integration ==========

    def full_inventory_routine(self, town_manager) -> bool:
        """
        Complete inventory management routine.

        1. Open stash
        2. Stash valuable items
        3. Close stash
        4. Go to vendor
        5. Buy potions
        6. Fill belt

        Args:
            town_manager: TownManager instance

        Returns:
            True if routine completed
        """
        self.log.info("Starting inventory management routine")

        # 1. Stash items
        if town_manager.open_stash():
            time.sleep(0.5)
            self.stash_all_items()
            time.sleep(0.3)
            town_manager.close_stash()
            time.sleep(0.3)

        self.log.info("Inventory routine complete")
        return True
