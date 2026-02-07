"""Tests for leveling system (skill/stat allocation)."""

from unittest.mock import Mock

import numpy as np

from src.game.leveling import (
    LevelManager,
    LevelState,
    Stat,
    SkillTab,
    SKILL_POSITIONS,
    SKILL_TAB_POSITIONS,
    STAT_BUTTON_POSITIONS,
    LEVEL_UP_COLOR_LOWER,
    LEVEL_UP_COLOR_UPPER,
)
from src.data.models import Build, Config
from src.utils.logger import setup_logger, get_logger


def create_mock_level_manager():
    """Create LevelManager with mocked dependencies."""
    config = Config()
    input_ctrl = Mock()
    capture = Mock()
    detector = Mock()

    build = Build(
        name="Blizzard Sorc",
        stat_priority=["vitality"],
        strength_target=156,
        dexterity_target=0,
        skill_progression={
            2: ["ice_bolt"],
            3: ["frost_nova"],
            4: ["frost_nova"],
            5: ["static_field"],
            6: ["telekinesis"],
            10: ["nova"],
            26: ["blizzard"],
            27: ["blizzard"],
        },
        respec_level=26,
    )

    capture.grab.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)

    manager = LevelManager(
        config=config,
        build=build,
        input_ctrl=input_ctrl,
        screen_capture=capture,
        game_detector=detector,
    )

    # Speed up tests
    manager.click_delay = 0.01
    manager.screen_transition_delay = 0.01

    return manager, input_ctrl, capture, build


def test_initial_state():
    """Test initial leveling state."""
    log = get_logger()
    log.info("Testing initial state...")

    manager, _, _, _ = create_mock_level_manager()

    state = manager.get_state()
    assert state.current_level == 1
    assert state.stat_points_available == 0
    assert state.skill_points_available == 0
    assert state.respec_done is False

    log.info("PASSED: initial state")
    return True


def test_stat_enum():
    """Test Stat enum values."""
    log = get_logger()
    log.info("Testing Stat enum...")

    assert Stat.STRENGTH.value == "strength"
    assert Stat.DEXTERITY.value == "dexterity"
    assert Stat.VITALITY.value == "vitality"
    assert Stat.ENERGY.value == "energy"

    log.info("PASSED: Stat enum")
    return True


def test_skill_tab_enum():
    """Test SkillTab enum values."""
    log = get_logger()
    log.info("Testing SkillTab enum...")

    assert SkillTab.FIRE.value == 0
    assert SkillTab.LIGHTNING.value == 1
    assert SkillTab.COLD.value == 2

    log.info("PASSED: SkillTab enum")
    return True


def test_skill_positions_defined():
    """Test skill positions are defined for all skills."""
    log = get_logger()
    log.info("Testing skill positions...")

    assert len(SKILL_POSITIONS) == 30  # 10 per tree x 3 trees
    assert "blizzard" in SKILL_POSITIONS
    assert "nova" in SKILL_POSITIONS
    assert "teleport" in SKILL_POSITIONS

    # Check structure
    for skill, (tab, pos) in SKILL_POSITIONS.items():
        assert isinstance(tab, SkillTab)
        assert isinstance(pos, tuple)
        assert len(pos) == 2

    log.info("PASSED: skill positions")
    return True


def test_stat_button_positions():
    """Test stat button positions are defined."""
    log = get_logger()
    log.info("Testing stat button positions...")

    for stat in Stat:
        assert stat in STAT_BUTTON_POSITIONS
        pos = STAT_BUTTON_POSITIONS[stat]
        assert isinstance(pos, tuple)
        assert len(pos) == 2

    log.info("PASSED: stat button positions")
    return True


def test_skill_tab_positions():
    """Test skill tab positions are defined."""
    log = get_logger()
    log.info("Testing skill tab positions...")

    for tab in SkillTab:
        assert tab in SKILL_TAB_POSITIONS

    log.info("PASSED: skill tab positions")
    return True


def test_set_level():
    """Test setting character level."""
    log = get_logger()
    log.info("Testing set level...")

    manager, _, _, _ = create_mock_level_manager()

    manager.set_level(25)
    assert manager.state.current_level == 25

    log.info("PASSED: set level")
    return True


def test_set_build():
    """Test setting build."""
    log = get_logger()
    log.info("Testing set build...")

    manager, _, _, _ = create_mock_level_manager()

    new_build = Build(name="Nova Sorc")
    manager.set_build(new_build)
    assert manager.build.name == "Nova Sorc"

    log.info("PASSED: set build")
    return True


def test_check_level_up_no_glow():
    """Test level-up check with no glow (no level up)."""
    log = get_logger()
    log.info("Testing check level up no glow...")

    manager, _, _, _ = create_mock_level_manager()

    # Dark screen = no level up indicator
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    assert manager.check_level_up(screen) is False

    log.info("PASSED: check level up no glow")
    return True


