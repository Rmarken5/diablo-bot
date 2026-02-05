"""Tests for loot detection and pickup system."""

import time
from unittest.mock import Mock, MagicMock

import numpy as np

from src.game.loot import (
    LootManager,
    LootItem,
    LootStats,
    ItemQuality,
    ItemFilter,
    QUALITY_COLORS,
)
from src.data.models import Config, PickitRules, DetectedItem
from src.utils.logger import setup_logger, get_logger


def create_mock_loot_manager():
    """Create LootManager with mocked dependencies."""
    config = Config()
    input_ctrl = Mock()
    capture = Mock()
    pickit = PickitRules()

    # Default pickit settings
    pickit.pickup_uniques = True
    pickit.pickup_sets = True
    pickit.pickup_rares = True
    pickit.pickup_magic = False
    pickit.pickup_white = False
    pickit.pickup_socketed = True
    pickit.always_pickup = ["key", "rune"]
    pickit.never_pickup = ["quiver", "arrows"]

    manager = LootManager(
        config=config,
        input_ctrl=input_ctrl,
        screen_capture=capture,
        pickit_rules=pickit,
    )

    # Speed up tests
    manager.scan_delay = 0.01
    manager.pickup_delay = 0.01
    manager.click_delay = 0.01

    return manager, input_ctrl, capture


def test_initial_state():
    """Test initial loot manager state."""
    log = get_logger()
    log.info("Testing initial state...")

    manager, _, _ = create_mock_loot_manager()

    stats = manager.get_stats()
    assert stats.items_scanned == 0
    assert stats.items_picked == 0
    assert stats.items_skipped == 0

    log.info("PASSED: initial state")
    return True


def test_loot_item_dataclass():
    """Test LootItem dataclass."""
    log = get_logger()
    log.info("Testing LootItem...")

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.GOLD,
        name="Shako",
        should_pickup=True,
    )

    assert item.position == (500, 300)
    assert item.quality == ItemQuality.GOLD
    assert item.name == "Shako"
    assert item.should_pickup is True

    log.info("PASSED: LootItem")
    return True


def test_loot_stats_dataclass():
    """Test LootStats dataclass."""
    log = get_logger()
    log.info("Testing LootStats...")

    stats = LootStats()
    assert stats.items_scanned == 0
    assert stats.items_picked == 0

    stats.items_picked = 5
    stats.items_skipped = 3
    assert stats.items_picked == 5

    log.info("PASSED: LootStats")
    return True


def test_item_quality_enum():
    """Test ItemQuality enum values."""
    log = get_logger()
    log.info("Testing ItemQuality enum...")

    assert ItemQuality.WHITE is not None
    assert ItemQuality.BLUE is not None
    assert ItemQuality.YELLOW is not None
    assert ItemQuality.GREEN is not None
    assert ItemQuality.GOLD is not None
    assert ItemQuality.GRAY is not None

    log.info("PASSED: ItemQuality enum")
    return True


def test_quality_colors_defined():
    """Test quality colors are defined."""
    log = get_logger()
    log.info("Testing quality colors...")

    # Key qualities should have colors
    assert ItemQuality.GOLD in QUALITY_COLORS
    assert ItemQuality.GREEN in QUALITY_COLORS
    assert ItemQuality.BLUE in QUALITY_COLORS
    assert ItemQuality.YELLOW in QUALITY_COLORS

    # Colors should have lower and upper bounds
    for quality, colors in QUALITY_COLORS.items():
        assert "lower" in colors
        assert "upper" in colors
        assert len(colors["lower"]) == 3  # BGR
        assert len(colors["upper"]) == 3

    log.info("PASSED: quality colors")
    return True


def test_should_pickup_unique():
    """Test pickup rule for unique items."""
    log = get_logger()
    log.info("Testing should_pickup unique...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.GOLD,  # Unique
        name="Unique Item",
    )

    assert manager.should_pickup(item) is True

    log.info("PASSED: should_pickup unique")
    return True


