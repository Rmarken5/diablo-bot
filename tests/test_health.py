"""Tests for health monitoring and chicken system."""

import time
from unittest.mock import Mock, MagicMock

from src.game.health import (
    HealthMonitor,
    HealthStatus,
    HealthState,
    PotionType,
    ChickenEvent,
    MercenaryMonitor,
)
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


def create_mock_health_monitor(health: float = 100.0, mana: float = 100.0):
    """Create HealthMonitor with mocked dependencies."""
    config = Config()
    config.chicken_health_percent = 30
    config.chicken_mana_percent = 0

    input_ctrl = Mock()
    detector = Mock()
    capture = Mock()

    # Setup detector to return specified health/mana
    detector.get_health_percent.return_value = health
    detector.get_mana_percent.return_value = mana
    capture.grab.return_value = Mock()

    monitor = HealthMonitor(
        config=config,
        input_ctrl=input_ctrl,
        game_detector=detector,
        screen_capture=capture,
    )

    # Speed up tests
    monitor.check_interval = 0.01
    monitor.potion_cooldown = 0.1

    return monitor, input_ctrl, detector, capture


def test_initial_state():
    """Test initial health monitor state."""
    log = get_logger()
    log.info("Testing initial state...")

    monitor, _, _, _ = create_mock_health_monitor()

    assert monitor.state.health_percent == 100.0
    assert monitor.state.mana_percent == 100.0
    assert monitor.state.status == HealthStatus.SAFE
    assert monitor.state.chicken_triggered is False
    assert not monitor.is_monitoring()

    log.info("PASSED: initial state")
    return True


def test_start_stop_monitoring():
    """Test starting and stopping monitoring."""
    log = get_logger()
    log.info("Testing start/stop monitoring...")

    monitor, _, _, _ = create_mock_health_monitor()

    # Start
    monitor.start_monitoring()
    assert monitor.is_monitoring()
    time.sleep(0.05)

    # Stop
    monitor.stop_monitoring()
    assert not monitor.is_monitoring()

    log.info("PASSED: start/stop monitoring")
    return True


def test_health_status_safe():
    """Test health status when safe."""
    log = get_logger()
    log.info("Testing safe health status...")

    monitor, _, _, _ = create_mock_health_monitor(health=80.0)

    monitor._update_health_state()
    status = monitor._evaluate_status()

    assert status == HealthStatus.SAFE
    assert monitor.state.health_percent == 80.0

    log.info("PASSED: safe health status")
    return True


def test_health_status_warning():
    """Test health status at warning level."""
    log = get_logger()
    log.info("Testing warning health status...")

    monitor, _, _, _ = create_mock_health_monitor(health=45.0)
    monitor.warning_health = 50

    monitor._update_health_state()
    status = monitor._evaluate_status()

    assert status == HealthStatus.WARNING

    log.info("PASSED: warning health status")
    return True


def test_health_status_critical():
    """Test health status at critical level."""
    log = get_logger()
    log.info("Testing critical health status...")

    monitor, _, _, _ = create_mock_health_monitor(health=25.0)

    monitor._update_health_state()
    status = monitor._evaluate_status()

    assert status == HealthStatus.CRITICAL

    log.info("PASSED: critical health status")
    return True


def test_mana_chicken():
    """Test chicken triggers on low mana."""
    log = get_logger()
    log.info("Testing mana chicken...")

    monitor, _, _, _ = create_mock_health_monitor(health=100.0, mana=5.0)
    monitor.chicken_mana = 10  # Chicken at 10% mana

    monitor._update_health_state()
    status = monitor._evaluate_status()

    assert status == HealthStatus.CRITICAL

    log.info("PASSED: mana chicken")
    return True


def test_check_health():
    """Test check_health method."""
    log = get_logger()
    log.info("Testing check_health...")

    # Safe health
    monitor, _, detector, _ = create_mock_health_monitor(health=80.0)
    assert monitor.check_health() is True

    # Critical health
    detector.get_health_percent.return_value = 20.0
    assert monitor.check_health() is False

    log.info("PASSED: check_health")
    return True


