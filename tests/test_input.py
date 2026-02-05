"""Tests for input controller module."""

import math
from unittest.mock import Mock, patch

from src.input.mouse import wind_mouse, generate_path, MouseMover
from src.input.keyboard import KeyboardController
from src.input.controller import InputController
from src.utils.logger import setup_logger, get_logger


def test_wind_mouse_generates_path():
    """Test that wind_mouse generates a path to destination."""
    log = get_logger()
    log.info("Testing wind_mouse path generation...")

    path = generate_path(0, 0, 100, 100)

    assert len(path) > 0, "Should generate path points"
    assert path[-1] == (100, 100), f"Should end at destination, got {path[-1]}"

    log.info(f"Generated path with {len(path)} points")
    log.info("PASSED: wind_mouse path generation")
    return True


def test_wind_mouse_path_is_curved():
    """Test that wind_mouse creates non-linear paths."""
    log = get_logger()
    log.info("Testing wind_mouse path curvature...")

    path = generate_path(0, 0, 100, 0, wind=5.0)

    # Check that not all Y values are 0 (path has curves)
    y_values = [p[1] for p in path]
    has_variation = any(y != 0 for y in y_values)

    assert has_variation, "Path should have Y variation (curves)"

    max_deviation = max(abs(y) for y in y_values)
    log.info(f"Maximum Y deviation from straight line: {max_deviation}")
    log.info("PASSED: wind_mouse path curvature")
    return True


def test_wind_mouse_respects_parameters():
    """Test that wind_mouse parameters affect behavior."""
    log = get_logger()
    log.info("Testing wind_mouse parameters...")

    # Fast movement (high gravity, low wind)
    fast_path = generate_path(0, 0, 100, 100, gravity=15, wind=1)

    # Slow wandering movement (low gravity, high wind)
    slow_path = generate_path(0, 0, 100, 100, gravity=3, wind=8)

    # Fast path should generally be shorter
    log.info(f"Fast path: {len(fast_path)} points")
    log.info(f"Slow path: {len(slow_path)} points")

    # Both should reach destination
    assert fast_path[-1] == (100, 100)
    assert slow_path[-1] == (100, 100)

    log.info("PASSED: wind_mouse parameters")
    return True


def test_mouse_mover():
    """Test MouseMover class."""
    log = get_logger()
    log.info("Testing MouseMover...")

    mover = MouseMover(move_delay=(0, 0))  # No sleep delay for tests

    # Track movements
    moves = []
    mover.set_move_function(lambda x, y: moves.append((x, y)))
    mover.set_position(0, 0)

    # Move to position
    mover.move_to(50, 50)

    assert len(moves) > 0, "Should have recorded moves"
    assert moves[-1] == (50, 50), f"Should end at target, got {moves[-1]}"
    assert mover.get_position() == (50, 50), "Position should be updated"

    log.info(f"MouseMover made {len(moves)} moves")
    log.info("PASSED: MouseMover")
    return True


def test_keyboard_controller():
    """Test KeyboardController class."""
    log = get_logger()
    log.info("Testing KeyboardController...")

    kb = KeyboardController(
        key_delay=(0, 0),  # No delays for tests
        hold_duration=(0, 0),
    )

    # Track calls
    key_downs = []
    key_ups = []
    presses = []

    kb.set_key_functions(
        key_down=lambda k: key_downs.append(k),
        key_up=lambda k: key_ups.append(k),
        press=lambda k: presses.append(k),
    )

    # Test press
    kb.press("a")
    assert "a" in presses, "Should have pressed 'a'"

    # Test hold
    kb.hold("shift", 0.001)
    assert "shift" in key_downs, "Should have key_down 'shift'"
    assert "shift" in key_ups, "Should have key_up 'shift'"

    log.info("PASSED: KeyboardController")
    return True


def test_keyboard_combo():
    """Test key combination pressing."""
    log = get_logger()
    log.info("Testing keyboard combo...")

    kb = KeyboardController(
        key_delay=(0, 0),
        hold_duration=(0, 0),
    )

    key_downs = []
    key_ups = []

    kb.set_key_functions(
        key_down=lambda k: key_downs.append(k),
        key_up=lambda k: key_ups.append(k),
    )

    kb.press_combo("ctrl", "c", hold_time=0.001)

    assert "ctrl" in key_downs, "Should press ctrl"
    assert "c" in key_downs, "Should press c"
    assert "ctrl" in key_ups, "Should release ctrl"
    assert "c" in key_ups, "Should release c"

    log.info("PASSED: keyboard combo")
    return True


def test_input_controller_mock():
    """Test InputController with mocked backend."""
    log = get_logger()
    log.info("Testing InputController (mocked)...")

    # Patch the imports
    with patch.dict('src.input.controller.__dict__', {
        'HAS_PYDIRECTINPUT': False,
        'HAS_PYAUTOGUI': False,
    }):
        controller = InputController()

        # Should handle missing backend gracefully
        assert controller._backend is None
        controller.move_to(100, 100)  # Should not crash
        controller.click()  # Should not crash

    log.info("PASSED: InputController (mocked)")
    return True


def test_path_endpoints():
    """Test that paths always start and end correctly."""
    log = get_logger()
    log.info("Testing path endpoints...")

    test_cases = [
        (0, 0, 100, 100),
        (50, 50, 200, 300),
        (100, 0, 0, 100),
        (500, 500, 510, 510),  # Short distance
    ]

    for start_x, start_y, end_x, end_y in test_cases:
        path = generate_path(start_x, start_y, end_x, end_y)
        assert path[-1] == (end_x, end_y), f"Path should end at ({end_x}, {end_y})"

    log.info("PASSED: path endpoints")
    return True


def test_cast_skill():
    """Test skill casting helper."""
    log = get_logger()
    log.info("Testing cast_skill...")

    controller = InputController(human_like=False)  # Disable delays

    # Mock the functions
    pressed_keys = []
    clicks = []

    controller.keyboard._press_func = lambda k: pressed_keys.append(k)
    controller.keyboard.key_delay = (0, 0)  # No delay
    controller._click = lambda button="left": clicks.append(button)
    controller.mouse._move_func = Mock()
    controller.click_delay = (0, 0)  # No delay

    # Cast skill at target
    controller.cast_skill("q", target=(100, 200))

    assert "q" in pressed_keys, "Should press skill key"
    assert "left" in clicks, "Should click at target"

    log.info("PASSED: cast_skill")
    return True


def run_all_tests():
    """Run all input tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Input Controller Tests")
    log.info("=" * 50)

    tests = [
        ("WindMouse Path Generation", test_wind_mouse_generates_path),
        ("WindMouse Path Curvature", test_wind_mouse_path_is_curved),
        ("WindMouse Parameters", test_wind_mouse_respects_parameters),
        ("MouseMover", test_mouse_mover),
        ("KeyboardController", test_keyboard_controller),
        ("Keyboard Combo", test_keyboard_combo),
        ("InputController (Mocked)", test_input_controller_mock),
        ("Path Endpoints", test_path_endpoints),
        ("Cast Skill", test_cast_skill),
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
