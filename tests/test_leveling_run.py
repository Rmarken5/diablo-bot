"""Tests for leveling run and leveling manager."""

from unittest.mock import Mock

from src.game.runs.leveling import (
    LevelingRun,
    LevelingManager,
    LevelingPhase,
    LevelingState,
    Difficulty,
    PhaseConfig,
    PHASE_CONFIGS,
    DIFFICULTY_TRANSITIONS,
)
from src.game.runs import RunStatus, RunResult
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.town import TownManager, Act
from src.data.models import Config, Build
from src.utils.logger import setup_logger, get_logger


def create_mock_leveling_run(phase=LevelingPhase.NORMAL_EARLY):
    """Create LevelingRun with mocked dependencies."""
    config = Config()
    config.hotkeys = {
        "teleport": "f3",
        "blizzard": "f4",
        "static_field": "f5",
        "frozen_armor": "f6",
        "nova": "f7",
    }

    input_ctrl = Mock()
    detector = Mock()
    capture = Mock()
    capture.grab.return_value = Mock()

    combat = SorceressCombat(config=config, input_ctrl=input_ctrl)
    combat.cast_delay = 0.01
    combat.teleport_delay = 0.01

    health = HealthMonitor(
        config=config,
        input_ctrl=input_ctrl,
        game_detector=detector,
        screen_capture=capture,
    )
    health.check_interval = 0.01
    detector.get_health_percent.return_value = 100.0
    detector.get_mana_percent.return_value = 100.0

    town = TownManager(
        config=config,
        input_ctrl=input_ctrl,
        template_matcher=Mock(),
        screen_capture=capture,
    )

    phase_config = PHASE_CONFIGS[phase]

    run = LevelingRun(
        phase_config=phase_config,
        config=config,
        input_ctrl=input_ctrl,
        combat=combat,
        health_monitor=health,
        town_manager=town,
        game_detector=detector,
        screen_capture=capture,
    )

    return run, input_ctrl, detector, combat, health, town


def create_mock_leveling_manager():
    """Create LevelingManager with mocked dependencies."""
    config = Config()
    config.hotkeys = {
        "teleport": "f3",
        "blizzard": "f4",
        "static_field": "f5",
        "frozen_armor": "f6",
    }

    input_ctrl = Mock()
    combat = Mock()
    health = Mock()
    town = Mock()
    capture = Mock()
    detector = Mock()

    build = Build(
        name="Blizzard Sorc",
        respec_level=26,
    )

    manager = LevelingManager(
        config=config,
        build=build,
        input_ctrl=input_ctrl,
        combat=combat,
        health_monitor=health,
        town_manager=town,
        game_detector=detector,
        screen_capture=capture,
    )

    return manager, input_ctrl, combat, town


# ========== LevelingPhase / Difficulty Tests ==========

def test_difficulty_enum():
    """Test Difficulty enum."""
    log = get_logger()
    log.info("Testing Difficulty enum...")

    assert Difficulty.NORMAL.value == "normal"
    assert Difficulty.NIGHTMARE.value == "nightmare"
    assert Difficulty.HELL.value == "hell"

    log.info("PASSED: Difficulty enum")
    return True


def test_leveling_phase_enum():
    """Test LevelingPhase enum."""
    log = get_logger()
    log.info("Testing LevelingPhase enum...")

    assert LevelingPhase.NORMAL_EARLY.value == "normal_early"
    assert LevelingPhase.ENDGAME_FARMING.value == "endgame_farming"
    assert len(LevelingPhase) == 8

    log.info("PASSED: LevelingPhase enum")
    return True


def test_phase_configs_defined():
    """Test all phase configs are defined."""
    log = get_logger()
    log.info("Testing phase configs...")

    assert len(PHASE_CONFIGS) == 7  # All except ENDGAME_FARMING

    for phase, cfg in PHASE_CONFIGS.items():
        assert cfg.min_level < cfg.max_level
        assert isinstance(cfg.difficulty, Difficulty)
        assert isinstance(cfg.act, Act)
        assert len(cfg.waypoint_act_tab) == 2
        assert len(cfg.waypoint_destination) == 2
        assert cfg.combat_style in ("nova", "blizzard", "static_blizzard")
        assert len(cfg.teleport_targets) > 0
        assert len(cfg.clear_positions) > 0
        assert cfg.run_timeout > 0

    log.info("PASSED: phase configs")
    return True


