"""Tests for template matcher module."""

from pathlib import Path

import cv2
import numpy as np

from src.vision.template_matcher import TemplateMatcher, Match
from src.utils.logger import setup_logger, get_logger


# Test assets directory
TEST_ASSETS_DIR = Path("tests/test_assets")


def create_test_assets():
    """Create synthetic test images for template matching tests."""
    TEST_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Create a simple test template (red square)
    template = np.zeros((50, 50, 3), dtype=np.uint8)
    template[:, :] = (0, 0, 255)  # Red in BGR
    cv2.imwrite(str(TEST_ASSETS_DIR / "red_square.png"), template)

    # Create a test template with unique pattern
    pattern = np.zeros((30, 30, 3), dtype=np.uint8)
    pattern[10:20, 10:20] = (255, 0, 0)  # Blue square in center
    pattern[5:25, 14:16] = (0, 255, 0)   # Green cross
    pattern[14:16, 5:25] = (0, 255, 0)
    cv2.imwrite(str(TEST_ASSETS_DIR / "pattern.png"), pattern)

    # Create a screen image containing the templates
    screen = np.zeros((480, 640, 3), dtype=np.uint8)
    screen[:, :] = (50, 50, 50)  # Dark gray background

    # Place red square at (100, 100)
    screen[100:150, 100:150] = (0, 0, 255)

    # Place pattern at (300, 200)
    screen[200:230, 300:330] = pattern

    # Place multiple patterns for multi-match test
    screen[50:80, 500:530] = pattern
    screen[350:380, 400:430] = pattern

    cv2.imwrite(str(TEST_ASSETS_DIR / "test_screen.png"), screen)

    return True


def test_match_dataclass():
    """Test Match dataclass properties."""
    log = get_logger()
    log.info("Testing Match dataclass...")

    match = Match(x=100, y=200, width=50, height=30, confidence=0.95)

    assert match.center == (125, 215), f"Center should be (125, 215), got {match.center}"
    assert match.bottom_center == (125, 230), f"Bottom center wrong"
    assert match.region == (100, 200, 50, 30), f"Region wrong"
    assert match.rect == (100, 200, 150, 230), f"Rect wrong"

    log.info("PASSED: Match dataclass")
    return True


def test_template_loading():
    """Test template loading and caching."""
    log = get_logger()
    log.info("Testing template loading...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    # Load template
    template = matcher.load_template("red_square")
    assert template is not None, "Template should load"
    assert template.shape == (50, 50, 3), f"Wrong shape: {template.shape}"

    # Should be cached now
    assert "red_square" in matcher.get_cached_templates()

    # Load same template again (from cache)
    template2 = matcher.load_template("red_square")
    assert template2 is template, "Should return cached template"

    # Try loading non-existent template
    missing = matcher.load_template("nonexistent")
    assert missing is None, "Missing template should return None"

    log.info("PASSED: Template loading")
    return True


def test_single_match():
    """Test finding a single template match."""
    log = get_logger()
    log.info("Testing single match...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    # Load test screen
    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))
    assert screen is not None, "Test screen should load"

    # Find pattern (better for matching than solid colors)
    match = matcher.find(screen, "pattern", threshold=0.9)
    assert match is not None, "Should find pattern"
    # Pattern is at (300, 200)
    assert 295 <= match.x <= 305, f"X should be ~300, got {match.x}"
    assert 195 <= match.y <= 205, f"Y should be ~200, got {match.y}"
    assert match.confidence > 0.95, f"Confidence should be high: {match.confidence}"

    log.info(f"Found pattern at ({match.x}, {match.y}) conf={match.confidence:.3f}")
    log.info("PASSED: Single match")
    return True


