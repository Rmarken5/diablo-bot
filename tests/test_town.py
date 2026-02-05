"""Tests for town navigation and NPC interaction."""

from unittest.mock import Mock
from dataclasses import dataclass
from typing import Tuple

from src.game.town import (
    TownManager,
    Act,
    NPC,
    NPC_TEMPLATES,
    OBJECT_TEMPLATES,
    SCREEN_POSITIONS,
)
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


def create_mock_town_manager():
    """Create TownManager with mocked dependencies."""
    config = Config()
    input_ctrl = Mock()
    matcher = Mock()
    capture = Mock()

    # Default: no matches
    matcher.find.return_value = None
    capture.grab.return_value = Mock()

    manager = TownManager(
        config=config,
        input_ctrl=input_ctrl,
        template_matcher=matcher,
        screen_capture=capture,
    )

    # Speed up tests
    manager.move_timeout = 0.1
    manager.interact_delay = 0.01
    manager.dialog_timeout = 0.1

    return manager, input_ctrl, matcher, capture


def test_find_object_with_template():
    """Test finding object via template matching."""
    log = get_logger()
    log.info("Testing object finding with template...")

    manager, _, matcher, _ = create_mock_town_manager()

    # Object found via template
    matcher.find.return_value = MockMatch(200, 300)
    pos = manager.find_object("stash")

    assert pos is not None
    assert pos == (250, 325)

    log.info("PASSED: object finding with template")
    return True


def test_find_object_fallback():
    """Test finding object with fallback position."""
    log = get_logger()
    log.info("Testing object finding with fallback...")

    manager, _, matcher, _ = create_mock_town_manager()
    manager.current_act = Act.ACT5

    # Template not found, use fallback
    matcher.find.return_value = None
    pos = manager.find_object("stash")

    # Should use act5_stash fallback
    expected = SCREEN_POSITIONS.get("act5_stash")
    assert pos == expected

    log.info("PASSED: object finding with fallback")
    return True


def test_find_npc():
    """Test finding NPC."""
    log = get_logger()
    log.info("Testing NPC finding...")

    manager, _, matcher, _ = create_mock_town_manager()

    # NPC found via template
    matcher.find.return_value = MockMatch(400, 200)
    pos = manager.find_npc(NPC.MALAH)

    assert pos is not None
    assert pos == (450, 225)

    log.info("PASSED: NPC finding")
    return True


def test_find_npc_fallback():
    """Test finding NPC with fallback position."""
    log = get_logger()
    log.info("Testing NPC finding with fallback...")

    manager, _, matcher, _ = create_mock_town_manager()
    manager.current_act = Act.ACT5

    # Template not found
    matcher.find.return_value = None
    pos = manager.find_npc(NPC.MALAH)

    expected = SCREEN_POSITIONS.get("act5_malah")
    assert pos == expected

    log.info("PASSED: NPC finding with fallback")
    return True


def test_move_to():
    """Test movement."""
    log = get_logger()
    log.info("Testing movement...")

    manager, input_ctrl, _, _ = create_mock_town_manager()

    result = manager.move_to(500, 300)

    assert result is True
    input_ctrl.click.assert_called_once_with(500, 300)

    log.info("PASSED: movement")
    return True


def test_teleport_to():
    """Test teleport."""
    log = get_logger()
    log.info("Testing teleport...")

    manager, input_ctrl, _, _ = create_mock_town_manager()

    result = manager.teleport_to(600, 400)

    assert result is True
    input_ctrl.right_click.assert_called_once_with(600, 400)

    log.info("PASSED: teleport")
    return True


