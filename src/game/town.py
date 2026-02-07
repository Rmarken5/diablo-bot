"""Town navigation and NPC interaction for D2R Bot."""

import time
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from src.data.models import Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class Act(Enum):
    """Game acts."""
    ACT1 = 1  # Rogue Encampment
    ACT2 = 2  # Lut Gholein
    ACT3 = 3  # Kurast Docks
    ACT4 = 4  # Pandemonium Fortress
    ACT5 = 5  # Harrogath


class NPC(Enum):
    """Town NPCs by act."""
    # Act 5 - Harrogath (primary focus)
    MALAH = "malah"          # Healer
    LARZUK = "larzuk"        # Smith/repair
    QUAL_KEHK = "qual_kehk"  # Hire mercenary
    ANYA = "anya"            # Red portal to Pindleskin
    NIHLATHAK = "nihlathak"  # Personalize items
    CAIN = "cain"            # Identify items

    # Act 1 - Rogue Encampment
    AKARA = "akara"          # Healer
    CHARSI = "charsi"        # Smith
    KASHYA = "kashya"        # Hire merc
    GHEED = "gheed"          # Gamble

    # Act 2 - Lut Gholein
    FARA = "fara"            # Healer/Smith
    DROGNAN = "drognan"      # Magic vendor
    ATMA = "atma"            # Tavern
    LYSANDER = "lysander"    # Potions

    # Act 3 - Kurast Docks
    ORMUS = "ormus"          # Magic vendor
    HRATLI = "hratli"        # Smith
    ALKOR = "alkor"          # Potions

    # Act 4 - Pandemonium Fortress
    JAMELLA = "jamella"      # Healer/vendor
    HALBU = "halbu"          # Smith
    TYRAEL = "tyrael"        # Quest


# Template names for NPCs
NPC_TEMPLATES = {
    # Act 5
    NPC.MALAH: "npcs/malah",
    NPC.LARZUK: "npcs/larzuk",
    NPC.QUAL_KEHK: "npcs/qual_kehk",
    NPC.ANYA: "npcs/anya",
    NPC.CAIN: "npcs/cain",
    # Other acts can be added as needed
}

# Template names for town objects
OBJECT_TEMPLATES = {
    "stash": "hud/stash",
    "waypoint": "hud/waypoint",
    "portal": "hud/portal",
    "red_portal": "hud/red_portal",
}

# NPC dialog button templates
DIALOG_TEMPLATES = {
    "trade": "dialog/trade",
    "repair": "dialog/repair",
    "heal": "dialog/heal",
    "identify": "dialog/identify_all",
    "gamble": "dialog/gamble",
}

# Screen positions for common actions (1920x1080)
# These are fallback positions when templates aren't found
SCREEN_POSITIONS = {
    # Act 1 Rogue Encampment approximate positions (1920x1080)
    "act1_stash": (950, 450),
    "act1_waypoint": (980, 380),
    "act1_akara": (850, 350),
    "act1_charsi": (1050, 350),
    "act1_kashya": (920, 320),
    "act1_cain": (880, 400),

    # Act 5 Harrogath approximate positions
    "act5_stash": (175, 280),
    "act5_waypoint": (100, 130),
    "act5_malah": (450, 130),
    "act5_larzuk": (275, 100),
    "act5_anya": (100, 450),
    "act5_red_portal": (80, 520),
    "act5_cain": (350, 200),
}


