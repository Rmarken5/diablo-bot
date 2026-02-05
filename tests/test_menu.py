"""Tests for menu navigation."""

import time
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional, Tuple

from src.game.menu import MenuNavigator, MenuState, MENU_TEMPLATES, BUTTON_TEMPLATES
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


@dataclass
class MockMatch:
    """Mock template match result."""
    x: int
    y: int
    width: int = 100
    height: int = 50
    confidence: float = 0.9

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


def create_mock_navigator(menu_state: MenuState = MenuState.MAIN_MENU):
    """Create a MenuNavigator with mocked dependencies."""
    config = Config(character_name="TestChar")
    input_ctrl = Mock()
    matcher = Mock()
    capture = Mock()

    # Setup capture to return a dummy screen
    capture.grab.return_value = Mock()

    # Setup default state detection
    def mock_find(screen, template_name, threshold=0.8):
        # Return match for the current menu state template
        state_template = MENU_TEMPLATES.get(menu_state, "")
        if template_name == state_template:
            return MockMatch(100, 100)
        return None

    matcher.find.side_effect = mock_find

    nav = MenuNavigator(
        config=config,
        input_ctrl=input_ctrl,
        template_matcher=matcher,
        screen_capture=capture,
    )

    return nav, input_ctrl, matcher, capture


def test_detect_menu_state():
    """Test menu state detection."""
    log = get_logger()
    log.info("Testing menu state detection...")

    nav, _, matcher, _ = create_mock_navigator(MenuState.MAIN_MENU)

    state = nav.detect_menu_state()
    assert state == MenuState.MAIN_MENU

    # Change to character select
    def new_find(screen, template_name, threshold=0.8):
        if template_name == MENU_TEMPLATES.get(MenuState.CHARACTER_SELECT):
            return MockMatch(100, 100)
        return None

    matcher.find.side_effect = new_find
    state = nav.detect_menu_state()
    assert state == MenuState.CHARACTER_SELECT

    log.info("PASSED: menu state detection")
    return True


def test_detect_unknown_state():
    """Test detection when no templates match."""
    log = get_logger()
    log.info("Testing unknown state detection...")

    nav, _, matcher, _ = create_mock_navigator()

    # No templates match - override side_effect with return_value
    matcher.find.side_effect = None
    matcher.find.return_value = None
    state = nav.detect_menu_state()
    assert state == MenuState.UNKNOWN

    log.info("PASSED: unknown state detection")
    return True


def test_find_button():
    """Test button finding."""
    log = get_logger()
    log.info("Testing button finding...")

    nav, _, matcher, _ = create_mock_navigator()

    # Mock button found - override side_effect
    matcher.find.side_effect = None
    matcher.find.return_value = MockMatch(200, 300)

    pos = nav.find_button("play")
    assert pos is not None
    assert pos == (250, 325)  # center of 200,300 with 100x50 size

    # Mock button not found
    matcher.find.return_value = None
    pos = nav.find_button("play")
    assert pos is None

    log.info("PASSED: button finding")
    return True


def test_click_button():
    """Test button clicking."""
    log = get_logger()
    log.info("Testing button clicking...")

    nav, input_ctrl, matcher, _ = create_mock_navigator()

    # Button found on first try - override side_effect
    matcher.find.side_effect = None
    matcher.find.return_value = MockMatch(200, 300)
    nav.click_delay = 0.01  # Speed up test

    result = nav.click_button("play", timeout=1.0)
    assert result is True
    input_ctrl.click.assert_called_once()

    log.info("PASSED: button clicking")
    return True


def test_click_button_timeout():
    """Test button click timeout."""
    log = get_logger()
    log.info("Testing button click timeout...")

    nav, input_ctrl, matcher, _ = create_mock_navigator()

    # Button never found
    matcher.find.return_value = None

    result = nav.click_button("play", timeout=0.3)
    assert result is False
    input_ctrl.click.assert_not_called()

    log.info("PASSED: button click timeout")
    return True


def test_wait_for_state():
    """Test waiting for state transition."""
    log = get_logger()
    log.info("Testing wait for state...")

    nav, _, matcher, _ = create_mock_navigator(MenuState.MAIN_MENU)

    # Simulate state change after some time
    call_count = [0]

    def changing_find(screen, template_name, threshold=0.8):
        call_count[0] += 1
        # After 2 calls, switch to lobby
        if call_count[0] > 2:
            if template_name == MENU_TEMPLATES.get(MenuState.LOBBY):
                return MockMatch(100, 100)
        else:
            if template_name == MENU_TEMPLATES.get(MenuState.MAIN_MENU):
                return MockMatch(100, 100)
        return None

    matcher.find.side_effect = changing_find
    nav.transition_timeout = 2.0

    result = nav.wait_for_state(MenuState.LOBBY, timeout=2.0)
    assert result is True

    log.info("PASSED: wait for state")
    return True


def test_wait_for_state_timeout():
    """Test wait for state timeout."""
    log = get_logger()
    log.info("Testing wait for state timeout...")

    nav, _, matcher, _ = create_mock_navigator(MenuState.MAIN_MENU)

    # State never changes
    result = nav.wait_for_state(MenuState.LOBBY, timeout=0.5)
    assert result is False

    log.info("PASSED: wait for state timeout")
    return True


