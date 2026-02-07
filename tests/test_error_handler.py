"""Tests for error detection and recovery system."""

from unittest.mock import Mock

from src.utils.error_handler import (
    ErrorHandler,
    ErrorType,
    ErrorSeverity,
    ErrorResolution,
    StuckDetector,
    BotError,
    ERROR_CLASSIFICATION,
)
from src.utils.logger import setup_logger, get_logger


def create_mock_error_handler():
    """Create ErrorHandler with mocked dependencies."""
    input_ctrl = Mock()
    capture = Mock()
    detector = Mock()
    combat = Mock()

    handler = ErrorHandler(
        max_retries=3,
        input_ctrl=input_ctrl,
        screen_capture=capture,
        game_detector=detector,
        combat=combat,
    )

    return handler, input_ctrl, combat, detector


def test_error_type_enum():
    """Test ErrorType enum members."""
    log = get_logger()
    log.info("Testing ErrorType enum...")

    assert ErrorType.STUCK.value == "stuck"
    assert ErrorType.DISCONNECT.value == "disconnect"
    assert ErrorType.GAME_CRASH.value == "game_crash"
    assert ErrorType.DEATH.value == "death"
    assert ErrorType.INVENTORY_FULL.value == "inventory_full"
    assert len(ErrorType) == 8

    log.info("PASSED: ErrorType enum")
    return True


def test_error_severity_enum():
    """Test ErrorSeverity enum members."""
    log = get_logger()
    log.info("Testing ErrorSeverity enum...")

    assert ErrorSeverity.RECOVERABLE is not None
    assert ErrorSeverity.RUN_ENDING is not None
    assert ErrorSeverity.CRITICAL is not None

    log.info("PASSED: ErrorSeverity enum")
    return True


def test_error_classification():
    """Test error classification mapping."""
    log = get_logger()
    log.info("Testing error classification...")

    assert ERROR_CLASSIFICATION[ErrorType.STUCK] == ErrorSeverity.RECOVERABLE
    assert ERROR_CLASSIFICATION[ErrorType.DEATH] == ErrorSeverity.RUN_ENDING
    assert ERROR_CLASSIFICATION[ErrorType.GAME_CRASH] == ErrorSeverity.CRITICAL
    assert ERROR_CLASSIFICATION[ErrorType.TEMPLATE_FAIL] == ErrorSeverity.RECOVERABLE
    assert ERROR_CLASSIFICATION[ErrorType.DISCONNECT] == ErrorSeverity.RUN_ENDING

    log.info("PASSED: error classification")
    return True


def test_handle_stuck_recovery():
    """Test stuck error recovery."""
    log = get_logger()
    log.info("Testing stuck recovery...")

    handler, _, combat, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.STUCK, "Character not moving")

    assert result == ErrorResolution.CONTINUE
    combat.cast_teleport.assert_called_once()

    log.info("PASSED: stuck recovery")
    return True


def test_handle_template_fail_recovery():
    """Test template fail recovery."""
    log = get_logger()
    log.info("Testing template fail recovery...")

    handler, _, _, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.TEMPLATE_FAIL, "Button not found")

    assert result == ErrorResolution.CONTINUE

    log.info("PASSED: template fail recovery")
    return True


def test_handle_timeout_recovery():
    """Test timeout recovery."""
    log = get_logger()
    log.info("Testing timeout recovery...")

    handler, input_ctrl, _, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.TIMEOUT, "Action timed out")

    assert result == ErrorResolution.CONTINUE
    input_ctrl.press.assert_called_with("escape")

    log.info("PASSED: timeout recovery")
    return True


def test_handle_inventory_full():
    """Test inventory full handling."""
    log = get_logger()
    log.info("Testing inventory full handling...")

    handler, _, _, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.INVENTORY_FULL, "No space")

    # Inventory full recovery returns False, so should end run
    assert result == ErrorResolution.END_RUN

    log.info("PASSED: inventory full handling")
    return True


def test_handle_death():
    """Test death handling."""
    log = get_logger()
    log.info("Testing death handling...")

    handler, _, _, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.DEATH, "Character died")

    assert result == ErrorResolution.END_RUN

    log.info("PASSED: death handling")
    return True


def test_handle_game_crash():
    """Test game crash handling."""
    log = get_logger()
    log.info("Testing game crash handling...")

    handler, _, _, _ = create_mock_error_handler()

    result = handler.handle(ErrorType.GAME_CRASH, "Game process terminated")

    assert result == ErrorResolution.RESTART_GAME

    log.info("PASSED: game crash handling")
    return True


