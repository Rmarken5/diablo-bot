"""Menu navigation for D2R Bot."""

import time
from enum import Enum, auto
from typing import Optional, Tuple

from src.data.models import Config
from src.input.controller import InputController
from src.utils.logger import get_logger


class MenuState(Enum):
    """Detected menu states."""
    UNKNOWN = auto()
    MAIN_MENU = auto()
    CHARACTER_SELECT = auto()
    LOBBY = auto()
    CREATE_GAME = auto()
    JOIN_GAME = auto()
    LOADING = auto()
    IN_GAME = auto()


# Template names for menu detection
MENU_TEMPLATES = {
    MenuState.MAIN_MENU: "screens/main_menu",
    MenuState.CHARACTER_SELECT: "screens/character_select",
    MenuState.LOBBY: "screens/lobby",
    MenuState.CREATE_GAME: "screens/create_game",
    MenuState.LOADING: "screens/loading",
}

# Button template names
BUTTON_TEMPLATES = {
    "play": "buttons/play_button",
    "single_player": "buttons/single_player",
    "online": "buttons/online_button",
    "create_game": "buttons/create_game",
    "join_game": "buttons/join_game",
    "ok": "buttons/ok_button",
    "cancel": "buttons/cancel_button",
    "save_exit": "buttons/save_exit",
}


