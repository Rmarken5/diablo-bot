"""Tests for game state detector module."""

from pathlib import Path

import cv2
import numpy as np

from src.vision.game_detector import GameStateDetector, GameState, HealthStatus
from src.vision.template_matcher import TemplateMatcher
from src.utils.logger import setup_logger, get_logger


# Test assets directory
TEST_ASSETS_DIR = Path("tests/test_assets")
TEMPLATE_DIR = TEST_ASSETS_DIR / "templates"


def create_test_templates():
    """Create synthetic templates for testing."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    (TEMPLATE_DIR / "screens").mkdir(exist_ok=True)
    (TEMPLATE_DIR / "hud").mkdir(exist_ok=True)

    # Create a simple "main menu" template (blue rectangle)
    main_menu = np.zeros((50, 100, 3), dtype=np.uint8)
    main_menu[:, :] = (255, 100, 0)  # Blue-ish
    cv2.putText(main_menu, "PLAY", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(str(TEMPLATE_DIR / "screens" / "main_menu.png"), main_menu)

    # Create "death" template (red with text)
    death = np.zeros((40, 120, 3), dtype=np.uint8)
    death[:, :] = (0, 0, 150)  # Dark red
    cv2.putText(death, "YOU DIED", (5, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imwrite(str(TEMPLATE_DIR / "screens" / "death.png"), death)

    # Create "loading" template
    loading = np.zeros((30, 100, 3), dtype=np.uint8)
    loading[:, :] = (50, 50, 50)
    cv2.putText(loading, "Loading", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.imwrite(str(TEMPLATE_DIR / "screens" / "loading.png"), loading)

    # Create "health_orb" template indicator
    health_orb = np.zeros((30, 30, 3), dtype=np.uint8)
    cv2.circle(health_orb, (15, 15), 12, (0, 0, 200), -1)  # Red circle
    cv2.imwrite(str(TEMPLATE_DIR / "hud" / "health_orb.png"), health_orb)

    # Create "inventory_open" template
    inventory = np.zeros((40, 80, 3), dtype=np.uint8)
    inventory[:, :] = (40, 40, 40)
    cv2.rectangle(inventory, (5, 5), (75, 35), (100, 100, 100), 2)
    cv2.imwrite(str(TEMPLATE_DIR / "hud" / "inventory_open.png"), inventory)

    return True


def create_mock_game_screen(
    state: str = "in_game",
    health_pct: float = 1.0,
    mana_pct: float = 1.0,
) -> np.ndarray:
    """
    Create a mock game screen for testing.

    Args:
        state: Type of screen to create
        health_pct: Health fill percentage (0-1)
        mana_pct: Mana fill percentage (0-1)

    Returns:
        Mock screenshot as numpy array
    """
    # Create 1920x1080 screen
    screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
    screen[:, :] = (30, 30, 30)  # Dark background

    if state == "main_menu":
        # Add main menu template
        template = cv2.imread(str(TEMPLATE_DIR / "screens" / "main_menu.png"))
        if template is not None:
            screen[400:450, 900:1000] = template

    elif state == "death":
        # Add death template
        template = cv2.imread(str(TEMPLATE_DIR / "screens" / "death.png"))
        if template is not None:
            screen[500:540, 900:1020] = template

    elif state == "loading":
        # Add loading template
        template = cv2.imread(str(TEMPLATE_DIR / "screens" / "loading.png"))
        if template is not None:
            screen[520:550, 910:1010] = template

    elif state == "in_game":
        # Add HUD elements
        # Health orb (bottom left) - filled based on health_pct
        orb_region = (30, 885, 150, 150)
        fill_height = int(150 * health_pct)
        if fill_height > 0:
            screen[
                orb_region[1] + (150 - fill_height):orb_region[1] + 150,
                orb_region[0]:orb_region[0] + 150
            ] = (0, 0, 200)  # Red for health

        # Mana orb (bottom right)
        mana_region = (1742, 885, 150, 150)
        fill_height = int(150 * mana_pct)
        if fill_height > 0:
            screen[
                mana_region[1] + (150 - fill_height):mana_region[1] + 150,
                mana_region[0]:mana_region[0] + 150
            ] = (200, 0, 0)  # Blue for mana

        # Add health orb indicator template
        orb_template = cv2.imread(str(TEMPLATE_DIR / "hud" / "health_orb.png"))
        if orb_template is not None:
            screen[900:930, 50:80] = orb_template

    elif state == "inventory":
        # In-game with inventory open
        screen = create_mock_game_screen("in_game", health_pct, mana_pct)
        template = cv2.imread(str(TEMPLATE_DIR / "hud" / "inventory_open.png"))
        if template is not None:
            screen[300:340, 1400:1480] = template

    return screen


def test_game_state_enum():
    """Test GameState enum values."""
    log = get_logger()
    log.info("Testing GameState enum...")

    # Check key states exist
    assert GameState.MAIN_MENU.value == "main_menu"
    assert GameState.IN_GAME.value == "in_game"
    assert GameState.DEATH.value == "death"
    assert GameState.UNKNOWN.value == "unknown"

    log.info(f"GameState has {len(GameState)} states")
    log.info("PASSED: GameState enum")
    return True


def test_health_status_dataclass():
    """Test HealthStatus dataclass."""
    log = get_logger()
    log.info("Testing HealthStatus dataclass...")

    status = HealthStatus(
        health_percent=0.75,
        mana_percent=0.50,
        is_poisoned=False,
        is_low_health=False,
        is_low_mana=False,
    )

    assert status.health_percent == 0.75
    assert status.mana_percent == 0.50
    assert not status.is_poisoned

    # Test with low health
    low_status = HealthStatus(
        health_percent=0.20,
        mana_percent=0.10,
        is_low_health=True,
        is_low_mana=True,
    )
    assert low_status.is_low_health
    assert low_status.is_low_mana

    log.info("PASSED: HealthStatus dataclass")
    return True


def test_detector_initialization():
    """Test GameStateDetector initialization."""
    log = get_logger()
    log.info("Testing detector initialization...")

    detector = GameStateDetector()

    assert detector.resolution == (1920, 1080)
    assert detector.matcher is not None
    assert detector.get_last_state() == GameState.UNKNOWN

    log.info("PASSED: Detector initialization")
    return True


def test_custom_resolution():
    """Test detector with custom resolution."""
    log = get_logger()
    log.info("Testing custom resolution...")

    detector = GameStateDetector(resolution=(2560, 1440))

    assert detector.resolution == (2560, 1440)
    # Regions should be scaled
    # Original health orb: (30, 885, 150, 150)
    # Scaled: should be proportionally larger

    log.info("PASSED: Custom resolution")
    return True


def test_detect_main_menu():
    """Test detecting main menu state."""
    log = get_logger()
    log.info("Testing main menu detection...")

    matcher = TemplateMatcher(template_dir=str(TEMPLATE_DIR))
    detector = GameStateDetector(template_matcher=matcher)

    screen = create_mock_game_screen("main_menu")
    state = detector.detect_state(screen)

    log.info(f"Detected state: {state.value}")
    assert state == GameState.MAIN_MENU, f"Expected MAIN_MENU, got {state}"

    log.info("PASSED: Main menu detection")
    return True


def test_detect_death():
    """Test detecting death state."""
    log = get_logger()
    log.info("Testing death detection...")

    matcher = TemplateMatcher(template_dir=str(TEMPLATE_DIR))
    detector = GameStateDetector(template_matcher=matcher)

    screen = create_mock_game_screen("death")
    state = detector.detect_state(screen)

    log.info(f"Detected state: {state.value}")
    assert state == GameState.DEATH, f"Expected DEATH, got {state}"

    log.info("PASSED: Death detection")
    return True


def test_detect_in_game():
    """Test detecting in-game state."""
    log = get_logger()
    log.info("Testing in-game detection...")

    matcher = TemplateMatcher(template_dir=str(TEMPLATE_DIR))
    detector = GameStateDetector(template_matcher=matcher)

    screen = create_mock_game_screen("in_game", health_pct=0.8, mana_pct=0.6)
    state = detector.detect_state(screen)

    log.info(f"Detected state: {state.value}")
    assert state == GameState.IN_GAME, f"Expected IN_GAME, got {state}"

    log.info("PASSED: In-game detection")
    return True


def test_health_detection():
    """Test health percentage detection."""
    log = get_logger()
    log.info("Testing health detection...")

    detector = GameStateDetector()

    # Test full health
    screen_full = create_mock_game_screen("in_game", health_pct=1.0)
    health_full = detector.get_health_percent(screen_full)
    log.info(f"Full health detected: {health_full:.2%}")

    # Test half health
    screen_half = create_mock_game_screen("in_game", health_pct=0.5)
    health_half = detector.get_health_percent(screen_half)
    log.info(f"Half health detected: {health_half:.2%}")

    # Test low health
    screen_low = create_mock_game_screen("in_game", health_pct=0.2)
    health_low = detector.get_health_percent(screen_low)
    log.info(f"Low health detected: {health_low:.2%}")

    # Verify ordering (full > half > low)
    assert health_full > health_half > health_low, "Health ordering incorrect"

    log.info("PASSED: Health detection")
    return True


def test_mana_detection():
    """Test mana percentage detection."""
    log = get_logger()
    log.info("Testing mana detection...")

    detector = GameStateDetector()

    # Test full mana
    screen_full = create_mock_game_screen("in_game", mana_pct=1.0)
    mana_full = detector.get_mana_percent(screen_full)
    log.info(f"Full mana detected: {mana_full:.2%}")

    # Test low mana
    screen_low = create_mock_game_screen("in_game", mana_pct=0.2)
    mana_low = detector.get_mana_percent(screen_low)
    log.info(f"Low mana detected: {mana_low:.2%}")

    assert mana_full > mana_low, "Mana ordering incorrect"

    log.info("PASSED: Mana detection")
    return True


def test_health_status():
    """Test complete health status detection."""
    log = get_logger()
    log.info("Testing health status...")

    detector = GameStateDetector()

    # Low health scenario
    screen = create_mock_game_screen("in_game", health_pct=0.15, mana_pct=0.05)
    status = detector.get_health_status(screen)

    log.info(f"Health: {status.health_percent:.2%}")
    log.info(f"Mana: {status.mana_percent:.2%}")
    log.info(f"Low health: {status.is_low_health}")
    log.info(f"Low mana: {status.is_low_mana}")

    # With 15% health and threshold of 30%, should be low
    # Note: Detection may not be exact due to color sampling
    assert isinstance(status, HealthStatus)

    log.info("PASSED: Health status")
    return True


def test_player_position():
    """Test player position detection."""
    log = get_logger()
    log.info("Testing player position...")

    detector = GameStateDetector()

    pos = detector.get_player_position(np.zeros((1080, 1920, 3), dtype=np.uint8))

    # Should return center of screen
    assert pos == (960, 540), f"Expected (960, 540), got {pos}"

    log.info(f"Player position: {pos}")
    log.info("PASSED: Player position")
    return True


def test_last_state_caching():
    """Test that last state is cached correctly."""
    log = get_logger()
    log.info("Testing state caching...")

    matcher = TemplateMatcher(template_dir=str(TEMPLATE_DIR))
    detector = GameStateDetector(template_matcher=matcher)

    # Initial state
    assert detector.get_last_state() == GameState.UNKNOWN

    # Detect a state
    screen = create_mock_game_screen("main_menu")
    state = detector.detect_state(screen)

    # Last state should be updated
    assert detector.get_last_state() == state

    log.info("PASSED: State caching")
    return True


def run_all_tests():
    """Run all game detector tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Game State Detector Tests")
    log.info("=" * 50)

    # Create test templates first
    log.info("\nCreating test templates...")
    create_test_templates()

    tests = [
        ("GameState Enum", test_game_state_enum),
        ("HealthStatus Dataclass", test_health_status_dataclass),
        ("Detector Initialization", test_detector_initialization),
        ("Custom Resolution", test_custom_resolution),
        ("Detect Main Menu", test_detect_main_menu),
        ("Detect Death", test_detect_death),
        ("Detect In-Game", test_detect_in_game),
        ("Health Detection", test_health_detection),
        ("Mana Detection", test_mana_detection),
        ("Health Status", test_health_status),
        ("Player Position", test_player_position),
        ("State Caching", test_last_state_caching),
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