def test_select_character():
    """Test character selection."""
    log = get_logger()
    log.info("Testing character selection...")

    nav, input_ctrl, matcher, _ = create_mock_navigator(MenuState.CHARACTER_SELECT)
    nav.click_delay = 0.01

    result = nav.select_character("TestChar")
    assert result is True
    input_ctrl.double_click.assert_called_once()

    log.info("PASSED: character selection")
    return True


def test_select_character_wrong_state():
    """Test character selection from wrong state."""
    log = get_logger()
    log.info("Testing character selection from wrong state...")

    nav, input_ctrl, _, _ = create_mock_navigator(MenuState.MAIN_MENU)

    result = nav.select_character()
    assert result is False
    input_ctrl.double_click.assert_not_called()

    log.info("PASSED: character selection from wrong state")
    return True


def test_create_game():
    """Test game creation."""
    log = get_logger()
    log.info("Testing game creation...")

    nav, input_ctrl, matcher, _ = create_mock_navigator(MenuState.LOBBY)
    nav.click_delay = 0.01

    # Setup button finding and state transitions
    call_count = [0]

    def mock_find(screen, template_name, threshold=0.8):
        call_count[0] += 1
        # Return matches for buttons
        if "create_game" in template_name:
            return MockMatch(200, 200)
        if "ok" in template_name:
            return MockMatch(300, 400)
        # State detection
        if call_count[0] < 5:
            if template_name == MENU_TEMPLATES.get(MenuState.LOBBY):
                return MockMatch(100, 100)
        else:
            if template_name == MENU_TEMPLATES.get(MenuState.CREATE_GAME):
                return MockMatch(100, 100)
        return None

    matcher.find.side_effect = mock_find

    result = nav.create_game("testgame", difficulty="hell")
    assert result is True
    input_ctrl.type_text.assert_called()

    log.info("PASSED: game creation")
    return True


def test_no_capture_returns_unknown():
    """Test that missing capture returns UNKNOWN state."""
    log = get_logger()
    log.info("Testing no capture scenario...")

    nav = MenuNavigator()  # No capture/matcher
    state = nav.detect_menu_state()
    assert state == MenuState.UNKNOWN

    log.info("PASSED: no capture scenario")
    return True


def test_no_capture_button_returns_none():
    """Test that missing capture returns None for buttons."""
    log = get_logger()
    log.info("Testing no capture button scenario...")

    nav = MenuNavigator()  # No capture/matcher
    pos = nav.find_button("play")
    assert pos is None

    log.info("PASSED: no capture button scenario")
    return True


def test_exit_game():
    """Test exiting game."""
    log = get_logger()
    log.info("Testing exit game...")

    nav, input_ctrl, matcher, _ = create_mock_navigator(MenuState.IN_GAME)
    nav.click_delay = 0.01
    nav.transition_timeout = 1.0

    # Setup for successful exit
    call_count = [0]

    def mock_find(screen, template_name, threshold=0.8):
        call_count[0] += 1
        # Return match for save_exit button
        if "save_exit" in template_name:
            return MockMatch(200, 200)
        # After clicking (call_count > 5), transition to character select
        if call_count[0] > 5:
            if template_name == MENU_TEMPLATES.get(MenuState.CHARACTER_SELECT):
                return MockMatch(100, 100)
        return None

    matcher.find.side_effect = mock_find

    result = nav.exit_game()
    assert result is True
    input_ctrl.press.assert_called_with("escape")

    log.info("PASSED: exit game")
    return True


def test_templates_defined():
    """Verify all expected templates are defined."""
    log = get_logger()
    log.info("Testing template definitions...")

    # Menu templates
    expected_menus = [
        MenuState.MAIN_MENU,
        MenuState.CHARACTER_SELECT,
        MenuState.LOBBY,
        MenuState.CREATE_GAME,
        MenuState.LOADING,
    ]
    for state in expected_menus:
        assert state in MENU_TEMPLATES, f"Missing template for {state.name}"

    # Button templates
    expected_buttons = [
        "play", "single_player", "online",
        "create_game", "join_game", "ok", "cancel", "save_exit"
    ]
    for button in expected_buttons:
        assert button in BUTTON_TEMPLATES, f"Missing button template: {button}"

    log.info(f"All {len(MENU_TEMPLATES)} menu and {len(BUTTON_TEMPLATES)} button templates defined")
    log.info("PASSED: template definitions")
    return True


def run_all_tests():
    """Run all menu navigation tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Menu Navigation Tests")
    log.info("=" * 50)

    tests = [
        ("Menu State Detection", test_detect_menu_state),
        ("Unknown State Detection", test_detect_unknown_state),
        ("Button Finding", test_find_button),
        ("Button Clicking", test_click_button),
        ("Button Click Timeout", test_click_button_timeout),
        ("Wait For State", test_wait_for_state),
        ("Wait For State Timeout", test_wait_for_state_timeout),
        ("Character Selection", test_select_character),
        ("Character Selection Wrong State", test_select_character_wrong_state),
        ("Game Creation", test_create_game),
        ("No Capture Returns Unknown", test_no_capture_returns_unknown),
        ("No Capture Button Returns None", test_no_capture_button_returns_none),
        ("Exit Game", test_exit_game),
        ("Template Definitions", test_templates_defined),
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
