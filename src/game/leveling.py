"""Leveling system: skill and stat point allocation for D2R Bot."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.data.models import Build, Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class Stat(Enum):
    """Character stats."""
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    VITALITY = "vitality"
    ENERGY = "energy"


@dataclass
class LevelState:
    """Current leveling state."""
    current_level: int = 1
    stat_points_available: int = 0
    skill_points_available: int = 0
    total_stats_allocated: Dict[str, int] = field(default_factory=lambda: {
        "strength": 0,
        "dexterity": 0,
        "vitality": 0,
        "energy": 0,
    })
    total_skills_allocated: Dict[str, int] = field(default_factory=dict)
    respec_done: bool = False


# ========== Skill Tree Layout ==========
# D2R Sorceress skill tree tab positions (1920x1080)
# The skill tree has 3 tabs: Fire, Lightning, Cold
class SkillTab(Enum):
    """Skill tree tabs."""
    FIRE = 0
    LIGHTNING = 1
    COLD = 2


# Skill tree tab button positions
SKILL_TAB_POSITIONS = {
    SkillTab.FIRE: (135, 530),
    SkillTab.LIGHTNING: (230, 530),
    SkillTab.COLD: (325, 530),
}

# Skill positions within each tab (approximate screen positions when tree is open)
# Layout: 3 columns, 6 rows per tab
# Row 0 = top (level 1 skills), Row 5 = bottom (level 30 skills)
SKILL_POSITIONS: Dict[str, Tuple[SkillTab, Tuple[int, int]]] = {
    # Fire Tree
    "fire_bolt": (SkillTab.FIRE, (135, 175)),
    "warmth": (SkillTab.FIRE, (230, 175)),
    "inferno": (SkillTab.FIRE, (135, 250)),
    "blaze": (SkillTab.FIRE, (230, 250)),
    "fire_ball": (SkillTab.FIRE, (135, 325)),
    "fire_wall": (SkillTab.FIRE, (230, 325)),
    "enchant": (SkillTab.FIRE, (325, 325)),
    "meteor": (SkillTab.FIRE, (135, 400)),
    "fire_mastery": (SkillTab.FIRE, (325, 400)),
    "hydra": (SkillTab.FIRE, (230, 475)),

    # Lightning Tree
    "charged_bolt": (SkillTab.LIGHTNING, (135, 175)),
    "static_field": (SkillTab.LIGHTNING, (230, 175)),
    "telekinesis": (SkillTab.LIGHTNING, (325, 175)),
    "nova": (SkillTab.LIGHTNING, (135, 250)),
    "lightning": (SkillTab.LIGHTNING, (230, 250)),
    "chain_lightning": (SkillTab.LIGHTNING, (135, 325)),
    "teleport": (SkillTab.LIGHTNING, (325, 325)),
    "thunder_storm": (SkillTab.LIGHTNING, (230, 400)),
    "energy_shield": (SkillTab.LIGHTNING, (325, 400)),
    "lightning_mastery": (SkillTab.LIGHTNING, (230, 475)),

    # Cold Tree
    "ice_bolt": (SkillTab.COLD, (135, 175)),
    "frozen_armor": (SkillTab.COLD, (230, 175)),
    "frost_nova": (SkillTab.COLD, (135, 250)),
    "ice_blast": (SkillTab.COLD, (230, 250)),
    "shiver_armor": (SkillTab.COLD, (325, 250)),
    "glacial_spike": (SkillTab.COLD, (135, 325)),
    "blizzard": (SkillTab.COLD, (230, 325)),
    "chilling_armor": (SkillTab.COLD, (325, 325)),
    "frozen_orb": (SkillTab.COLD, (230, 400)),
    "cold_mastery": (SkillTab.COLD, (325, 400)),
}

# ========== Stat Screen Layout ==========
# Stat screen "+" button positions (1920x1080)
STAT_BUTTON_POSITIONS = {
    Stat.STRENGTH: (240, 230),
    Stat.DEXTERITY: (240, 275),
    Stat.VITALITY: (240, 320),
    Stat.ENERGY: (240, 365),
}

# Level-up indicators
# When level-up happens, a button/indicator glows on the HUD
LEVEL_UP_INDICATOR_REGION = (560, 535, 50, 30)  # (x, y, w, h) near stat button
SKILL_POINT_INDICATOR_REGION = (430, 535, 50, 30)  # Near skill button

# Gold/yellow color for level-up glow
LEVEL_UP_COLOR_LOWER = np.array([0, 150, 180], dtype=np.uint8)
LEVEL_UP_COLOR_UPPER = np.array([80, 255, 255], dtype=np.uint8)


class LevelManager:
    """
    Manages character leveling: stat and skill point allocation.

    Detects when points are available, navigates the skill tree
    and stat screen, and allocates points according to the
    predefined build configuration.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        build: Optional[Build] = None,
        input_ctrl: Optional[InputController] = None,
        screen_capture=None,
        game_detector=None,
    ):
        """
        Initialize level manager.

        Args:
            config: Bot configuration
            build: Character build definition
            input_ctrl: Input controller
            screen_capture: Screen capture
            game_detector: Game state detector
        """
        self.config = config or Config()
        self.build = build
        self.input = input_ctrl or InputController()
        self.capture = screen_capture
        self.detector = game_detector
        self.log = get_logger()

        # State
        self.state = LevelState()

        # Timing
        self.click_delay = 0.15
        self.screen_transition_delay = 0.5

    def set_build(self, build: Build) -> None:
        """Set the active build."""
        self.build = build
        self.log.info(f"Build set to: {build.name}")

    def set_level(self, level: int) -> None:
        """Set current character level."""
        self.state.current_level = level
        self.log.info(f"Level set to {level}")

    # ========== Detection ==========

    def check_level_up(self, screen: np.ndarray = None) -> bool:
        """
        Check if level-up occurred (stat/skill points available).

        Looks for the golden glow indicators near the stat and skill
        buttons on the HUD.

        Args:
            screen: Screen capture

        Returns:
            True if points are available
        """
        if screen is None:
            if self.capture is None:
                return False
            screen = self.capture.grab()

        stat_available = self._check_indicator(screen, LEVEL_UP_INDICATOR_REGION)
        skill_available = self._check_indicator(screen, SKILL_POINT_INDICATOR_REGION)

        if stat_available or skill_available:
            self.log.info(
                f"Level up detected! Stats: {stat_available}, Skills: {skill_available}"
            )
            return True

        return False

    def _check_indicator(self, screen: np.ndarray, region: Tuple[int, int, int, int]) -> bool:
        """
        Check if a level-up indicator is glowing.

        Args:
            screen: Screen capture
            region: (x, y, w, h) of indicator area

        Returns:
            True if indicator is active (golden glow)
        """
        x, y, w, h = region

        if y + h > screen.shape[0] or x + w > screen.shape[1]:
            return False

        area = screen[y:y + h, x:x + w]
        mask = cv2.inRange(area, LEVEL_UP_COLOR_LOWER, LEVEL_UP_COLOR_UPPER)
        gold_pixels = cv2.countNonZero(mask)
        total_pixels = w * h

        # If >15% of area is golden, indicator is active
        return (gold_pixels / total_pixels) > 0.15

    def check_points_available(self, screen: np.ndarray = None) -> Tuple[bool, bool]:
        """
        Check which types of points are available.

        Args:
            screen: Screen capture

        Returns:
            (stat_points_available, skill_points_available)
        """
        if screen is None:
            if self.capture is None:
                return (False, False)
            screen = self.capture.grab()

        stat_available = self._check_indicator(screen, LEVEL_UP_INDICATOR_REGION)
        skill_available = self._check_indicator(screen, SKILL_POINT_INDICATOR_REGION)

        return (stat_available, skill_available)

    # ========== Stat Allocation ==========

    def allocate_stats(self, screen: np.ndarray = None) -> int:
        """
        Allocate stat points according to build priority.

        Opens stat screen, allocates points, closes screen.

        Args:
            screen: Screen capture

        Returns:
            Number of stat points allocated
        """
        if self.build is None:
            self.log.warning("No build configured - cannot allocate stats")
            return 0

        self.log.info("Allocating stat points")

        # Open stat screen (C key in D2R)
        self.input.press(self.config.hotkeys.get("character_screen", "c"))
        time.sleep(self.screen_transition_delay)

        allocated = 0

        # Determine how many points to allocate and where
        # Keep clicking the appropriate stat button until no more points
        # We do this in a loop with a safety limit
        max_clicks = 50  # Safety limit (max 5 level-ups worth)

        for _ in range(max_clicks):
            stat = self._get_next_stat()
            if stat is None:
                break

            pos = STAT_BUTTON_POSITIONS.get(stat)
            if pos is None:
                break

            self.input.click(pos[0], pos[1])
            time.sleep(self.click_delay)
            allocated += 1

            # Track allocation
            self.state.total_stats_allocated[stat.value] = (
                self.state.total_stats_allocated.get(stat.value, 0) + 1
            )

            # Check if more points available by re-checking after each click
            if self.capture:
                time.sleep(0.1)
                check_screen = self.capture.grab()
                if not self._check_indicator(check_screen, LEVEL_UP_INDICATOR_REGION):
                    break

        # Close stat screen
        self.input.press(self.config.hotkeys.get("character_screen", "c"))
        time.sleep(0.3)

        self.log.info(f"Allocated {allocated} stat points")
        return allocated

    def _get_next_stat(self) -> Optional[Stat]:
        """
        Determine which stat to allocate next based on build priority.

        Priority logic:
        1. If strength < target, allocate strength
        2. If dexterity < target, allocate dexterity
        3. Otherwise, allocate by priority list (typically vitality)

        Returns:
            Stat to allocate, or None if can't determine
        """
        if self.build is None:
            return Stat.VITALITY

        str_allocated = self.state.total_stats_allocated.get("strength", 0)
        dex_allocated = self.state.total_stats_allocated.get("dexterity", 0)

        # Check strength target
        # Base strength for Sorceress is 10
        current_str_estimate = 10 + str_allocated
        if self.build.strength_target > 0 and current_str_estimate < self.build.strength_target:
            # Allocate strength gradually (every 3rd point)
            total_allocated = sum(self.state.total_stats_allocated.values())
            if total_allocated % 3 == 0:
                return Stat.STRENGTH

        # Check dexterity target
        if self.build.dexterity_target > 0:
            current_dex_estimate = 25 + dex_allocated  # Base dex for Sorc
            if current_dex_estimate < self.build.dexterity_target:
                return Stat.DEXTERITY

        # Follow priority list
        for stat_name in self.build.stat_priority:
            try:
                return Stat(stat_name)
            except ValueError:
                continue

        return Stat.VITALITY

    # ========== Skill Allocation ==========

    def allocate_skills(self, screen: np.ndarray = None) -> int:
        """
        Allocate skill points according to build progression.

        Opens skill tree, navigates to correct tab, clicks skills,
        closes skill tree.

        Args:
            screen: Screen capture

        Returns:
            Number of skill points allocated
        """
        if self.build is None:
            self.log.warning("No build configured - cannot allocate skills")
            return 0

        # Get skills for current level
        skills = self.build.skill_progression.get(self.state.current_level, [])
        if not skills:
            # Try next few levels in case we missed some
            skills = self._get_pending_skills()

        if not skills:
            self.log.debug(f"No skills to allocate at level {self.state.current_level}")
            return 0

        self.log.info(f"Allocating skill points: {skills}")

        # Open skill tree (K key in D2R, or configured hotkey)
        self.input.press(self.config.hotkeys.get("skill_tree", "k"))
        time.sleep(self.screen_transition_delay)

        allocated = 0
        current_tab: Optional[SkillTab] = None

        for skill_name in skills:
            skill_info = SKILL_POSITIONS.get(skill_name)
            if skill_info is None:
                self.log.warning(f"Unknown skill position: {skill_name}")
                continue

            tab, pos = skill_info

            # Switch tab if needed
            if tab != current_tab:
                self._switch_skill_tab(tab)
                current_tab = tab

            # Click the skill to allocate a point
            self.input.click(pos[0], pos[1])
            time.sleep(self.click_delay)
            allocated += 1

            # Track allocation
            self.state.total_skills_allocated[skill_name] = (
                self.state.total_skills_allocated.get(skill_name, 0) + 1
            )

        # Close skill tree
        self.input.press(self.config.hotkeys.get("skill_tree", "k"))
        time.sleep(0.3)

        self.log.info(f"Allocated {allocated} skill points")
        return allocated

    def _switch_skill_tab(self, tab: SkillTab) -> None:
        """
        Switch to a skill tree tab.

        Args:
            tab: Target tab
        """
        pos = SKILL_TAB_POSITIONS.get(tab)
        if pos:
            self.log.debug(f"Switching to {tab.name} tab")
            self.input.click(pos[0], pos[1])
            time.sleep(0.3)

    def _get_pending_skills(self) -> List[str]:
        """
        Get any skills that should have been allocated but weren't.

        Checks the build progression for levels we may have skipped
        (e.g., if we leveled up multiple times in one run).

        Returns:
            List of skill names to allocate
        """
        if self.build is None:
            return []

        pending = []
        for level in range(2, self.state.current_level + 1):
            skills = self.build.skill_progression.get(level, [])
            for skill in skills:
                current_count = self.state.total_skills_allocated.get(skill, 0)
                expected_count = self._expected_skill_count(skill, level)
                if current_count < expected_count:
                    pending.append(skill)

        return pending

    def _expected_skill_count(self, skill_name: str, up_to_level: int) -> int:
        """Count how many times a skill appears in progression up to a level."""
        if self.build is None:
            return 0

        count = 0
        for level in range(2, up_to_level + 1):
            skills = self.build.skill_progression.get(level, [])
            count += skills.count(skill_name)
        return count

    # ========== Respec ==========

    def needs_respec(self) -> bool:
        """
        Check if character needs to respec at current level.

        Returns:
            True if respec needed
        """
        if self.build is None:
            return False

        if self.state.respec_done:
            return False

        if self.build.respec_level is None:
            return False

        return self.state.current_level >= self.build.respec_level

    def perform_respec(self) -> bool:
        """
        Perform a respec via Akara (Act 1).

        This is complex and requires:
        1. Go to Act 1 (waypoint)
        2. Talk to Akara
        3. Select "Reset Stat/Skill Points"
        4. Confirm
        5. Reallocate all points according to post-respec build

        Returns:
            True if respec completed
        """
        self.log.info(
            f"Respec needed at level {self.state.current_level} "
            f"(build respec level: {self.build.respec_level})"
        )

        # This is a complex multi-step process that requires:
        # - Town navigation to Act 1
        # - NPC interaction with Akara
        # - Dialog navigation
        # - Complete reallocation of all points
        #
        # For now, log the need and mark as pending.
        # Full implementation would integrate with TownManager.

        self.log.warning(
            "Respec requested - manual intervention needed. "
            "Automated respec via Akara not yet implemented."
        )

        # Mark respec as done to prevent repeated attempts
        # In full implementation, this would only be set after actual respec
        # self.state.respec_done = True

        return False

    # ========== Combined Allocation ==========

    def handle_level_up(self, screen: np.ndarray = None) -> Tuple[int, int]:
        """
        Handle a level-up event: allocate both stats and skills.

        Args:
            screen: Screen capture

        Returns:
            (stat_points_allocated, skill_points_allocated)
        """
        self.state.current_level += 1
        self.log.info(f"Level up! Now level {self.state.current_level}")

        # Check for respec
        if self.needs_respec():
            self.perform_respec()
            return (0, 0)

        stats_allocated = 0
        skills_allocated = 0

        # Check what's available
        stat_avail, skill_avail = self.check_points_available(screen)

        if stat_avail:
            stats_allocated = self.allocate_stats(screen)

        if skill_avail:
            skills_allocated = self.allocate_skills(screen)

        self.log.info(
            f"Level {self.state.current_level}: "
            f"+{stats_allocated} stats, +{skills_allocated} skills"
        )

        return (stats_allocated, skills_allocated)

    def auto_allocate(self, screen: np.ndarray = None) -> bool:
        """
        Check for and handle any pending level-ups.

        Call this periodically (e.g., when returning to town)
        to catch any missed level-ups.

        Args:
            screen: Screen capture

        Returns:
            True if any points were allocated
        """
        if not self.check_level_up(screen):
            return False

        stats, skills = self.handle_level_up(screen)
        return (stats + skills) > 0

    # ========== State Query ==========

    def get_state(self) -> LevelState:
        """Get current leveling state."""
        return self.state

    def get_skills_for_level(self, level: int) -> List[str]:
        """Get skills to allocate at a specific level."""
        if self.build is None:
            return []
        return self.build.skill_progression.get(level, [])

    def get_total_skills_allocated(self) -> Dict[str, int]:
        """Get total skill point allocations."""
        return self.state.total_skills_allocated.copy()

    def get_build_progress(self) -> str:
        """
        Get a summary of build progress.

        Returns:
            Formatted progress string
        """
        if self.build is None:
            return "No build configured"

        total_stats = sum(self.state.total_stats_allocated.values())
        total_skills = sum(self.state.total_skills_allocated.values())

        lines = [
            f"Build: {self.build.name}",
            f"Level: {self.state.current_level}",
            f"Stats allocated: {total_stats}",
        ]

        for stat, count in self.state.total_stats_allocated.items():
            if count > 0:
                lines.append(f"  {stat}: +{count}")

        lines.append(f"Skills allocated: {total_skills}")

        # Top skills
        sorted_skills = sorted(
            self.state.total_skills_allocated.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for skill, count in sorted_skills[:5]:
            lines.append(f"  {skill}: {count}")

        if self.build.respec_level:
            respec_status = "done" if self.state.respec_done else "pending"
            lines.append(f"Respec at {self.build.respec_level}: {respec_status}")

        return "\n".join(lines)