def test_go_to_npc():
    """Test going to NPC."""
    log = get_logger()
    log.info("Testing go to NPC...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()

    # NPC found
    matcher.find.return_value = MockMatch(400, 200)
    result = manager.go_to_npc(NPC.MALAH, use_teleport=True)

    assert result is True
    input_ctrl.right_click.assert_called()

    log.info("PASSED: go to NPC")
    return True


def test_go_to_npc_not_found():
    """Test going to NPC that can't be found."""
    log = get_logger()
    log.info("Testing go to NPC not found...")

    manager, _, matcher, _ = create_mock_town_manager()

    # No NPC found, no fallback
    matcher.find.return_value = None
    # Clear fallback positions for this test
    original = SCREEN_POSITIONS.copy()
    SCREEN_POSITIONS.clear()

    try:
        result = manager.go_to_npc(NPC.AKARA)  # Act 1 NPC, no fallback
        assert result is False
    finally:
        SCREEN_POSITIONS.update(original)

    log.info("PASSED: go to NPC not found")
    return True


def test_interact_with_npc():
    """Test NPC interaction."""
    log = get_logger()
    log.info("Testing NPC interaction...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()

    matcher.find.return_value = MockMatch(400, 200)
    result = manager.interact_with_npc(NPC.MALAH)

    assert result is True
    input_ctrl.click.assert_called()

    log.info("PASSED: NPC interaction")
    return True


def test_open_stash():
    """Test opening stash."""
    log = get_logger()
    log.info("Testing open stash...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()

    matcher.find.return_value = MockMatch(100, 200)
    result = manager.open_stash()

    assert result is True
    input_ctrl.click.assert_called()

    log.info("PASSED: open stash")
    return True


def test_close_stash():
    """Test closing stash."""
    log = get_logger()
    log.info("Testing close stash...")

    manager, input_ctrl, _, _ = create_mock_town_manager()

    manager.close_stash()
    input_ctrl.press.assert_called_with("escape")

    log.info("PASSED: close stash")
    return True


def test_use_waypoint():
    """Test using waypoint."""
    log = get_logger()
    log.info("Testing waypoint usage...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()

    matcher.find.return_value = MockMatch(50, 100)
    result = manager.use_waypoint()

    assert result is True
    input_ctrl.click.assert_called()

    log.info("PASSED: waypoint usage")
    return True


def test_go_to_red_portal():
    """Test going to red portal."""
    log = get_logger()
    log.info("Testing go to red portal...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()
    manager.current_act = Act.ACT5

    # Red portal found
    matcher.find.return_value = MockMatch(50, 500)
    result = manager.go_to_red_portal()

    assert result is True
    input_ctrl.right_click.assert_called()

    log.info("PASSED: go to red portal")
    return True


def test_enter_red_portal():
    """Test entering red portal."""
    log = get_logger()
    log.info("Testing enter red portal...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()

    matcher.find.return_value = MockMatch(50, 500)
    result = manager.enter_red_portal()

    assert result is True
    input_ctrl.click.assert_called()

    log.info("PASSED: enter red portal")
    return True


def test_set_act():
    """Test setting current act."""
    log = get_logger()
    log.info("Testing set act...")

    manager, _, _, _ = create_mock_town_manager()

    manager.set_act(Act.ACT3)
    assert manager.current_act == Act.ACT3

    manager.set_act(Act.ACT1)
    assert manager.current_act == Act.ACT1

    log.info("PASSED: set act")
    return True


def test_go_to_healer():
    """Test going to healer for current act."""
    log = get_logger()
    log.info("Testing go to healer...")

    manager, input_ctrl, matcher, _ = create_mock_town_manager()
    manager.current_act = Act.ACT5

    matcher.find.return_value = MockMatch(400, 100)
    result = manager.go_to_healer()

    assert result is True
    # Should have gone to Malah in Act 5
    input_ctrl.right_click.assert_called()

    log.info("PASSED: go to healer")
    return True


def test_close_dialog():
    """Test closing dialog."""
    log = get_logger()
    log.info("Testing close dialog...")

    manager, input_ctrl, _, _ = create_mock_town_manager()

    manager.close_dialog()
    input_ctrl.press.assert_called_with("escape")

    log.info("PASSED: close dialog")
    return True


def test_npc_templates_defined():
    """Verify NPC templates are defined."""
    log = get_logger()
    log.info("Testing NPC template definitions...")

    # Check Act 5 NPCs have templates
    act5_npcs = [NPC.MALAH, NPC.LARZUK, NPC.QUAL_KEHK, NPC.ANYA, NPC.CAIN]
    for npc in act5_npcs:
        assert npc in NPC_TEMPLATES, f"Missing template for {npc.value}"

    log.info(f"Verified {len(NPC_TEMPLATES)} NPC templates")
    log.info("PASSED: NPC template definitions")
    return True


def test_object_templates_defined():
    """Verify object templates are defined."""
    log = get_logger()
    log.info("Testing object template definitions...")

    expected_objects = ["stash", "waypoint", "portal", "red_portal"]
    for obj in expected_objects:
        assert obj in OBJECT_TEMPLATES, f"Missing template for {obj}"

    log.info(f"Verified {len(OBJECT_TEMPLATES)} object templates")
    log.info("PASSED: object template definitions")
    return True


def test_screen_positions_defined():
    """Verify fallback screen positions are defined."""
    log = get_logger()
    log.info("Testing fallback positions...")

    # Check Act 5 positions exist
    expected_positions = [
        "act5_stash", "act5_waypoint", "act5_malah",
        "act5_larzuk", "act5_anya", "act5_red_portal"
    ]
    for pos in expected_positions:
        assert pos in SCREEN_POSITIONS, f"Missing fallback position: {pos}"

    log.info(f"Verified {len(expected_positions)} fallback positions")
    log.info("PASSED: fallback positions")
    return True


def run_all_tests():
    """Run all town navigation tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Town Navigation Tests")
    log.info("=" * 50)

    tests = [
        ("Find Object With Template", test_find_object_with_template),
        ("Find Object Fallback", test_find_object_fallback),
        ("Find NPC", test_find_npc),
        ("Find NPC Fallback", test_find_npc_fallback),
        ("Move To", test_move_to),
        ("Teleport To", test_teleport_to),
        ("Go To NPC", test_go_to_npc),
        ("Go To NPC Not Found", test_go_to_npc_not_found),
        ("Interact With NPC", test_interact_with_npc),
        ("Open Stash", test_open_stash),
        ("Close Stash", test_close_stash),
        ("Use Waypoint", test_use_waypoint),
        ("Go To Red Portal", test_go_to_red_portal),
        ("Enter Red Portal", test_enter_red_portal),
        ("Set Act", test_set_act),
        ("Go To Healer", test_go_to_healer),
        ("Close Dialog", test_close_dialog),
        ("NPC Template Definitions", test_npc_templates_defined),
        ("Object Template Definitions", test_object_templates_defined),
        ("Fallback Positions", test_screen_positions_defined),
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