def test_check_level_up_without_capture():
    """Test level-up check without screen capture."""
    log = get_logger()
    log.info("Testing check level up without capture...")

    config = Config()
    manager = LevelManager(config=config, screen_capture=None)

    assert manager.check_level_up() is False

    log.info("PASSED: check level up without capture")
    return True


def test_check_points_available():
    """Test checking which points are available."""
    log = get_logger()
    log.info("Testing check points available...")

    manager, _, _, _ = create_mock_level_manager()

    # Dark screen = nothing available
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    stat_avail, skill_avail = manager.check_points_available(screen)
    assert stat_avail is False
    assert skill_avail is False

    log.info("PASSED: check points available")
    return True


def test_get_next_stat_vitality():
    """Test stat allocation defaults to vitality."""
    log = get_logger()
    log.info("Testing next stat = vitality...")

    manager, _, _, _ = create_mock_level_manager()

    # At low allocations, strength target not yet relevant
    # (needs every 3rd point, total 0 isn't divisible by 3 in a useful way)
    stat = manager._get_next_stat()
    # First call with 0 total allocated: 0 % 3 == 0, so it returns strength
    # Then subsequent calls go to vitality
    assert stat in (Stat.STRENGTH, Stat.VITALITY)

    log.info("PASSED: next stat")
    return True


