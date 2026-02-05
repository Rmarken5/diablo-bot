"""Bot state machine for controlling execution flow."""

import time
import threading
from enum import Enum, auto
from typing import Callable, Dict, Optional, Set

from src.data.models import Config
from src.utils.logger import get_logger


class BotState(Enum):
    """Possible states for the bot."""

    # Core states
    IDLE = auto()
    STARTING = auto()
    STOPPING = auto()

    # Menu/lobby states
    MAIN_MENU = auto()
    CHARACTER_SELECT = auto()
    LOBBY = auto()
    CREATING_GAME = auto()
    JOINING_GAME = auto()
    LOADING = auto()

    # In-game states
    IN_TOWN = auto()
    RUNNING = auto()  # Executing a run
    IN_COMBAT = auto()
    LOOTING = auto()
    RETURNING_TO_TOWN = auto()

    # Town activities
    STASHING = auto()
    SHOPPING = auto()
    HEALING = auto()
    REPAIRING = auto()

    # Special states
    LEVELING_UP = auto()  # Allocating points
    DEAD = auto()
    CHICKENED = auto()  # Emergency exited

    # Error states
    STUCK = auto()
    ERROR = auto()
    DISCONNECTED = auto()


# Valid state transitions map
# Each state maps to a set of states it can transition to
VALID_TRANSITIONS: Dict[BotState, Set[BotState]] = {
    BotState.IDLE: {
        BotState.STARTING,
        BotState.STOPPING,
    },
    BotState.STARTING: {
        BotState.MAIN_MENU,
        BotState.CHARACTER_SELECT,
        BotState.IN_TOWN,  # If already in game
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.MAIN_MENU: {
        BotState.CHARACTER_SELECT,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.CHARACTER_SELECT: {
        BotState.LOBBY,
        BotState.CREATING_GAME,
        BotState.MAIN_MENU,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.LOBBY: {
        BotState.CREATING_GAME,
        BotState.JOINING_GAME,
        BotState.CHARACTER_SELECT,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.CREATING_GAME: {
        BotState.LOADING,
        BotState.LOBBY,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.JOINING_GAME: {
        BotState.LOADING,
        BotState.LOBBY,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.LOADING: {
        BotState.IN_TOWN,
        BotState.MAIN_MENU,  # Disconnect during load
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.IN_TOWN: {
        BotState.RUNNING,
        BotState.STASHING,
        BotState.SHOPPING,
        BotState.HEALING,
        BotState.REPAIRING,
        BotState.LEVELING_UP,
        BotState.LOADING,  # Save & exit
        BotState.MAIN_MENU,  # Quit to menu
        BotState.DISCONNECTED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.RUNNING: {
        BotState.IN_COMBAT,
        BotState.LOOTING,
        BotState.RETURNING_TO_TOWN,
        BotState.IN_TOWN,
        BotState.DEAD,
        BotState.CHICKENED,
        BotState.STUCK,
        BotState.DISCONNECTED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.IN_COMBAT: {
        BotState.RUNNING,
        BotState.LOOTING,
        BotState.DEAD,
        BotState.CHICKENED,
        BotState.STUCK,
        BotState.DISCONNECTED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.LOOTING: {
        BotState.RUNNING,
        BotState.IN_COMBAT,
        BotState.RETURNING_TO_TOWN,
        BotState.DEAD,
        BotState.CHICKENED,
        BotState.DISCONNECTED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.RETURNING_TO_TOWN: {
        BotState.IN_TOWN,
        BotState.LOADING,
        BotState.DEAD,
        BotState.CHICKENED,
        BotState.DISCONNECTED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.STASHING: {
        BotState.IN_TOWN,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.SHOPPING: {
        BotState.IN_TOWN,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.HEALING: {
        BotState.IN_TOWN,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.REPAIRING: {
        BotState.IN_TOWN,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.LEVELING_UP: {
        BotState.IN_TOWN,
        BotState.RUNNING,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.DEAD: {
        BotState.IN_TOWN,  # Respawn
        BotState.MAIN_MENU,  # Quit
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.CHICKENED: {
        BotState.MAIN_MENU,
        BotState.CHARACTER_SELECT,
        BotState.IN_TOWN,  # Rejoined
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.STUCK: {
        BotState.RUNNING,  # Unstuck successful
        BotState.IN_TOWN,  # TP out
        BotState.CHICKENED,
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.ERROR: {
        BotState.IDLE,  # Recovery
        BotState.MAIN_MENU,
        BotState.STOPPING,
    },
    BotState.DISCONNECTED: {
        BotState.MAIN_MENU,
        BotState.STARTING,  # Reconnect
        BotState.ERROR,
        BotState.STOPPING,
    },
    BotState.STOPPING: {
        BotState.IDLE,
    },
}


class StateTransitionError(Exception):
    """Invalid state transition attempted."""
    pass


class BotStateMachine:
    """
    Core state machine for controlling bot execution flow.

    Manages state transitions, executes handlers, and runs the main loop.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        tick_rate: float = 0.1,  # 10 updates per second
    ):
        """
        Initialize the state machine.

        Args:
            config: Bot configuration (optional)
            tick_rate: Seconds between update ticks
        """
        self.config = config or Config()
        self.tick_rate = tick_rate
        self.log = get_logger()

        # State tracking
        self._state = BotState.IDLE
        self._previous_state: Optional[BotState] = None
        self._state_start_time = time.time()

        # Handlers
        self._state_handlers: Dict[BotState, Callable] = {}
        self._entry_handlers: Dict[BotState, Callable] = {}
        self._exit_handlers: Dict[BotState, Callable] = {}

        # Control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> BotState:
        """Get current state."""
        return self._state

    @property
    def previous_state(self) -> Optional[BotState]:
        """Get previous state."""
        return self._previous_state

    @property
    def state_duration(self) -> float:
        """Get time in current state (seconds)."""
        return time.time() - self._state_start_time

    @property
    def is_running(self) -> bool:
        """Check if main loop is running."""
        return self._running

    def can_transition_to(self, target: BotState) -> bool:
        """Check if transition to target state is valid."""
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return target in valid_targets

    def transition_to(self, target: BotState, force: bool = False) -> bool:
        """
        Transition to a new state.

        Args:
            target: State to transition to
            force: Skip validation (use with caution)

        Returns:
            True if transition succeeded

        Raises:
            StateTransitionError: If transition is invalid and not forced
        """
        with self._lock:
            if self._state == target:
                return True  # Already in target state

            if not force and not self.can_transition_to(target):
                raise StateTransitionError(
                    f"Cannot transition from {self._state.name} to {target.name}"
                )

            # Call exit handler for current state
            exit_handler = self._exit_handlers.get(self._state)
            if exit_handler:
                try:
                    exit_handler(self._state, target)
                except Exception as e:
                    self.log.error(f"Exit handler error for {self._state.name}: {e}")

            # Update state
            self._previous_state = self._state
            self._state = target
            self._state_start_time = time.time()

            self.log.info(
                f"State: {self._previous_state.name} -> {target.name}"
            )

            # Call entry handler for new state
            entry_handler = self._entry_handlers.get(target)
            if entry_handler:
                try:
                    entry_handler(self._previous_state, target)
                except Exception as e:
                    self.log.error(f"Entry handler error for {target.name}: {e}")

            return True

    def register_handler(
        self,
        state: BotState,
        handler: Callable,
        on_entry: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
    ) -> None:
        """
        Register handlers for a state.

        Args:
            state: State to register handlers for
            handler: Main handler called each tick while in state
            on_entry: Called once when entering state (prev_state, new_state)
            on_exit: Called once when leaving state (old_state, new_state)
        """
        self._state_handlers[state] = handler
        if on_entry:
            self._entry_handlers[state] = on_entry
        if on_exit:
            self._exit_handlers[state] = on_exit

    def unregister_handler(self, state: BotState) -> None:
        """Remove all handlers for a state."""
        self._state_handlers.pop(state, None)
        self._entry_handlers.pop(state, None)
        self._exit_handlers.pop(state, None)

    def update(self) -> None:
        """
        Execute one update tick.

        Calls the handler for the current state.
        """
        handler = self._state_handlers.get(self._state)
        if handler:
            try:
                handler()
            except Exception as e:
                self.log.error(f"Handler error in {self._state.name}: {e}")
                # Transition to error state
                try:
                    self.transition_to(BotState.ERROR)
                except StateTransitionError:
                    pass  # Already can't transition

    def start(self) -> None:
        """
        Start the main loop in a background thread.

        The loop runs until stop() is called.
        """
        if self._running:
            self.log.warning("State machine already running")
            return

        self._running = True
        self.transition_to(BotState.STARTING, force=True)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.log.info("State machine started")

    def stop(self) -> None:
        """
        Stop the main loop.

        Waits for the loop to exit cleanly.
        """
        if not self._running:
            return

        self.log.info("Stopping state machine...")
        self._running = False

        try:
            self.transition_to(BotState.STOPPING)
        except StateTransitionError:
            # Force transition if needed
            self.transition_to(BotState.STOPPING, force=True)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self.transition_to(BotState.IDLE, force=True)
        self.log.info("State machine stopped")

    def _run_loop(self) -> None:
        """Main loop that runs in background thread."""
        while self._running:
            try:
                self.update()
                time.sleep(self.tick_rate)
            except Exception as e:
                self.log.error(f"Main loop error: {e}")
                if self._state != BotState.ERROR:
                    try:
                        self.transition_to(BotState.ERROR)
                    except StateTransitionError:
                        pass

    def wait_for_state(
        self,
        target: BotState,
        timeout: float = 30.0,
    ) -> bool:
        """
        Wait for a specific state to be reached.

        Args:
            target: State to wait for
            timeout: Maximum wait time in seconds

        Returns:
            True if state was reached, False on timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self._state == target:
                return True
            time.sleep(0.1)
        return False

    def run_synchronously(self, max_ticks: int = 100) -> None:
        """
        Run the state machine synchronously (for testing).

        Args:
            max_ticks: Maximum number of update ticks
        """
        self._running = True
        self.transition_to(BotState.STARTING, force=True)

        for _ in range(max_ticks):
            if not self._running or self._state == BotState.IDLE:
                break
            self.update()

        self._running = False