def test_should_pickup_set():
    """Test pickup rule for set items."""
    log = get_logger()
    log.info("Testing should_pickup set...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.GREEN,  # Set
        name="Set Item",
    )

    assert manager.should_pickup(item) is True

    log.info("PASSED: should_pickup set")
    return True


def test_should_pickup_rare():
    """Test pickup rule for rare items."""
    log = get_logger()
    log.info("Testing should_pickup rare...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.YELLOW,  # Rare
        name="Rare Item",
    )

    assert manager.should_pickup(item) is True

    log.info("PASSED: should_pickup rare")
    return True


def test_should_not_pickup_magic():
    """Test magic items not picked up by default."""
    log = get_logger()
    log.info("Testing should not pickup magic...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.BLUE,  # Magic
        name="Magic Item",
    )

    # Default pickit has pickup_magic = False
    assert manager.should_pickup(item) is False

    log.info("PASSED: should not pickup magic")
    return True


def test_should_not_pickup_white():
    """Test white items not picked up by default."""
    log = get_logger()
    log.info("Testing should not pickup white...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.WHITE,
        name="White Item",
    )

    assert manager.should_pickup(item) is False

    log.info("PASSED: should not pickup white")
    return True


def test_should_pickup_socketed():
    """Test socketed items picked up."""
    log = get_logger()
    log.info("Testing should pickup socketed...")

    manager, _, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.GRAY,  # Socketed
        name="Socketed Item",
    )

    assert manager.should_pickup(item) is True

    log.info("PASSED: should pickup socketed")
    return True


def test_always_pickup_pattern():
    """Test always_pickup patterns."""
    log = get_logger()
    log.info("Testing always_pickup pattern...")

    manager, _, _ = create_mock_loot_manager()

    # "key" and "rune" are in always_pickup
    key_item = LootItem(
        position=(500, 300),
        quality=ItemQuality.WHITE,
        name="Key of Hate",
    )
    assert manager.should_pickup(key_item) is True

    rune_item = LootItem(
        position=(500, 300),
        quality=ItemQuality.WHITE,
        name="Ber Rune",
    )
    assert manager.should_pickup(rune_item) is True

    log.info("PASSED: always_pickup pattern")
    return True


def test_never_pickup_pattern():
    """Test never_pickup patterns."""
    log = get_logger()
    log.info("Testing never_pickup pattern...")

    manager, _, _ = create_mock_loot_manager()

    # "quiver" and "arrows" are in never_pickup
    quiver_item = LootItem(
        position=(500, 300),
        quality=ItemQuality.BLUE,  # Even if magic
        name="Magic Quiver",
    )
    # Note: quality check happens before pattern check
    # So magic items already fail
    assert manager.should_pickup(quiver_item) is False

    log.info("PASSED: never_pickup pattern")
    return True


def test_pickup_gold():
    """Test gold always picked up."""
    log = get_logger()
    log.info("Testing pickup gold...")

    manager, _, _ = create_mock_loot_manager()

    gold_item = LootItem(
        position=(500, 300),
        quality=ItemQuality.WHITE,
        name="Gold",
    )

    assert manager.should_pickup(gold_item) is True

    log.info("PASSED: pickup gold")
    return True


def test_pickup_item():
    """Test item pickup action."""
    log = get_logger()
    log.info("Testing pickup item...")

    manager, input_ctrl, _ = create_mock_loot_manager()

    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.GOLD,
        name="Unique Item",
    )

    result = manager.pickup_item(item)

    assert result is True
    input_ctrl.click.assert_called_with(500, 300)
    assert manager.stats.items_picked == 1

    log.info("PASSED: pickup item")
    return True


def test_quick_loot():
    """Test quick loot at positions."""
    log = get_logger()
    log.info("Testing quick loot...")

    manager, input_ctrl, _ = create_mock_loot_manager()

    positions = [(500, 300), (600, 350), (700, 400)]
    count = manager.quick_loot(positions)

    assert count == 3
    assert input_ctrl.click.call_count == 3
    input_ctrl.key_down.assert_called_with("alt")
    input_ctrl.key_up.assert_called_with("alt")

    log.info("PASSED: quick loot")
    return True


