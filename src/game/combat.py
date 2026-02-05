"""Combat system for D2R Bot - Sorceress implementation."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from src.data.models import Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class Skill(Enum):
    """Sorceress skills."""
    # Cold
    ICE_BOLT = "ice_bolt"
    FROZEN_ARMOR = "frozen_armor"
    FROST_NOVA = "frost_nova"
    ICE_BLAST = "ice_blast"
    SHIVER_ARMOR = "shiver_armor"
    GLACIAL_SPIKE = "glacial_spike"
    BLIZZARD = "blizzard"
    CHILLING_ARMOR = "chilling_armor"
    FROZEN_ORB = "frozen_orb"
    COLD_MASTERY = "cold_mastery"

    # Lightning
    CHARGED_BOLT = "charged_bolt"
    STATIC_FIELD = "static_field"
    TELEKINESIS = "telekinesis"
    NOVA = "nova"
    LIGHTNING = "lightning"
    CHAIN_LIGHTNING = "chain_lightning"
    TELEPORT = "teleport"
    THUNDER_STORM = "thunder_storm"
    ENERGY_SHIELD = "energy_shield"
    LIGHTNING_MASTERY = "lightning_mastery"

    # Fire
    FIRE_BOLT = "fire_bolt"
    WARMTH = "warmth"
    INFERNO = "inferno"
    BLAZE = "blaze"
    FIRE_BALL = "fire_ball"
    FIRE_WALL = "fire_wall"
    ENCHANT = "enchant"
    METEOR = "meteor"
    FIRE_MASTERY = "fire_mastery"
    HYDRA = "hydra"


@dataclass
class SkillInfo:
    """Information about a skill."""
    skill: Skill
    hotkey: str
    cooldown: float = 0.0  # Seconds between casts
    is_buff: bool = False  # Self-cast buff
    requires_target: bool = True  # Needs a target location
    cast_time: float = 0.1  # Time to cast


# Default skill configurations
DEFAULT_SKILL_INFO: Dict[Skill, SkillInfo] = {
    Skill.TELEPORT: SkillInfo(Skill.TELEPORT, "f3", cooldown=0.0, requires_target=True, cast_time=0.1),
    Skill.BLIZZARD: SkillInfo(Skill.BLIZZARD, "f4", cooldown=1.8, requires_target=True, cast_time=0.2),
    Skill.STATIC_FIELD: SkillInfo(Skill.STATIC_FIELD, "f5", cooldown=0.5, requires_target=False, cast_time=0.1),
    Skill.FROZEN_ARMOR: SkillInfo(Skill.FROZEN_ARMOR, "f6", cooldown=0.0, is_buff=True, requires_target=False, cast_time=0.2),
    Skill.GLACIAL_SPIKE: SkillInfo(Skill.GLACIAL_SPIKE, "f5", cooldown=0.0, requires_target=True, cast_time=0.1),
    Skill.ICE_BLAST: SkillInfo(Skill.ICE_BLAST, "f6", cooldown=0.0, requires_target=True, cast_time=0.1),
    Skill.NOVA: SkillInfo(Skill.NOVA, "f4", cooldown=0.0, requires_target=False, cast_time=0.1),
    Skill.FROZEN_ORB: SkillInfo(Skill.FROZEN_ORB, "f4", cooldown=1.0, requires_target=True, cast_time=0.2),
}


@dataclass
class CombatState:
    """Current combat state."""
    in_combat: bool = False
    target_position: Optional[Tuple[int, int]] = None
    last_skill_times: Dict[Skill, float] = field(default_factory=dict)
    buffs_active: Dict[Skill, float] = field(default_factory=dict)  # skill -> expiry time


class SorceressCombat:
    """
    Combat handler for Sorceress class.

    Implements Blizzard Sorceress combat pattern with:
    - Teleport for movement
    - Blizzard as main damage
    - Static Field for boss health reduction
    - Glacial Spike for single target / freeze
    """

    # Screen center for relative positioning (1920x1080)
    SCREEN_CENTER = (960, 540)

    # Buff durations in seconds
    BUFF_DURATIONS = {
        Skill.FROZEN_ARMOR: 144.0,  # 144 seconds base
        Skill.SHIVER_ARMOR: 144.0,
        Skill.CHILLING_ARMOR: 144.0,
        Skill.ENERGY_SHIELD: 144.0,
        Skill.THUNDER_STORM: 24.0,
    }

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
    ):
        """
        Initialize Sorceress combat.

        Args:
            config: Bot configuration (for hotkeys)
            input_ctrl: Input controller
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.log = get_logger()

        # Combat state
        self.state = CombatState()

        # Setup skill hotkeys from config
        self._setup_skills()

        # Timing
        self.cast_delay = 0.1  # Delay after casting
        self.teleport_delay = 0.15  # Delay after teleport

    def _setup_skills(self) -> None:
        """Setup skill info from config hotkeys."""
        self.skills: Dict[Skill, SkillInfo] = {}

        # Map config hotkey names to skills
        hotkey_skill_map = {
            "teleport": Skill.TELEPORT,
            "blizzard": Skill.BLIZZARD,
            "static_field": Skill.STATIC_FIELD,
            "frozen_armor": Skill.FROZEN_ARMOR,
            "glacial_spike": Skill.GLACIAL_SPIKE,
            "ice_blast": Skill.ICE_BLAST,
            "nova": Skill.NOVA,
            "frozen_orb": Skill.FROZEN_ORB,
        }

        for hotkey_name, skill in hotkey_skill_map.items():
            hotkey = self.config.hotkeys.get(hotkey_name)
            if hotkey and skill in DEFAULT_SKILL_INFO:
                info = DEFAULT_SKILL_INFO[skill]
                self.skills[skill] = SkillInfo(
                    skill=skill,
                    hotkey=hotkey,
                    cooldown=info.cooldown,
                    is_buff=info.is_buff,
                    requires_target=info.requires_target,
                    cast_time=info.cast_time,
                )

    def can_cast(self, skill: Skill) -> bool:
        """
        Check if skill can be cast (off cooldown).

        Args:
            skill: Skill to check

        Returns:
            True if skill can be cast
        """
        if skill not in self.skills:
            return False

        info = self.skills[skill]
        if info.cooldown <= 0:
            return True

        last_cast = self.state.last_skill_times.get(skill, 0)
        return time.time() - last_cast >= info.cooldown

    def get_cooldown_remaining(self, skill: Skill) -> float:
        """Get remaining cooldown for a skill."""
        if skill not in self.skills:
            return 0.0

        info = self.skills[skill]
        if info.cooldown <= 0:
            return 0.0

        last_cast = self.state.last_skill_times.get(skill, 0)
        remaining = info.cooldown - (time.time() - last_cast)
        return max(0.0, remaining)

    def _record_cast(self, skill: Skill) -> None:
        """Record skill cast time."""
        self.state.last_skill_times[skill] = time.time()

    def _cast_skill(
        self,
        skill: Skill,
        target: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        Cast a skill.

        Args:
            skill: Skill to cast
            target: Target position (for targeted skills)

        Returns:
            True if cast initiated
        """
        if skill not in self.skills:
            self.log.warning(f"Skill not configured: {skill.value}")
            return False

        info = self.skills[skill]

        if not self.can_cast(skill):
            remaining = self.get_cooldown_remaining(skill)
            self.log.debug(f"{skill.value} on cooldown ({remaining:.1f}s remaining)")
            return False

        # Press skill hotkey
        self.input.press(info.hotkey)
        time.sleep(0.05)

        # Cast at target or self
        if info.requires_target and target:
            self.input.click(target[0], target[1], button="right")
        elif info.is_buff or not info.requires_target:
            # Self-cast or AoE around self
            self.input.click(button="right")
        else:
            # Default: cast at screen center
            self.input.click(self.SCREEN_CENTER[0], self.SCREEN_CENTER[1], button="right")

        time.sleep(info.cast_time)
        self._record_cast(skill)

        self.log.debug(f"Cast {skill.value}" + (f" at {target}" if target else ""))
        return True

    def cast_teleport(self, target: Tuple[int, int]) -> bool:
        """
        Teleport to target position.

        Args:
            target: Screen position to teleport to

        Returns:
            True if teleport cast
        """
        result = self._cast_skill(Skill.TELEPORT, target)
        if result:
            time.sleep(self.teleport_delay)
        return result

    def cast_blizzard(self, target: Tuple[int, int]) -> bool:
        """
        Cast Blizzard at target position.

        Args:
            target: Screen position for Blizzard

        Returns:
            True if Blizzard cast
        """
        return self._cast_skill(Skill.BLIZZARD, target)

    def cast_static_field(self) -> bool:
        """
        Cast Static Field (reduces nearby enemy HP by 25%).

        Returns:
            True if Static Field cast
        """
        return self._cast_skill(Skill.STATIC_FIELD)

    def cast_glacial_spike(self, target: Tuple[int, int]) -> bool:
        """
        Cast Glacial Spike at target (freeze + damage).

        Args:
            target: Target position

        Returns:
            True if cast
        """
        return self._cast_skill(Skill.GLACIAL_SPIKE, target)

    def cast_frozen_armor(self) -> bool:
        """
        Cast Frozen Armor buff.

        Returns:
            True if cast
        """
        result = self._cast_skill(Skill.FROZEN_ARMOR)
        if result:
            duration = self.BUFF_DURATIONS.get(Skill.FROZEN_ARMOR, 144.0)
            self.state.buffs_active[Skill.FROZEN_ARMOR] = time.time() + duration
        return result

    def cast_nova(self) -> bool:
        """
        Cast Nova (AoE lightning damage).

        Returns:
            True if cast
        """
        return self._cast_skill(Skill.NOVA)

    def is_buff_active(self, skill: Skill) -> bool:
        """Check if a buff is still active."""
        expiry = self.state.buffs_active.get(skill, 0)
        return time.time() < expiry

    def ensure_buffs(self) -> None:
        """Ensure all defensive buffs are active."""
        if not self.is_buff_active(Skill.FROZEN_ARMOR):
            self.log.info("Refreshing Frozen Armor")
            self.cast_frozen_armor()

    def attack_pattern(
        self,
        target: Tuple[int, int],
        use_static: bool = False,
    ) -> None:
        """
        Execute standard attack pattern on target.

        Pattern: Teleport close -> Static Field (if boss) -> Blizzard

        Args:
            target: Target position
            use_static: Use Static Field (for bosses)
        """
        self.log.info(f"Attack pattern at {target}")

        # Teleport near target (slightly offset to avoid being on top)
        teleport_pos = (target[0] - 100, target[1])
        self.cast_teleport(teleport_pos)

        # Static Field for bosses (reduces HP by 25% per cast)
        if use_static:
            for _ in range(3):  # Cast a few times
                if self.can_cast(Skill.STATIC_FIELD):
                    self.cast_static_field()
                    time.sleep(0.3)

        # Main damage: Blizzard
        if self.can_cast(Skill.BLIZZARD):
            self.cast_blizzard(target)

    def kite_and_attack(
        self,
        target: Tuple[int, int],
        kite_distance: int = 200,
    ) -> None:
        """
        Kite away from target while attacking.

        Used when taking damage or enemies are too close.

        Args:
            target: Enemy position
            kite_distance: Distance to maintain from target
        """
        self.log.info("Kiting and attacking")

        # Calculate kite position (away from target)
        # Move towards screen center if target is between us and center
        if target[0] < self.SCREEN_CENTER[0]:
            kite_x = target[0] + kite_distance
        else:
            kite_x = target[0] - kite_distance

        if target[1] < self.SCREEN_CENTER[1]:
            kite_y = target[1] + kite_distance
        else:
            kite_y = target[1] - kite_distance

        # Teleport to kite position
        self.cast_teleport((kite_x, kite_y))

        # Cast Blizzard on original target position
        if self.can_cast(Skill.BLIZZARD):
            self.cast_blizzard(target)

    def boss_attack_pattern(
        self,
        target: Tuple[int, int],
        static_casts: int = 5,
    ) -> None:
        """
        Attack pattern optimized for bosses.

        Uses multiple Static Fields then Blizzard spam.

        Args:
            target: Boss position
            static_casts: Number of Static Field casts
        """
        self.log.info(f"Boss attack pattern at {target}")

        # Teleport close
        teleport_pos = (target[0] - 150, target[1])
        self.cast_teleport(teleport_pos)

        # Spam Static Field to reduce boss HP
        for i in range(static_casts):
            if self.can_cast(Skill.STATIC_FIELD):
                self.cast_static_field()
                time.sleep(0.4)

        # Blizzard on boss
        if self.can_cast(Skill.BLIZZARD):
            self.cast_blizzard(target)

        # Keep casting Blizzard while waiting for boss to die
        # In real implementation, would check if boss is dead

    def clear_area(
        self,
        positions: List[Tuple[int, int]],
    ) -> None:
        """
        Clear an area by casting Blizzard at multiple positions.

        Args:
            positions: List of positions to Blizzard
        """
        self.log.info(f"Clearing area with {len(positions)} Blizzards")

        for pos in positions:
            if self.can_cast(Skill.BLIZZARD):
                self.cast_blizzard(pos)
                # Wait for Blizzard cooldown
                time.sleep(2.0)

    def use_potion(self, slot: int = 1) -> None:
        """
        Use a potion from belt.

        Args:
            slot: Belt slot (1-4)
        """
        self.input.use_potion(slot)

    def emergency_teleport(self) -> None:
        """
        Emergency teleport to safety (screen center/town direction).

        Used when health is critically low.
        """
        self.log.warning("Emergency teleport!")
        # Teleport towards top-left (usually safer/towards town)
        self.cast_teleport((200, 200))