def test_difficulty_transitions():
    """Test difficulty transition requirements."""
    log = get_logger()
    log.info("Testing difficulty transitions...")

    assert Difficulty.NIGHTMARE in DIFFICULTY_TRANSITIONS
    assert Difficulty.HELL in DIFFICULTY_TRANSITIONS

    nm = DIFFICULTY_TRANSITIONS[Difficulty.NIGHTMARE]
    assert nm["min_level"] == 25

    hell = DIFFICULTY_TRANSITIONS[Difficulty.HELL]
    assert hell["min_level"] == 50

    log.info("PASSED: difficulty transitions")
    return True


# ========== LevelingRun Tests ==========

def test_run_name():
    """Test run name includes area."""
    log = get_logger()
    log.info("Testing run name...")

    run, _, _, _, _, _ = create_mock_leveling_run(LevelingPhase.NORMAL_EARLY)
    assert "Tristram" in run.name

    run2, _, _, _, _, _ = create_mock_leveling_run(LevelingPhase.NORMAL_BAAL)
    assert "Baal" in run2.name

    log.info("PASSED: run name")
    return True


def test_run_timeout_from_phase():
    """Test run timeout is set from phase config."""
    log = get_logger()
    log.info("Testing run timeout from phase...")

    run, _, _, _, _, _ = create_mock_leveling_run(LevelingPhase.NORMAL_EARLY)
    assert run.run_timeout == 90.0

    run2, _, _, _, _, _ = create_mock_leveling_run(LevelingPhase.HELL_CHAOS)
    assert run2.run_timeout == 300.0

    log.info("PASSED: run timeout from phase")
    return True


def test_execute_success():
    """Test successful leveling run execution."""
    log = get_logger()
    log.info("Testing execute success...")

    run, _, _, _, _, town = create_mock_leveling_run()
    town.use_waypoint = Mock(return_value=True)

    result = run.execute()

    assert result.status == RunStatus.SUCCESS
    assert result.run_time > 0

    log.info("PASSED: execute success")
    return True


def test_execute_chicken():
    """Test chicken during leveling run."""
    log = get_logger()
    log.info("Testing chicken during run...")

    run, _, detector, _, _, town = create_mock_leveling_run()
    town.use_waypoint = Mock(return_value=True)

    detector.get_health_percent.return_value = 10.0

    result = run.execute()

    assert result.status == RunStatus.CHICKEN

    log.info("PASSED: chicken during run")
    return True


def test_execute_no_town():
    """Test run fails without town manager."""
    log = get_logger()
    log.info("Testing execute without town...")

    config = Config()
    input_ctrl = Mock()
    phase_config = PHASE_CONFIGS[LevelingPhase.NORMAL_EARLY]

    run = LevelingRun(
        phase_config=phase_config,
        config=config,
        input_ctrl=input_ctrl,
        town_manager=None,
    )

    result = run.execute()

    assert result.status == RunStatus.ERROR

    log.info("PASSED: execute without town")
    return True


# ========== LevelingManager Tests ==========

def test_initial_state():
    """Test initial leveling manager state."""
    log = get_logger()
    log.info("Testing initial state...")

    manager, _, _, _ = create_mock_leveling_manager()

    assert manager.state.current_level == 1
    assert manager.state.current_difficulty == Difficulty.NORMAL
    assert manager.state.current_phase == LevelingPhase.NORMAL_EARLY
    assert manager.state.total_runs == 0

    log.info("PASSED: initial state")
    return True