def test_multi_match():
    """Test finding multiple template matches."""
    log = get_logger()
    log.info("Testing multi match...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))

    # Find all patterns (should find 3)
    matches = matcher.find_all(screen, "pattern", threshold=0.9)

    assert len(matches) == 3, f"Should find 3 patterns, found {len(matches)}"

    # Matches should be sorted by confidence
    for i in range(len(matches) - 1):
        assert matches[i].confidence >= matches[i+1].confidence, "Should be sorted by confidence"

    log.info(f"Found {len(matches)} patterns")
    for i, m in enumerate(matches):
        log.info(f"  Match {i+1}: ({m.x}, {m.y}) conf={m.confidence:.3f}")

    log.info("PASSED: Multi match")
    return True


def test_threshold_filtering():
    """Test that threshold correctly filters matches."""
    log = get_logger()
    log.info("Testing threshold filtering...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))

    # With very high threshold, might not find anything (or perfect matches only)
    match_high = matcher.find(screen, "red_square", threshold=0.9999)

    # With lower threshold, should definitely find
    match_low = matcher.find(screen, "red_square", threshold=0.5)
    assert match_low is not None, "Should find with low threshold"

    log.info("PASSED: Threshold filtering")
    return True


def test_no_match():
    """Test behavior when template is not found."""
    log = get_logger()
    log.info("Testing no match scenario...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    # Create a screen with random noise (no pattern present)
    np.random.seed(42)  # Reproducible
    noise_screen = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)

    # Pattern template has distinct features, won't match random noise
    match = matcher.find(noise_screen, "pattern", threshold=0.9)
    assert match is None, "Should not find pattern in noise screen"

    log.info("PASSED: No match scenario")
    return True


def test_find_any():
    """Test finding any template from a list."""
    log = get_logger()
    log.info("Testing find_any...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))

    # Should find first matching template
    result = matcher.find_any(screen, ["nonexistent", "red_square", "pattern"])

    assert result is not None, "Should find a template"
    name, match = result
    assert name == "red_square", f"Should find red_square first, got {name}"

    log.info(f"Found '{name}' at ({match.x}, {match.y})")
    log.info("PASSED: find_any")
    return True


def test_find_best():
    """Test finding best matching template from a list."""
    log = get_logger()
    log.info("Testing find_best...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))

    result = matcher.find_best(screen, ["red_square", "pattern"])

    assert result is not None, "Should find a template"
    name, match = result
    # Both should have very high confidence for exact matches
    log.info(f"Best match: '{name}' conf={match.confidence:.3f}")

    log.info("PASSED: find_best")
    return True


def test_draw_match():
    """Test drawing matches on images."""
    log = get_logger()
    log.info("Testing draw_match...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    screen = cv2.imread(str(TEST_ASSETS_DIR / "test_screen.png"))
    screen_copy = screen.copy()

    match = matcher.find(screen, "red_square")
    assert match is not None

    # Draw match
    result = matcher.draw_match(screen_copy, match, color=(0, 255, 0))

    # Save for visual inspection
    output_path = TEST_ASSETS_DIR / "test_output_draw.png"
    cv2.imwrite(str(output_path), result)

    log.info(f"Saved annotated image to {output_path}")
    log.info("PASSED: draw_match")
    return True


def test_nearby_filtering():
    """Test that nearby duplicate matches are filtered."""
    log = get_logger()
    log.info("Testing nearby filtering...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    # Create matches that are close together
    matches = [
        Match(x=100, y=100, width=30, height=30, confidence=0.95),
        Match(x=102, y=101, width=30, height=30, confidence=0.93),  # Very close
        Match(x=200, y=200, width=30, height=30, confidence=0.90),  # Far away
        Match(x=201, y=199, width=30, height=30, confidence=0.88),  # Very close to above
    ]

    filtered = matcher._filter_nearby_matches(matches, min_distance=10)

    # Should keep 2 matches (one from each cluster)
    assert len(filtered) == 2, f"Should have 2 matches after filtering, got {len(filtered)}"

    # Higher confidence ones should be kept
    assert filtered[0].confidence == 0.95
    assert filtered[1].confidence == 0.90

    log.info(f"Filtered {len(matches)} matches down to {len(filtered)}")
    log.info("PASSED: nearby filtering")
    return True


def test_preload_templates():
    """Test preloading multiple templates."""
    log = get_logger()
    log.info("Testing preload_templates...")

    matcher = TemplateMatcher(template_dir=str(TEST_ASSETS_DIR))

    loaded = matcher.preload_templates(["red_square", "pattern", "nonexistent"])

    assert loaded == 2, f"Should load 2 templates, loaded {loaded}"
    assert len(matcher.get_cached_templates()) == 2

    # Clear and verify
    matcher.clear_cache()
    assert len(matcher.get_cached_templates()) == 0

    log.info("PASSED: preload_templates")
    return True


def run_all_tests():
    """Run all template matcher tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Template Matcher Tests")
    log.info("=" * 50)

    # Create test assets first
    log.info("\nCreating test assets...")
    create_test_assets()

    tests = [
        ("Match Dataclass", test_match_dataclass),
        ("Template Loading", test_template_loading),
        ("Single Match", test_single_match),
        ("Multi Match", test_multi_match),
        ("Threshold Filtering", test_threshold_filtering),
        ("No Match Scenario", test_no_match),
        ("Find Any", test_find_any),
        ("Find Best", test_find_best),
        ("Draw Match", test_draw_match),
        ("Nearby Filtering", test_nearby_filtering),
        ("Preload Templates", test_preload_templates),
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