def test_max_retries_exceeded():
    """Test max retries escalation."""
    log = get_logger()
    log.info("Testing max retries exceeded...")

    handler, _, _, _ = create_mock_error_handler()
    handler.max_retries = 2

    # First two should recover
    r1 = handler.handle(ErrorType.TEMPLATE_FAIL, "fail 1")
    assert r1 == ErrorResolution.CONTINUE

    r2 = handler.handle(ErrorType.TEMPLATE_FAIL, "fail 2")
    assert r2 == ErrorResolution.CONTINUE

    # Third should end run (max retries exceeded)
    r3 = handler.handle(ErrorType.TEMPLATE_FAIL, "fail 3")
    assert r3 == ErrorResolution.END_RUN

    log.info("PASSED: max retries exceeded")
    return True


def test_consecutive_errors_escalation():
    """Test that repeated errors eventually end run via max retries."""
    log = get_logger()
    log.info("Testing consecutive errors escalation...")

    handler, _, _, _ = create_mock_error_handler()
    handler.max_retries = 3

    # Successful recovery resets consecutive counter, so we need
    # to trigger errors that don't recover to build up consecutive count.
    # Use INVENTORY_FULL which returns False from recovery.
    results = []
    for _ in range(5):
        r = handler.handle(ErrorType.INVENTORY_FULL, "full")
        results.append(r)

    # First should end run (recovery returns False), subsequent too
    assert ErrorResolution.END_RUN in results

    log.info("PASSED: consecutive errors escalation")
    return True


def test_error_history():
    """Test error history tracking."""
    log = get_logger()
    log.info("Testing error history...")

    handler, _, _, _ = create_mock_error_handler()

    handler.handle(ErrorType.STUCK, "first")
    handler.handle(ErrorType.TIMEOUT, "second")

    history = handler.get_error_history()
    assert len(history) == 2
    assert history[0].error_type == ErrorType.STUCK
    assert history[1].error_type == ErrorType.TIMEOUT

    log.info("PASSED: error history")
    return True


def test_error_count():
    """Test error count."""
    log = get_logger()
    log.info("Testing error count...")

    handler, _, _, _ = create_mock_error_handler()

    handler.handle(ErrorType.STUCK, "one")
    handler.handle(ErrorType.STUCK, "two")

    assert handler.get_error_count() == 2

    log.info("PASSED: error count")
    return True


def test_recovery_rate():
    """Test recovery rate calculation."""
    log = get_logger()
    log.info("Testing recovery rate...")

    handler, _, _, _ = create_mock_error_handler()

    handler.handle(ErrorType.STUCK, "recoverable")  # Recovered
    handler.handle(ErrorType.TEMPLATE_FAIL, "recoverable")  # Recovered

    rate = handler.get_recovery_rate()
    assert rate == 100.0

    log.info("PASSED: recovery rate")
    return True


def test_recovery_rate_empty():
    """Test recovery rate with no errors."""
    log = get_logger()
    log.info("Testing empty recovery rate...")

    handler, _, _, _ = create_mock_error_handler()

    assert handler.get_recovery_rate() == 0.0

    log.info("PASSED: empty recovery rate")
    return True


def test_clear_error_state():
    """Test clearing error state."""
    log = get_logger()
    log.info("Testing clear error state...")

    handler, _, _, _ = create_mock_error_handler()

    handler.handle(ErrorType.STUCK, "error")
    handler.clear_error_state()

    assert handler._retry_count == 0
    assert handler._consecutive_errors == 0

    log.info("PASSED: clear error state")
    return True


def test_callbacks():
    """Test error callbacks."""
    log = get_logger()
    log.info("Testing callbacks...")

    handler, _, _, _ = create_mock_error_handler()

    recovery_called = [False]
    critical_called = [False]

    def on_recovery(error):
        recovery_called[0] = True

    def on_critical(error):
        critical_called[0] = True

    handler.set_callbacks(on_critical=on_critical, on_recovery=on_recovery)

    # Trigger recoverable error
    handler.handle(ErrorType.STUCK, "stuck")
    assert recovery_called[0] is True

    # Trigger critical error
    handler.handle(ErrorType.GAME_CRASH, "crash")
    assert critical_called[0] is True

    log.info("PASSED: callbacks")
    return True


def test_stuck_detector_basic():
    """Test basic stuck detection."""
    log = get_logger()
    log.info("Testing stuck detector basic...")

    detector = StuckDetector(threshold=3, distance_threshold=10)

    # Moving positions - not stuck
    assert detector.update(100, 100) is False
    assert detector.update(200, 200) is False
    assert detector.update(300, 300) is False

    log.info("PASSED: stuck detector basic")
    return True


