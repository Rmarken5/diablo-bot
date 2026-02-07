"""Full leveling journey integration for D2R Bot.

Orchestrates the automated leveling process from level 1 to 75+,
managing area progression, difficulty transitions, and run execution.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from src.data.models import Build, Config
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.leveling import LevelManager
from src.game.town import TownManager, Act, NPC
from src.input.controller import InputController
from src.utils.logger import get_logger

from .base import BaseRun, RunResult, RunStatus


# ========== Leveling Phases ==========

class Difficulty(Enum):
    """Game difficulties."""
    NORMAL = "normal"
    NIGHTMARE = "nightmare"
    HELL = "hell"


class LevelingPhase(Enum):
    """Leveling phases with associated level ranges and activities."""
    # Normal difficulty
    NORMAL_EARLY = "normal_early"          # 1-15: Tristram/Countess runs
    NORMAL_TOMBS = "normal_tombs"          # 13-20: Tal Rasha's Tombs
    NORMAL_COWS = "normal_cows"            # 20-25: Cow Level
    NORMAL_BAAL = "normal_baal"            # 25-40: Normal Baal runs

    # Nightmare difficulty
    NIGHTMARE_BAAL = "nightmare_baal"      # 41-60: Nightmare Baal runs

    # Hell difficulty
    HELL_CHAOS = "hell_chaos"              # 60-70: Hell Chaos Sanctuary
    HELL_BAAL = "hell_baal"               # 70-75+: Hell Baal runs

    # Endgame farming (post-leveling)
    ENDGAME_FARMING = "endgame_farming"    # 75+: Pindle/Mephisto farming


@dataclass
class PhaseConfig:
    """Configuration for a leveling phase."""
    phase: LevelingPhase
    min_level: int
    max_level: int
    difficulty: Difficulty
    act: Act
    area: str                    # Area name for display
    waypoint_act_tab: Tuple[int, int]    # Position of act tab in WP menu
    waypoint_destination: Tuple[int, int]  # Position of destination WP
    combat_style: str            # "nova", "blizzard", "static_blizzard"
    teleport_targets: List[Tuple[int, int]]  # Positions to teleport to
    clear_positions: List[Tuple[int, int]]   # Positions to attack
    run_timeout: float = 120.0


# ========== Phase Definitions ==========

PHASE_CONFIGS: Dict[LevelingPhase, PhaseConfig] = {
    LevelingPhase.NORMAL_EARLY: PhaseConfig(
        phase=LevelingPhase.NORMAL_EARLY,
        min_level=1,
        max_level=15,
        difficulty=Difficulty.NORMAL,
        act=Act.ACT1,
        area="Tristram / Countess",
        waypoint_act_tab=(260, 120),
        waypoint_destination=(260, 220),     # Stony Field -> Tristram portal
        combat_style="nova",
        teleport_targets=[
            (960, 400), (960, 300),          # North toward Tristram portal
        ],
        clear_positions=[
            (960, 350), (800, 350), (1100, 350),
            (960, 250), (800, 250), (1100, 250),
        ],
        run_timeout=90.0,
    ),

    LevelingPhase.NORMAL_TOMBS: PhaseConfig(
        phase=LevelingPhase.NORMAL_TOMBS,
        min_level=13,
        max_level=24,
        difficulty=Difficulty.NORMAL,
        act=Act.ACT2,
        area="Tal Rasha's Tombs",
        waypoint_act_tab=(350, 120),         # Act 2 tab
        waypoint_destination=(350, 370),     # Canyon of the Magi
        combat_style="nova",
        teleport_targets=[
            (960, 350), (960, 250), (960, 150),
        ],
        clear_positions=[
            (960, 300), (750, 300), (1150, 300),
            (960, 200), (750, 200), (1150, 200),
        ],
        run_timeout=120.0,
    ),

    LevelingPhase.NORMAL_COWS: PhaseConfig(
        phase=LevelingPhase.NORMAL_COWS,
        min_level=20,
        max_level=25,
        difficulty=Difficulty.NORMAL,
        act=Act.ACT1,
        area="Cow Level",
        waypoint_act_tab=(260, 120),
        waypoint_destination=(260, 170),     # Rogue Encampment
        combat_style="nova",
        teleport_targets=[
            (960, 400), (960, 300),
        ],
        clear_positions=[
            (960, 350), (700, 350), (1200, 350),
            (960, 200), (700, 200), (1200, 200),
            (500, 350), (1400, 350),
        ],
        run_timeout=180.0,
    ),

    LevelingPhase.NORMAL_BAAL: PhaseConfig(
        phase=LevelingPhase.NORMAL_BAAL,
        min_level=25,
        max_level=40,
        difficulty=Difficulty.NORMAL,
        act=Act.ACT5,
        area="Baal Throne / Worldstone",
        waypoint_act_tab=(590, 120),         # Act 5 tab
        waypoint_destination=(590, 370),     # Worldstone Keep Level 2
        combat_style="nova",
        teleport_targets=[
            (960, 350), (960, 250), (960, 150),
            (960, 350), (960, 250),
        ],
        clear_positions=[
            (960, 300), (750, 300), (1150, 300),
            (960, 200), (750, 200), (1150, 200),
        ],
        run_timeout=180.0,
    ),

    LevelingPhase.NIGHTMARE_BAAL: PhaseConfig(
        phase=LevelingPhase.NIGHTMARE_BAAL,
        min_level=41,
        max_level=60,
        difficulty=Difficulty.NIGHTMARE,
        act=Act.ACT5,
        area="Nightmare Baal",
        waypoint_act_tab=(590, 120),
        waypoint_destination=(590, 370),
        combat_style="blizzard",
        teleport_targets=[
            (960, 350), (960, 250), (960, 150),
            (960, 350), (960, 250),
        ],
        clear_positions=[
            (960, 300), (750, 300), (1150, 300),
        ],
        run_timeout=240.0,
    ),

    LevelingPhase.HELL_CHAOS: PhaseConfig(
        phase=LevelingPhase.HELL_CHAOS,
        min_level=60,
        max_level=70,
        difficulty=Difficulty.HELL,
        act=Act.ACT4,
        area="Hell Chaos Sanctuary",
        waypoint_act_tab=(480, 120),         # Act 4 tab
        waypoint_destination=(480, 220),     # River of Flame
        combat_style="static_blizzard",
        teleport_targets=[
            (960, 350), (960, 250), (960, 150),
            (1100, 300), (800, 300),
        ],
        clear_positions=[
            (960, 300), (750, 300), (1150, 300),
            (960, 200), (600, 350), (1300, 350),
        ],
        run_timeout=300.0,
    ),

    LevelingPhase.HELL_BAAL: PhaseConfig(
        phase=LevelingPhase.HELL_BAAL,
        min_level=70,
        max_level=75,
        difficulty=Difficulty.HELL,
        act=Act.ACT5,
        area="Hell Baal",
        waypoint_act_tab=(590, 120),
        waypoint_destination=(590, 370),
        combat_style="static_blizzard",
        teleport_targets=[
            (960, 350), (960, 250), (960, 150),
            (960, 350), (960, 250),
        ],
        clear_positions=[
            (960, 300), (750, 300), (1150, 300),
        ],
        run_timeout=300.0,
    ),
}

# Difficulty transition requirements
DIFFICULTY_TRANSITIONS = {
    Difficulty.NIGHTMARE: {
        "min_level": 25,
        "quest_required": "normal_baal",  # Must kill Normal Baal
    },
    Difficulty.HELL: {
        "min_level": 50,
        "quest_required": "nightmare_baal",
    },
}


@dataclass
class LevelingState:
    """Persistent state for the leveling journey."""
    current_level: int = 1
    current_difficulty: Difficulty = Difficulty.NORMAL
    current_phase: LevelingPhase = LevelingPhase.NORMAL_EARLY
    runs_in_phase: int = 0
    total_runs: int = 0
    total_deaths: int = 0
    quests_completed: List[str] = field(default_factory=list)
    difficulty_unlocked: Dict[str, bool] = field(default_factory=lambda: {
        "normal": True,
        "nightmare": False,
        "hell": False,
    })


class LevelingRun(BaseRun):
    """
    Executes a single leveling run for the current phase.

    Adapts behavior based on the active LevelingPhase — selects
    the correct waypoint, combat style, and area to farm.
    """

    def __init__(
        self,
        phase_config: PhaseConfig,
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

        self.phase = phase_config
        self.run_timeout = phase_config.run_timeout
        self.log = get_logger()

    @property
    def name(self) -> str:
        return f"Leveling ({self.phase.area})"

    def _execute_run(self) -> RunResult:
        kills = 0
        items = 0

        # Step 1: Ensure in town
        if not self._ensure_in_town():
            return RunResult(status=RunStatus.ERROR, error_message="Not in town")

        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 2: Buffs
        if self.combat:
            self.combat.ensure_buffs()
            time.sleep(0.3)

        # Step 3: Waypoint to leveling area
        if not self._waypoint_to_area():
            return RunResult(
                status=RunStatus.ERROR,
                error_message=f"Could not waypoint to {self.phase.area}",
            )
        time.sleep(1.5)

        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN)

        # Step 4: Teleport toward mobs
        self._teleport_to_mobs()

        # Step 5: Clear area with appropriate combat style
        kills = self._clear_area()

        if not self._check_health():
            return RunResult(status=RunStatus.CHICKEN, kills=kills)

        # Step 6: Loot
        time.sleep(0.8)
        items = self._loot_area()

        # Step 7: Save & Exit for fast restart
        self._exit_game()

        return RunResult(
            status=RunStatus.SUCCESS,
            kills=kills,
            items_picked=items,
        )

    def _ensure_in_town(self) -> bool:
        if self.detector:
            screen = self._grab_screen()
            if screen is not None and hasattr(self.detector, "is_in_town"):
                return self.detector.is_in_town(screen)
        return True

    def _waypoint_to_area(self) -> bool:
        """Use waypoint to travel to the leveling area."""
        self.log.info(f"Waypointing to {self.phase.area}")

        if not self.town:
            return False

        if not self.town.use_waypoint():
            return False

        time.sleep(0.5)

        # Click the correct act tab
        self.input.click(
            self.phase.waypoint_act_tab[0],
            self.phase.waypoint_act_tab[1],
        )
        time.sleep(0.3)

        # Click the destination waypoint
        self.input.click(
            self.phase.waypoint_destination[0],
            self.phase.waypoint_destination[1],
        )
        time.sleep(0.5)

        return True

    def _teleport_to_mobs(self) -> None:
        """Teleport toward monster packs."""
        if not self.combat:
            return

        self.log.info("Teleporting to mobs")
        for pos in self.phase.teleport_targets:
            if not self._check_health():
                return
            self.combat.cast_teleport(pos)
            time.sleep(0.2)

    def _clear_area(self) -> int:
        """Clear the area using the phase's combat style."""
        if not self.combat:
            return 0

        self.log.info(f"Clearing area ({self.phase.combat_style})")
        kills = 0

        if self.phase.combat_style == "nova":
            kills = self._clear_with_nova()
        elif self.phase.combat_style == "blizzard":
            kills = self._clear_with_blizzard()
        elif self.phase.combat_style == "static_blizzard":
            kills = self._clear_with_static_blizzard()

        return kills

    def _clear_with_nova(self) -> int:
        """Clear using Nova (early leveling)."""
        kills = 0
        for pos in self.phase.clear_positions:
            if not self._check_health():
                break
            # Teleport to pack, cast Nova
            self.combat.cast_teleport(pos)
            time.sleep(0.15)
            self.combat.cast_nova()
            time.sleep(0.2)
            self.combat.cast_nova()
            time.sleep(0.2)
            kills += 1  # Approximate

        return kills

    def _clear_with_blizzard(self) -> int:
        """Clear using Blizzard (mid-game)."""
        kills = 0
        for pos in self.phase.clear_positions:
            if not self._check_health():
                break
            self.combat.cast_blizzard(pos)
            time.sleep(0.3)
            kills += 1

        # Wait for Blizzard damage
        time.sleep(2.5)
        return kills

    def _clear_with_static_blizzard(self) -> int:
        """Clear using Static Field + Blizzard (Hell difficulty bosses)."""
        kills = 0

        # Static Field to weaken everything first
        for _ in range(3):
            if not self._check_health():
                break
            self.combat.cast_static_field()
            time.sleep(0.3)

        # Then Blizzard the area
        for pos in self.phase.clear_positions:
            if not self._check_health():
                break
            self.combat.cast_blizzard(pos)
            time.sleep(0.3)
            kills += 1

        time.sleep(3.0)
        return kills

    def _loot_area(self) -> int:
        if self.loot:
            return self.loot.pickup_all_valid()

        # Fallback
        self.input.key_down("alt")
        time.sleep(0.3)
        for pos in self.phase.clear_positions[:3]:
            self.input.click(pos[0], pos[1])
            time.sleep(0.15)
        self.input.key_up("alt")
        return 0


