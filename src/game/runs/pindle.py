"""Pindleskin farming run implementation."""

import time
from typing import Optional, Tuple

import numpy as np

from src.data.models import Config
from src.input.controller import InputController
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.town import TownManager, NPC
from src.utils.logger import get_logger

from .base import BaseRun, RunResult, RunStatus


class PindleRun(BaseRun):
    """
    Pindleskin farming run.

    Run sequence:
    1. Start in Harrogath (Act 5 town)
    2. Go to Anya's red portal (Nihlathak's Temple)
    3. Enter portal
    4. Teleport to Pindleskin (short distance north)
    5. Cast Blizzard/attack until dead
    6. Loot items
    7. Save & Exit or Town Portal
    8. Repeat

    Pindleskin is always in the same location outside the red portal,
    making this one of the easiest and fastest boss runs.
    """

    # Screen positions (1920x1080)
    SCREEN_CENTER = (960, 540)
    PORTAL_ENTER_OFFSET = (0, -50)  # Click slightly above center to enter portal

    # Pindleskin spawns north of portal - teleport direction
    PINDLE_TELEPORT_POSITIONS = [
        (960, 300),   # North of center
        (960, 200),   # Further north
    ]

    # After killing, expected Pindleskin corpse area
    LOOT_SCAN_POSITIONS = [
        (960, 250),
        (860, 250),
        (1060, 250),
    ]

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        combat: Optional[SorceressCombat] = None,
        health_monitor: Optional[HealthMonitor] = None,
        town_manager: Optional[TownManager] = None,
        game_detector=None,
        screen_capture=None,
    ):
        """Initialize Pindleskin run."""
        super().__init__(
            config=config,
            input_ctrl=input_ctrl,
            combat=combat,
            health_monitor=health_monitor,
            town_manager=town_manager,
            game_detector=game_detector,
            screen_capture=screen_capture,
        )

        self.log = get_logger()

        # Run settings
        self.static_casts: int = 2  # Static Field casts before Blizzard
        self.blizzard_casts: int = 3  # Blizzard casts
        self.wait_for_loot: float = 1.0  # Seconds to wait after kill
        self.teleport_to_pindle: bool = True  # Use teleport to reach Pindle

        # Timing
        self.portal_load_time: float = 1.5  # Wait after entering portal
        self.cast_settle_time: float = 0.3  # Wait between casts

    @property
    def name(self) -> str:
        """Get run name."""
        return "Pindleskin"

    def _execute_run(self) -> RunResult:
        """
        Execute Pindleskin run.

        Returns:
            RunResult with status
        """
        kills = 0
        items = 0

        # Step 1: Make sure we're in town
        if not self._ensure_in_town():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Not in town",
            )

        # Health check
        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 2: Ensure buffs are up
        if self.combat:
            self.combat.ensure_buffs()
            time.sleep(0.3)

        # Step 3: Go to red portal
        if not self._go_to_red_portal():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Could not find red portal",
            )

        # Step 4: Enter portal
        if not self._enter_portal():
            return RunResult(
                status=RunStatus.ERROR,
                error_message="Could not enter portal",
            )

        # Loading screen wait
        time.sleep(self.portal_load_time)

        # Health check after zone
        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 5: Teleport to Pindleskin
        if self.teleport_to_pindle:
            self._teleport_to_pindle()

        # Step 6: Kill Pindleskin
        if self._kill_pindleskin():
            kills = 1

        # Health check after combat
        if not self._check_health():
            return RunResult(
                status=RunStatus.CHICKEN,
                kills=kills,
            )

        # Step 7: Loot
        time.sleep(self.wait_for_loot)  # Wait for items to drop
        items = self._loot_area()

        # Step 8: Exit game (save & exit for fast restart)
        self._exit_game()

        return RunResult(
            status=RunStatus.SUCCESS,
            kills=kills,
            items_picked=items,
        )

    def _ensure_in_town(self) -> bool:
        """
        Verify we're in Act 5 town.

        Returns:
            True if in town
        """
        if self.detector:
            screen = self._grab_screen()
            if screen is not None:
                # Would check for town indicators
                pass

        # For now, assume we're in town if starting a run
        self.log.debug("Assuming in town")
        return True

    def _go_to_red_portal(self) -> bool:
        """
        Navigate to Anya's red portal.

        Returns:
            True if portal found
        """
        self.log.info("Going to red portal")

        if self.town:
            return self.town.go_to_portal()

        # Fallback: assume portal is nearby
        # In real implementation, would use town navigation
        return True

    def _enter_portal(self) -> bool:
        """
        Enter the red portal.

        Returns:
            True if entered successfully
        """
        self.log.info("Entering red portal")

        # Click on portal to enter
        portal_pos = (
            self.SCREEN_CENTER[0] + self.PORTAL_ENTER_OFFSET[0],
            self.SCREEN_CENTER[1] + self.PORTAL_ENTER_OFFSET[1],
        )

        self.input.click(portal_pos[0], portal_pos[1])
        time.sleep(0.5)

        # Double-click to ensure entry
        self.input.click(portal_pos[0], portal_pos[1])

        return True

    def _teleport_to_pindle(self) -> None:
        """Teleport toward Pindleskin location."""
        self.log.info("Teleporting to Pindleskin")

        if not self.combat:
            return

        for pos in self.PINDLE_TELEPORT_POSITIONS:
            if not self._check_health():
                return

            self.combat.cast_teleport(pos)
            time.sleep(0.2)

    def _kill_pindleskin(self) -> bool:
        """
        Execute combat to kill Pindleskin.

        Returns:
            True if kill assumed successful
        """
        self.log.info("Engaging Pindleskin")

        if not self.combat:
            return False

        # Target area (Pindleskin spawns north of entry)
        target = (960, 250)

        # Cast Static Field to reduce HP quickly
        for _ in range(self.static_casts):
            if not self._check_health():
                return False
            self.combat.cast_static_field()
            time.sleep(self.cast_settle_time)

        # Cast Blizzard
        for _ in range(self.blizzard_casts):
            if not self._check_health():
                return False
            self.combat.cast_blizzard(target)
            time.sleep(self.cast_settle_time)

        # Wait for Blizzard damage
        time.sleep(2.0)

        # Additional Blizzard if needed
        if self._check_health():
            self.combat.cast_blizzard(target)

        self.log.info("Pindleskin kill sequence complete")
        return True

    def _loot_area(self) -> int:
        """
        Scan and loot items.

        Returns:
            Number of items picked up
        """
        self.log.info("Looting area")

        # In full implementation, would:
        # 1. Press show items key
        # 2. Scan for item labels
        # 3. Check pickit rules
        # 4. Click to pickup

        # For now, simulate looting by pressing show items
        self.input.press("alt")  # Show items
        time.sleep(0.5)

        # Scan the loot positions
        items_picked = 0
        for pos in self.LOOT_SCAN_POSITIONS:
            # Would check for items at this position
            # Click if valid item found
            pass

        self.input.key_up("alt")  # Hide items

        return items_picked

    def _exit_game(self) -> None:
        """Exit game via save & exit."""
        self.log.info("Exiting game")

        # Press Escape twice for Save & Exit
        self.input.press("escape")
        time.sleep(0.3)
        self.input.press("escape")
        time.sleep(0.5)

    def find_pindleskin(self, screen: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect Pindleskin on screen.

        Args:
            screen: Screen capture

        Returns:
            Position of Pindleskin or None
        """
        if self.detector is None:
            return None

        # Would use template matching or name detection
        # Pindleskin has a unique name label

        # For now, return expected position
        return (960, 250)

    def set_static_casts(self, count: int) -> None:
        """Set number of Static Field casts."""
        self.static_casts = max(0, count)

    def set_blizzard_casts(self, count: int) -> None:
        """Set number of Blizzard casts."""
        self.blizzard_casts = max(1, count)
