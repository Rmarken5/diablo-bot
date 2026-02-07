"""Error detection and recovery system for D2R Bot."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple

from src.utils.logger import get_logger


class ErrorSeverity(Enum):
    """Error severity levels."""
    RECOVERABLE = auto()   # Can auto-recover (stuck, minor glitch)
    RUN_ENDING = auto()    # Must end current run (death, chicken)
    CRITICAL = auto()      # Must stop bot (crash, repeated failures)


class ErrorType(Enum):
    """Types of errors the bot can encounter."""
    STUCK = "stuck"                     # Character not moving
    DISCONNECT = "disconnect"           # Lost connection
    GAME_CRASH = "game_crash"           # Game process died
    UNKNOWN_STATE = "unknown_state"     # Can't determine game state
    TEMPLATE_FAIL = "template_fail"     # Template matching failed
    TIMEOUT = "timeout"                 # Action timed out
    DEATH = "death"                     # Character died
    INVENTORY_FULL = "inventory_full"   # No space for items


# Classification of error types
ERROR_CLASSIFICATION: Dict[ErrorType, ErrorSeverity] = {
    ErrorType.STUCK: ErrorSeverity.RECOVERABLE,
    ErrorType.TEMPLATE_FAIL: ErrorSeverity.RECOVERABLE,
    ErrorType.TIMEOUT: ErrorSeverity.RECOVERABLE,
    ErrorType.INVENTORY_FULL: ErrorSeverity.RECOVERABLE,
    ErrorType.DEATH: ErrorSeverity.RUN_ENDING,
    ErrorType.DISCONNECT: ErrorSeverity.RUN_ENDING,
    ErrorType.UNKNOWN_STATE: ErrorSeverity.RUN_ENDING,
    ErrorType.GAME_CRASH: ErrorSeverity.CRITICAL,
}


@dataclass
class BotError:
    """Represents a bot error."""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    recovery_attempted: bool = False
    recovered: bool = False


class ErrorResolution(Enum):
    """Outcome of error handling."""
    CONTINUE = auto()        # Resume normal operation
    END_RUN = auto()         # End current run, start new
    RESTART_GAME = auto()    # Restart game client
    PAUSE_AND_ALERT = auto() # Stop and notify user


@dataclass
class PositionSample:
    """Position sample for stuck detection."""
    x: int
    y: int
    timestamp: float = field(default_factory=time.time)


class StuckDetector:
    """
    Detects when the character is stuck (not moving).

    Tracks position history and flags stuck state when
    position hasn't changed for a threshold number of samples.
    """

    def __init__(self, threshold: int = 5, distance_threshold: int = 10):
        """
        Initialize stuck detector.

        Args:
            threshold: Number of similar positions before flagging stuck
            distance_threshold: Max pixel distance to consider "same position"
        """
        self.threshold = threshold
        self.distance_threshold = distance_threshold
        self._history: List[PositionSample] = []
        self._max_history = 20
        self.log = get_logger()

    def update(self, x: int, y: int) -> bool:
        """
        Record new position and check if stuck.

        Args:
            x: Current X position
            y: Current Y position

        Returns:
            True if character appears stuck
        """
        sample = PositionSample(x=x, y=y)
        self._history.append(sample)

        if len(self._history) > self._max_history:
            self._history.pop(0)

        if len(self._history) < self.threshold:
            return False

        # Check if last N positions are all similar
        recent = self._history[-self.threshold:]
        reference = recent[0]

        for sample in recent[1:]:
            dx = abs(sample.x - reference.x)
            dy = abs(sample.y - reference.y)
            if dx > self.distance_threshold or dy > self.distance_threshold:
                return False

        self.log.warning(
            f"Stuck detected: position ~({reference.x}, {reference.y}) "
            f"for {self.threshold} samples"
        )
        return True

    def reset(self) -> None:
        """Clear position history."""
        self._history.clear()


class ErrorHandler:
    """
    Central error handling and recovery system.

    Classifies errors, attempts recovery, and escalates
    when recovery fails.
    """

    def __init__(
        self,
        max_retries: int = 3,
        input_ctrl=None,
        screen_capture=None,
        game_detector=None,
        combat=None,
        menu_navigator=None,
    ):
        """
        Initialize error handler.

        Args:
            max_retries: Maximum recovery attempts before escalating
            input_ctrl: Input controller
            screen_capture: Screen capture
            game_detector: Game state detector
            combat: Combat system (for emergency teleport)
            menu_navigator: Menu navigator
        """
        self.max_retries = max_retries
        self.input = input_ctrl
        self.capture = screen_capture
        self.detector = game_detector
        self.combat = combat
        self.menu = menu_navigator
        self.log = get_logger()

        # State
        self._error_history: List[BotError] = []
        self._retry_count: int = 0
        self._consecutive_errors: int = 0
        self._last_error_time: float = 0

        # Stuck detection
        self.stuck_detector = StuckDetector()

        # Callbacks
        self._on_critical: Optional[Callable] = None
        self._on_recovery: Optional[Callable] = None

    def set_callbacks(
        self,
        on_critical: Optional[Callable] = None,
        on_recovery: Optional[Callable] = None,
    ) -> None:
        """Set callback functions."""
        self._on_critical = on_critical
        self._on_recovery = on_recovery

    def handle(self, error_type: ErrorType, message: str = "") -> ErrorResolution:
        """
        Handle an error.

        Classifies the error, attempts recovery, and returns
        the appropriate resolution.

        Args:
            error_type: Type of error
            message: Error description

        Returns:
            ErrorResolution indicating what the caller should do
        """
        severity = ERROR_CLASSIFICATION.get(error_type, ErrorSeverity.CRITICAL)

        error = BotError(
            error_type=error_type,
            severity=severity,
            message=message,
        )
        self._error_history.append(error)

        self.log.warning(
            f"Error: {error_type.value} ({severity.name}) - {message}"
        )

        # Track consecutive errors
        self._consecutive_errors += 1
        self._last_error_time = time.time()

        # Too many consecutive errors -> escalate to critical
        if self._consecutive_errors > self.max_retries * 2:
            self.log.error("Too many consecutive errors - escalating to critical")
            return self._handle_critical(error)

        # Handle based on severity
        if severity == ErrorSeverity.RECOVERABLE:
            return self._handle_recoverable(error)
        elif severity == ErrorSeverity.RUN_ENDING:
            return self._handle_run_ending(error)
        else:
            return self._handle_critical(error)

    def _handle_recoverable(self, error: BotError) -> ErrorResolution:
        """
        Handle a recoverable error.

        Args:
            error: The error to handle

        Returns:
            ErrorResolution
        """
        self._retry_count += 1

        if self._retry_count > self.max_retries:
            self.log.warning(
                f"Max retries ({self.max_retries}) exceeded for "
                f"{error.error_type.value} - ending run"
            )
            self._retry_count = 0
            return ErrorResolution.END_RUN

        # Attempt recovery based on error type
        recovered = False

        if error.error_type == ErrorType.STUCK:
            recovered = self._recover_stuck()
        elif error.error_type == ErrorType.TEMPLATE_FAIL:
            recovered = self._recover_template_fail()
        elif error.error_type == ErrorType.TIMEOUT:
            recovered = self._recover_timeout()
        elif error.error_type == ErrorType.INVENTORY_FULL:
            recovered = self._recover_inventory_full()

        error.recovery_attempted = True
        error.recovered = recovered

        if recovered:
            self.log.info(f"Recovered from {error.error_type.value}")
            self._consecutive_errors = 0
            if self._on_recovery:
                self._on_recovery(error)
            return ErrorResolution.CONTINUE
        else:
            self.log.warning(f"Recovery failed for {error.error_type.value}")
            return ErrorResolution.END_RUN

    def _handle_run_ending(self, error: BotError) -> ErrorResolution:
        """Handle a run-ending error."""
        self._retry_count = 0

        if error.error_type == ErrorType.DISCONNECT:
            # Try to reconnect
            if self._recover_disconnect():
                return ErrorResolution.RESTART_GAME
            return ErrorResolution.PAUSE_AND_ALERT

        if error.error_type == ErrorType.DEATH:
            return ErrorResolution.END_RUN

        return ErrorResolution.END_RUN

    def _handle_critical(self, error: BotError) -> ErrorResolution:
        """Handle a critical error."""
        self.log.error(f"CRITICAL ERROR: {error.error_type.value} - {error.message}")

        if self._on_critical:
            self._on_critical(error)

        if error.error_type == ErrorType.GAME_CRASH:
            return ErrorResolution.RESTART_GAME

        return ErrorResolution.PAUSE_AND_ALERT

    # ========== Recovery Strategies ==========

    def _recover_stuck(self) -> bool:
        """
        Attempt to recover from stuck state.

        Strategy: Teleport in a random direction.

        Returns:
            True if recovery successful
        """
        self.log.info("Attempting stuck recovery")

        if self.combat:
            import random
            # Teleport in a random direction
            x = random.randint(400, 1500)
            y = random.randint(200, 800)
            self.combat.cast_teleport((x, y))
            time.sleep(0.5)
            self.stuck_detector.reset()
            return True

        if self.input:
            # Without combat, try clicking in a random direction
            import random
            x = random.randint(400, 1500)
            y = random.randint(200, 800)
            self.input.click(x, y)
            time.sleep(1.0)
            return True

        return False

    def _recover_template_fail(self) -> bool:
        """
        Recover from template matching failure.

        Strategy: Wait a moment and retry (screen may have been
        in transition).

        Returns:
            True (always - just adds a delay)
        """
        self.log.info("Template fail recovery - waiting for screen update")
        time.sleep(1.0)
        return True

    def _recover_timeout(self) -> bool:
        """
        Recover from an action timeout.

        Strategy: Press Escape to close any open UI, small delay.

        Returns:
            True if recovery attempted
        """
        self.log.info("Timeout recovery - closing UI and waiting")

        if self.input:
            self.input.press("escape")
            time.sleep(0.5)

        return True

    def _recover_inventory_full(self) -> bool:
        """
        Handle full inventory.

        Returns False to signal the run should end and do
        town management.

        Returns:
            False (caller should go to town)
        """
        self.log.info("Inventory full - signaling town trip needed")
        return False

    def _recover_disconnect(self) -> bool:
        """
        Attempt to recover from a disconnect.

        Strategy: Wait for reconnect dialog, try to rejoin.

        Returns:
            True if reconnection possible
        """
        self.log.info("Attempting disconnect recovery")

        # Wait for possible auto-reconnect
        time.sleep(5.0)

        # Check if we're back in game or at menu
        if self.detector and self.capture:
            screen = self.capture.grab()
            state = self.detector.detect_state(screen)
            if state in ("in_game", "in_town"):
                return True
            if state in ("main_menu", "character_select"):
                return True  # Caller should restart game

        return False

    # ========== Stuck Detection Integration ==========

    def check_stuck(self, x: int, y: int) -> bool:
        """
        Update position and check if stuck.

        Args:
            x: Current X position
            y: Current Y position

        Returns:
            True if stuck
        """
        return self.stuck_detector.update(x, y)

    def reset_stuck(self) -> None:
        """Reset stuck detection."""
        self.stuck_detector.reset()

    # ========== Statistics ==========

    def get_error_history(self) -> List[BotError]:
        """Get error history."""
        return self._error_history.copy()

    def get_error_count(self) -> int:
        """Get total error count."""
        return len(self._error_history)

    def get_recovery_rate(self) -> float:
        """Get percentage of errors that were recovered."""
        attempted = [e for e in self._error_history if e.recovery_attempted]
        if not attempted:
            return 0.0
        recovered = sum(1 for e in attempted if e.recovered)
        return (recovered / len(attempted)) * 100

    def clear_error_state(self) -> None:
        """Reset error tracking (e.g., after successful run)."""
        self._retry_count = 0
        self._consecutive_errors = 0
        self.stuck_detector.reset()