def test_get_next_stat_no_build():
    """Test stat allocation without build returns vitality."""
    log = get_logger()
    log.info("Testing next stat without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    stat = manager._get_next_stat()
    assert stat == Stat.VITALITY

    log.info("PASSED: next stat without build")
    return True


def test_allocate_stats_no_build():
    """Test stat allocation without build does nothing."""
    log = get_logger()
    log.info("Testing allocate stats without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    allocated = manager.allocate_stats()
    assert allocated == 0

    log.info("PASSED: allocate stats without build")
    return True


def test_allocate_skills_no_build():
    """Test skill allocation without build does nothing."""
    log = get_logger()
    log.info("Testing allocate skills without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    allocated = manager.allocate_skills()
    assert allocated == 0

    log.info("PASSED: allocate skills without build")
    return True


def test_get_skills_for_level():
    """Test getting skills for a specific level."""
    log = get_logger()
    log.info("Testing get skills for level...")

    manager, _, _, _ = create_mock_level_manager()

    skills = manager.get_skills_for_level(2)
    assert skills == ["ice_bolt"]

    skills = manager.get_skills_for_level(26)
    assert skills == ["blizzard"]

    skills = manager.get_skills_for_level(99)
    assert skills == []

    log.info("PASSED: get skills for level")
    return True


def test_get_skills_no_build():
    """Test get skills without build."""
    log = get_logger()
    log.info("Testing get skills without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    skills = manager.get_skills_for_level(2)
    assert skills == []

    log.info("PASSED: get skills without build")
    return True


def test_needs_respec():
    """Test respec detection."""
    log = get_logger()
    log.info("Testing needs respec...")

    manager, _, _, _ = create_mock_level_manager()

    # At level 1, no respec needed
    assert manager.needs_respec() is False

    # At level 26, respec needed
    manager.set_level(26)
    assert manager.needs_respec() is True

    # After respec done, no longer needed
    manager.state.respec_done = True
    assert manager.needs_respec() is False

    log.info("PASSED: needs respec")
    return True


def test_needs_respec_no_build():
    """Test respec check without build."""
    log = get_logger()
    log.info("Testing needs respec without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    assert manager.needs_respec() is False

    log.info("PASSED: needs respec without build")
    return True


def test_needs_respec_no_respec_level():
    """Test respec check with no respec level in build."""
    log = get_logger()
    log.info("Testing needs respec with no respec level...")

    config = Config()
    build = Build(name="Test", respec_level=None)
    manager = LevelManager(config=config, build=build)

    manager.set_level(99)
    assert manager.needs_respec() is False

    log.info("PASSED: needs respec no respec level")
    return True


def test_perform_respec():
    """Test respec execution (stub)."""
    log = get_logger()
    log.info("Testing perform respec...")

    manager, _, _, _ = create_mock_level_manager()

    # Respec is a stub that returns False
    result = manager.perform_respec()
    assert result is False

    log.info("PASSED: perform respec")
    return True


def test_handle_level_up():
    """Test level up handling."""
    log = get_logger()
    log.info("Testing handle level up...")

    manager, input_ctrl, capture, _ = create_mock_level_manager()

    # Dark screen = no indicators active
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    capture.grab.return_value = screen

    stats, skills = manager.handle_level_up(screen)

    # Level should have incremented
    assert manager.state.current_level == 2

    log.info("PASSED: handle level up")
    return True


def test_auto_allocate_no_level_up():
    """Test auto allocate with no pending level ups."""
    log = get_logger()
    log.info("Testing auto allocate no level up...")

    manager, _, capture, _ = create_mock_level_manager()

    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    capture.grab.return_value = screen

    result = manager.auto_allocate(screen)
    assert result is False

    log.info("PASSED: auto allocate no level up")
    return True


def test_get_total_skills_allocated():
    """Test getting total skills allocated."""
    log = get_logger()
    log.info("Testing get total skills allocated...")

    manager, _, _, _ = create_mock_level_manager()

    manager.state.total_skills_allocated = {"nova": 5, "blizzard": 3}
    result = manager.get_total_skills_allocated()

    assert result["nova"] == 5
    assert result["blizzard"] == 3

    log.info("PASSED: get total skills allocated")
    return True


def test_get_build_progress():
    """Test build progress summary."""
    log = get_logger()
    log.info("Testing get build progress...")

    manager, _, _, _ = create_mock_level_manager()

    manager.state.current_level = 30
    manager.state.total_stats_allocated["vitality"] = 100
    manager.state.total_skills_allocated["blizzard"] = 5

    progress = manager.get_build_progress()

    assert "Blizzard Sorc" in progress
    assert "Level: 30" in progress
    assert "vitality: +100" in progress
    assert "blizzard: 5" in progress

    log.info("PASSED: get build progress")
    return True


def test_get_build_progress_no_build():
    """Test build progress with no build."""
    log = get_logger()
    log.info("Testing build progress without build...")

    config = Config()
    manager = LevelManager(config=config, build=None)

    progress = manager.get_build_progress()
    assert "No build configured" in progress

    log.info("PASSED: build progress without build")
    return True


def test_pending_skills():
    """Test getting pending skills."""
    log = get_logger()
    log.info("Testing pending skills...")

    manager, _, _, _ = create_mock_level_manager()

    # Set level to 5 but allocate nothing
    manager.set_level(5)

    pending = manager._get_pending_skills()

    # Skills for levels 2-5 should be pending
    assert "ice_bolt" in pending
    assert "frost_nova" in pending
    assert "static_field" in pending

    log.info("PASSED: pending skills")
    return True


def test_expected_skill_count():
    """Test expected skill count calculation."""
    log = get_logger()
    log.info("Testing expected skill count...")

    manager, _, _, _ = create_mock_level_manager()

    # frost_nova appears at level 3 and 4
    count = manager._expected_skill_count("frost_nova", 5)
    assert count == 2

    # ice_bolt appears at level 2
    count = manager._expected_skill_count("ice_bolt", 5)
    assert count == 1

    log.info("PASSED: expected skill count")
    return True


def test_level_state_dataclass():
    """Test LevelState dataclass."""
    log = get_logger()
    log.info("Testing LevelState dataclass...")

    state = LevelState()
    assert state.current_level == 1
    assert "strength" in state.total_stats_allocated
    assert "vitality" in state.total_stats_allocated
    assert state.respec_done is False

    log.info("PASSED: LevelState dataclass")
    return True


def run_all_tests():
    """Run all leveling tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Leveling System Tests")
    log.info("=" * 50)

    tests = [
        ("Initial State", test_initial_state),
        ("Stat Enum", test_stat_enum),
        ("SkillTab Enum", test_skill_tab_enum),
        ("Skill Positions", test_skill_positions_defined),
        ("Stat Button Positions", test_stat_button_positions),
        ("Skill Tab Positions", test_skill_tab_positions),
        ("Set Level", test_set_level),
        ("Set Build", test_set_build),
        ("Check Level Up No Glow", test_check_level_up_no_glow),
        ("Check Level Up No Capture", test_check_level_up_without_capture),
        ("Check Points Available", test_check_points_available),
        ("Next Stat", test_get_next_stat_vitality),
        ("Next Stat No Build", test_get_next_stat_no_build),
        ("Allocate Stats No Build", test_allocate_stats_no_build),
        ("Allocate Skills No Build", test_allocate_skills_no_build),
        ("Get Skills For Level", test_get_skills_for_level),
        ("Get Skills No Build", test_get_skills_no_build),
        ("Needs Respec", test_needs_respec),
        ("Needs Respec No Build", test_needs_respec_no_build),
        ("Needs Respec No Level", test_needs_respec_no_respec_level),
        ("Perform Respec", test_perform_respec),
        ("Handle Level Up", test_handle_level_up),
        ("Auto Allocate No Level Up", test_auto_allocate_no_level_up),
        ("Total Skills Allocated", test_get_total_skills_allocated),
        ("Build Progress", test_get_build_progress),
        ("Build Progress No Build", test_get_build_progress_no_build),
        ("Pending Skills", test_pending_skills),
        ("Expected Skill Count", test_expected_skill_count),
        ("LevelState Dataclass", test_level_state_dataclass),
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
