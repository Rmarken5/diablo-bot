"""Tests for Sorceress combat system."""

import time
from unittest.mock import Mock, call

from src.game.combat import (
    SorceressCombat,
    Skill,
    SkillInfo,
    CombatState,
    DEFAULT_SKILL_INFO,
)
from src.data.models import Config
from src.utils.logger import setup_logger, get_logger


def create_mock_combat():
    """Create SorceressCombat with mocked input."""
    config = Config()
    # Set up hotkeys
    config.hotkeys = {
        "teleport": "f3",
        "blizzard": "f4",
        "static_field": "f5",
        "frozen_armor": "f6",
        "glacial_spike": "f7",
    }

    input_ctrl = Mock()
    combat = SorceressCombat(config=config, input_ctrl=input_ctrl)

    # Speed up tests
    combat.cast_delay = 0.01
    combat.teleport_delay = 0.01

    return combat, input_ctrl


def test_skill_setup():
    """Test that skills are set up from config."""
    log = get_logger()
    log.info("Testing skill setup...")

    combat, _ = create_mock_combat()

    # Check skills were configured
    assert Skill.TELEPORT in combat.skills
    assert Skill.BLIZZARD in combat.skills
    assert Skill.STATIC_FIELD in combat.skills
    assert Skill.FROZEN_ARMOR in combat.skills

    # Check hotkeys
    assert combat.skills[Skill.TELEPORT].hotkey == "f3"
    assert combat.skills[Skill.BLIZZARD].hotkey == "f4"

    log.info("PASSED: skill setup")
    return True


def test_can_cast_no_cooldown():
    """Test can_cast for skills without cooldown."""
    log = get_logger()
    log.info("Testing can_cast (no cooldown)...")

    combat, _ = create_mock_combat()

    # Teleport has no cooldown
    assert combat.can_cast(Skill.TELEPORT) is True

    # Cast it
    combat._record_cast(Skill.TELEPORT)

    # Should still be castable immediately
    assert combat.can_cast(Skill.TELEPORT) is True

    log.info("PASSED: can_cast (no cooldown)")
    return True


def test_can_cast_with_cooldown():
    """Test can_cast respects cooldowns."""
    log = get_logger()
    log.info("Testing can_cast (with cooldown)...")

    combat, _ = create_mock_combat()

    # Blizzard has ~1.8s cooldown
    assert combat.can_cast(Skill.BLIZZARD) is True

    # Record a cast
    combat._record_cast(Skill.BLIZZARD)

    # Should be on cooldown now
    assert combat.can_cast(Skill.BLIZZARD) is False

    # Check remaining cooldown
    remaining = combat.get_cooldown_remaining(Skill.BLIZZARD)
    assert remaining > 0
    assert remaining <= 1.8

    log.info("PASSED: can_cast (with cooldown)")
    return True


def test_cast_teleport():
    """Test teleport casting."""
    log = get_logger()
    log.info("Testing teleport...")

    combat, input_ctrl = create_mock_combat()

    result = combat.cast_teleport((500, 300))

    assert result is True
    # Should press hotkey then right-click at target
    input_ctrl.press.assert_called_with("f3")
    input_ctrl.click.assert_called()

    log.info("PASSED: teleport")
    return True


def test_cast_blizzard():
    """Test Blizzard casting."""
    log = get_logger()
    log.info("Testing Blizzard...")

    combat, input_ctrl = create_mock_combat()

    result = combat.cast_blizzard((600, 400))

    assert result is True
    input_ctrl.press.assert_called_with("f4")
    input_ctrl.click.assert_called()

    log.info("PASSED: Blizzard")
    return True


def test_cast_static_field():
    """Test Static Field casting."""
    log = get_logger()
    log.info("Testing Static Field...")

    combat, input_ctrl = create_mock_combat()

    result = combat.cast_static_field()

    assert result is True
    input_ctrl.press.assert_called_with("f5")
    # Static Field doesn't need a target
    input_ctrl.click.assert_called()

    log.info("PASSED: Static Field")
    return True


