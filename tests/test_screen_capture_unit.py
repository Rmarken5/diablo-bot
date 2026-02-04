"""Unit tests for screen capture module (no display required)."""

import time
from unittest.mock import Mock, patch, MagicMock

import numpy as np

from src.vision.screen_capture import ScreenCapture
from src.utils.logger import setup_logger, get_logger


def create_mock_screenshot(width: int = 1920, height: int = 1080):
    """Create a mock screenshot for testing."""
    # Create a simple gradient image
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[:, :, 0] = 255  # Blue channel
    img[:, :, 1] = 128  # Green channel
    img[:, :, 2] = 64   # Red channel
    img[:, :, 3] = 255  # Alpha channel

    # Create mock with pixel array
    mock = MagicMock()
    mock.__array__ = Mock(return_value=img)
    return mock


def test_cache_logic():
    """Test that caching logic works correctly."""
    log = get_logger()
    log.info("Testing cache logic...")

    with patch.object(ScreenCapture, '_build_monitor') as mock_monitor:
        mock_monitor.return_value = {"left": 0, "top": 0, "width": 100, "height": 100}

        capture = ScreenCapture(cache_duration=0.1)

        # Mock the mss grab method
        with patch.object(capture.sct, 'grab') as mock_grab:
            mock_grab.return_value = create_mock_screenshot(100, 100)

            # First grab should call sct.grab
            frame1 = capture.grab()
            assert mock_grab.call_count == 1, "First grab should call sct.grab"

            # Second immediate grab should use cache
            frame2 = capture.grab()
            assert mock_grab.call_count == 1, "Cached grab should not call sct.grab"
            assert frame1 is frame2, "Cached frames should be same object"

            # Wait for cache to expire
            time.sleep(0.15)

            # Third grab should call sct.grab again
            frame3 = capture.grab()
            assert mock_grab.call_count == 2, "After cache expiry should call sct.grab"

    log.info("PASSED: Cache logic")
    return True


def test_cache_bypass():
    """Test that cache bypass works."""
    log = get_logger()
    log.info("Testing cache bypass...")

    with patch.object(ScreenCapture, '_build_monitor') as mock_monitor:
        mock_monitor.return_value = {"left": 0, "top": 0, "width": 100, "height": 100}

        capture = ScreenCapture(cache_duration=10.0)  # Long cache

        with patch.object(capture.sct, 'grab') as mock_grab:
            mock_grab.return_value = create_mock_screenshot(100, 100)

            # First grab
            frame1 = capture.grab()
            assert mock_grab.call_count == 1

            # Second grab with cache bypass
            frame2 = capture.grab(use_cache=False)
            assert mock_grab.call_count == 2, "Cache bypass should call sct.grab"
            assert frame1 is not frame2, "Bypass should return new frame"

    log.info("PASSED: Cache bypass")
    return True


def test_invalidate_cache():
    """Test cache invalidation."""
    log = get_logger()
    log.info("Testing cache invalidation...")

    with patch.object(ScreenCapture, '_build_monitor') as mock_monitor:
        mock_monitor.return_value = {"left": 0, "top": 0, "width": 100, "height": 100}

        capture = ScreenCapture(cache_duration=10.0)

        with patch.object(capture.sct, 'grab') as mock_grab:
            mock_grab.return_value = create_mock_screenshot(100, 100)

            # First grab
            capture.grab()
            assert mock_grab.call_count == 1

            # Invalidate cache
            capture.invalidate_cache()

            # Next grab should fetch new frame
            capture.grab()
            assert mock_grab.call_count == 2, "After invalidate should fetch new"

    log.info("PASSED: Cache invalidation")
    return True


def test_frame_conversion():
    """Test that BGRA to BGR conversion works."""
    log = get_logger()
    log.info("Testing frame conversion...")

    with patch.object(ScreenCapture, '_build_monitor') as mock_monitor:
        mock_monitor.return_value = {"left": 0, "top": 0, "width": 100, "height": 100}

        capture = ScreenCapture()

        with patch.object(capture.sct, 'grab') as mock_grab:
            # Create BGRA image
            mock_grab.return_value = create_mock_screenshot(100, 100)

            frame = capture.grab()

            # Should be BGR (3 channels)
            assert frame.shape == (100, 100, 3), f"Expected (100, 100, 3), got {frame.shape}"

    log.info("PASSED: Frame conversion")
    return True


def test_region_monitor_building():
    """Test that region capture builds correct monitor."""
    log = get_logger()
    log.info("Testing region monitor building...")

    capture = ScreenCapture()

    # Test with explicit region
    region = (100, 200, 300, 400)
    monitor = capture._build_monitor(region)

    assert monitor["left"] == 100
    assert monitor["top"] == 200
    assert monitor["width"] == 300
    assert monitor["height"] == 400

    log.info("PASSED: Region monitor building")
    return True


def test_window_detection_fallback():
    """Test fallback when window not found."""
    log = get_logger()
    log.info("Testing window detection fallback...")

    capture = ScreenCapture(window_title="NonExistentWindow12345")

    # Should fall back to primary monitor
    monitor = capture._build_monitor()

    # Should have valid monitor dict
    assert "left" in monitor or "mon" in str(monitor)

    log.info("PASSED: Window detection fallback")
    return True


def test_is_game_running():
    """Test game running detection."""
    log = get_logger()
    log.info("Testing is_game_running...")

    capture = ScreenCapture()

    # Should return True or False without crashing
    result = capture.is_game_running()
    assert isinstance(result, bool)

    log.info(f"PASSED: is_game_running returned {result}")
    return True


def run_all_tests():
    """Run all unit tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Screen Capture Unit Tests")
    log.info("=" * 50)

    tests = [
        ("Cache Logic", test_cache_logic),
        ("Cache Bypass", test_cache_bypass),
        ("Invalidate Cache", test_invalidate_cache),
        ("Frame Conversion", test_frame_conversion),
        ("Region Monitor Building", test_region_monitor_building),
        ("Window Detection Fallback", test_window_detection_fallback),
        ("Is Game Running", test_is_game_running),
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