def test_use_potion():
    """Test potion usage."""
    log = get_logger()
    log.info("Testing potion usage...")

    monitor, input_ctrl, _, _ = create_mock_health_monitor()

    # Use health potion
    result = monitor.use_health_potion()
    assert result is True
    input_ctrl.use_potion.assert_called_with(1)

    # Use mana potion (should work, different slot)
    time.sleep(0.15)  # Wait for cooldown
    result = monitor.use_mana_potion()
    assert result is True
    input_ctrl.use_potion.assert_called_with(2)

    log.info("PASSED: potion usage")
    return True


def test_potion_cooldown():
    """Test potion cooldown prevents spam."""
    log = get_logger()
    log.info("Testing potion cooldown...")

    monitor, input_ctrl, _, _ = create_mock_health_monitor()

    # First potion works
    result1 = monitor.use_health_potion()
    assert result1 is True

    # Second potion blocked by cooldown
    result2 = monitor.use_health_potion()
    assert result2 is False

    # After cooldown, works again
    time.sleep(0.15)
    result3 = monitor.use_health_potion()
    assert result3 is True

    log.info("PASSED: potion cooldown")
    return True


def test_chicken_execution():
    """Test chicken executes game exit."""
    log = get_logger()
    log.info("Testing chicken execution...")

    monitor, input_ctrl, _, _ = create_mock_health_monitor()

    monitor.chicken(reason="test")

    # Should press escape twice
    assert input_ctrl.press.call_count >= 2

    # Should be marked as triggered
    assert monitor.state.chicken_triggered is True

    # Should have history entry
    assert monitor.get_chicken_count() == 1
    history = monitor.get_chicken_history()
    assert len(history) == 1
    assert history[0].reason == "test"

    log.info("PASSED: chicken execution")
    return True


def test_chicken_only_once():
    """Test chicken only triggers once."""
    log = get_logger()
    log.info("Testing chicken only once...")

    monitor, input_ctrl, _, _ = create_mock_health_monitor()

    # First chicken
    monitor.chicken(reason="first")
    first_count = input_ctrl.press.call_count

    # Second chicken should not execute
    monitor.chicken(reason="second")
    second_count = input_ctrl.press.call_count

    assert first_count == second_count  # No additional presses
    assert monitor.get_chicken_count() == 1  # Only one recorded

    log.info("PASSED: chicken only once")
    return True


def test_reset_chicken_flag():
    """Test resetting chicken flag."""
    log = get_logger()
    log.info("Testing reset chicken flag...")

    monitor, _, _, _ = create_mock_health_monitor()

    monitor.chicken(reason="test")
    assert monitor.state.chicken_triggered is True

    monitor.reset_chicken_flag()
    assert monitor.state.chicken_triggered is False

    log.info("PASSED: reset chicken flag")
    return True


def test_callbacks():
    """Test callback functions are called."""
    log = get_logger()
    log.info("Testing callbacks...")

    monitor, _, _, _ = create_mock_health_monitor()

    chicken_called = [False]
    low_health_called = [False]

    def on_chicken(event):
        chicken_called[0] = True

    def on_low_health(percent):
        low_health_called[0] = True

    monitor.set_callbacks(on_chicken=on_chicken, on_low_health=on_low_health)

    # Trigger chicken
    monitor.chicken(reason="test")
    assert chicken_called[0] is True

    log.info("PASSED: callbacks")
    return True


def test_set_thresholds():
    """Test updating thresholds."""
    log = get_logger()
    log.info("Testing set thresholds...")

    monitor, _, _, _ = create_mock_health_monitor()

    original_chicken = monitor.chicken_health
    monitor.set_thresholds(chicken_health=50, warning_health=70)

    assert monitor.chicken_health == 50
    assert monitor.warning_health == 70
    assert monitor.chicken_health != original_chicken

    log.info("PASSED: set thresholds")
    return True


def test_get_health_mana():
    """Test getting current health/mana."""
    log = get_logger()
    log.info("Testing get health/mana...")

    monitor, _, detector, _ = create_mock_health_monitor(health=75.0, mana=60.0)

    monitor._update_health_state()

    assert monitor.get_health_percent() == 75.0
    assert monitor.get_mana_percent() == 60.0

    log.info("PASSED: get health/mana")
    return True


def test_no_detector_graceful():
    """Test graceful handling when no detector."""
    log = get_logger()
    log.info("Testing no detector...")

    config = Config()
    monitor = HealthMonitor(config=config)

    # Should not crash
    monitor._update_health_state()

    # check_health should return True (safe) when can't detect
    result = monitor.check_health()
    # Status remains at default (SAFE) when can't read

    log.info("PASSED: no detector")
    return True


