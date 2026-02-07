"""Tests for Mephisto farming run."""

import time
from unittest.mock import Mock, MagicMock

from src.game.runs import MephistoRun, RunStatus, RunResult
from src.game.combat import SorceressCombat, Skill
from src.game.health import HealthMonitor
from src.game.town import TownManager
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


def create_mock_mephisto_run():
    """Create MephistoRun with mocked dependencies."""
    config = Config()
    config.hotkeys = {
        "teleport": "f3",
        "blizzard": "f4",
        "static_field": "f5",
        "frozen_armor": "f6",
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

    run = MephistoRun(
        config=config,
        input_ctrl=input_ctrl,
        combat=combat,
        health_monitor=health,
        town_manager=town,
        game_detector=detector,
        screen_capture=capture,
    )

    # Speed up tests
    run.portal_load_time = 0.01
    run.cast_settle_time = 0.01
    run.waypoint_load_time = 0.01
    run.search_timeout = 0.1

    return run, input_ctrl, detector, combat, health, town


def test_run_name():
    """Test run name."""
    log = get_logger()
    log.info("Testing run name...")

    run, _, _, _, _, _ = create_mock_mephisto_run()
    assert run.name == "Mephisto"

    log.info("PASSED: run name")
    return True


def test_execute_with_town():
    """Test run execution uses town manager."""
    log = get_logger()
    log.info("Testing execute with town...")

    run, _, _, _, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)

    result = run.execute()

    # Waypoint should have been used
    town.use_waypoint.assert_called()
    assert result.run_time > 0

    log.info("PASSED: execute with town")
    return True


def test_execute_no_town():
    """Test run fails without town manager."""
    log = get_logger()
    log.info("Testing execute without town...")

    config = Config()
    input_ctrl = Mock()

    run = MephistoRun(
        config=config,
        input_ctrl=input_ctrl,
        town_manager=None,
    )
    run.portal_load_time = 0.01
    run.cast_settle_time = 0.01
    run.waypoint_load_time = 0.01

    result = run.execute()

    assert result.status == RunStatus.ERROR
    assert "waypoint" in result.error_message.lower() or "durance" in result.error_message.lower()

    log.info("PASSED: execute without town")
    return True


def test_chicken_during_run():
    """Test chicken triggers abort."""
    log = get_logger()
    log.info("Testing chicken during run...")

    run, _, detector, _, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)

    # Trigger low health
    detector.get_health_percent.return_value = 15.0

    result = run.execute()

    assert result.status == RunStatus.CHICKEN

    log.info("PASSED: chicken during run")
    return True


def test_run_settings():
    """Test run settings modification."""
    log = get_logger()
    log.info("Testing run settings...")

    run, _, _, _, _, _ = create_mock_mephisto_run()

    run.set_static_casts(8)
    run.set_blizzard_casts(10)
    run.set_search_timeout(60.0)

    assert run.static_casts == 8
    assert run.blizzard_casts == 10
    assert run.search_timeout == 60.0

    log.info("PASSED: run settings")
    return True


def test_settings_bounds():
    """Test run settings minimum bounds."""
    log = get_logger()
    log.info("Testing settings bounds...")

    run, _, _, _, _, _ = create_mock_mephisto_run()

    run.set_static_casts(-5)
    assert run.static_casts == 0

    run.set_blizzard_casts(0)
    assert run.blizzard_casts == 1

    run.set_search_timeout(1.0)
    assert run.search_timeout == 10.0

    log.info("PASSED: settings bounds")
    return True


def test_run_timeout():
    """Test run timeout setting."""
    log = get_logger()
    log.info("Testing run timeout...")

    run, _, _, _, _, _ = create_mock_mephisto_run()

    assert run.run_timeout == 180.0  # Longer than Pindle

    log.info("PASSED: run timeout")
    return True


def test_screen_positions():
    """Test screen position constants."""
    log = get_logger()
    log.info("Testing screen positions...")

    assert MephistoRun.SCREEN_CENTER == (960, 540)
    assert MephistoRun.MEPHISTO_TARGET == (800, 400)
    assert len(MephistoRun.SEARCH_DIRECTIONS) == 8
    assert len(MephistoRun.MOAT_POSITIONS) == 3
    assert MephistoRun.MAX_SEARCH_TELEPORTS == 25

    log.info("PASSED: screen positions")
    return True


