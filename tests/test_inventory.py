"""Tests for inventory and stash management."""

from unittest.mock import Mock

import numpy as np

from src.game.inventory import (
    InventoryManager,
    InventoryState,
    StashTab,
    BeltSlot,
    InventorySlot,
)
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


def create_mock_inventory_manager():
    """Create InventoryManager with mocked dependencies."""
    config = Config()
    input_ctrl = Mock()
    capture = Mock()
    matcher = Mock()

    capture.grab.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)

    manager = InventoryManager(
        config=config,
        input_ctrl=input_ctrl,
        screen_capture=capture,
        template_matcher=matcher,
    )

    # Speed up tests
    manager.click_delay = 0.01
    manager.transfer_delay = 0.01

    return manager, input_ctrl, capture


def test_initial_state():
    """Test initial inventory state."""
    log = get_logger()
    log.info("Testing initial state...")

    manager, _, _ = create_mock_inventory_manager()

    assert manager.state.total_slots == 40
    assert manager.state.free_slots == 40
    assert manager.state.occupied_slots == 0
    assert manager.state.is_open is False

    log.info("PASSED: initial state")
    return True


def test_grid_initialization():
    """Test inventory grid is created correctly."""
    log = get_logger()
    log.info("Testing grid initialization...")

    manager, _, _ = create_mock_inventory_manager()

    # Should be 4 rows x 10 cols
    assert len(manager._grid) == 4
    assert len(manager._grid[0]) == 10

    # Check first slot position
    slot = manager._grid[0][0]
    assert slot.row == 0
    assert slot.col == 0
    assert slot.occupied is False

    log.info("PASSED: grid initialization")
    return True


def test_get_slot_position():
    """Test getting slot screen positions."""
    log = get_logger()
    log.info("Testing get slot position...")

    manager, _, _ = create_mock_inventory_manager()

    # Valid slot
    pos = manager.get_slot_position(0, 0)
    assert pos != (0, 0)

    # Out of bounds
    pos = manager.get_slot_position(10, 10)
    assert pos == (0, 0)

    log.info("PASSED: get slot position")
    return True


def test_scan_inventory_empty():
    """Test scanning an empty (dark) inventory."""
    log = get_logger()
    log.info("Testing scan empty inventory...")

    manager, _, capture = create_mock_inventory_manager()

    # All black screen = empty inventory
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    capture.grab.return_value = screen

    state = manager.scan_inventory(screen)

    assert state.free_slots == 40
    assert state.occupied_slots == 0

    log.info("PASSED: scan empty inventory")
    return True


def test_scan_inventory_full():
    """Test scanning a full (bright) inventory."""
    log = get_logger()
    log.info("Testing scan full inventory...")

    manager, _, _ = create_mock_inventory_manager()

    # Bright screen = all slots occupied
    screen = np.full((1080, 1920, 3), 200, dtype=np.uint8)
    state = manager.scan_inventory(screen)

    assert state.occupied_slots == 40
    assert state.free_slots == 0

    log.info("PASSED: scan full inventory")
    return True


def test_is_full():
    """Test inventory full detection."""
    log = get_logger()
    log.info("Testing is_full...")

    manager, _, _ = create_mock_inventory_manager()

    # Bright screen = full
    screen = np.full((1080, 1920, 3), 200, dtype=np.uint8)
    assert manager.is_full(screen) is True

    # Dark screen = empty
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    assert manager.is_full(screen) is False

    log.info("PASSED: is_full")
    return True


def test_get_free_space():
    """Test free space calculation."""
    log = get_logger()
    log.info("Testing get free space...")

    manager, _, _ = create_mock_inventory_manager()

    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    free = manager.get_free_space(screen)
    assert free == 40

    log.info("PASSED: get free space")
    return True


