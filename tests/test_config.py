"""Tests for configuration system."""

import os
import tempfile
from pathlib import Path

import yaml

from src.data.config import ConfigManager, ConfigError
from src.data.models import (
    CharacterClass,
    Config,
    ItemQuality,
)
from src.utils.logger import setup_logger, get_logger


def test_load_default_config():
    """Test loading config with no file (uses defaults)."""
    log = get_logger()
    log.info("Testing default config loading...")

    # Use a temp directory with no config files
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ConfigManager(config_dir=tmpdir)
        config = manager.load()

        assert config.window_title == "Diablo II: Resurrected"
        assert config.character_class == CharacterClass.SORCERESS
        assert config.chicken_health_percent == 30
        assert config.human_like_input is True

    log.info("PASSED: default config loading")
    return True


def test_load_config_from_yaml():
    """Test loading config from YAML file."""
    log = get_logger()
    log.info("Testing YAML config loading...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config file
        config_data = {
            "general": {
                "game_path": "/test/path",
                "window_title": "Test Window",
                "resolution": [1280, 720],
            },
            "character": {
                "name": "TestChar",
                "class": "amazon",
                "build": "test_build",
            },
            "safety": {
                "chicken_health": 50,
            },
        }

        settings_path = Path(tmpdir) / "settings.yaml"
        with open(settings_path, "w") as f:
            yaml.dump(config_data, f)

        manager = ConfigManager(config_dir=tmpdir)
        config = manager.load()

        assert config.game_path == "/test/path"
        assert config.window_title == "Test Window"
        assert config.resolution == (1280, 720)
        assert config.character_name == "TestChar"
        assert config.character_class == CharacterClass.AMAZON
        assert config.chicken_health_percent == 50

    log.info("PASSED: YAML config loading")
    return True


def test_invalid_yaml_raises_error():
    """Test that invalid YAML raises ConfigError."""
    log = get_logger()
    log.info("Testing invalid YAML handling...")

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.yaml"
        with open(settings_path, "w") as f:
            f.write("invalid: yaml: content: {{{")

        manager = ConfigManager(config_dir=tmpdir)

        try:
            manager.load()
            assert False, "Should have raised ConfigError"
        except ConfigError as e:
            assert "Invalid YAML" in str(e)

    log.info("PASSED: invalid YAML handling")
    return True


def test_load_build():
    """Test loading a build file."""
    log = get_logger()
    log.info("Testing build loading...")

    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "builds"
        builds_dir.mkdir()

        build_data = {
            "description": "Test build",
            "stats": {
                "priority": ["vitality", "strength"],
                "strength_target": 100,
            },
            "skills": {
                "progression": {
                    2: ["fire_bolt"],
                    3: ["fire_bolt", "warmth"],
                    10: ["blizzard"],
                },
                "hotkeys": {
                    "blizzard": "f4",
                },
            },
            "respec": {
                "level": 26,
            },
        }

        build_path = builds_dir / "test_build.yaml"
        with open(build_path, "w") as f:
            yaml.dump(build_data, f)

        manager = ConfigManager(config_dir=tmpdir)
        build = manager.get_build("test_build")

        assert build.name == "test_build"
        assert build.description == "Test build"
        assert build.strength_target == 100
        assert build.stat_priority == ["vitality", "strength"]
        assert build.respec_level == 26
        assert 2 in build.skill_progression
        assert build.skill_progression[2] == ["fire_bolt"]
        assert build.skill_progression[3] == ["fire_bolt", "warmth"]
        assert build.skill_hotkeys.get("blizzard") == "f4"

    log.info("PASSED: build loading")
    return True


def test_build_not_found():
    """Test that missing build file raises ConfigError."""
    log = get_logger()
    log.info("Testing build not found...")

    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "builds"
        builds_dir.mkdir()

        manager = ConfigManager(config_dir=tmpdir)

        try:
            manager.get_build("nonexistent_build")
            assert False, "Should have raised ConfigError"
        except ConfigError as e:
            assert "not found" in str(e)

    log.info("PASSED: build not found")
    return True


def test_load_pickit_rules():
    """Test loading pickit rules."""
    log = get_logger()
    log.info("Testing pickit rules loading...")

    with tempfile.TemporaryDirectory() as tmpdir:
        pickit_data = {
            "pickup_qualities": ["unique", "set", "rare"],
            "pickup_bases": ["monarch", "diadem"],
            "gold_threshold": 10000,
            "rules": [
                {"quality": "magic", "base_type": "jewel", "pickup": True},
                {"base_type": "charm", "pickup": True},
            ],
        }

        pickit_path = Path(tmpdir) / "pickit.yaml"
        with open(pickit_path, "w") as f:
            yaml.dump(pickit_data, f)

        manager = ConfigManager(config_dir=tmpdir)
        rules = manager.get_pickit_rules()

        assert ItemQuality.UNIQUE in rules.pickup_qualities
        assert ItemQuality.SET in rules.pickup_qualities
        assert ItemQuality.RARE in rules.pickup_qualities
        assert "monarch" in rules.pickup_bases
        assert rules.gold_threshold == 10000
        assert len(rules.rules) == 2
        assert rules.rules[0].quality == ItemQuality.MAGIC
        assert rules.rules[0].base_type == "jewel"

    log.info("PASSED: pickit rules loading")
    return True


def test_default_pickit_rules():
    """Test default pickit rules when no file exists."""
    log = get_logger()
    log.info("Testing default pickit rules...")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ConfigManager(config_dir=tmpdir)
        rules = manager.get_pickit_rules()

        # Should have default qualities
        assert ItemQuality.UNIQUE in rules.pickup_qualities
        assert ItemQuality.SET in rules.pickup_qualities
        assert ItemQuality.RUNE in rules.pickup_qualities

    log.info("PASSED: default pickit rules")
    return True


def test_save_config():
    """Test saving config to file."""
    log = get_logger()
    log.info("Testing config save...")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ConfigManager(config_dir=tmpdir)

        config = Config(
            game_path="/saved/path",
            character_name="SavedChar",
            chicken_health_percent=40,
        )

        manager.save(config)

        # Verify file was created
        settings_path = Path(tmpdir) / "settings.yaml"
        assert settings_path.exists()

        # Load and verify
        with open(settings_path, "r") as f:
            data = yaml.safe_load(f)

        assert data["general"]["game_path"] == "/saved/path"
        assert data["character"]["name"] == "SavedChar"
        assert data["safety"]["chicken_health"] == 40

    log.info("PASSED: config save")
    return True


def test_skill_progression_helpers():
    """Test skill progression helper methods."""
    log = get_logger()
    log.info("Testing skill progression helpers...")

    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "builds"
        builds_dir.mkdir()

        build_data = {
            "skills": {
                "progression": {
                    2: ["fire_bolt"],
                    3: ["warmth"],
                    5: ["blaze"],
                    10: ["meteor"],
                },
            },
        }

        build_path = builds_dir / "test.yaml"
        with open(build_path, "w") as f:
            yaml.dump(build_data, f)

        manager = ConfigManager(config_dir=tmpdir)
        build = manager.get_build("test")

        # Test single level
        skills = manager.get_skills_for_level(build, 3)
        assert skills == ["warmth"]

        # Test range
        progression = manager.get_skill_progression_range(build, 2, 5)
        assert 2 in progression
        assert 3 in progression
        assert 5 in progression
        assert 10 not in progression

    log.info("PASSED: skill progression helpers")
    return True


def test_load_real_config():
    """Test loading actual config files from project."""
    log = get_logger()
    log.info("Testing real config files...")

    # Only run if config directory exists
    if not Path("config/settings.yaml").exists():
        log.info("SKIPPED: No config/settings.yaml found")
        return True

    manager = ConfigManager()
    config = manager.load()

    assert config.window_title == "Diablo II: Resurrected"
    assert config.build_name == "blizzard_leveling"

    log.info(f"Loaded config: {config.character_name} ({config.character_class.value})")

    # Test build loading
    build = manager.get_build(config.build_name)
    assert build.name == "blizzard_leveling"
    assert len(build.skill_progression) > 0

    log.info(f"Loaded build with {len(build.skill_progression)} level entries")

    # Test pickit
    pickit = manager.get_pickit_rules()
    assert len(pickit.pickup_qualities) > 0

    log.info(f"Loaded {len(pickit.rules)} pickit rules")

    log.info("PASSED: real config files")
    return True


def run_all_tests():
    """Run all config tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Configuration System Tests")
    log.info("=" * 50)

    tests = [
        ("Default Config Loading", test_load_default_config),
        ("YAML Config Loading", test_load_config_from_yaml),
        ("Invalid YAML Handling", test_invalid_yaml_raises_error),
        ("Build Loading", test_load_build),
        ("Build Not Found", test_build_not_found),
        ("Pickit Rules Loading", test_load_pickit_rules),
        ("Default Pickit Rules", test_default_pickit_rules),
        ("Config Save", test_save_config),
        ("Skill Progression Helpers", test_skill_progression_helpers),
        ("Real Config Files", test_load_real_config),
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