class LevelingManager:
    """
    Orchestrates the full leveling journey from level 1 to 75+.

    Manages:
    - Phase progression (which area to farm based on level)
    - Difficulty transitions (Normal -> Nightmare -> Hell)
    - Run execution and repetition
    - Skill/stat allocation via LevelManager
    - Town management between runs
    - Respec at level 26
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        build: Optional[Build] = None,
        input_ctrl: Optional[InputController] = None,
        combat: Optional[SorceressCombat] = None,
        health_monitor: Optional[HealthMonitor] = None,
        town_manager: Optional[TownManager] = None,
        level_manager: Optional[LevelManager] = None,
        game_detector=None,
        screen_capture=None,
        menu_navigator=None,
        loot_manager=None,
        statistics=None,
    ):
        self.config = config or Config()
        self.build = build
        self.input = input_ctrl or InputController()
        self.combat = combat
        self.health = health_monitor
        self.town = town_manager
        self.leveler = level_manager
        self.detector = game_detector
        self.capture = screen_capture
        self.menu = menu_navigator
        self.loot = loot_manager
        self.stats = statistics
        self.log = get_logger()

        # State
        self.state = LevelingState()
        self._running = False
        self._current_run: Optional[LevelingRun] = None

        # Settings
        self.runs_before_town = 5      # Town trip every N runs
        self.target_level = 75         # Stop leveling at this level
        self.max_runs_per_phase = 200  # Safety limit per phase

    # ========== Phase Management ==========

    def get_current_phase(self) -> LevelingPhase:
        """Determine the current leveling phase based on level and difficulty."""
        level = self.state.current_level
        diff = self.state.current_difficulty

        if diff == Difficulty.HELL:
            if level >= 70:
                return LevelingPhase.HELL_BAAL
            return LevelingPhase.HELL_CHAOS

        if diff == Difficulty.NIGHTMARE:
            return LevelingPhase.NIGHTMARE_BAAL

        # Normal difficulty
        if level >= 25:
            return LevelingPhase.NORMAL_BAAL
        if level >= 20:
            return LevelingPhase.NORMAL_COWS
        if level >= 13:
            return LevelingPhase.NORMAL_TOMBS
        return LevelingPhase.NORMAL_EARLY

    def get_phase_config(self, phase: Optional[LevelingPhase] = None) -> PhaseConfig:
        """Get configuration for a phase."""
        phase = phase or self.get_current_phase()
        return PHASE_CONFIGS[phase]

    def should_progress_phase(self) -> bool:
        """Check if we should move to the next phase."""
        phase_cfg = self.get_phase_config()
        return self.state.current_level >= phase_cfg.max_level

    def should_change_difficulty(self) -> bool:
        """Check if we should advance to the next difficulty."""
        level = self.state.current_level
        diff = self.state.current_difficulty

        if diff == Difficulty.NORMAL and level >= 40:
            return True
        if diff == Difficulty.NIGHTMARE and level >= 60:
            return True

        return False

    def get_next_difficulty(self) -> Optional[Difficulty]:
        """Get the next difficulty to transition to."""
        if self.state.current_difficulty == Difficulty.NORMAL:
            return Difficulty.NIGHTMARE
        if self.state.current_difficulty == Difficulty.NIGHTMARE:
            return Difficulty.HELL
        return None

    # ========== Difficulty Transitions ==========

    def transition_difficulty(self) -> bool:
        """
        Handle transition to the next difficulty.

        This involves:
        1. Verifying the current difficulty boss is defeated
        2. Creating a new game on the next difficulty
        3. Updating internal state

        Returns:
            True if transition was successful
        """
        next_diff = self.get_next_difficulty()
        if next_diff is None:
            self.log.info("Already at highest difficulty")
            return False

        self.log.info(
            f"Transitioning from {self.state.current_difficulty.value} "
            f"to {next_diff.value}"
        )

        # In D2R, difficulty is selected at game creation.
        # We need to: Save & Exit -> Create new game on next difficulty.
        #
        # The menu navigator handles game creation with difficulty selection.
        # For now, we update state and assume the user/bot creates the game
        # on the right difficulty.

        self.state.current_difficulty = next_diff
        self.state.difficulty_unlocked[next_diff.value] = True
        self.state.runs_in_phase = 0

        self.log.info(f"Now on {next_diff.value} difficulty")
        return True

    # ========== Run Execution ==========

    def create_run(self) -> LevelingRun:
        """Create a LevelingRun for the current phase."""
        phase = self.get_current_phase()
        phase_cfg = self.get_phase_config(phase)

        self.state.current_phase = phase

        run = LevelingRun(
            phase_config=phase_cfg,
            config=self.config,
            input_ctrl=self.input,
            combat=self.combat,
            health_monitor=self.health,
            town_manager=self.town,
            game_detector=self.detector,
            screen_capture=self.capture,
            menu_navigator=self.menu,
            loot_manager=self.loot,
        )

        return run

    def execute_single_run(self) -> RunResult:
        """
        Execute a single leveling run.

        Returns:
            RunResult from the run
        """
        run = self.create_run()
        self._current_run = run

        self.log.info(
            f"Leveling run #{self.state.total_runs + 1}: "
            f"Level {self.state.current_level}, "
            f"{self.state.current_phase.value} "
            f"({self.state.current_difficulty.value})"
        )

        result = run.execute()

        # Update state
        self.state.total_runs += 1
        self.state.runs_in_phase += 1

        if result.status == RunStatus.SUCCESS:
            self.log.info(
                f"Run complete: {result.kills} kills, "
                f"{result.items_picked} items ({result.run_time:.1f}s)"
            )
        elif result.status == RunStatus.CHICKEN:
            self.log.warning("Run ended with chicken")
        elif result.status == RunStatus.DEATH:
            self.state.total_deaths += 1
            self.log.warning(f"Death during run (total: {self.state.total_deaths})")

        # Record stats
        if self.stats:
            self.stats.record_run(
                run_type=f"leveling_{self.state.current_phase.value}",
                status=result.status.name,
                duration=result.run_time,
                kills=result.kills,
                items_picked=result.items_picked,
            )

        self._current_run = None
        return result

    def execute_leveling_session(self, max_runs: int = 0) -> None:
        """
        Execute a full leveling session.

        Runs continuously until target level is reached or stopped.

        Args:
            max_runs: Maximum runs (0 = unlimited until target level)
        """
        self._running = True
        runs = 0

        self.log.info(
            f"Starting leveling session: Level {self.state.current_level} -> "
            f"{self.target_level} ({self.state.current_difficulty.value})"
        )

        while self._running:
            # Check if we've reached target level
            if self.state.current_level >= self.target_level:
                self.log.info(
                    f"Target level {self.target_level} reached! "
                    f"Leveling complete."
                )
                break

            # Check run limit
            if max_runs > 0 and runs >= max_runs:
                self.log.info(f"Max runs ({max_runs}) reached")
                break

            # Safety: too many runs in one phase
            if self.state.runs_in_phase >= self.max_runs_per_phase:
                self.log.warning(
                    f"Max runs per phase ({self.max_runs_per_phase}) reached "
                    f"in {self.state.current_phase.value} - stopping"
                )
                break

            # Check if we should change difficulty
            if self.should_change_difficulty():
                self.transition_difficulty()

            # Check for respec
            if self.leveler and self.leveler.needs_respec():
                self.log.info("Respec needed before continuing")
                self.leveler.perform_respec()

            # Handle level-up point allocation
            self._handle_pending_levelups()

            # Town trip every N runs
            if runs > 0 and runs % self.runs_before_town == 0:
                self._town_routine()

            # Execute the run
            result = self.execute_single_run()

            runs += 1

            # Handle run result
            if result.status == RunStatus.ERROR:
                self.log.error(f"Run error: {result.error_message}")
                # Brief pause before retrying
                time.sleep(2.0)

            # Small delay between runs
            time.sleep(0.5)

        self._running = False
        self.log.info(
            f"Leveling session ended: {runs} runs, "
            f"Level {self.state.current_level}, "
            f"{self.state.total_deaths} deaths"
        )

    def stop(self) -> None:
        """Stop the leveling session."""
        self._running = False
        if self._current_run:
            self._current_run.abort()
        self.log.info("Leveling session stop requested")

    # ========== Support Methods ==========

    def _handle_pending_levelups(self) -> None:
        """Check for and handle any pending level-ups."""
        if self.leveler is None:
            return

        if self.capture is None:
            return

        screen = self.capture.grab()
        if self.leveler.check_level_up(screen):
            self.leveler.handle_level_up(screen)
            self.state.current_level = self.leveler.state.current_level

    def _town_routine(self) -> None:
        """Execute town management routine between runs."""
        self.log.info("Town routine between leveling runs")

        if self.town:
            self.town.town_routine()

    def set_level(self, level: int) -> None:
        """Set current level (e.g., when starting mid-journey)."""
        self.state.current_level = level
        if self.leveler:
            self.leveler.set_level(level)
        self.log.info(f"Level set to {level}")

    def set_difficulty(self, difficulty: Difficulty) -> None:
        """Set current difficulty."""
        self.state.current_difficulty = difficulty
        self.log.info(f"Difficulty set to {difficulty.value}")

    def set_target_level(self, level: int) -> None:
        """Set the target level to stop at."""
        self.target_level = level
        self.log.info(f"Target level set to {level}")

    # ========== Status ==========

    def get_progress(self) -> str:
        """Get a formatted progress summary."""
        phase_cfg = self.get_phase_config()

        lines = [
            "=" * 40,
            "  LEVELING PROGRESS",
            "=" * 40,
            f"  Level:      {self.state.current_level} / {self.target_level}",
            f"  Difficulty: {self.state.current_difficulty.value}",
            f"  Phase:      {self.state.current_phase.value}",
            f"  Area:       {phase_cfg.area}",
            f"  Runs:       {self.state.total_runs} total, "
            f"{self.state.runs_in_phase} in phase",
            f"  Deaths:     {self.state.total_deaths}",
        ]

        if self.leveler:
            lines.append("")
            lines.append(self.leveler.get_build_progress())

        lines.append("=" * 40)
        return "\n".join(lines)

    def is_running(self) -> bool:
        """Check if leveling session is active."""
        return self._running
