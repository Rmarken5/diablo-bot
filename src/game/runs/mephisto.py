"""Mephisto farming run implementation."""

import time
from typing import Optional, Tuple

import numpy as np

from src.data.models import Config
from src.input.controller import InputController
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.town import TownManager
from src.utils.logger import get_logger

from .base import BaseRun, RunResult, RunStatus


class MephistoRun(BaseRun):
    """
    Mephisto farming run using the moat trick.

    Run sequence:
    1. Start in Act 3 town (or use waypoint from any town)
    2. Use waypoint to Durance of Hate Level 2
    3. Teleport to find Level 3 entrance
    4. Enter Durance of Hate Level 3
    5. Teleport to moat trick position
    6. Cast Static Field + Blizzard across the moat
    7. Loot drops
    8. Save & Exit

    The moat trick exploits that Mephisto cannot cross the moat
    surrounding his platform. The Sorceress teleports to a position
    across the moat and attacks from safety.
    """

    # Screen positions (1920x1080)
    SCREEN_CENTER = (960, 540)

    # Waypoint menu positions
    WAYPOINT_ACT3_TAB = (480, 120)  # Act 3 tab in waypoint menu
    WAYPOINT_DURANCE_2 = (480, 390)  # Durance of Hate Level 2

    # Teleport search directions for finding Level 3 entrance
    # Durance Level 2 is semi-random, so we teleport in a pattern
    SEARCH_DIRECTIONS = [
        (960, 300),    # North
        (1200, 300),   # North-East
        (1200, 540),   # East
        (1200, 700),   # South-East
        (960, 700),    # South
        (700, 700),    # South-West
        (700, 540),    # West
        (700, 300),    # North-West
    ]

    # Moat trick positions (relative to Mephisto's platform)
    # After entering Level 3, Mephisto is on a central raised platform
    # We teleport to a position across the moat (southeast corner is common)
    MOAT_POSITIONS = [
        (1100, 300),   # First moat position attempt
        (1150, 350),   # Slightly adjusted
        (1050, 280),   # Alternative angle
    ]

    # Mephisto's expected position from moat trick spot
    MEPHISTO_TARGET = (800, 400)

    # Max teleports before giving up on finding Level 3
    MAX_SEARCH_TELEPORTS = 25

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        combat: Optional[SorceressCombat] = None,
        health_monitor: Optional[HealthMonitor] = None,
        town_manager: Optional[TownManager] = None,
        game_detector=None,
        screen_capture=None,
        menu_navigator=None,
        loot_manager=None,
    ):
        """Initialize Mephisto run."""
        super().__init__(
            config=config,
            input_ctrl=input_ctrl,
            combat=combat,
            health_monitor=health_monitor,
            town_manager=town_manager,
            game_detector=game_detector,
            screen_capture=screen_capture,
            menu_navigator=menu_navigator,
            loot_manager=loot_manager,
        )

        self.log = get_logger()

        # Run settings
        self.static_casts: int = 5   # More casts for Mephisto (tankier boss)
        self.blizzard_casts: int = 6  # More Blizzards needed
        self.search_timeout: float = 30.0  # Max seconds searching for Level 3

        # Timing
        self.portal_load_time: float = 2.0
        self.cast_settle_time: float = 0.3
        self.waypoint_load_time: float = 1.5

        # Run timeout for Mephisto (longer than Pindle)
        self.run_timeout = 180.0

    @property
    def name(self) -> str:
        """Get run name."""
        return "Mephisto"

    def _execute_run(self) -> RunResult:
        """
        Execute Mephisto run.

        Returns:
            RunResult with status
        """
        kills = 0
        items = 0

        # Step 1: Ensure in town
        if not self._ensure_in_town():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Not in town",
            )

        # Health check
        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 2: Ensure buffs
        if self.combat:
            self.combat.ensure_buffs()
            time.sleep(0.3)

        # Step 3: Use waypoint to Durance Level 2
        if not self._waypoint_to_durance():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Could not waypoint to Durance Level 2",
            )

        # Wait for zone load
        time.sleep(self.waypoint_load_time)

        # Health check after zone
        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 4: Teleport to find Level 3 entrance
        if not self._find_level_3():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Could not find Durance Level 3 entrance",
            )

        # Step 5: Enter Level 3
        time.sleep(self.portal_load_time)

        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 6: Teleport to moat trick position
        if not self._position_for_moat_trick():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Could not reach moat position",
            )

        # Step 7: Kill Mephisto
        if self._kill_mephisto():
            kills = 1

        # Health check after combat
        if not self._check_health():
            return RunResult(
                status=RunStatus.CHICKEN,
                kills=kills,
            )

        # Step 8: Loot
        time.sleep(1.5)  # Wait for drops
        items = self._loot_area()

        # Step 9: Exit game
        self._exit_game()

        return RunResult(
            status=RunStatus.SUCCESS,
            kills=kills,
            items_picked=items,
        )

    def _ensure_in_town(self) -> bool:
        """Verify we're in town."""
        if self.detector:
            screen = self._grab_screen()
            if screen is not None and hasattr(self.detector, "is_in_town"):
                return self.detector.is_in_town(screen)

        self.log.debug("Assuming in town")
        return True

    def _waypoint_to_durance(self) -> bool:
        """
        Use waypoint to travel to Durance of Hate Level 2.

        Returns:
            True if waypoint taken successfully
        """
        self.log.info("Using waypoint to Durance of Hate Level 2")

        # Go to waypoint
        if self.town:
            if not self.town.use_waypoint():
                self.log.warning("Could not open waypoint")
                return False
        else:
            return False

        time.sleep(0.5)

        # Click Act 3 tab
        self.input.click(self.WAYPOINT_ACT3_TAB[0], self.WAYPOINT_ACT3_TAB[1])
        time.sleep(0.3)

        # Click Durance of Hate Level 2
        self.input.click(self.WAYPOINT_DURANCE_2[0], self.WAYPOINT_DURANCE_2[1])
        time.sleep(0.5)

        return True

    def _find_level_3(self) -> bool:
        """
        Teleport through Durance Level 2 to find Level 3 entrance.

        Uses a spiral-like search pattern, checking for the Level 3
        entrance (stairs) via template matching after each teleport.

        Returns:
            True if Level 3 entrance found and entered
        """
        self.log.info("Searching for Durance Level 3 entrance")

        if not self.combat:
            return False

        search_start = time.time()
        teleport_count = 0
        direction_idx = 0

        while teleport_count < self.MAX_SEARCH_TELEPORTS:
            # Check timeout
            if time.time() - search_start > self.search_timeout:
                self.log.warning("Search timeout - Level 3 not found")
                return False

            # Health check during search
            if not self._check_health():
                return False

            # Check for Level 3 entrance on screen
            if self._detect_level_3_entrance():
                self.log.info("Found Level 3 entrance!")
                return self._enter_level_3()

            # Teleport in current direction
            target = self.SEARCH_DIRECTIONS[direction_idx % len(self.SEARCH_DIRECTIONS)]
            self.combat.cast_teleport(target)
            time.sleep(0.2)

            teleport_count += 1

            # Cycle through directions (spiral pattern)
            # Change direction every 3 teleports
            if teleport_count % 3 == 0:
                direction_idx += 1

        self.log.warning(f"Level 3 not found after {teleport_count} teleports")
        return False

    def _detect_level_3_entrance(self) -> bool:
        """
        Check if Level 3 entrance (stairs) is visible on screen.

        Uses template matching if available, otherwise checks for
        characteristic visual elements.

        Returns:
            True if entrance detected
        """
        if getattr(self, 'matcher', None) is None or self.capture is None:
            # Without template matching, we can't reliably detect
            # Use heuristic: after enough teleports, try clicking center
            return False

        screen = self.capture.grab()
        # Look for stairs/entrance template
        match = self.matcher.find(screen, "objects/durance_stairs", threshold=0.7)
        if match:
            # Click on the stairs to enter
            self.log.info(f"Level 3 stairs detected at {match.center}")
            self.input.click(match.center[0], match.center[1])
            time.sleep(0.5)
            return True

        return False

    def _enter_level_3(self) -> bool:
        """
        Enter Durance of Hate Level 3.

        Returns:
            True if entered successfully
        """
        self.log.info("Entering Durance Level 3")

        # The entrance should already have been clicked in _detect_level_3_entrance
        # Wait for loading
        time.sleep(self.portal_load_time)

        return True

    def _position_for_moat_trick(self) -> bool:
        """
        Teleport to the moat trick position.

        After entering Level 3, teleport to a spot across the moat
        from Mephisto's platform where he cannot reach us.

        Returns:
            True if positioned successfully
        """
        self.log.info("Positioning for moat trick")

        if not self.combat:
            return False

        # Teleport toward Mephisto's platform first
        # Level 3 entrance is at the edge, Mephisto is in the center
        center_teleports = [
            (960, 350),   # North toward center
            (960, 300),   # Further toward platform
        ]

        for pos in center_teleports:
            if not self._check_health():
                return False
            self.combat.cast_teleport(pos)
            time.sleep(0.2)

        # Now teleport to moat position
        for pos in self.MOAT_POSITIONS:
            if not self._check_health():
                return False

            self.combat.cast_teleport(pos)
            time.sleep(0.3)

            # Check if we're in a good position
            # (In real implementation, would verify position visually)
            break  # Use first position for now

        self.log.info("Moat trick position reached")
        return True

    def _kill_mephisto(self) -> bool:
        """
        Kill Mephisto using moat trick.

        From across the moat:
        1. Cast Static Field (reduces Mephisto HP by 25% per cast)
        2. Cast Blizzard on Mephisto's position
        3. Repeat until dead

        Returns:
            True if kill sequence completed
        """
        self.log.info("Engaging Mephisto")

        if not self.combat:
            return False

        target = self.MEPHISTO_TARGET

        # Phase 1: Static Field spam (works across moat)
        for _ in range(self.static_casts):
            if not self._check_health():
                return False
            self.combat.cast_static_field()
            time.sleep(self.cast_settle_time)

        # Phase 2: Blizzard spam with Static Field between casts
        from src.game.combat import Skill

        for _ in range(self.blizzard_casts):
            if not self._check_health():
                return False
            self.combat.cast_blizzard(target)
            time.sleep(self.cast_settle_time)

            # Cast Static Field between Blizzard cooldowns
            if self.combat.can_cast(Skill.STATIC_FIELD):
                self.combat.cast_static_field()
                time.sleep(self.cast_settle_time)

        # Wait for final Blizzard damage
        time.sleep(3.0)

        # Extra Blizzard to ensure kill
        if self._check_health() and self.combat:
            self.combat.cast_blizzard(target)
            time.sleep(2.0)
            self.combat.cast_blizzard(target)

        self.log.info("Mephisto kill sequence complete")
        return True

    def _loot_area(self) -> int:
        """
        Loot items from Mephisto's corpse.

        Need to teleport onto the platform to pick up items
        since we're across the moat.

        Returns:
            Number of items picked up
        """
        self.log.info("Looting Mephisto drops")

        # Teleport onto Mephisto's platform to loot
        if self.combat:
            self.combat.cast_teleport(self.MEPHISTO_TARGET)
            time.sleep(0.5)

        # Use loot manager if available
        if self.loot:
            return self.loot.pickup_all_valid()

        # Fallback: click around corpse area with show items
        self.input.key_down("alt")
        time.sleep(0.3)

        items_picked = 0
        loot_positions = [
            self.MEPHISTO_TARGET,
            (self.MEPHISTO_TARGET[0] - 50, self.MEPHISTO_TARGET[1]),
            (self.MEPHISTO_TARGET[0] + 50, self.MEPHISTO_TARGET[1]),
            (self.MEPHISTO_TARGET[0], self.MEPHISTO_TARGET[1] - 40),
            (self.MEPHISTO_TARGET[0], self.MEPHISTO_TARGET[1] + 40),
        ]

        for pos in loot_positions:
            self.input.click(pos[0], pos[1])
            time.sleep(0.15)
            items_picked += 1

        self.input.key_up("alt")
        return items_picked

    # ========== Configuration ==========

    def set_static_casts(self, count: int) -> None:
        """Set number of Static Field casts."""
        self.static_casts = max(0, count)

    def set_blizzard_casts(self, count: int) -> None:
        """Set number of Blizzard casts."""
        self.blizzard_casts = max(1, count)

    def set_search_timeout(self, seconds: float) -> None:
        """Set Level 3 search timeout."""
        self.search_timeout = max(10.0, seconds)
