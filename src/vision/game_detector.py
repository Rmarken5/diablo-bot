"""Game state detection module."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.vision.template_matcher import TemplateMatcher, Match
from src.utils.logger import get_logger


class GameState(Enum):
    """Possible game states."""

    # Menu states
    MAIN_MENU = "main_menu"
    CHARACTER_SELECT = "character_select"
    LOBBY = "lobby"
    CREATE_GAME = "create_game"

    # Loading
    LOADING = "loading"

    # In-game states
    IN_GAME = "in_game"
    IN_TOWN = "in_town"

    # UI overlays (in-game)
    INVENTORY = "inventory"
    STASH = "stash"
    WAYPOINT = "waypoint"
    NPC_DIALOG = "npc_dialog"
    SKILL_TREE = "skill_tree"
    STAT_SCREEN = "stat_screen"
    QUEST_LOG = "quest_log"

    # Special states
    DEATH = "death"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """Player health and mana status."""

    health_percent: float
    mana_percent: float
    is_poisoned: bool = False
    is_low_health: bool = False
    is_low_mana: bool = False


class GameStateDetector:
    """
    Detects the current game state from screenshots.

    Uses template matching for UI detection and color analysis
    for health/mana orbs.
    """

    # Screen regions for 1920x1080 resolution
    # Health orb is bottom-left, mana orb is bottom-right
    HEALTH_ORB_REGION = (30, 885, 150, 150)  # (x, y, w, h)
    MANA_ORB_REGION = (1742, 885, 150, 150)

    # Belt region (bottom center)
    BELT_REGION = (800, 970, 320, 50)

    # Minimap region (top-right)
    MINIMAP_REGION = (1650, 10, 260, 260)

    # Color ranges for health/mana detection (BGR format)
    # Red color range for health
    HEALTH_COLOR_LOWER = np.array([0, 0, 120])
    HEALTH_COLOR_UPPER = np.array([80, 80, 255])

    # Blue color range for mana
    MANA_COLOR_LOWER = np.array([120, 0, 0])
    MANA_COLOR_UPPER = np.array([255, 80, 80])

    # Green tint for poison
    POISON_COLOR_LOWER = np.array([0, 100, 0])
    POISON_COLOR_UPPER = np.array([80, 255, 80])

    # Thresholds
    LOW_HEALTH_THRESHOLD = 0.30  # 30%
    LOW_MANA_THRESHOLD = 0.15    # 15%

    def __init__(
        self,
        template_matcher: Optional[TemplateMatcher] = None,
        resolution: Tuple[int, int] = (1920, 1080),
    ):
        """
        Initialize game state detector.

        Args:
            template_matcher: TemplateMatcher instance (creates one if not provided)
            resolution: Game resolution (width, height)
        """
        self.matcher = template_matcher or TemplateMatcher()
        self.resolution = resolution
        self.log = get_logger()

        # Cache for last detected state
        self._last_state: GameState = GameState.UNKNOWN
        self._last_health_status: Optional[HealthStatus] = None

        # Scale regions if not 1920x1080
        self._scale_regions()

        # Template mappings for state detection
        self._state_templates: Dict[GameState, List[str]] = {
            GameState.MAIN_MENU: ["screens/main_menu", "screens/play_button"],
            GameState.CHARACTER_SELECT: ["screens/character_select", "screens/char_list"],
            GameState.LOBBY: ["screens/lobby", "screens/game_list"],
            GameState.CREATE_GAME: ["screens/create_game"],
            GameState.LOADING: ["screens/loading", "screens/loading_bar"],
            GameState.DEATH: ["screens/death", "screens/you_died"],
            GameState.INVENTORY: ["hud/inventory_open", "hud/inventory_grid"],
            GameState.STASH: ["hud/stash_open", "hud/stash_tabs"],
            GameState.WAYPOINT: ["hud/waypoint_menu", "hud/waypoint_acts"],
            GameState.NPC_DIALOG: ["hud/npc_dialog", "hud/dialog_box"],
            GameState.SKILL_TREE: ["hud/skill_tree", "hud/skill_points"],
            GameState.STAT_SCREEN: ["hud/stat_screen", "hud/stat_points"],
            GameState.PAUSED: ["screens/paused", "screens/options_menu"],
            GameState.DISCONNECTED: ["screens/disconnected", "screens/connection_lost"],
        }

        # Templates that indicate we're in-game (HUD elements)
        self._in_game_templates = [
            "hud/health_orb",
            "hud/mana_orb",
            "hud/belt",
            "hud/minimap",
            "hud/experience_bar",
        ]

    def _scale_regions(self) -> None:
        """Scale detection regions based on resolution."""
        if self.resolution == (1920, 1080):
            return  # Default, no scaling needed

        scale_x = self.resolution[0] / 1920
        scale_y = self.resolution[1] / 1080

        def scale_region(region: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
            return (
                int(region[0] * scale_x),
                int(region[1] * scale_y),
                int(region[2] * scale_x),
                int(region[3] * scale_y),
            )

        self.HEALTH_ORB_REGION = scale_region(self.HEALTH_ORB_REGION)
        self.MANA_ORB_REGION = scale_region(self.MANA_ORB_REGION)
        self.BELT_REGION = scale_region(self.BELT_REGION)
        self.MINIMAP_REGION = scale_region(self.MINIMAP_REGION)

    def detect_state(self, screen: np.ndarray) -> GameState:
        """
        Detect the current game state from a screenshot.

        Args:
            screen: Screenshot as numpy array (BGR format)

        Returns:
            Detected GameState
        """
        # Check for specific UI states first (most specific to least)

        # Check for death screen
        if self._check_state_templates(screen, GameState.DEATH):
            self._last_state = GameState.DEATH
            return GameState.DEATH

        # Check for loading screen
        if self._check_state_templates(screen, GameState.LOADING):
            self._last_state = GameState.LOADING
            return GameState.LOADING

        # Check for menus
        if self._check_state_templates(screen, GameState.MAIN_MENU):
            self._last_state = GameState.MAIN_MENU
            return GameState.MAIN_MENU

        if self._check_state_templates(screen, GameState.CHARACTER_SELECT):
            self._last_state = GameState.CHARACTER_SELECT
            return GameState.CHARACTER_SELECT

        # Check for disconnection
        if self._check_state_templates(screen, GameState.DISCONNECTED):
            self._last_state = GameState.DISCONNECTED
            return GameState.DISCONNECTED

        # Check if we're in-game first
        if self._is_in_game(screen):
            # Check for in-game overlays
            for state in [
                GameState.INVENTORY,
                GameState.STASH,
                GameState.WAYPOINT,
                GameState.NPC_DIALOG,
                GameState.SKILL_TREE,
                GameState.STAT_SCREEN,
                GameState.PAUSED,
            ]:
                if self._check_state_templates(screen, state):
                    self._last_state = state
                    return state

            # Basic in-game state
            # Could differentiate IN_TOWN vs IN_GAME with town templates
            self._last_state = GameState.IN_GAME
            return GameState.IN_GAME

        # If nothing matched, return unknown
        self._last_state = GameState.UNKNOWN
        return GameState.UNKNOWN

    def _check_state_templates(self, screen: np.ndarray, state: GameState) -> bool:
        """Check if any template for a state matches."""
        templates = self._state_templates.get(state, [])
        for template_name in templates:
            match = self.matcher.find(screen, template_name, threshold=0.8)
            if match:
                self.log.debug(f"Found {template_name} for state {state.value}")
                return True
        return False

    def _is_in_game(self, screen: np.ndarray) -> bool:
        """Check if we're in-game by looking for HUD elements."""
        for template_name in self._in_game_templates:
            match = self.matcher.find(screen, template_name, threshold=0.7)
            if match:
                return True

        # Fallback: check for health orb by color
        health_pct = self.get_health_percent(screen)
        if health_pct > 0:
            return True

        return False

    def get_health_percent(self, screen: np.ndarray) -> float:
        """
        Get current health percentage from the health orb.

        Uses color detection to measure the amount of red in the orb.

        Args:
            screen: Screenshot as numpy array

        Returns:
            Health percentage (0.0 to 1.0)
        """
        return self._get_orb_percent(
            screen,
            self.HEALTH_ORB_REGION,
            self.HEALTH_COLOR_LOWER,
            self.HEALTH_COLOR_UPPER,
        )

    def get_mana_percent(self, screen: np.ndarray) -> float:
        """
        Get current mana percentage from the mana orb.

        Args:
            screen: Screenshot as numpy array

        Returns:
            Mana percentage (0.0 to 1.0)
        """
        return self._get_orb_percent(
            screen,
            self.MANA_ORB_REGION,
            self.MANA_COLOR_LOWER,
            self.MANA_COLOR_UPPER,
        )

    def _get_orb_percent(
        self,
        screen: np.ndarray,
        region: Tuple[int, int, int, int],
        color_lower: np.ndarray,
        color_upper: np.ndarray,
    ) -> float:
        """
        Calculate percentage fill of an orb by color.

        Args:
            screen: Screenshot
            region: (x, y, width, height) of orb area
            color_lower: Lower bound of color range (BGR)
            color_upper: Upper bound of color range (BGR)

        Returns:
            Fill percentage (0.0 to 1.0)
        """
        # Safety check for invalid screen
        if screen is None or screen.size == 0:
            self.log.debug("Invalid screen for orb detection, assuming full")
            return 1.0  # Assume full health/mana when can't detect

        x, y, w, h = region

        # Bounds check
        if y + h > screen.shape[0] or x + w > screen.shape[1]:
            self.log.debug(f"Region {region} out of bounds for screen {screen.shape}, assuming full")
            return 1.0  # Assume full when can't detect (safer than 0.0)

        # Extract orb region
        orb = screen[y:y+h, x:x+w]

        # Create mask for the color
        mask = cv2.inRange(orb, color_lower, color_upper)

        # Count colored pixels
        colored_pixels = cv2.countNonZero(mask)
        total_pixels = w * h

        # If no colored pixels detected, might be detection issue - assume full
        if colored_pixels == 0:
            self.log.debug("No colored pixels detected in orb, assuming full (may need calibration)")
            return 1.0

        # Calculate percentage
        # Note: This is a simple approximation. The actual orb is circular,
        # and the fill level is from bottom to top. For accurate reading,
        # we'd need to account for the orb shape.
        percentage = colored_pixels / total_pixels

        # Scale to approximate actual fill (orb is ~60-70% of bounding box)
        percentage = min(1.0, percentage / 0.65)

        return percentage

    def get_health_status(self, screen: np.ndarray) -> HealthStatus:
        """
        Get complete health and mana status.

        Args:
            screen: Screenshot

        Returns:
            HealthStatus with current values
        """
        health = self.get_health_percent(screen)
        mana = self.get_mana_percent(screen)

        # Check for poison (green tint in health orb)
        is_poisoned = self._check_poison(screen)

        status = HealthStatus(
            health_percent=health,
            mana_percent=mana,
            is_poisoned=is_poisoned,
            is_low_health=health < self.LOW_HEALTH_THRESHOLD,
            is_low_mana=mana < self.LOW_MANA_THRESHOLD,
        )

        self._last_health_status = status
        return status

    def _check_poison(self, screen: np.ndarray) -> bool:
        """Check if character is poisoned (green health orb)."""
        x, y, w, h = self.HEALTH_ORB_REGION

        if y + h > screen.shape[0] or x + w > screen.shape[1]:
            return False

        orb = screen[y:y+h, x:x+w]
        mask = cv2.inRange(orb, self.POISON_COLOR_LOWER, self.POISON_COLOR_UPPER)
        green_pixels = cv2.countNonZero(mask)

        # If significant green, probably poisoned
        return green_pixels > (w * h * 0.1)

    def is_inventory_open(self, screen: np.ndarray) -> bool:
        """Check if inventory is currently open."""
        return self._check_state_templates(screen, GameState.INVENTORY)

    def is_stash_open(self, screen: np.ndarray) -> bool:
        """Check if stash is currently open."""
        return self._check_state_templates(screen, GameState.STASH)

    def is_in_town(self, screen: np.ndarray) -> bool:
        """
        Check if player is in a town.

        Uses town-specific templates or minimap indicators.
        """
        # Check for town-specific elements
        town_templates = [
            "hud/town_indicator",
            "npcs/stash",  # Stash is only in town
        ]

        templates_available = False
        for template in town_templates:
            match = self.matcher.find(screen, template, threshold=0.7)
            if match:
                return True
            # Check if template was actually loaded (not just failed to match)
            if hasattr(self.matcher, '_cache') and template in self.matcher._cache:
                templates_available = True

        # If no templates are available, assume we're in town (development mode)
        if not templates_available:
            self.log.debug("Town detection templates not available, assuming in town")
            return True

        return False

    def get_player_position(self, screen: np.ndarray) -> Tuple[int, int]:
        """
        Get the player's position on screen.

        The player is typically centered, but this can be used
        to find the exact position for relative calculations.

        Returns:
            (x, y) position of player center
        """
        # Player is typically at screen center
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2

        # Could refine with player template matching
        # For now, return screen center
        return (center_x, center_y)

    def find_enemies(self, screen: np.ndarray) -> List[Match]:
        """
        Find enemy health bars on screen.

        Enemies have red health bars above them.

        Returns:
            List of Match objects for enemy positions
        """
        # Look for enemy health bar template
        matches = self.matcher.find_all(
            screen,
            "hud/enemy_health_bar",
            threshold=0.7,
            max_matches=20,
        )
        return matches

    def find_items(self, screen: np.ndarray) -> List[Match]:
        """
        Find item labels on the ground.

        Items have colored text labels based on quality.

        Returns:
            List of Match objects for item positions
        """
        # This would use color detection for item labels
        # For now, return empty list (implement in LootManager)
        return []

    def get_last_state(self) -> GameState:
        """Get the last detected state without re-scanning."""
        return self._last_state

    def get_last_health_status(self) -> Optional[HealthStatus]:
        """Get the last detected health status without re-scanning."""
        return self._last_health_status

    def preload_templates(self) -> int:
        """Preload all state detection templates."""
        all_templates = []

        for templates in self._state_templates.values():
            all_templates.extend(templates)

        all_templates.extend(self._in_game_templates)

        return self.matcher.preload_templates(all_templates)