class TownManager:
    """
    Manages town navigation and NPC interactions.

    Provides methods to move around town, interact with NPCs,
    use stash, waypoints, and portals.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        template_matcher=None,
        screen_capture=None,
    ):
        """
        Initialize town manager.

        Args:
            config: Bot configuration
            input_ctrl: Input controller
            template_matcher: Template matcher for detection
            screen_capture: Screen capture
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.matcher = template_matcher
        self.capture = screen_capture
        self.log = get_logger()

        # Current act (default to Act 5 for Pindleskin runs)
        self.current_act = Act.ACT5

        # Timing
        self.move_timeout = 5.0
        self.interact_delay = 0.5
        self.dialog_timeout = 3.0

    def set_act(self, act: Act) -> None:
        """Set current act for position lookups."""
        self.current_act = act
        self.log.info(f"Set current act to {act.name}")

    def find_object(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Find a town object on screen.

        Args:
            name: Object name (stash, waypoint, portal, etc.)

        Returns:
            (x, y) position or None if not found
        """
        if self.capture is None or self.matcher is None:
            return None

        template_name = OBJECT_TEMPLATES.get(name)
        if not template_name:
            self.log.warning(f"Unknown object: {name}")
            return None

        screen = self.capture.grab()
        match = self.matcher.find(screen, template_name, threshold=0.75)

        if match:
            return match.center

        # Fallback to hardcoded position
        fallback_key = f"act{self.current_act.value}_{name}"
        fallback = SCREEN_POSITIONS.get(fallback_key)
        if fallback:
            self.log.debug(f"Using fallback position for {name}: {fallback}")
            return fallback

        return None

    def find_npc(self, npc: NPC) -> Optional[Tuple[int, int]]:
        """
        Find an NPC on screen.

        Args:
            npc: NPC to find

        Returns:
            (x, y) position or None if not found
        """
        if self.capture is None or self.matcher is None:
            # Use fallback position
            fallback_key = f"act{self.current_act.value}_{npc.value}"
            fallback = SCREEN_POSITIONS.get(fallback_key)
            if fallback:
                return fallback
            return None

        template_name = NPC_TEMPLATES.get(npc)
        if not template_name:
            self.log.warning(f"No template for NPC: {npc.value}")
            return None

        screen = self.capture.grab()
        match = self.matcher.find(screen, template_name, threshold=0.75)

        if match:
            return match.center

        # Try fallback
        fallback_key = f"act{self.current_act.value}_{npc.value}"
        return SCREEN_POSITIONS.get(fallback_key)

    def move_to(self, x: int, y: int) -> bool:
        """
        Move character to position by clicking.

        Args:
            x: Target X position on screen
            y: Target Y position on screen

        Returns:
            True if movement initiated
        """
        self.log.debug(f"Moving to ({x}, {y})")
        self.input.click(x, y)
        time.sleep(0.3)  # Wait for movement to start
        return True

    def teleport_to(self, x: int, y: int) -> bool:
        """
        Teleport to position.

        Args:
            x: Target X position
            y: Target Y position

        Returns:
            True if teleport initiated
        """
        # Assuming teleport is on right-click
        self.log.debug(f"Teleporting to ({x}, {y})")
        self.input.right_click(x, y)
        time.sleep(0.2)
        return True

    def go_to_npc(self, npc: NPC, use_teleport: bool = True) -> bool:
        """
        Move to an NPC.

        Args:
            npc: NPC to go to
            use_teleport: Use teleport if available

        Returns:
            True if reached NPC
        """
        self.log.info(f"Going to NPC: {npc.value}")

        pos = self.find_npc(npc)
        if pos is None:
            self.log.warning(f"Could not find NPC: {npc.value}")
            return False

        if use_teleport:
            self.teleport_to(pos[0], pos[1])
        else:
            self.move_to(pos[0], pos[1])

        # Wait for movement
        time.sleep(0.5)
        return True

    def interact_with_npc(self, npc: NPC) -> bool:
        """
        Interact with an NPC (open dialog).

        Args:
            npc: NPC to interact with

        Returns:
            True if dialog opened
        """
        self.log.info(f"Interacting with NPC: {npc.value}")

        pos = self.find_npc(npc)
        if pos is None:
            self.log.warning(f"Could not find NPC: {npc.value}")
            return False

        # Click on NPC to interact
        self.input.click(pos[0], pos[1])
        time.sleep(self.interact_delay)

        # TODO: Verify dialog opened via template matching
        return True

    def click_dialog_option(self, option: str) -> bool:
        """
        Click a dialog option.

        Args:
            option: Dialog option (trade, repair, heal, etc.)

        Returns:
            True if clicked
        """
        if self.capture is None or self.matcher is None:
            self.log.warning("No capture/matcher for dialog detection")
            return False

        template_name = DIALOG_TEMPLATES.get(option)
        if not template_name:
            self.log.warning(f"Unknown dialog option: {option}")
            return False

        screen = self.capture.grab()
        match = self.matcher.find(screen, template_name, threshold=0.8)

        if match:
            self.log.info(f"Clicking dialog option: {option}")
            self.input.click(match.center[0], match.center[1])
            time.sleep(self.interact_delay)
            return True

        return False

    def open_stash(self) -> bool:
        """
        Go to and open stash.

        Returns:
            True if stash opened
        """
        self.log.info("Opening stash")

        pos = self.find_object("stash")
        if pos is None:
            self.log.warning("Could not find stash")
            return False

        self.input.click(pos[0], pos[1])
        time.sleep(self.interact_delay)

        # TODO: Verify stash is open
        return True

    def close_stash(self) -> None:
        """Close stash (press Escape)."""
        self.input.press("escape")
        time.sleep(0.3)

    def use_waypoint(self, destination: str = None) -> bool:
        """
        Use waypoint to travel.

        Args:
            destination: Destination waypoint name (if None, just opens menu)

        Returns:
            True if waypoint used
        """
        self.log.info(f"Using waypoint{f' to {destination}' if destination else ''}")

        pos = self.find_object("waypoint")
        if pos is None:
            self.log.warning("Could not find waypoint")
            return False

        self.input.click(pos[0], pos[1])
        time.sleep(self.interact_delay)

        # If destination specified, would need to click it
        # For now, just opens the waypoint menu
        # TODO: Add waypoint destination selection

        return True

    def close_waypoint(self) -> None:
        """Close waypoint menu."""
        self.input.press("escape")
        time.sleep(0.3)

    def go_to_red_portal(self) -> bool:
        """
        Go to Anya's red portal (Pindleskin entrance).

        Returns:
            True if at portal
        """
        self.log.info("Going to red portal")

        pos = self.find_object("red_portal")
        if pos is None:
            # Try finding Anya and moving near her
            anya_pos = self.find_npc(NPC.ANYA)
            if anya_pos:
                # Red portal is near Anya
                pos = (anya_pos[0] - 50, anya_pos[1] + 100)
            else:
                pos = SCREEN_POSITIONS.get("act5_red_portal")

        if pos:
            self.teleport_to(pos[0], pos[1])
            time.sleep(0.3)
            return True

        return False

    def enter_red_portal(self) -> bool:
        """
        Enter Anya's red portal.

        Returns:
            True if portal entered
        """
        self.log.info("Entering red portal")

        pos = self.find_object("red_portal")
        if pos is None:
            pos = SCREEN_POSITIONS.get("act5_red_portal")

        if pos:
            # Click to enter
            self.input.click(pos[0], pos[1])
            time.sleep(1.0)  # Wait for loading
            return True

        return False

    def go_to_cain(self) -> bool:
        """
        Go to Deckard Cain for identification.

        Returns:
            True if reached Cain
        """
        return self.go_to_npc(NPC.CAIN)

    def identify_items(self) -> bool:
        """
        Have Cain identify all items.

        Returns:
            True if identification started
        """
        if not self.go_to_cain():
            return False

        if not self.interact_with_npc(NPC.CAIN):
            return False

        return self.click_dialog_option("identify")

    def go_to_healer(self) -> bool:
        """
        Go to act-appropriate healer.

        Returns:
            True if reached healer
        """
        healers = {
            Act.ACT1: NPC.AKARA,
            Act.ACT2: NPC.FARA,
            Act.ACT3: NPC.ORMUS,
            Act.ACT4: NPC.JAMELLA,
            Act.ACT5: NPC.MALAH,
        }
        healer = healers.get(self.current_act, NPC.MALAH)
        return self.go_to_npc(healer)

    def heal(self) -> bool:
        """
        Get healed by NPC.

        Returns:
            True if healed
        """
        if not self.go_to_healer():
            return False

        healers = {
            Act.ACT1: NPC.AKARA,
            Act.ACT2: NPC.FARA,
            Act.ACT3: NPC.ORMUS,
            Act.ACT4: NPC.JAMELLA,
            Act.ACT5: NPC.MALAH,
        }
        healer = healers.get(self.current_act, NPC.MALAH)

        if not self.interact_with_npc(healer):
            return False

        return self.click_dialog_option("heal")

    def go_to_repair(self) -> bool:
        """
        Go to act-appropriate smith for repair.

        Returns:
            True if reached smith
        """
        smiths = {
            Act.ACT1: NPC.CHARSI,
            Act.ACT2: NPC.FARA,
            Act.ACT3: NPC.HRATLI,
            Act.ACT4: NPC.HALBU,
            Act.ACT5: NPC.LARZUK,
        }
        smith = smiths.get(self.current_act, NPC.LARZUK)
        return self.go_to_npc(smith)

    def repair_items(self) -> bool:
        """
        Repair all items at smith.

        Returns:
            True if repair initiated
        """
        smiths = {
            Act.ACT1: NPC.CHARSI,
            Act.ACT2: NPC.FARA,
            Act.ACT3: NPC.HRATLI,
            Act.ACT4: NPC.HALBU,
            Act.ACT5: NPC.LARZUK,
        }
        smith = smiths.get(self.current_act, NPC.LARZUK)

        if not self.go_to_npc(smith):
            return False

        if not self.interact_with_npc(smith):
            return False

        # Click trade, then repair
        if not self.click_dialog_option("trade"):
            return False

        return self.click_dialog_option("repair")

    def close_dialog(self) -> None:
        """Close any open NPC dialog."""
        self.input.press("escape")
        time.sleep(0.3)

    def town_routine(self, inventory_manager=None) -> bool:
        """
        Execute standard town routine.

        Heal -> Repair -> Identify -> Stash

        Args:
            inventory_manager: InventoryManager for stashing items

        Returns:
            True if routine completed
        """
        self.log.info("Starting town routine")

        # 1. Heal
        if self.go_to_healer():
            self.interact_with_npc(NPC.MALAH)
            self.click_dialog_option("heal")
            self.close_dialog()

        # 2. Repair (if needed - would check durability)
        # self.repair_items()
        # self.close_dialog()

        # 3. Identify items
        if self.go_to_cain():
            self.identify_items()
            self.close_dialog()

        # 4. Stash items
        if self.open_stash():
            time.sleep(0.5)
            if inventory_manager:
                inventory_manager.stash_all_items()
            time.sleep(0.3)
            self.close_stash()

        self.log.info("Town routine complete")
        return True
