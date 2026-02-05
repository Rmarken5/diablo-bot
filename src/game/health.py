"""Health monitoring and chicken (emergency exit) system."""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional, List

from src.data.models import Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class HealthStatus(Enum):
    """Health status levels."""
    SAFE = auto()       # Above safe threshold
    WARNING = auto()    # Below warning but above chicken
    CRITICAL = auto()   # At or below chicken threshold
    UNKNOWN = auto()    # Cannot determine health


class PotionType(Enum):
    """Potion types."""
    HEALTH = "health"
    MANA = "mana"
    REJUV = "rejuv"  # Full rejuvenation


@dataclass
class HealthState:
    """Current health/mana state."""
    health_percent: float = 100.0
    mana_percent: float = 100.0
    status: HealthStatus = HealthStatus.SAFE
    last_check_time: float = 0.0
    last_potion_time: float = 0.0
    chicken_triggered: bool = False


@dataclass
class ChickenEvent:
    """Record of a chicken (emergency exit) event."""
    timestamp: float
    health_percent: float
    mana_percent: float
    reason: str
    potion_attempted: bool = False


class HealthMonitor:
    """
    Monitors health/mana and triggers emergency actions.

    Runs in a background thread, checking health at regular intervals.
    When health drops below threshold, attempts potion then chickens.
    """

    # Belt slot mapping
    POTION_SLOTS = {
        PotionType.HEALTH: 1,  # Slot 1 = health potions
        PotionType.MANA: 2,    # Slot 2 = mana potions
        PotionType.REJUV: 3,   # Slot 3 = rejuvs (emergency)
    }

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        game_detector=None,
        screen_capture=None,
    ):
        """
        Initialize health monitor.

        Args:
            config: Bot configuration
            input_ctrl: Input controller
            game_detector: Game state detector (for health reading)
            screen_capture: Screen capture
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.detector = game_detector
        self.capture = screen_capture
        self.log = get_logger()

        # State
        self.state = HealthState()
        self._chicken_history: List[ChickenEvent] = []

        # Thresholds from config
        self.chicken_health = self.config.chicken_health_percent
        self.chicken_mana = self.config.chicken_mana_percent
        self.warning_health = min(60, self.chicken_health + 20)

        # Potion cooldown (don't spam potions)
        self.potion_cooldown = 1.0  # seconds

        # Monitoring control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.check_interval = 0.1  # 100ms between checks

        # Callbacks
        self._on_chicken: Optional[Callable] = None
        self._on_low_health: Optional[Callable] = None

    def set_callbacks(
        self,
        on_chicken: Optional[Callable] = None,
        on_low_health: Optional[Callable] = None,
    ) -> None:
        """
        Set callback functions for events.

        Args:
            on_chicken: Called when chicken is triggered
            on_low_health: Called when health drops to warning level
        """
        self._on_chicken = on_chicken
        self._on_low_health = on_low_health

    def start_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._running:
            self.log.warning("Health monitor already running")
            return

        self._running = True
        self.state.chicken_triggered = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.log.info(f"Health monitor started (chicken at {self.chicken_health}%)")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.log.info("Health monitor stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop (runs in background thread)."""
        while self._running:
            try:
                self._check_and_respond()
                time.sleep(self.check_interval)
            except Exception as e:
                self.log.error(f"Health monitor error: {e}")
                time.sleep(0.5)

    def _check_and_respond(self) -> None:
        """Check health and take appropriate action."""
        # Update health state
        self._update_health_state()

        # Determine status
        status = self._evaluate_status()

        with self._lock:
            self.state.status = status
            self.state.last_check_time = time.time()

        # Respond based on status
        if status == HealthStatus.CRITICAL:
            self._handle_critical()
        elif status == HealthStatus.WARNING:
            self._handle_warning()

    def _update_health_state(self) -> None:
        """Update health/mana readings from game."""
        if self.detector is None or self.capture is None:
            # No detector - can't read health
            return

        try:
            screen = self.capture.grab()
            health = self.detector.get_health_percent(screen)
            mana = self.detector.get_mana_percent(screen)

            with self._lock:
                self.state.health_percent = health
                self.state.mana_percent = mana
        except Exception as e:
            self.log.debug(f"Failed to read health: {e}")

    def _evaluate_status(self) -> HealthStatus:
        """Evaluate current health status."""
        health = self.state.health_percent
        mana = self.state.mana_percent

        # Check chicken thresholds
        if health <= self.chicken_health:
            return HealthStatus.CRITICAL

        if self.chicken_mana > 0 and mana <= self.chicken_mana:
            return HealthStatus.CRITICAL

        # Check warning threshold
        if health <= self.warning_health:
            return HealthStatus.WARNING

        return HealthStatus.SAFE

    def _handle_critical(self) -> None:
        """Handle critical (chicken) situation."""
        if self.state.chicken_triggered:
            return  # Already triggered

        self.log.warning(
            f"CRITICAL: Health at {self.state.health_percent:.0f}% "
            f"(threshold: {self.chicken_health}%)"
        )

        # Try rejuv potion first
        potion_used = self.use_potion(PotionType.REJUV)

        # Small delay to see if potion helps
        if potion_used:
            time.sleep(0.3)
            self._update_health_state()
            if self.state.health_percent > self.chicken_health:
                self.log.info("Rejuv saved us!")
                return

        # Still critical - chicken out
        self.chicken(reason="health_critical", potion_attempted=potion_used)

    def _handle_warning(self) -> None:
        """Handle warning (low health) situation."""
        self.log.debug(f"Warning: Health at {self.state.health_percent:.0f}%")

        # Use health potion if off cooldown
        self.use_potion(PotionType.HEALTH)

        # Call warning callback
        if self._on_low_health:
            try:
                self._on_low_health(self.state.health_percent)
            except Exception as e:
                self.log.error(f"Low health callback error: {e}")

    def check_health(self) -> bool:
        """
        Check if health is safe (above chicken threshold).

        Returns:
            True if safe, False if should chicken
        """
        self._update_health_state()
        status = self._evaluate_status()
        return status != HealthStatus.CRITICAL

    def get_health_percent(self) -> float:
        """Get current health percentage."""
        return self.state.health_percent

    def get_mana_percent(self) -> float:
        """Get current mana percentage."""
        return self.state.mana_percent

    def use_potion(self, potion_type: PotionType) -> bool:
        """
        Use a potion from belt.

        Args:
            potion_type: Type of potion to use

        Returns:
            True if potion was used
        """
        # Check cooldown
        now = time.time()
        if now - self.state.last_potion_time < self.potion_cooldown:
            return False

        slot = self.POTION_SLOTS.get(potion_type, 1)
        self.log.info(f"Using {potion_type.value} potion (slot {slot})")

        self.input.use_potion(slot)
        self.state.last_potion_time = now
        return True

    def use_health_potion(self) -> bool:
        """Use health potion."""
        return self.use_potion(PotionType.HEALTH)

    def use_mana_potion(self) -> bool:
        """Use mana potion."""
        return self.use_potion(PotionType.MANA)

    def use_rejuv(self) -> bool:
        """Use rejuvenation potion."""
        return self.use_potion(PotionType.REJUV)

    def chicken(
        self,
        reason: str = "manual",
        potion_attempted: bool = False,
    ) -> None:
        """
        Emergency exit from game.

        Args:
            reason: Reason for chicken
            potion_attempted: Whether potion was tried first
        """
        with self._lock:
            if self.state.chicken_triggered:
                return
            self.state.chicken_triggered = True

        self.log.warning(f"CHICKEN! Reason: {reason}")

        # Record event
        event = ChickenEvent(
            timestamp=time.time(),
            health_percent=self.state.health_percent,
            mana_percent=self.state.mana_percent,
            reason=reason,
            potion_attempted=potion_attempted,
        )
        self._chicken_history.append(event)

        # Execute chicken sequence
        self._execute_chicken()

        # Call callback
        if self._on_chicken:
            try:
                self._on_chicken(event)
            except Exception as e:
                self.log.error(f"Chicken callback error: {e}")

    def _execute_chicken(self) -> None:
        """Execute the chicken (game exit) sequence."""
        self.log.info("Executing chicken sequence...")

        # Method 1: Save & Exit via menu
        # Press Escape to open menu
        self.input.press("escape")
        time.sleep(0.3)

        # Press Escape again for Save & Exit (or click the button)
        # In D2R, pressing Escape twice should save & exit
        self.input.press("escape")
        time.sleep(0.5)

        # Alternative: Use the quit hotkey if configured
        # Some people bind a key to quit

        self.log.info("Chicken sequence complete")

    def get_chicken_history(self) -> List[ChickenEvent]:
        """Get history of chicken events."""
        return self._chicken_history.copy()

    def get_chicken_count(self) -> int:
        """Get number of chickens this session."""
        return len(self._chicken_history)

    def reset_chicken_flag(self) -> None:
        """Reset chicken triggered flag (after rejoining game)."""
        with self._lock:
            self.state.chicken_triggered = False

    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._running

    def set_thresholds(
        self,
        chicken_health: Optional[int] = None,
        chicken_mana: Optional[int] = None,
        warning_health: Optional[int] = None,
    ) -> None:
        """
        Update monitoring thresholds.

        Args:
            chicken_health: New chicken health threshold
            chicken_mana: New chicken mana threshold
            warning_health: New warning health threshold
        """
        if chicken_health is not None:
            self.chicken_health = chicken_health
        if chicken_mana is not None:
            self.chicken_mana = chicken_mana
        if warning_health is not None:
            self.warning_health = warning_health

        self.log.info(
            f"Thresholds updated: chicken={self.chicken_health}%, "
            f"warning={self.warning_health}%"
        )


class MercenaryMonitor:
    """
    Monitor mercenary health.

    Similar to HealthMonitor but for the mercenary.
    Can trigger town portal to save merc.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        game_detector=None,
    ):
        """Initialize mercenary monitor."""
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.detector = game_detector
        self.log = get_logger()

        self.merc_health_percent: float = 100.0
        self.save_merc_threshold: int = 20  # TP if merc below this

    def check_merc_health(self) -> float:
        """
        Check mercenary health.

        Returns:
            Merc health percentage (0 if dead/no merc)
        """
        if self.detector is None:
            return 100.0

        # Would need detector method to read merc health
        # For now, return stored value
        return self.merc_health_percent

    def should_save_merc(self) -> bool:
        """Check if we should TP to save merc."""
        return self.merc_health_percent <= self.save_merc_threshold

    def give_merc_potion(self) -> None:
        """Give potion to mercenary (Shift+potion key)."""
        self.log.info("Giving potion to mercenary")
        self.input.key_down("shift")
        time.sleep(0.05)
        self.input.press("1")  # Health potion slot
        time.sleep(0.05)
        self.input.key_up("shift")
