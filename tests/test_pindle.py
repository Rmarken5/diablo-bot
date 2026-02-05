"""Tests for Pindleskin run implementation."""

import time
from unittest.mock import Mock, MagicMock, patch

from src.game.runs import PindleRun, RunStatus, RunResult
from src.game.combat import SorceressCombat, Skill
from src.game.health import HealthMonitor, HealthStatus
from src.game.town import TownManager
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


def create_mock_pindle_run():
    """Create PindleRun with mocked dependencies."""
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

    # Create combat
    combat = SorceressCombat(config=config, input_ctrl=input_ctrl)
    combat.cast_delay = 0.01
    combat.teleport_delay = 0.01

    # Create health monitor
    health = HealthMonitor(
        config=config,
        input_ctrl=input_ctrl,
        game_detector=detector,
        screen_capture=capture,
    )
    health.check_interval = 0.01
    detector.get_health_percent.return_value = 100.0
    detector.get_mana_percent.return_value = 100.0

    # Create town manager
    town = TownManager(
        config=config,
        input_ctrl=input_ctrl,
        template_matcher=Mock(),
        screen_capture=capture,
    )

    run = PindleRun(
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
    run.wait_for_loot = 0.01

    return run, input_ctrl, detector, combat, health, town


def test_run_name():
    """Test run name."""
    log = get_logger()
    log.info("Testing run name...")

    run, _, _, _, _, _ = create_mock_pindle_run()
    assert run.name == "Pindleskin"

    log.info("PASSED: run name")
    return True


def test_execute_success():
    """Test successful run execution."""
    log = get_logger()
    log.info("Testing execute success...")

    run, input_ctrl, detector, _, _, town = create_mock_pindle_run()

    # Mock town navigation
    town.go_to_portal = Mock(return_value=True)

    result = run.execute()

    assert result.status == RunStatus.SUCCESS
    assert result.kills == 1
    assert result.run_time > 0

    log.info("PASSED: execute success")
    return True


def test_execute_records_history():
    """Test run history is recorded."""
    log = get_logger()
    log.info("Testing run history...")

    run, _, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    # Run twice
    run.execute()
    run.execute()

    assert run.get_run_count() == 2
    assert len(run.get_run_history()) == 2

    log.info("PASSED: run history")
    return True


def test_chicken_triggers_abort():
    """Test chicken status triggers abort."""
    log = get_logger()
    log.info("Testing chicken abort...")

    run, _, detector, _, health, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    # Trigger low health during run
    detector.get_health_percent.return_value = 15.0

    result = run.execute()

    # Should have chicken status
    assert result.status == RunStatus.CHICKEN

    log.info("PASSED: chicken abort")
    return True


def test_portal_navigation():
    """Test portal navigation is called."""
    log = get_logger()
    log.info("Testing portal navigation...")

    run, input_ctrl, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    town.go_to_portal.assert_called_once()

    log.info("PASSED: portal navigation")
    return True


def test_combat_execution():
    """Test combat skills are used."""
    log = get_logger()
    log.info("Testing combat execution...")

    run, input_ctrl, _, combat, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    # Should have pressed combat hotkeys
    calls = input_ctrl.press.call_args_list
    hotkeys = [c[0][0] for c in calls]

    # Check for Static Field (f5) and Blizzard (f4)
    assert "f5" in hotkeys  # Static Field
    assert "f4" in hotkeys  # Blizzard

    log.info("PASSED: combat execution")
    return True


def test_teleport_to_pindle():
    """Test teleporting to Pindleskin."""
    log = get_logger()
    log.info("Testing teleport to Pindle...")

    run, input_ctrl, _, combat, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    # Should have pressed teleport key
    calls = input_ctrl.press.call_args_list
    hotkeys = [c[0][0] for c in calls]

    assert "f3" in hotkeys  # Teleport

    log.info("PASSED: teleport to Pindle")
    return True


def test_buffs_cast():
    """Test buffs are cast before run."""
    log = get_logger()
    log.info("Testing buffs cast...")

    run, input_ctrl, _, combat, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    # Should have pressed frozen armor key
    calls = input_ctrl.press.call_args_list
    hotkeys = [c[0][0] for c in calls]

    assert "f6" in hotkeys  # Frozen Armor

    log.info("PASSED: buffs cast")
    return True


def test_exit_game_called():
    """Test game exit is called after run."""
    log = get_logger()
    log.info("Testing exit game...")

    run, input_ctrl, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    # Should have pressed escape (for save & exit)
    calls = input_ctrl.press.call_args_list
    keys = [c[0][0] for c in calls]

    escape_count = keys.count("escape")
    assert escape_count >= 2  # Escape pressed twice for save & exit

    log.info("PASSED: exit game")
    return True


def test_loot_alt_pressed():
    """Test alt key pressed for looting."""
    log = get_logger()
    log.info("Testing loot alt key...")

    run, input_ctrl, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    run.execute()

    # Should have pressed alt for show items
    input_ctrl.press.assert_any_call("alt")

    log.info("PASSED: loot alt key")
    return True


def test_run_settings():
    """Test run settings modification."""
    log = get_logger()
    log.info("Testing run settings...")

    run, _, _, _, _, _ = create_mock_pindle_run()

    run.set_static_casts(5)
    run.set_blizzard_casts(4)

    assert run.static_casts == 5
    assert run.blizzard_casts == 4

    # Test minimum bounds
    run.set_static_casts(-1)
    run.set_blizzard_casts(0)

    assert run.static_casts == 0  # Minimum 0
    assert run.blizzard_casts == 1  # Minimum 1

    log.info("PASSED: run settings")
    return True


def test_run_abort():
    """Test run can be aborted."""
    log = get_logger()
    log.info("Testing run abort...")

    run, _, _, _, _, _ = create_mock_pindle_run()

    # Abort (would normally be called from another thread)
    run.abort()

    assert run.is_running() is False

    log.info("PASSED: run abort")
    return True


def test_run_timeout_check():
    """Test timeout detection."""
    log = get_logger()
    log.info("Testing timeout check...")

    run, _, _, _, _, _ = create_mock_pindle_run()

    # Not running - no timeout
    assert run.check_timeout() is False

    log.info("PASSED: timeout check")
    return True


def test_statistics_tracking():
    """Test run statistics."""
    log = get_logger()
    log.info("Testing statistics...")

    run, _, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    # Run a few times
    run.execute()
    run.execute()

    assert run.get_run_count() == 2
    assert run.get_success_count() == 2
    assert run.get_chicken_count() == 0
    assert run.get_average_run_time() > 0

    log.info("PASSED: statistics")
    return True


def test_callbacks_called():
    """Test callbacks are invoked."""
    log = get_logger()
    log.info("Testing callbacks...")

    run, _, _, _, _, town = create_mock_pindle_run()
    town.go_to_portal = Mock(return_value=True)

    callback_called = [False]

    def on_complete(result):
        callback_called[0] = True

    run.set_callbacks(on_run_complete=on_complete)
    run.execute()

    assert callback_called[0] is True

    log.info("PASSED: callbacks")
    return True


def test_find_pindleskin():
    """Test Pindleskin detection."""
    log = get_logger()
    log.info("Testing find Pindleskin...")

    run, _, detector, _, _, _ = create_mock_pindle_run()

    # With detector, returns expected position
    pos = run.find_pindleskin(Mock())
    assert pos == (960, 250)

    # Without detector, returns None
    run.detector = None
    pos = run.find_pindleskin(Mock())
    assert pos is None

    log.info("PASSED: find Pindleskin")
    return True


def test_run_result_dataclass():
    """Test RunResult dataclass."""
    log = get_logger()
    log.info("Testing RunResult...")

    result = RunResult(
        status=RunStatus.SUCCESS,
        run_time=15.5,
        kills=1,
        items_picked=3,
    )

    assert result.status == RunStatus.SUCCESS
    assert result.run_time == 15.5
    assert result.kills == 1
    assert result.items_picked == 3
    assert result.timestamp > 0

    log.info("PASSED: RunResult")
    return True


def test_run_without_combat():
    """Test run without combat system."""
    log = get_logger()
    log.info("Testing run without combat...")

    config = Config()
    input_ctrl = Mock()

    run = PindleRun(
        config=config,
        input_ctrl=input_ctrl,
        combat=None,  # No combat
    )

    # Speed up
    run.portal_load_time = 0.01
    run.cast_settle_time = 0.01
    run.wait_for_loot = 0.01

    result = run.execute()

    # Should still complete (with 0 kills)
    assert result.status == RunStatus.SUCCESS
    assert result.kills == 0

    log.info("PASSED: run without combat")
    return True


def test_run_without_health_monitor():
    """Test run without health monitoring."""
    log = get_logger()
    log.info("Testing run without health monitor...")

    config = Config()
    input_ctrl = Mock()
    config.hotkeys = {"teleport": "f3", "blizzard": "f4", "static_field": "f5"}

    combat = SorceressCombat(config=config, input_ctrl=input_ctrl)
    combat.cast_delay = 0.01

    run = PindleRun(
        config=config,
        input_ctrl=input_ctrl,
        combat=combat,
        health_monitor=None,  # No health monitor
    )

    run.portal_load_time = 0.01
    run.cast_settle_time = 0.01
    run.wait_for_loot = 0.01

    result = run.execute()

    # Should complete successfully
    assert result.status == RunStatus.SUCCESS

    log.info("PASSED: run without health monitor")
    return True


def run_all_tests():
    """Run all Pindleskin run tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Pindleskin Run Tests")
    log.info("=" * 50)

    tests = [
        ("Run Name", test_run_name),
        ("Execute Success", test_execute_success),
        ("Run History", test_execute_records_history),
        ("Chicken Abort", test_chicken_triggers_abort),
        ("Portal Navigation", test_portal_navigation),
        ("Combat Execution", test_combat_execution),
        ("Teleport to Pindle", test_teleport_to_pindle),
        ("Buffs Cast", test_buffs_cast),
        ("Exit Game", test_exit_game_called),
        ("Loot Alt Key", test_loot_alt_pressed),
        ("Run Settings", test_run_settings),
        ("Run Abort", test_run_abort),
        ("Timeout Check", test_run_timeout_check),
        ("Statistics", test_statistics_tracking),
        ("Callbacks", test_callbacks_called),
        ("Find Pindleskin", test_find_pindleskin),
        ("RunResult Dataclass", test_run_result_dataclass),
        ("Run Without Combat", test_run_without_combat),
        ("Run Without Health Monitor", test_run_without_health_monitor),
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