def test_open_close_inventory():
    """Test opening and closing inventory."""
    log = get_logger()
    log.info("Testing open/close inventory...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    manager.open_inventory()
    assert manager.state.is_open is True
    input_ctrl.press.assert_called_with("i")

    manager.close_inventory()
    assert manager.state.is_open is False
    input_ctrl.press.assert_called_with("escape")

    log.info("PASSED: open/close inventory")
    return True


def test_click_slot():
    """Test clicking an inventory slot."""
    log = get_logger()
    log.info("Testing click slot...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    manager.click_slot(0, 0)
    input_ctrl.click.assert_called()

    log.info("PASSED: click slot")
    return True


def test_ctrl_click_slot():
    """Test ctrl+clicking a slot for transfer."""
    log = get_logger()
    log.info("Testing ctrl+click slot...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    manager.ctrl_click_slot(1, 2)

    input_ctrl.key_down.assert_called_with("ctrl")
    input_ctrl.click.assert_called()
    input_ctrl.key_up.assert_called_with("ctrl")

    log.info("PASSED: ctrl+click slot")
    return True


def test_stash_all_items():
    """Test stashing all items."""
    log = get_logger()
    log.info("Testing stash all items...")

    manager, input_ctrl, capture = create_mock_inventory_manager()

    # Make a few slots bright (occupied)
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Brighten one slot region
    for row in range(manager.ROWS):
        for col in range(manager.COLS):
            slot = manager._grid[row][col]
            x, y = slot.screen_pos
            half = manager.SLOT_WIDTH // 2 - 2
            if row == 0 and col < 3:
                screen[y - half:y + half, x - half:x + half] = 200

    capture.grab.return_value = screen

    transferred = manager.stash_all_items()
    assert transferred == 3

    log.info("PASSED: stash all items")
    return True


def test_select_stash_tab():
    """Test selecting a stash tab."""
    log = get_logger()
    log.info("Testing select stash tab...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    manager.select_stash_tab(StashTab.SHARED_1)
    pos = manager.STASH_TAB_POSITIONS[StashTab.SHARED_1]
    input_ctrl.click.assert_called_with(pos[0], pos[1])

    log.info("PASSED: select stash tab")
    return True


def test_stash_tab_enum():
    """Test StashTab enum has expected members."""
    log = get_logger()
    log.info("Testing StashTab enum...")

    assert StashTab.PERSONAL_1.value == 0
    assert StashTab.SHARED_3.value == 5
    assert len(StashTab) == 6

    log.info("PASSED: StashTab enum")
    return True


def test_get_belt_slot_position():
    """Test belt slot position calculation."""
    log = get_logger()
    log.info("Testing belt slot position...")

    manager, _, _ = create_mock_inventory_manager()

    pos = manager.get_belt_slot_position(0, 0)
    assert pos != (0, 0)
    assert isinstance(pos, tuple)
    assert len(pos) == 2

    log.info("PASSED: belt slot position")
    return True


def test_scan_belt_without_capture():
    """Test belt scan without screen capture returns defaults."""
    log = get_logger()
    log.info("Testing scan belt without capture...")

    config = Config()
    manager = InventoryManager(config=config, screen_capture=None)

    belt = manager.scan_belt()
    # Should return all True (assume full)
    assert all(belt.values())

    log.info("PASSED: scan belt without capture")
    return True


def test_buy_potions():
    """Test buying potions."""
    log = get_logger()
    log.info("Testing buy potions...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    bought = manager.buy_potions("health", 4)
    assert bought == 4
    assert input_ctrl.right_click.call_count == 4

    log.info("PASSED: buy potions")
    return True


def test_buy_potions_invalid_type():
    """Test buying invalid potion type."""
    log = get_logger()
    log.info("Testing buy invalid potion type...")

    manager, _, _ = create_mock_inventory_manager()

    bought = manager.buy_potions("unknown", 4)
    assert bought == 0

    log.info("PASSED: buy invalid potion type")
    return True


def test_buy_and_fill_potions():
    """Test buy and fill potions."""
    log = get_logger()
    log.info("Testing buy and fill potions...")

    manager, input_ctrl, _ = create_mock_inventory_manager()

    total = manager.buy_and_fill_potions()
    assert total == 16  # 8 health + 8 mana

    log.info("PASSED: buy and fill potions")
    return True


def test_get_stash_slot_position():
    """Test stash slot position calculation."""
    log = get_logger()
    log.info("Testing stash slot position...")

    manager, _, _ = create_mock_inventory_manager()

    pos = manager.get_stash_slot_position(0, 0)
    expected_x = manager.STASH_TOP_LEFT[0] + manager.SLOT_WIDTH // 2
    expected_y = manager.STASH_TOP_LEFT[1] + manager.SLOT_HEIGHT // 2
    assert pos == (expected_x, expected_y)

    log.info("PASSED: stash slot position")
    return True


def test_is_potion_slot_health():
    """Test health potion detection."""
    log = get_logger()
    log.info("Testing health potion detection...")

    manager, _, _ = create_mock_inventory_manager()

    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Red potion in BGR
    screen[490:510, 490:510] = (30, 30, 200)

    assert manager._is_potion_slot(screen, (500, 500)) is True

    log.info("PASSED: health potion detection")
    return True


def test_is_potion_slot_mana():
    """Test mana potion detection."""
    log = get_logger()
    log.info("Testing mana potion detection...")

    manager, _, _ = create_mock_inventory_manager()

    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Blue potion in BGR
    screen[490:510, 490:510] = (200, 30, 30)

    assert manager._is_potion_slot(screen, (500, 500)) is True

    log.info("PASSED: mana potion detection")
    return True


def test_is_potion_slot_empty():
    """Test empty slot is not detected as potion."""
    log = get_logger()
    log.info("Testing empty slot detection...")

    manager, _, _ = create_mock_inventory_manager()

    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    assert manager._is_potion_slot(screen, (500, 500)) is False

    log.info("PASSED: empty slot detection")
    return True


def test_full_inventory_routine():
    """Test full inventory routine."""
    log = get_logger()
    log.info("Testing full inventory routine...")

    manager, input_ctrl, capture = create_mock_inventory_manager()

    # Dark screen = empty inventory
    capture.grab.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)

    town = Mock()
    town.open_stash.return_value = True

    result = manager.full_inventory_routine(town)

    assert result is True
    town.open_stash.assert_called_once()
    town.close_stash.assert_called_once()

    log.info("PASSED: full inventory routine")
    return True


def test_inventory_state_dataclass():
    """Test InventoryState dataclass."""
    log = get_logger()
    log.info("Testing InventoryState dataclass...")

    state = InventoryState()
    assert state.total_slots == 40
    assert state.free_slots == 40
    assert state.occupied_slots == 0
    assert state.is_open is False

    state.free_slots = 10
    state.occupied_slots = 30
    assert state.free_slots == 10

    log.info("PASSED: InventoryState dataclass")
    return True


def run_all_tests():
    """Run all inventory tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Inventory Management Tests")
    log.info("=" * 50)

    tests = [
        ("Initial State", test_initial_state),
        ("Grid Initialization", test_grid_initialization),
        ("Get Slot Position", test_get_slot_position),
        ("Scan Empty Inventory", test_scan_inventory_empty),
        ("Scan Full Inventory", test_scan_inventory_full),
        ("Is Full", test_is_full),
        ("Get Free Space", test_get_free_space),
        ("Open/Close Inventory", test_open_close_inventory),
        ("Click Slot", test_click_slot),
        ("Ctrl+Click Slot", test_ctrl_click_slot),
        ("Stash All Items", test_stash_all_items),
        ("Select Stash Tab", test_select_stash_tab),
        ("StashTab Enum", test_stash_tab_enum),
        ("Belt Slot Position", test_get_belt_slot_position),
        ("Scan Belt Without Capture", test_scan_belt_without_capture),
        ("Buy Potions", test_buy_potions),
        ("Buy Invalid Potion Type", test_buy_potions_invalid_type),
        ("Buy And Fill Potions", test_buy_and_fill_potions),
        ("Stash Slot Position", test_get_stash_slot_position),
        ("Health Potion Detection", test_is_potion_slot_health),
        ("Mana Potion Detection", test_is_potion_slot_mana),
        ("Empty Slot Detection", test_is_potion_slot_empty),
        ("Full Inventory Routine", test_full_inventory_routine),
        ("InventoryState Dataclass", test_inventory_state_dataclass),
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