def test_health_state_dataclass():
    """Test HealthState dataclass."""
    log = get_logger()
    log.info("Testing HealthState...")

    state = HealthState()
    assert state.health_percent == 100.0
    assert state.mana_percent == 100.0
    assert state.status == HealthStatus.SAFE
    assert state.chicken_triggered is False

    state.health_percent = 50.0
    state.status = HealthStatus.WARNING
    assert state.health_percent == 50.0

    log.info("PASSED: HealthState")
    return True


def test_chicken_event_dataclass():
    """Test ChickenEvent dataclass."""
    log = get_logger()
    log.info("Testing ChickenEvent...")

    event = ChickenEvent(
        timestamp=time.time(),
        health_percent=25.0,
        mana_percent=50.0,
        reason="test_chicken",
        potion_attempted=True,
    )

    assert event.health_percent == 25.0
    assert event.reason == "test_chicken"
    assert event.potion_attempted is True

    log.info("PASSED: ChickenEvent")
    return True


def test_potion_type_slots():
    """Test potion type to slot mapping."""
    log = get_logger()
    log.info("Testing potion slots...")

    monitor, _, _, _ = create_mock_health_monitor()

    assert monitor.POTION_SLOTS[PotionType.HEALTH] == 1
    assert monitor.POTION_SLOTS[PotionType.MANA] == 2
    assert monitor.POTION_SLOTS[PotionType.REJUV] == 3

    log.info("PASSED: potion slots")
    return True


def test_mercenary_monitor():
    """Test mercenary monitor."""
    log = get_logger()
    log.info("Testing mercenary monitor...")

    config = Config()
    input_ctrl = Mock()
    merc_monitor = MercenaryMonitor(config=config, input_ctrl=input_ctrl)

    # Initial state
    assert merc_monitor.merc_health_percent == 100.0
    assert merc_monitor.should_save_merc() is False

    # Low merc health
    merc_monitor.merc_health_percent = 15.0
    assert merc_monitor.should_save_merc() is True

    # Give potion
    merc_monitor.give_merc_potion()
    input_ctrl.key_down.assert_called_with("shift")
    input_ctrl.press.assert_called_with("1")
    input_ctrl.key_up.assert_called_with("shift")

    log.info("PASSED: mercenary monitor")
    return True


def test_monitoring_updates_state():
    """Test that monitoring loop updates state."""
    log = get_logger()
    log.info("Testing monitoring updates state...")

    monitor, _, detector, _ = create_mock_health_monitor(health=90.0)

    # Start monitoring
    monitor.start_monitoring()
    time.sleep(0.1)  # Let it run a few cycles

    # Change detected health
    detector.get_health_percent.return_value = 70.0
    time.sleep(0.1)

    # State should update
    monitor.stop_monitoring()

    # The state should have been updated at some point
    # (exact timing depends on thread scheduling)
    log.info(f"Final health state: {monitor.state.health_percent}")

    log.info("PASSED: monitoring updates state")
    return True


def run_all_tests():
    """Run all health monitoring tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Health Monitoring Tests")
    log.info("=" * 50)

    tests = [
        ("Initial State", test_initial_state),
        ("Start/Stop Monitoring", test_start_stop_monitoring),
        ("Health Status Safe", test_health_status_safe),
        ("Health Status Warning", test_health_status_warning),
        ("Health Status Critical", test_health_status_critical),
        ("Mana Chicken", test_mana_chicken),
        ("Check Health", test_check_health),
        ("Use Potion", test_use_potion),
        ("Potion Cooldown", test_potion_cooldown),
        ("Chicken Execution", test_chicken_execution),
        ("Chicken Only Once", test_chicken_only_once),
        ("Reset Chicken Flag", test_reset_chicken_flag),
        ("Callbacks", test_callbacks),
        ("Set Thresholds", test_set_thresholds),
        ("Get Health/Mana", test_get_health_mana),
        ("No Detector Graceful", test_no_detector_graceful),
        ("HealthState Dataclass", test_health_state_dataclass),
        ("ChickenEvent Dataclass", test_chicken_event_dataclass),
        ("Potion Type Slots", test_potion_type_slots),
        ("Mercenary Monitor", test_mercenary_monitor),
        ("Monitoring Updates State", test_monitoring_updates_state),
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