def test_get_current_phase_normal():
    """Test phase detection for Normal difficulty."""
    log = get_logger()
    log.info("Testing phase detection Normal...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.state.current_level = 5
    assert manager.get_current_phase() == LevelingPhase.NORMAL_EARLY

    manager.state.current_level = 15
    assert manager.get_current_phase() == LevelingPhase.NORMAL_TOMBS

    manager.state.current_level = 22
    assert manager.get_current_phase() == LevelingPhase.NORMAL_COWS

    manager.state.current_level = 30
    assert manager.get_current_phase() == LevelingPhase.NORMAL_BAAL

    log.info("PASSED: phase detection Normal")
    return True


def test_get_current_phase_nightmare():
    """Test phase detection for Nightmare."""
    log = get_logger()
    log.info("Testing phase detection Nightmare...")

    manager, _, _, _ = create_mock_leveling_manager()
    manager.state.current_difficulty = Difficulty.NIGHTMARE

    manager.state.current_level = 50
    assert manager.get_current_phase() == LevelingPhase.NIGHTMARE_BAAL

    log.info("PASSED: phase detection Nightmare")
    return True


def test_get_current_phase_hell():
    """Test phase detection for Hell."""
    log = get_logger()
    log.info("Testing phase detection Hell...")

    manager, _, _, _ = create_mock_leveling_manager()
    manager.state.current_difficulty = Difficulty.HELL

    manager.state.current_level = 65
    assert manager.get_current_phase() == LevelingPhase.HELL_CHAOS

    manager.state.current_level = 72
    assert manager.get_current_phase() == LevelingPhase.HELL_BAAL

    log.info("PASSED: phase detection Hell")
    return True


def test_should_change_difficulty():
    """Test difficulty change detection."""
    log = get_logger()
    log.info("Testing should change difficulty...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.state.current_level = 30
    assert manager.should_change_difficulty() is False

    manager.state.current_level = 40
    assert manager.should_change_difficulty() is True

    log.info("PASSED: should change difficulty")
    return True


def test_get_next_difficulty():
    """Test next difficulty lookup."""
    log = get_logger()
    log.info("Testing next difficulty...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.state.current_difficulty = Difficulty.NORMAL
    assert manager.get_next_difficulty() == Difficulty.NIGHTMARE

    manager.state.current_difficulty = Difficulty.NIGHTMARE
    assert manager.get_next_difficulty() == Difficulty.HELL

    manager.state.current_difficulty = Difficulty.HELL
    assert manager.get_next_difficulty() is None

    log.info("PASSED: next difficulty")
    return True


def test_transition_difficulty():
    """Test difficulty transition."""
    log = get_logger()
    log.info("Testing difficulty transition...")

    manager, _, _, _ = create_mock_leveling_manager()

    result = manager.transition_difficulty()

    assert result is True
    assert manager.state.current_difficulty == Difficulty.NIGHTMARE
    assert manager.state.difficulty_unlocked["nightmare"] is True
    assert manager.state.runs_in_phase == 0

    log.info("PASSED: difficulty transition")
    return True


def test_transition_from_hell():
    """Test no transition from Hell."""
    log = get_logger()
    log.info("Testing no transition from Hell...")

    manager, _, _, _ = create_mock_leveling_manager()
    manager.state.current_difficulty = Difficulty.HELL

    result = manager.transition_difficulty()
    assert result is False

    log.info("PASSED: no transition from Hell")
    return True


def test_set_level():
    """Test setting level."""
    log = get_logger()
    log.info("Testing set level...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.set_level(50)
    assert manager.state.current_level == 50

    log.info("PASSED: set level")
    return True


def test_set_difficulty():
    """Test setting difficulty."""
    log = get_logger()
    log.info("Testing set difficulty...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.set_difficulty(Difficulty.NIGHTMARE)
    assert manager.state.current_difficulty == Difficulty.NIGHTMARE

    log.info("PASSED: set difficulty")
    return True


def test_set_target_level():
    """Test setting target level."""
    log = get_logger()
    log.info("Testing set target level...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.set_target_level(85)
    assert manager.target_level == 85

    log.info("PASSED: set target level")
    return True


def test_stop():
    """Test stopping the manager."""
    log = get_logger()
    log.info("Testing stop...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.stop()
    assert manager.is_running() is False

    log.info("PASSED: stop")
    return True


def test_get_progress():
    """Test progress summary."""
    log = get_logger()
    log.info("Testing progress summary...")

    manager, _, _, _ = create_mock_leveling_manager()

    manager.state.current_level = 30
    manager.state.total_runs = 50
    manager.state.total_deaths = 2

    progress = manager.get_progress()

    assert "LEVELING PROGRESS" in progress
    assert "30" in progress
    assert "50" in progress

    log.info("PASSED: progress summary")
    return True


def test_should_progress_phase():
    """Test phase progression check."""
    log = get_logger()
    log.info("Testing should progress phase...")

    manager, _, _, _ = create_mock_leveling_manager()

    # Level 5, phase=NORMAL_EARLY (max=15) - should not progress
    manager.state.current_level = 5
    assert manager.should_progress_phase() is False

    # Level 40, phase=NORMAL_BAAL (max=40) - should progress
    manager.state.current_level = 40
    assert manager.should_progress_phase() is True

    log.info("PASSED: should progress phase")
    return True


def test_leveling_state_dataclass():
    """Test LevelingState dataclass."""
    log = get_logger()
    log.info("Testing LevelingState dataclass...")

    state = LevelingState()

    assert state.current_level == 1
    assert state.current_difficulty == Difficulty.NORMAL
    assert state.current_phase == LevelingPhase.NORMAL_EARLY
    assert state.runs_in_phase == 0
    assert state.total_runs == 0
    assert state.total_deaths == 0
    assert state.difficulty_unlocked["normal"] is True
    assert state.difficulty_unlocked["nightmare"] is False

    log.info("PASSED: LevelingState dataclass")
    return True


def test_execute_leveling_session_max_runs():
    """Test leveling session with max runs limit."""
    log = get_logger()
    log.info("Testing leveling session max runs...")

    manager, _, _, town = create_mock_leveling_manager()
    town.use_waypoint = Mock(return_value=True)
    town.town_routine = Mock()

    # Already at target level to stop immediately
    manager.state.current_level = 75

    manager.execute_leveling_session(max_runs=1)

    assert manager.is_running() is False

    log.info("PASSED: leveling session max runs")
    return True


def test_phase_config_dataclass():
    """Test PhaseConfig dataclass."""
    log = get_logger()
    log.info("Testing PhaseConfig dataclass...")

    cfg = PhaseConfig(
        phase=LevelingPhase.NORMAL_EARLY,
        min_level=1,
        max_level=15,
        difficulty=Difficulty.NORMAL,
        act=Act.ACT1,
        area="Test Area",
        waypoint_act_tab=(260, 120),
        waypoint_destination=(260, 220),
        combat_style="nova",
        teleport_targets=[(960, 400)],
        clear_positions=[(960, 350)],
        run_timeout=90.0,
    )

    assert cfg.phase == LevelingPhase.NORMAL_EARLY
    assert cfg.area == "Test Area"
    assert cfg.combat_style == "nova"

    log.info("PASSED: PhaseConfig dataclass")
    return True


def run_all_tests():
    """Run all leveling run tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Leveling Run Tests")
    log.info("=" * 50)

    tests = [
        ("Difficulty Enum", test_difficulty_enum),
        ("LevelingPhase Enum", test_leveling_phase_enum),
        ("Phase Configs", test_phase_configs_defined),
        ("Difficulty Transitions", test_difficulty_transitions),
        ("Run Name", test_run_name),
        ("Run Timeout From Phase", test_run_timeout_from_phase),
        ("Execute Success", test_execute_success),
        ("Execute Chicken", test_execute_chicken),
        ("Execute No Town", test_execute_no_town),
        ("Initial State", test_initial_state),
        ("Phase Detection Normal", test_get_current_phase_normal),
        ("Phase Detection Nightmare", test_get_current_phase_nightmare),
        ("Phase Detection Hell", test_get_current_phase_hell),
        ("Should Change Difficulty", test_should_change_difficulty),
        ("Next Difficulty", test_get_next_difficulty),
        ("Transition Difficulty", test_transition_difficulty),
        ("No Transition From Hell", test_transition_from_hell),
        ("Set Level", test_set_level),
        ("Set Difficulty", test_set_difficulty),
        ("Set Target Level", test_set_target_level),
        ("Stop", test_stop),
        ("Progress Summary", test_get_progress),
        ("Should Progress Phase", test_should_progress_phase),
        ("LevelingState Dataclass", test_leveling_state_dataclass),
        ("Session Max Runs", test_execute_leveling_session_max_runs),
        ("PhaseConfig Dataclass", test_phase_config_dataclass),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            log.info(f"\n--- {name} ---")
            result = test_func()
            if result:
                passed += 1
            else:
                log.error(f"FAILED: {name}")
                failed += 1
        except Exception as e:
            log.error(f"FAILED: {name} - {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    log.info("\n" + "=" * 50)
    log.info(f"Results: {passed} passed, {failed} failed")
    log.info("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
