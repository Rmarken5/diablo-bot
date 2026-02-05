"""Data models for configuration and game entities."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CharacterClass(Enum):
    """Supported character classes."""
    SORCERESS = "sorceress"
    AMAZON = "amazon"
    NECROMANCER = "necromancer"
    BARBARIAN = "barbarian"
    PALADIN = "paladin"
    DRUID = "druid"
    ASSASSIN = "assassin"


class ItemQuality(Enum):
    """Item quality levels."""
    NORMAL = "normal"
    MAGIC = "magic"
    RARE = "rare"
    SET = "set"
    UNIQUE = "unique"
    RUNE = "rune"
    CRAFTED = "crafted"


class RunType(Enum):
    """Available run types."""
    PINDLESKIN = "pindleskin"
    MEPHISTO = "mephisto"
    BAAL = "baal"
    CHAOS = "chaos"
    COWS = "cows"
    TRISTRAM = "tristram"
    TOMBS = "tombs"


@dataclass
class Config:
    """Main bot configuration."""

    # General
    game_path: str = ""
    window_title: str = "Diablo II: Resurrected"
    resolution: Tuple[int, int] = (1920, 1080)

    # Character
    character_name: str = "BotChar"
    character_class: CharacterClass = CharacterClass.SORCERESS
    build_name: str = "blizzard_leveling"

    # Runs
    enabled_runs: List[str] = field(default_factory=lambda: ["pindleskin"])
    run_count: int = 0  # 0 for infinite

    # Safety
    chicken_health_percent: int = 30
    chicken_mana_percent: int = 0
    max_deaths_per_session: int = 5

    # Timing
    action_delay_ms: int = 50
    human_like_input: bool = True
    mouse_speed: str = "normal"  # slow, normal, fast

    # Logging
    log_level: str = "INFO"
    log_dir: str = "logs"
    save_screenshots: bool = True
    screenshot_dir: str = "screenshots"

    # Hotkeys (D2R defaults)
    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        "skill_left": "f1",
        "skill_right": "f2",
        "teleport": "f3",
        "blizzard": "f4",
        "static_field": "f5",
        "frozen_armor": "f6",
        "town_portal": "t",
        "show_items": "alt",
        "inventory": "i",
        "character_screen": "c",
        "skill_tree": "k",
        "potion_1": "1",
        "potion_2": "2",
        "potion_3": "3",
        "potion_4": "4",
    })


@dataclass
class SkillAllocation:
    """Single skill point allocation."""
    skill_name: str
    points: int = 1


@dataclass
class Build:
    """Character build definition."""

    name: str
    description: str = ""

    # Stat allocation per level-up (default all to vitality)
    stat_priority: List[str] = field(default_factory=lambda: ["vitality"])
    strength_target: int = 156  # For Monarch
    dexterity_target: int = 0

    # Skill progression: level -> list of skills to allocate
    skill_progression: Dict[int, List[str]] = field(default_factory=dict)

    # Respec configuration
    respec_level: Optional[int] = None
    respec_build_name: Optional[str] = None

    # Hotkey assignments for this build
    skill_hotkeys: Dict[str, str] = field(default_factory=dict)


@dataclass
class PickitRule:
    """Single item pickup rule."""

    # Match criteria
    quality: Optional[ItemQuality] = None
    base_type: Optional[str] = None  # e.g., "monarch", "diadem"
    name_contains: Optional[str] = None

    # Action
    pickup: bool = True


@dataclass
class PickitRules:
    """Collection of pickit rules."""

    # Always pickup these qualities
    pickup_qualities: List[ItemQuality] = field(default_factory=lambda: [
        ItemQuality.UNIQUE,
        ItemQuality.SET,
        ItemQuality.RUNE,
    ])

    # Specific rules (evaluated in order)
    rules: List[PickitRule] = field(default_factory=list)

    # Item bases to always pickup (regardless of quality)
    pickup_bases: List[str] = field(default_factory=lambda: [
        "monarch",
        "archon plate",
        "diadem",
        "sacred armor",
    ])

    # Gold threshold (pickup gold stacks >= this value)
    gold_threshold: int = 5000


@dataclass
class DetectedItem:
    """Item detected on ground."""
    name: str
    quality: ItemQuality
    position: Tuple[int, int]
    base_type: Optional[str] = None


@dataclass
class Match:
    """Template match result."""
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of match."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class RunResult:
    """Result of a single run."""
    run_type: str
    success: bool
    duration: float
    items_found: List[DetectedItem] = field(default_factory=list)
    experience_gained: int = 0
    deaths: int = 0
    error: Optional[str] = None


@dataclass
class SessionStats:
    """Statistics for a bot session."""
    runs_completed: int = 0
    runs_failed: int = 0
    items_found: Dict[str, int] = field(default_factory=dict)
    deaths: int = 0
    chickens: int = 0
    total_run_time: float = 0.0

    @property
    def average_run_time(self) -> float:
        """Calculate average run time."""
        total_runs = self.runs_completed + self.runs_failed
        if total_runs == 0:
            return 0.0
        return self.total_run_time / total_runs