def test_run_abort():
    """Test run abort."""
    log = get_logger()
    log.info("Testing run abort...")

    run, _, _, _, _, _ = create_mock_mephisto_run()

    run.abort()
    assert run.is_running() is False

    log.info("PASSED: run abort")
    return True


def test_run_history():
    """Test run history tracking."""
    log = get_logger()
    log.info("Testing run history...")

    run, _, _, _, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)

    run.execute()
    run.execute()

    assert run.get_run_count() == 2
    assert len(run.get_run_history()) == 2

    log.info("PASSED: run history")
    return True


def test_combat_skills_used():
    """Test combat skills are used during kill when level 3 is found."""
    log = get_logger()
    log.info("Testing combat skills used...")

    run, input_ctrl, _, _, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)

    # Mock _find_level_3 to succeed so combat is reached
    run._find_level_3 = Mock(return_value=True)

    run.execute()

    calls = input_ctrl.press.call_args_list
    hotkeys = [c[0][0] for c in calls]

    # Should use Static Field and Blizzard
    assert "f5" in hotkeys  # Static Field
    assert "f4" in hotkeys  # Blizzard

    log.info("PASSED: combat skills used")
    return True


def test_teleport_used():
    """Test teleport is used during level 3 search."""
    log = get_logger()
    log.info("Testing teleport used...")

    run, input_ctrl, _, combat, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)
    run.search_timeout = 0.5

    run.execute()

    calls = input_ctrl.press.call_args_list
    hotkeys = [c[0][0] for c in calls]

    # Teleport should be used during search
    assert "f3" in hotkeys  # Teleport

    log.info("PASSED: teleport used")
    return True


def test_run_without_combat():
    """Test run without combat system."""
    log = get_logger()
    log.info("Testing run without combat...")

    config = Config()
    input_ctrl = Mock()
    town = TownManager(config=config, input_ctrl=input_ctrl)
    town.use_waypoint = Mock(return_value=True)

    run = MephistoRun(
        config=config,
        input_ctrl=input_ctrl,
        combat=None,
        town_manager=town,
    )
    run.portal_load_time = 0.01
    run.cast_settle_time = 0.01
    run.waypoint_load_time = 0.01
    run.search_timeout = 0.1

    result = run.execute()

    # Without combat, Level 3 search fails
    assert result.status == RunStatus.ERROR

    log.info("PASSED: run without combat")
    return True


def test_callbacks():
    """Test callbacks are invoked."""
    log = get_logger()
    log.info("Testing callbacks...")

    run, _, _, _, _, town = create_mock_mephisto_run()
    town.use_waypoint = Mock(return_value=True)

    callback_called = [False]

    def on_complete(result):
        callback_called[0] = True

    run.set_callbacks(on_run_complete=on_complete)
    run.execute()

    assert callback_called[0] is True

    log.info("PASSED: callbacks")
    return True


def test_run_result_dataclass():
    """Test RunResult dataclass."""
    log = get_logger()
    log.info("Testing RunResult...")

    result = RunResult(
        status=RunStatus.SUCCESS,
        run_time=45.0,
        kills=1,
        items_picked=5,
    )

    assert result.status == RunStatus.SUCCESS
    assert result.kills == 1
    assert result.items_picked == 5
    assert result.run_time == 45.0

    log.info("PASSED: RunResult")
    return True


def run_all_tests():
    """Run all Mephisto run tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Mephisto Run Tests")
    log.info("=" * 50)

    tests = [
        ("Run Name", test_run_name),
        ("Execute With Town", test_execute_with_town),
        ("Execute No Town", test_execute_no_town),
        ("Chicken During Run", test_chicken_during_run),
        ("Run Settings", test_run_settings),
        ("Settings Bounds", test_settings_bounds),
        ("Run Timeout", test_run_timeout),
        ("Screen Positions", test_screen_positions),
        ("Run Abort", test_run_abort),
        ("Run History", test_run_history),
        ("Combat Skills Used", test_combat_skills_used),
        ("Teleport Used", test_teleport_used),
        ("Run Without Combat", test_run_without_combat),
        ("Callbacks", test_callbacks),
        ("RunResult Dataclass", test_run_result_dataclass),
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