def test_cast_frozen_armor():
    """Test Frozen Armor buff."""
    log = get_logger()
    log.info("Testing Frozen Armor...")

    combat, input_ctrl = create_mock_combat()

    # Should not be active initially
    assert combat.is_buff_active(Skill.FROZEN_ARMOR) is False

    result = combat.cast_frozen_armor()

    assert result is True
    # Buff should now be tracked as active
    assert combat.is_buff_active(Skill.FROZEN_ARMOR) is True

    log.info("PASSED: Frozen Armor")
    return True


def test_ensure_buffs():
    """Test buff maintenance."""
    log = get_logger()
    log.info("Testing ensure_buffs...")

    combat, input_ctrl = create_mock_combat()

    # Buffs not active
    assert combat.is_buff_active(Skill.FROZEN_ARMOR) is False

    # Ensure buffs should cast Frozen Armor
    combat.ensure_buffs()

    input_ctrl.press.assert_called()
    assert combat.is_buff_active(Skill.FROZEN_ARMOR) is True

    log.info("PASSED: ensure_buffs")
    return True


def test_attack_pattern():
    """Test standard attack pattern."""
    log = get_logger()
    log.info("Testing attack pattern...")

    combat, input_ctrl = create_mock_combat()

    combat.attack_pattern((700, 400), use_static=False)

    # Should have pressed teleport and blizzard keys
    calls = input_ctrl.press.call_args_list
    hotkeys_pressed = [c[0][0] for c in calls]

    assert "f3" in hotkeys_pressed  # Teleport
    assert "f4" in hotkeys_pressed  # Blizzard

    log.info("PASSED: attack pattern")
    return True


def test_attack_pattern_with_static():
    """Test attack pattern with Static Field."""
    log = get_logger()
    log.info("Testing attack pattern with Static...")

    combat, input_ctrl = create_mock_combat()

    combat.attack_pattern((700, 400), use_static=True)

    calls = input_ctrl.press.call_args_list
    hotkeys_pressed = [c[0][0] for c in calls]

    assert "f3" in hotkeys_pressed  # Teleport
    assert "f5" in hotkeys_pressed  # Static Field
    assert "f4" in hotkeys_pressed  # Blizzard

    log.info("PASSED: attack pattern with Static")
    return True


def test_kite_and_attack():
    """Test kiting behavior."""
    log = get_logger()
    log.info("Testing kite and attack...")

    combat, input_ctrl = create_mock_combat()

    # Enemy at screen center
    combat.kite_and_attack((960, 540), kite_distance=200)

    calls = input_ctrl.press.call_args_list
    hotkeys_pressed = [c[0][0] for c in calls]

    assert "f3" in hotkeys_pressed  # Teleport (to kite)
    assert "f4" in hotkeys_pressed  # Blizzard

    log.info("PASSED: kite and attack")
    return True


def test_boss_attack_pattern():
    """Test boss attack pattern."""
    log = get_logger()
    log.info("Testing boss attack pattern...")

    combat, input_ctrl = create_mock_combat()

    combat.boss_attack_pattern((800, 400), static_casts=3)

    calls = input_ctrl.press.call_args_list
    hotkeys_pressed = [c[0][0] for c in calls]

    # Should have multiple static casts
    static_count = hotkeys_pressed.count("f5")
    assert static_count >= 1  # At least some static casts

    assert "f3" in hotkeys_pressed  # Teleport
    assert "f4" in hotkeys_pressed  # Blizzard

    log.info("PASSED: boss attack pattern")
    return True


def test_clear_area():
    """Test area clearing."""
    log = get_logger()
    log.info("Testing clear area...")

    combat, input_ctrl = create_mock_combat()

    positions = [(600, 400), (700, 400), (800, 400)]
    combat.clear_area(positions)

    # Should have cast Blizzard multiple times
    calls = input_ctrl.press.call_args_list
    blizzard_count = sum(1 for c in calls if c[0][0] == "f4")
    assert blizzard_count >= 1

    log.info("PASSED: clear area")
    return True


def test_use_potion():
    """Test potion usage."""
    log = get_logger()
    log.info("Testing potion usage...")

    combat, input_ctrl = create_mock_combat()

    combat.use_potion(1)
    input_ctrl.use_potion.assert_called_with(1)

    combat.use_potion(3)
    input_ctrl.use_potion.assert_called_with(3)

    log.info("PASSED: potion usage")
    return True