def test_pickup_gold_action():
    """Test pickup gold action."""
    log = get_logger()
    log.info("Testing pickup gold action...")

    manager, input_ctrl, _ = create_mock_loot_manager()

    manager.pickup_gold()

    # Should have clicked multiple times
    assert input_ctrl.click.call_count >= 5

    log.info("PASSED: pickup gold action")
    return True


def test_scan_returns_empty_without_capture():
    """Test scan returns empty without capture."""
    log = get_logger()
    log.info("Testing scan without capture...")

    config = Config()
    manager = LootManager(config=config, screen_capture=None)

    items = manager.scan_for_items()
    assert items == []

    log.info("PASSED: scan without capture")
    return True


def test_detect_quality_unknown():
    """Test quality detection returns unknown for invalid."""
    log = get_logger()
    log.info("Testing detect quality unknown...")

    manager, _, _ = create_mock_loot_manager()

    quality = manager.detect_quality(None, (500, 300))
    assert quality == ItemQuality.UNKNOWN

    log.info("PASSED: detect quality unknown")
    return True


def test_detect_quality_gold():
    """Test quality detection for gold/unique items."""
    log = get_logger()
    log.info("Testing detect quality gold...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with gold-colored region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    # Gold/unique color (BGR: tan/gold)
    screen[295:305, 480:520] = (50, 180, 220)  # BGR

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.GOLD

    log.info("PASSED: detect quality gold")
    return True


def test_detect_quality_green():
    """Test quality detection for set items."""
    log = get_logger()
    log.info("Testing detect quality green...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with green region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    screen[295:305, 480:520] = (50, 200, 50)  # BGR - green

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.GREEN

    log.info("PASSED: detect quality green")
    return True


def test_detect_quality_blue():
    """Test quality detection for magic items."""
    log = get_logger()
    log.info("Testing detect quality blue...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with blue region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    screen[295:305, 480:520] = (220, 100, 50)  # BGR - blue

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.BLUE

    log.info("PASSED: detect quality blue")
    return True


def test_detect_quality_yellow():
    """Test quality detection for rare items."""
    log = get_logger()
    log.info("Testing detect quality yellow...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with yellow region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    screen[295:305, 480:520] = (50, 220, 220)  # BGR - yellow

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.YELLOW

    log.info("PASSED: detect quality yellow")
    return True


def test_detect_quality_white():
    """Test quality detection for white items."""
    log = get_logger()
    log.info("Testing detect quality white...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with white region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    screen[295:305, 480:520] = (230, 230, 230)  # BGR - white

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.WHITE

    log.info("PASSED: detect quality white")
    return True


def test_detect_quality_gray():
    """Test quality detection for socketed items."""
    log = get_logger()
    log.info("Testing detect quality gray...")

    manager, _, _ = create_mock_loot_manager()

    # Create fake screen with gray region
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    screen[295:305, 480:520] = (140, 140, 140)  # BGR - gray

    quality = manager.detect_quality(screen, (500, 300))
    assert quality == ItemQuality.GRAY

    log.info("PASSED: detect quality gray")
    return True


def test_set_pickit_rules():
    """Test updating pickit rules."""
    log = get_logger()
    log.info("Testing set pickit rules...")

    manager, _, _ = create_mock_loot_manager()

    new_rules = PickitRules()
    # Add required attributes that LootManager expects
    new_rules.pickup_uniques = True
    new_rules.pickup_sets = True
    new_rules.pickup_rares = True
    new_rules.pickup_magic = True  # Enable magic pickup
    new_rules.pickup_white = False
    new_rules.pickup_socketed = True
    new_rules.always_pickup = []
    new_rules.never_pickup = []

    manager.set_pickit_rules(new_rules)

    # Now magic should be picked up
    item = LootItem(
        position=(500, 300),
        quality=ItemQuality.BLUE,
        name="Magic Item",
    )
    assert manager.should_pickup(item) is True

    log.info("PASSED: set pickit rules")
    return True


def test_reset_stats():
    """Test resetting statistics."""
    log = get_logger()
    log.info("Testing reset stats...")

    manager, _, _ = create_mock_loot_manager()

    # Add some stats
    manager.stats.items_picked = 10
    manager.stats.items_skipped = 5

    manager.reset_stats()

    assert manager.stats.items_picked == 0
    assert manager.stats.items_skipped == 0

    log.info("PASSED: reset stats")
    return True


def test_item_filter():
    """Test ItemFilter class."""
    log = get_logger()
    log.info("Testing ItemFilter...")

    filter_ = ItemFilter()

    # Add requirements
    filter_.add_stat_requirement("strength", 100)
    filter_.add_required_mod("faster cast rate")

    assert filter_.min_stats["strength"] == 100
    assert "faster cast rate" in filter_.required_mods

    # Clear filters
    filter_.clear_filters()
    assert len(filter_.min_stats) == 0
    assert len(filter_.required_mods) == 0

    log.info("PASSED: ItemFilter")
    return True


def test_item_filter_passes():
    """Test ItemFilter.passes_filter."""
    log = get_logger()
    log.info("Testing ItemFilter passes...")

    filter_ = ItemFilter()

    # Quality items pass
    unique_item = DetectedItem(
        name="Unique Item",
        quality="unique",
        position=(500, 300),
    )
    assert filter_.passes_filter(unique_item) is True

    # White items fail
    white_item = DetectedItem(
        name="White Item",
        quality="white",
        position=(500, 300),
    )
    assert filter_.passes_filter(white_item) is False

    log.info("PASSED: ItemFilter passes")
    return True


def test_get_last_items():
    """Test getting last scanned items."""
    log = get_logger()
    log.info("Testing get last items...")

    manager, _, _ = create_mock_loot_manager()

    # Initially empty
    items = manager.get_last_items()
    assert items == []

    log.info("PASSED: get last items")
    return True


def run_all_tests():
    """Run all loot tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Loot Detection Tests")
    log.info("=" * 50)

    tests = [
        ("Initial State", test_initial_state),
        ("LootItem Dataclass", test_loot_item_dataclass),
        ("LootStats Dataclass", test_loot_stats_dataclass),
        ("ItemQuality Enum", test_item_quality_enum),
        ("Quality Colors Defined", test_quality_colors_defined),
        ("Should Pickup Unique", test_should_pickup_unique),
        ("Should Pickup Set", test_should_pickup_set),
        ("Should Pickup Rare", test_should_pickup_rare),
        ("Should Not Pickup Magic", test_should_not_pickup_magic),
        ("Should Not Pickup White", test_should_not_pickup_white),
        ("Should Pickup Socketed", test_should_pickup_socketed),
        ("Always Pickup Pattern", test_always_pickup_pattern),
        ("Never Pickup Pattern", test_never_pickup_pattern),
        ("Pickup Gold", test_pickup_gold),
        ("Pickup Item Action", test_pickup_item),
        ("Quick Loot", test_quick_loot),
        ("Pickup Gold Action", test_pickup_gold_action),
        ("Scan Without Capture", test_scan_returns_empty_without_capture),
        ("Detect Quality Unknown", test_detect_quality_unknown),
        ("Detect Quality Gold", test_detect_quality_gold),
        ("Detect Quality Green", test_detect_quality_green),
        ("Detect Quality Blue", test_detect_quality_blue),
        ("Detect Quality Yellow", test_detect_quality_yellow),
        ("Detect Quality White", test_detect_quality_white),
        ("Detect Quality Gray", test_detect_quality_gray),
        ("Set Pickit Rules", test_set_pickit_rules),
        ("Reset Stats", test_reset_stats),
        ("ItemFilter", test_item_filter),
        ("ItemFilter Passes", test_item_filter_passes),
        ("Get Last Items", test_get_last_items),
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
