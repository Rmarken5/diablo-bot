"""Tests for screen capture module."""

import time
import os
from pathlib import Path

import cv2
import numpy as np

from src.vision.screen_capture import ScreenCapture
from src.utils.logger import setup_logger, get_logger


def test_basic_capture():
    """Test basic screen capture functionality."""
    log = get_logger()
    log.info("Testing basic screen capture...")

    capture = ScreenCapture()

    # Capture screen
    frame = capture.grab()

    # Verify frame is valid numpy array
    assert isinstance(frame, np.ndarray), "Frame should be numpy array"
    assert len(frame.shape) == 3, "Frame should be 3D (height, width, channels)"
    assert frame.shape[2] == 3, "Frame should have 3 channels (BGR)"

    log.info(f"Captured frame: {frame.shape[1]}x{frame.shape[0]} pixels")
    return True


def test_cache_behavior():
    """Test that caching works correctly."""
    log = get_logger()
    log.info("Testing cache behavior...")

    capture = ScreenCapture(cache_duration=0.1)  # 100ms cache

    # First capture
    frame1 = capture.grab()
    time1 = time.time()

    # Immediate second capture should use cache
    frame2 = capture.grab()
    time2 = time.time()

    # Frames should be identical (same object)
    assert frame1 is frame2, "Cached frames should be same object"
    log.info(f"Cache working: second grab took {(time2-time1)*1000:.2f}ms")

    # Wait for cache to expire
    time.sleep(0.15)

    # Third capture should be new
    frame3 = capture.grab()
    assert frame1 is not frame3, "After cache expiry, should get new frame"
    log.info("Cache expiry working correctly")

    return True


def test_cache_bypass():
    """Test cache can be bypassed."""
    log = get_logger()
    log.info("Testing cache bypass...")

    capture = ScreenCapture(cache_duration=1.0)  # Long cache

    frame1 = capture.grab()
    frame2 = capture.grab(use_cache=False)  # Bypass cache

    # With bypass, should get new capture (different object)
    # Note: content might be same, but object should be different
    assert frame1 is not frame2, "Cache bypass should create new frame"
    log.info("Cache bypass working")

    return True


def test_region_capture():
    """Test region capture functionality."""
    log = get_logger()
    log.info("Testing region capture...")

    capture = ScreenCapture()

    # Capture a 200x200 region from top-left
    region = (100, 100, 200, 200)
    frame = capture.grab_region(region)

    assert frame.shape[1] == 200, f"Width should be 200, got {frame.shape[1]}"
    assert frame.shape[0] == 200, f"Height should be 200, got {frame.shape[0]}"
    log.info(f"Region capture: {frame.shape[1]}x{frame.shape[0]} pixels")

    return True


def test_capture_performance():
    """Test capture performance."""
    log = get_logger()
    log.info("Testing capture performance...")

    capture = ScreenCapture()

    # Warm up
    capture.grab(use_cache=False)

    # Time multiple captures
    num_captures = 10
    start = time.time()

    for _ in range(num_captures):
        capture.grab(use_cache=False)

    elapsed = time.time() - start
    avg_time = (elapsed / num_captures) * 1000

    log.info(f"Average capture time: {avg_time:.2f}ms ({num_captures} captures)")
    log.info(f"Captures per second: {num_captures/elapsed:.1f}")

    # Should be reasonably fast (< 100ms per capture)
    assert avg_time < 100, f"Capture too slow: {avg_time}ms"

    return True


def test_save_capture():
    """Test saving captured frames to disk."""
    log = get_logger()
    log.info("Testing save capture...")

    capture = ScreenCapture()
    frame = capture.grab()

    # Create test output directory
    output_dir = Path("test_captures")
    output_dir.mkdir(exist_ok=True)

    # Save frame
    output_path = output_dir / "test_capture.png"
    cv2.imwrite(str(output_path), frame)

    assert output_path.exists(), "Saved file should exist"
    log.info(f"Saved capture to {output_path}")

    # Verify we can read it back
    loaded = cv2.imread(str(output_path))
    assert loaded.shape == frame.shape, "Loaded frame should match original"
    log.info("Save and load verified")

    return True


def test_dimensions():
    """Test getting frame dimensions."""
    log = get_logger()
    log.info("Testing get_frame_dimensions...")

    capture = ScreenCapture()
    width, height = capture.get_frame_dimensions()

    log.info(f"Frame dimensions: {width}x{height}")
    assert width > 0 and height > 0, "Dimensions should be positive"

    return True


def run_all_tests():
    """Run all screen capture tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Screen Capture Tests")
    log.info("=" * 50)

    tests = [
        ("Basic Capture", test_basic_capture),
        ("Cache Behavior", test_cache_behavior),
        ("Cache Bypass", test_cache_bypass),
        ("Region Capture", test_region_capture),
        ("Capture Performance", test_capture_performance),
        ("Save Capture", test_save_capture),
        ("Dimensions", test_dimensions),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            log.info(f"\n--- {name} ---")
            result = test_func()
            if result:
                log.info(f"PASSED: {name}")
                passed += 1
            else:
                log.error(f"FAILED: {name}")
                failed += 1
        except Exception as e:
            log.error(f"FAILED: {name} - {e}")
            failed += 1

    log.info("\n" + "=" * 50)
    log.info(f"Results: {passed} passed, {failed} failed")
    log.info("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