def test_emergency_teleport():
    """Test emergency teleport."""
    log = get_logger()
    log.info("Testing emergency teleport...")

    combat, input_ctrl = create_mock_combat()

    combat.emergency_teleport()

    input_ctrl.press.assert_called_with("f3")
    # Should click somewhere safe (top-left area)
    click_call = input_ctrl.click.call_args
    x, y = click_call[0][:2]
    assert x < 500  # Should be in left portion
    assert y < 500  # Should be in top portion

    log.info("PASSED: emergency teleport")
    return True


def test_cooldown_remaining():
    """Test cooldown remaining calculation."""
    log = get_logger()
    log.info("Testing cooldown remaining...")

    combat, _ = create_mock_combat()

    # No cast yet - should be 0
    remaining = combat.get_cooldown_remaining(Skill.BLIZZARD)
    assert remaining == 0.0

    # Cast and check
    combat._record_cast(Skill.BLIZZARD)
    remaining = combat.get_cooldown_remaining(Skill.BLIZZARD)
    assert remaining > 0
    assert remaining <= 1.8

    log.info("PASSED: cooldown remaining")
    return True


def test_unconfigured_skill():
    """Test casting unconfigured skill fails gracefully."""
    log = get_logger()
    log.info("Testing unconfigured skill...")

    combat, _ = create_mock_combat()

    # Nova not configured in our test config
    result = combat._cast_skill(Skill.NOVA)
    assert result is False

    # Can cast should return False
    assert combat.can_cast(Skill.NOVA) is False

    log.info("PASSED: unconfigured skill")
    return True


def test_default_skill_info():
    """Verify default skill info is defined."""
    log = get_logger()
    log.info("Testing default skill info...")

    # Key skills should have defaults
    assert Skill.TELEPORT in DEFAULT_SKILL_INFO
    assert Skill.BLIZZARD in DEFAULT_SKILL_INFO
    assert Skill.STATIC_FIELD in DEFAULT_SKILL_INFO
    assert Skill.FROZEN_ARMOR in DEFAULT_SKILL_INFO

    # Check Blizzard cooldown is reasonable
    blizzard_info = DEFAULT_SKILL_INFO[Skill.BLIZZARD]
    assert blizzard_info.cooldown > 1.0
    assert blizzard_info.cooldown < 3.0

    log.info(f"Verified {len(DEFAULT_SKILL_INFO)} default skill configurations")
    log.info("PASSED: default skill info")
    return True


def test_combat_state():
    """Test combat state tracking."""
    log = get_logger()
    log.info("Testing combat state...")

    state = CombatState()

    assert state.in_combat is False
    assert state.target_position is None
    assert len(state.last_skill_times) == 0
    assert len(state.buffs_active) == 0

    # Update state
    state.in_combat = True
    state.target_position = (500, 300)
    state.last_skill_times[Skill.BLIZZARD] = time.time()

    assert state.in_combat is True
    assert state.target_position == (500, 300)
    assert Skill.BLIZZARD in state.last_skill_times

    log.info("PASSED: combat state")
    return True


def run_all_tests():
    """Run all combat tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Combat System Tests")
    log.info("=" * 50)

    tests = [
        ("Skill Setup", test_skill_setup),
        ("Can Cast (No Cooldown)", test_can_cast_no_cooldown),
        ("Can Cast (With Cooldown)", test_can_cast_with_cooldown),
        ("Cast Teleport", test_cast_teleport),
        ("Cast Blizzard", test_cast_blizzard),
        ("Cast Static Field", test_cast_static_field),
        ("Cast Frozen Armor", test_cast_frozen_armor),
        ("Ensure Buffs", test_ensure_buffs),
        ("Attack Pattern", test_attack_pattern),
        ("Attack Pattern With Static", test_attack_pattern_with_static),
        ("Kite And Attack", test_kite_and_attack),
        ("Boss Attack Pattern", test_boss_attack_pattern),
        ("Clear Area", test_clear_area),
        ("Use Potion", test_use_potion),
        ("Emergency Teleport", test_emergency_teleport),
        ("Cooldown Remaining", test_cooldown_remaining),
        ("Unconfigured Skill", test_unconfigured_skill),
        ("Default Skill Info", test_default_skill_info),
        ("Combat State", test_combat_state),
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