def test_stuck_detector_triggers():
    """Test stuck detector triggers on same position."""
    log = get_logger()
    log.info("Testing stuck detector triggers...")

    detector = StuckDetector(threshold=3, distance_threshold=10)

    # Same position repeatedly
    assert detector.update(500, 500) is False
    assert detector.update(502, 498) is False
    assert detector.update(501, 501) is True  # 3rd similar = stuck

    log.info("PASSED: stuck detector triggers")
    return True


def test_stuck_detector_reset():
    """Test stuck detector reset."""
    log = get_logger()
    log.info("Testing stuck detector reset...")

    detector = StuckDetector(threshold=3, distance_threshold=10)

    detector.update(500, 500)
    detector.update(500, 500)
    detector.reset()

    # After reset, should need threshold samples again
    assert detector.update(500, 500) is False

    log.info("PASSED: stuck detector reset")
    return True


def test_stuck_detector_not_enough_samples():
    """Test stuck detector with insufficient samples."""
    log = get_logger()
    log.info("Testing insufficient samples...")

    detector = StuckDetector(threshold=5, distance_threshold=10)

    # Only 2 samples - can't be stuck yet
    assert detector.update(500, 500) is False
    assert detector.update(500, 500) is False

    log.info("PASSED: insufficient samples")
    return True


def test_check_stuck_integration():
    """Test check_stuck integration in ErrorHandler."""
    log = get_logger()
    log.info("Testing check_stuck integration...")

    handler, _, _, _ = create_mock_error_handler()

    # Moving positions
    assert handler.check_stuck(100, 100) is False
    assert handler.check_stuck(500, 500) is False
    assert handler.check_stuck(800, 300) is False

    log.info("PASSED: check_stuck integration")
    return True


def test_reset_stuck():
    """Test reset_stuck in ErrorHandler."""
    log = get_logger()
    log.info("Testing reset_stuck...")

    handler, _, _, _ = create_mock_error_handler()

    handler.check_stuck(500, 500)
    handler.check_stuck(500, 500)
    handler.reset_stuck()

    # After reset, should not trigger immediately
    assert handler.check_stuck(500, 500) is False

    log.info("PASSED: reset_stuck")
    return True


def test_bot_error_dataclass():
    """Test BotError dataclass."""
    log = get_logger()
    log.info("Testing BotError dataclass...")

    error = BotError(
        error_type=ErrorType.STUCK,
        severity=ErrorSeverity.RECOVERABLE,
        message="test error",
    )

    assert error.error_type == ErrorType.STUCK
    assert error.severity == ErrorSeverity.RECOVERABLE
    assert error.message == "test error"
    assert error.recovery_attempted is False
    assert error.recovered is False
    assert error.timestamp > 0

    log.info("PASSED: BotError dataclass")
    return True


def test_handle_without_combat():
    """Test stuck recovery without combat system."""
    log = get_logger()
    log.info("Testing stuck recovery without combat...")

    input_ctrl = Mock()
    handler = ErrorHandler(
        max_retries=3,
        input_ctrl=input_ctrl,
        combat=None,
    )

    result = handler.handle(ErrorType.STUCK, "stuck without combat")

    assert result == ErrorResolution.CONTINUE
    input_ctrl.click.assert_called_once()

    log.info("PASSED: stuck recovery without combat")
    return True


def run_all_tests():
    """Run all error handler tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Error Handler Tests")
    log.info("=" * 50)

    tests = [
        ("ErrorType Enum", test_error_type_enum),
        ("ErrorSeverity Enum", test_error_severity_enum),
        ("Error Classification", test_error_classification),
        ("Stuck Recovery", test_handle_stuck_recovery),
        ("Template Fail Recovery", test_handle_template_fail_recovery),
        ("Timeout Recovery", test_handle_timeout_recovery),
        ("Inventory Full", test_handle_inventory_full),
        ("Death Handling", test_handle_death),
        ("Game Crash", test_handle_game_crash),
        ("Max Retries Exceeded", test_max_retries_exceeded),
        ("Consecutive Errors", test_consecutive_errors_escalation),
        ("Error History", test_error_history),
        ("Error Count", test_error_count),
        ("Recovery Rate", test_recovery_rate),
        ("Empty Recovery Rate", test_recovery_rate_empty),
        ("Clear Error State", test_clear_error_state),
        ("Callbacks", test_callbacks),
        ("Stuck Detector Basic", test_stuck_detector_basic),
        ("Stuck Detector Triggers", test_stuck_detector_triggers),
        ("Stuck Detector Reset", test_stuck_detector_reset),
        ("Insufficient Samples", test_stuck_detector_not_enough_samples),
        ("Check Stuck Integration", test_check_stuck_integration),
        ("Reset Stuck", test_reset_stuck),
        ("BotError Dataclass", test_bot_error_dataclass),
        ("Stuck Without Combat", test_handle_without_combat),
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