class MenuNavigator:
    """
    Handles navigation through D2R menus.

    Provides methods to navigate from main menu to in-game,
    including character selection and game creation.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        input_ctrl: Optional[InputController] = None,
        template_matcher=None,
        screen_capture=None,
    ):
        """
        Initialize menu navigator.

        Args:
            config: Bot configuration
            input_ctrl: Input controller for mouse/keyboard
            template_matcher: Template matcher for UI detection
            screen_capture: Screen capture for getting frames
        """
        self.config = config or Config()
        self.input = input_ctrl or InputController()
        self.matcher = template_matcher
        self.capture = screen_capture
        self.log = get_logger()

        # Timing configuration
        self.click_delay = 0.5  # Delay after clicking buttons
        self.transition_timeout = 10.0  # Max wait for screen transitions
        self.load_timeout = 60.0  # Max wait for game to load

    def detect_menu_state(self) -> MenuState:
        """
        Detect current menu state from screen.

        Returns:
            Detected MenuState
        """
        if self.capture is None or self.matcher is None:
            self.log.warning("No capture/matcher available, returning UNKNOWN")
            return MenuState.UNKNOWN

        screen = self.capture.grab()

        # Check each menu template
        for state, template_name in MENU_TEMPLATES.items():
            match = self.matcher.find(screen, template_name, threshold=0.7)
            if match:
                self.log.debug(f"Detected menu state: {state.name}")
                return state

        return MenuState.UNKNOWN

    def find_button(self, button_name: str) -> Optional[Tuple[int, int]]:
        """
        Find a button on screen.

        Args:
            button_name: Name of button (key in BUTTON_TEMPLATES)

        Returns:
            (x, y) center position of button, or None if not found
        """
        if self.capture is None or self.matcher is None:
            return None

        template_name = BUTTON_TEMPLATES.get(button_name)
        if not template_name:
            self.log.warning(f"Unknown button: {button_name}")
            return None

        screen = self.capture.grab()
        match = self.matcher.find(screen, template_name, threshold=0.8)

        if match:
            return match.center

        return None

    def click_button(self, button_name: str, timeout: float = 5.0) -> bool:
        """
        Find and click a button.

        Args:
            button_name: Name of button to click
            timeout: Max time to wait for button to appear

        Returns:
            True if button was found and clicked
        """
        start = time.time()

        while time.time() - start < timeout:
            pos = self.find_button(button_name)
            if pos:
                self.log.info(f"Clicking {button_name} at {pos}")
                self.input.click(pos[0], pos[1])
                time.sleep(self.click_delay)
                return True
            time.sleep(0.2)

        self.log.warning(f"Button not found: {button_name}")
        return False

    def wait_for_state(
        self,
        target: MenuState,
        timeout: float = None,
    ) -> bool:
        """
        Wait for a specific menu state.

        Args:
            target: State to wait for
            timeout: Max wait time (uses transition_timeout if None)

        Returns:
            True if state was reached
        """
        timeout = timeout or self.transition_timeout
        start = time.time()

        while time.time() - start < timeout:
            current = self.detect_menu_state()
            if current == target:
                return True
            time.sleep(0.3)

        self.log.warning(f"Timeout waiting for {target.name}")
        return False

    def navigate_to_lobby(self, online: bool = True) -> bool:
        """
        Navigate from main menu to lobby/character select.

        Args:
            online: True for online play, False for single player

        Returns:
            True if reached lobby
        """
        current = self.detect_menu_state()

        if current == MenuState.LOBBY:
            return True

        if current == MenuState.CHARACTER_SELECT:
            # Already past lobby for single player
            return True

        if current != MenuState.MAIN_MENU:
            self.log.warning(f"Not at main menu, currently: {current.name}")
            return False

        # Click play button
        if not self.click_button("play"):
            return False

        # Choose online or single player
        button = "online" if online else "single_player"
        if not self.click_button(button):
            return False

        # Wait for transition
        target = MenuState.LOBBY if online else MenuState.CHARACTER_SELECT
        return self.wait_for_state(target)

    def select_character(self, name: str = None) -> bool:
        """
        Select a character to play.

        Args:
            name: Character name to select (uses config if None)

        Returns:
            True if character was selected
        """
        char_name = name or self.config.character_name

        current = self.detect_menu_state()
        if current not in (MenuState.CHARACTER_SELECT, MenuState.LOBBY):
            self.log.warning(f"Not at character select, currently: {current.name}")
            return False

        # For now, assume first character or use OCR to find name
        # This is a simplified implementation - real version would
        # scan character names and click the correct one

        self.log.info(f"Selecting character: {char_name}")

        # Double-click on character (assuming it's selected or first)
        # In reality, we'd find the character name via OCR
        # For single player, character is often pre-selected
        self.input.double_click()
        time.sleep(self.click_delay)

        return True

    def create_game(
        self,
        game_name: str = None,
        password: str = "",
        difficulty: str = "hell",
    ) -> bool:
        """
        Create a new game.

        Args:
            game_name: Name for the game (auto-generated if None)
            password: Game password (empty for no password)
            difficulty: Difficulty level (normal, nightmare, hell)

        Returns:
            True if game creation started
        """
        current = self.detect_menu_state()
        if current != MenuState.LOBBY:
            self.log.warning(f"Not in lobby, currently: {current.name}")
            return False

        # Click create game button
        if not self.click_button("create_game"):
            return False

        # Wait for create game screen
        if not self.wait_for_state(MenuState.CREATE_GAME):
            return False

        # Generate game name if not provided
        if game_name is None:
            import random
            game_name = f"bot{random.randint(1000, 9999)}"

        # Type game name (assuming cursor is in name field)
        self.log.info(f"Creating game: {game_name}")
        self.input.type_text(game_name)
        time.sleep(0.2)

        # Tab to password field and enter password
        if password:
            self.input.press("tab")
            time.sleep(0.1)
            self.input.type_text(password)

        # Select difficulty (would need to click appropriate button)
        # This is simplified - real implementation would detect current
        # difficulty and click to change if needed

        # Click OK/Create button
        return self.click_button("ok")

    def join_game(self, game_name: str, password: str = "") -> bool:
        """
        Join an existing game.

        Args:
            game_name: Name of game to join
            password: Game password if required

        Returns:
            True if join was initiated
        """
        current = self.detect_menu_state()
        if current != MenuState.LOBBY:
            self.log.warning(f"Not in lobby, currently: {current.name}")
            return False

        # Click join game button
        if not self.click_button("join_game"):
            return False

        # Type game name
        self.input.type_text(game_name)
        time.sleep(0.2)

        # Tab to password and enter if provided
        if password:
            self.input.press("tab")
            time.sleep(0.1)
            self.input.type_text(password)

        # Click OK
        return self.click_button("ok")

    def wait_for_load(self, timeout: float = None) -> bool:
        """
        Wait for game to finish loading.

        Args:
            timeout: Max wait time (uses load_timeout if None)

        Returns:
            True if game loaded successfully
        """
        timeout = timeout or self.load_timeout
        self.log.info("Waiting for game to load...")

        start = time.time()

        while time.time() - start < timeout:
            state = self.detect_menu_state()

            if state == MenuState.IN_GAME:
                self.log.info("Game loaded successfully")
                return True

            if state == MenuState.LOADING:
                # Still loading, continue waiting
                time.sleep(0.5)
                continue

            if state in (MenuState.MAIN_MENU, MenuState.LOBBY):
                # Kicked back to menu (failed to load)
                self.log.warning("Load failed, returned to menu")
                return False

            time.sleep(0.5)

        self.log.warning("Load timeout")
        return False

    def navigate_to_game(self, online: bool = True) -> bool:
        """
        Full navigation from main menu to in-game.

        Args:
            online: True for online play

        Returns:
            True if successfully entered game
        """
        self.log.info("Starting game navigation...")

        # Step 1: Get to lobby/character select
        if not self.navigate_to_lobby(online):
            return False

        # Step 2: Select character
        if not self.select_character():
            return False

        # Step 3: Create/enter game
        if online:
            # Online: Create game from lobby
            if not self.create_game():
                return False
        else:
            # Single player: Character select leads directly to game
            # Just need to wait for load
            pass

        # Step 4: Wait for load
        return self.wait_for_load()

    def exit_game(self) -> bool:
        """
        Exit current game (save and exit).

        Returns:
            True if successfully exited
        """
        self.log.info("Exiting game...")

        # Press Escape to open menu
        self.input.press("escape")
        time.sleep(0.5)

        # Click "Save and Exit" button
        # Template would be "buttons/save_exit"
        if self.click_button("save_exit", timeout=3.0):
            return self.wait_for_state(MenuState.CHARACTER_SELECT, timeout=10.0)

        return False

    def quit_to_menu(self) -> bool:
        """
        Quit to main menu from character select.

        Returns:
            True if at main menu
        """
        current = self.detect_menu_state()

        if current == MenuState.MAIN_MENU:
            return True

        if current == MenuState.IN_GAME:
            if not self.exit_game():
                return False

        # From character select, press Escape
        self.input.press("escape")
        time.sleep(0.5)

        return self.wait_for_state(MenuState.MAIN_MENU)
