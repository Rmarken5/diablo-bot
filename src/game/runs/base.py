"""Base class for farming runs."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, List

from src.data.models import Config
from src.input.controller import InputController
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.town import TownManager
from src.utils.logger import get_logger


class RunStatus(Enum):
    """Status of a run."""
    SUCCESS = auto()       # Run completed successfully
    DEATH = auto()         # Character died
    CHICKEN = auto()       # Emergency exit triggered
    ERROR = auto()         # Run failed with error
    TIMEOUT = auto()       # Run timed out
    ABORTED = auto()       # User aborted


@dataclass
class RunResult:
    """Result of a farming run."""
    status: RunStatus
    run_time: float = 0.0
    kills: int = 0
    items_picked: int = 0
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)


class BaseRun(ABC):
    """
    Base class for all farming runs.

    Provides common functionality for runs like:
    - Health monitoring integration
    - Run timing
    - Error handling
    - Result tracking
    """

    # Hardcoded Save & Exit button position for 1920x1080
    SAVE_EXIT_BUTTON_POS = (960, 540)

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
        """
        Initialize base run.

        Args:
            config: Bot configuration
            input_ctrl: Input controller
            combat: Combat system
            health_monitor: Health monitoring
            town_manager: Town navigation
            game_detector: Game state detector
            screen_capture: Screen capture
            menu_navigator: Menu navigator (for Save & Exit)
            loot_manager: Loot detection and pickup
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.combat = combat
        self.health = health_monitor
        self.town = town_manager
        self.detector = game_detector
        self.capture = screen_capture
        self.menu = menu_navigator
        self.loot = loot_manager
        self.log = get_logger()

        # Run state
        self._running = False
        self._start_time: float = 0.0
        self._run_history: List[RunResult] = []

        # Callbacks
        self._on_run_complete: Optional[Callable] = None
        self._on_chicken: Optional[Callable] = None

        # Timeouts
        self.run_timeout: float = 120.0  # Max run time in seconds

    def set_callbacks(
        self,
        on_run_complete: Optional[Callable] = None,
        on_chicken: Optional[Callable] = None,
    ) -> None:
        """Set callback functions."""
        self._on_run_complete = on_run_complete
        self._on_chicken = on_chicken

    @property
    @abstractmethod
    def name(self) -> str:
        """Get run name."""
        pass

    @abstractmethod
    def _execute_run(self) -> RunResult:
        """
        Execute the run logic.

        Subclasses implement this with specific run behavior.

        Returns:
            RunResult with status and stats
        """
        pass

    def execute(self) -> RunResult:
        """
        Execute the farming run with safety checks.

        Returns:
            RunResult with status and stats
        """
        self.log.info(f"Starting {self.name} run")
        self._running = True
        self._start_time = time.time()

        # Start health monitoring
        if self.health:
            self.health.reset_chicken_flag()
            self.health.start_monitoring()

        try:
            result = self._execute_run()

            # Check for chicken
            if self.health and self.health.state.chicken_triggered:
                result = RunResult(
                    status=RunStatus.CHICKEN,
                    run_time=time.time() - self._start_time,
                    error_message="Emergency exit triggered",
                )

        except Exception as e:
            self.log.error(f"{self.name} run error: {e}")
            result = RunResult(
                status=RunStatus.ERROR,
                run_time=time.time() - self._start_time,
                error_message=str(e),
            )

        finally:
            self._running = False
            if self.health:
                self.health.stop_monitoring()

        # Record result
        result.run_time = time.time() - self._start_time
        self._run_history.append(result)

        self.log.info(
            f"{self.name} run complete: {result.status.name} "
            f"({result.run_time:.1f}s)"
        )

        # Call callbacks
        if self._on_run_complete:
            try:
                self._on_run_complete(result)
            except Exception as e:
                self.log.error(f"Run complete callback error: {e}")

        if result.status == RunStatus.CHICKEN and self._on_chicken:
            try:
                self._on_chicken(result)
            except Exception as e:
                self.log.error(f"Chicken callback error: {e}")

        return result

    def abort(self) -> None:
        """Abort the current run."""
        self.log.warning(f"Aborting {self.name} run")
        self._running = False

    def is_running(self) -> bool:
        """Check if run is in progress."""
        return self._running

    def check_timeout(self) -> bool:
        """Check if run has exceeded timeout."""
        if not self._running:
            return False
        elapsed = time.time() - self._start_time
        return elapsed > self.run_timeout

    def get_elapsed_time(self) -> float:
        """Get elapsed time of current run."""
        if not self._running:
            return 0.0
        return time.time() - self._start_time

    def get_run_history(self) -> List[RunResult]:
        """Get history of runs."""
        return self._run_history.copy()

    def get_run_count(self) -> int:
        """Get total number of runs."""
        return len(self._run_history)

    def get_success_count(self) -> int:
        """Get number of successful runs."""
        return sum(1 for r in self._run_history if r.status == RunStatus.SUCCESS)

    def get_chicken_count(self) -> int:
        """Get number of chicken runs."""
        return sum(1 for r in self._run_history if r.status == RunStatus.CHICKEN)

    def get_average_run_time(self) -> float:
        """Get average run time (successful runs only)."""
        successful = [r for r in self._run_history if r.status == RunStatus.SUCCESS]
        if not successful:
            return 0.0
        return sum(r.run_time for r in successful) / len(successful)

    def _check_health(self) -> bool:
        """
        Check if health is safe to continue.

        Returns:
            True if safe, False if should abort
        """
        if not self.health:
            return True
        return self.health.check_health()

    def _grab_screen(self):
        """Grab current screen if capture available."""
        if self.capture:
            return self.capture.grab()
        return None

    def _exit_game(self) -> None:
        """Exit game via Save & Exit with layered fallback.

        1. MenuNavigator.exit_game() (template-based)
        2. Hardcoded Save & Exit button position
        3. Escape x2 as last resort
        """
        self.log.info("Exiting game")

        if self.menu is not None:
            try:
                if self.menu.exit_game():
                    return
                self.log.warning("Menu navigator exit_game failed, trying fallback")
            except Exception as e:
                self.log.error(f"Menu navigator error during exit: {e}")

        self.input.press("escape")
        time.sleep(0.5)
        self.input.click(
            self.SAVE_EXIT_BUTTON_POS[0],
            self.SAVE_EXIT_BUTTON_POS[1],
        )
        time.sleep(0.5)
        self.input.press("escape")
        time.sleep(0.3)
