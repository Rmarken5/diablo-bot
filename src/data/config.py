"""Configuration management for D2R Bot."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.data.models import (
    Build,
    CharacterClass,
    Config,
    ItemQuality,
    PickitRule,
    PickitRules,
)
from src.utils.logger import get_logger


class ConfigError(Exception):
    """Configuration related error."""
    pass


class ConfigManager:
    """
    Manages bot configuration from YAML files.

    Handles loading settings, builds, and pickit rules with
    defaults for missing values.
    """

    DEFAULT_CONFIG_DIR = "config"

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize config manager.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir or self.DEFAULT_CONFIG_DIR)
        self.log = get_logger()
        self._config: Optional[Config] = None
        self._builds: Dict[str, Build] = {}
        self._pickit: Optional[PickitRules] = None

    def load(self) -> Config:
        """
        Load main configuration.

        Returns:
            Config object with all settings

        Raises:
            ConfigError: If config file is invalid
        """
        settings_path = self.config_dir / "settings.yaml"

        if not settings_path.exists():
            self.log.warning(f"No settings.yaml found at {settings_path}, using defaults")
            self._config = Config()
            return self._config

        try:
            with open(settings_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in settings.yaml: {e}")

        self._config = self._parse_config(data)
        self.log.info(f"Loaded config from {settings_path}")
        return self._config

    def _parse_config(self, data: Dict[str, Any]) -> Config:
        """Parse raw YAML data into Config object."""
        general = data.get("general", {})
        character = data.get("character", {})
        runs = data.get("runs", {})
        safety = data.get("safety", {})
        timing = data.get("timing", {})
        logging_cfg = data.get("logging", {})
        hotkeys = data.get("hotkeys", {})

        # Parse character class
        char_class_str = character.get("class", "sorceress")
        try:
            char_class = CharacterClass(char_class_str.lower())
        except ValueError:
            self.log.warning(f"Unknown character class '{char_class_str}', defaulting to sorceress")
            char_class = CharacterClass.SORCERESS

        # Build config with defaults
        config = Config(
            # General
            game_path=general.get("game_path", ""),
            window_title=general.get("window_title", "Diablo II: Resurrected"),
            resolution=tuple(general.get("resolution", [1920, 1080])),
            # Character
            character_name=character.get("name", "BotChar"),
            character_class=char_class,
            build_name=character.get("build", "blizzard_leveling"),
            # Runs
            enabled_runs=runs.get("enabled", ["pindleskin"]),
            run_count=runs.get("count", 0),
            # Safety
            chicken_health_percent=safety.get("chicken_health", 30),
            chicken_mana_percent=safety.get("chicken_mana", 0),
            max_deaths_per_session=safety.get("max_deaths", 5),
            # Timing
            action_delay_ms=timing.get("action_delay_ms", 50),
            human_like_input=timing.get("human_like", True),
            mouse_speed=timing.get("mouse_speed", "normal"),
            # Logging
            log_level=logging_cfg.get("level", "INFO"),
            log_dir=logging_cfg.get("directory", "logs"),
            save_screenshots=logging_cfg.get("screenshots", True),
            screenshot_dir=logging_cfg.get("screenshot_dir", "screenshots"),
        )

        # Merge hotkeys with defaults
        if hotkeys:
            config.hotkeys.update(hotkeys)

        return config

    def get_config(self) -> Config:
        """Get loaded config, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config

    def get_build(self, name: str) -> Build:
        """
        Load a build configuration.

        Args:
            name: Build name (filename without extension)

        Returns:
            Build object

        Raises:
            ConfigError: If build file not found or invalid
        """
        if name in self._builds:
            return self._builds[name]

        build_path = self.config_dir / "builds" / f"{name}.yaml"

        if not build_path.exists():
            raise ConfigError(f"Build file not found: {build_path}")

        try:
            with open(build_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in build file {name}: {e}")

        build = self._parse_build(name, data)
        self._builds[name] = build
        self.log.info(f"Loaded build '{name}' from {build_path}")
        return build

    def _parse_build(self, name: str, data: Dict[str, Any]) -> Build:
        """Parse raw YAML data into Build object."""
        stats = data.get("stats", {})
        skills = data.get("skills", {})
        respec = data.get("respec", {})

        # Parse skill progression
        skill_progression: Dict[int, list] = {}
        progression_data = skills.get("progression", {})

        for level_str, skill_list in progression_data.items():
            try:
                level = int(level_str)
                if isinstance(skill_list, list):
                    skill_progression[level] = skill_list
                else:
                    skill_progression[level] = [skill_list]
            except ValueError:
                self.log.warning(f"Invalid level '{level_str}' in build {name}")

        return Build(
            name=name,
            description=data.get("description", ""),
            stat_priority=stats.get("priority", ["vitality"]),
            strength_target=stats.get("strength_target", 156),
            dexterity_target=stats.get("dexterity_target", 0),
            skill_progression=skill_progression,
            respec_level=respec.get("level"),
            respec_build_name=respec.get("build"),
            skill_hotkeys=skills.get("hotkeys", {}),
        )

    def get_pickit_rules(self) -> PickitRules:
        """
        Load pickit (item pickup) rules.

        Returns:
            PickitRules object
        """
        if self._pickit is not None:
            return self._pickit

        pickit_path = self.config_dir / "pickit.yaml"

        if not pickit_path.exists():
            self.log.warning(f"No pickit.yaml found, using defaults")
            self._pickit = PickitRules()
            return self._pickit

        try:
            with open(pickit_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in pickit.yaml: {e}")

        self._pickit = self._parse_pickit(data)
        self.log.info(f"Loaded pickit rules from {pickit_path}")
        return self._pickit

    def _parse_pickit(self, data: Dict[str, Any]) -> PickitRules:
        """Parse raw YAML data into PickitRules object."""
        # Parse quality list
        quality_strs = data.get("pickup_qualities", ["unique", "set", "rune"])
        qualities = []
        for q in quality_strs:
            try:
                qualities.append(ItemQuality(q.lower()))
            except ValueError:
                self.log.warning(f"Unknown item quality: {q}")

        # Parse specific rules
        rules = []
        for rule_data in data.get("rules", []):
            quality = None
            if "quality" in rule_data:
                try:
                    quality = ItemQuality(rule_data["quality"].lower())
                except ValueError:
                    pass

            rules.append(PickitRule(
                quality=quality,
                base_type=rule_data.get("base_type"),
                name_contains=rule_data.get("name_contains"),
                pickup=rule_data.get("pickup", True),
            ))

        return PickitRules(
            pickup_qualities=qualities,
            rules=rules,
            pickup_bases=data.get("pickup_bases", []),
            gold_threshold=data.get("gold_threshold", 5000),
        )

    def save(self, config: Config) -> None:
        """
        Save configuration to settings.yaml.

        Args:
            config: Config object to save
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        settings_path = self.config_dir / "settings.yaml"

        data = {
            "general": {
                "game_path": config.game_path,
                "window_title": config.window_title,
                "resolution": list(config.resolution),
            },
            "character": {
                "name": config.character_name,
                "class": config.character_class.value,
                "build": config.build_name,
            },
            "runs": {
                "enabled": config.enabled_runs,
                "count": config.run_count,
            },
            "safety": {
                "chicken_health": config.chicken_health_percent,
                "chicken_mana": config.chicken_mana_percent,
                "max_deaths": config.max_deaths_per_session,
            },
            "timing": {
                "action_delay_ms": config.action_delay_ms,
                "human_like": config.human_like_input,
                "mouse_speed": config.mouse_speed,
            },
            "logging": {
                "level": config.log_level,
                "directory": config.log_dir,
                "screenshots": config.save_screenshots,
                "screenshot_dir": config.screenshot_dir,
            },
            "hotkeys": config.hotkeys,
        }

        with open(settings_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self.log.info(f"Saved config to {settings_path}")

    def get_skills_for_level(self, build: Build, level: int) -> list:
        """
        Get skills to allocate at a specific level.

        Args:
            build: Build configuration
            level: Character level

        Returns:
            List of skill names to allocate
        """
        return build.skill_progression.get(level, [])

    def get_skill_progression_range(
        self, build: Build, start_level: int, end_level: int
    ) -> Dict[int, list]:
        """
        Get skill progression for a level range.

        Args:
            build: Build configuration
            start_level: Starting level (inclusive)
            end_level: Ending level (inclusive)

        Returns:
            Dict mapping levels to skill lists
        """
        return {
            level: skills
            for level, skills in build.skill_progression.items()
            if start_level <= level <= end_level
        }
