"""Tests for statistics tracking and reporting."""

import json
import os
import tempfile
import time

from src.data.statistics import (
    StatisticsTracker,
    SessionSummary,
    RunRecord,
    ItemRecord,
)
from src.utils.logger import setup_logger, get_logger


def create_tracker(stats_dir=None):
    """Create a StatisticsTracker with temp directory."""
    if stats_dir is None:
        stats_dir = tempfile.mkdtemp()
    return StatisticsTracker(stats_dir=stats_dir), stats_dir


def test_initial_session():
    """Test initial session state."""
    log = get_logger()
    log.info("Testing initial session...")

    tracker, _ = create_tracker()
    session = tracker.get_session_stats()

    assert session.runs_completed == 0
    assert session.runs_failed == 0
    assert session.total_kills == 0
    assert session.total_items == 0
    assert session.deaths == 0
    assert session.chickens == 0
    assert session.start_time > 0

    log.info("PASSED: initial session")
    return True


def test_record_successful_run():
    """Test recording a successful run."""
    log = get_logger()
    log.info("Testing record successful run...")

    tracker, _ = create_tracker()

    tracker.record_run(
        run_type="pindleskin",
        status="SUCCESS",
        duration=15.5,
        kills=1,
        items_picked=3,
    )

    session = tracker.get_session_stats()
    assert session.runs_completed == 1
    assert session.total_kills == 1
    assert session.total_items == 3
    assert session.fastest_run == 15.5
    assert session.slowest_run == 15.5

    log.info("PASSED: record successful run")
    return True


def test_record_chicken_run():
    """Test recording a chicken run."""
    log = get_logger()
    log.info("Testing record chicken run...")

    tracker, _ = create_tracker()

    tracker.record_run(
        run_type="pindleskin",
        status="CHICKEN",
        duration=5.0,
    )

    session = tracker.get_session_stats()
    assert session.runs_chickened == 1
    assert session.chickens == 1

    log.info("PASSED: record chicken run")
    return True


def test_record_death_run():
    """Test recording a death run."""
    log = get_logger()
    log.info("Testing record death run...")

    tracker, _ = create_tracker()

    tracker.record_run(
        run_type="mephisto",
        status="DEATH",
        duration=30.0,
    )

    session = tracker.get_session_stats()
    assert session.runs_failed == 1
    assert session.deaths == 1

    log.info("PASSED: record death run")
    return True


def test_record_error_run():
    """Test recording an error run."""
    log = get_logger()
    log.info("Testing record error run...")

    tracker, _ = create_tracker()

    tracker.record_run(
        run_type="mephisto",
        status="ERROR",
        duration=10.0,
        error="Template not found",
    )

    session = tracker.get_session_stats()
    assert session.runs_failed == 1

    log.info("PASSED: record error run")
    return True


def test_multiple_runs():
    """Test recording multiple runs."""
    log = get_logger()
    log.info("Testing multiple runs...")

    tracker, _ = create_tracker()

    tracker.record_run("pindleskin", "SUCCESS", 10.0, kills=1, items_picked=2)
    tracker.record_run("pindleskin", "SUCCESS", 20.0, kills=1, items_picked=1)
    tracker.record_run("pindleskin", "CHICKEN", 5.0)
    tracker.record_run("mephisto", "DEATH", 30.0)

    session = tracker.get_session_stats()
    assert session.runs_completed == 2
    assert session.runs_chickened == 1
    assert session.runs_failed == 1
    assert session.total_runs == 4
    assert session.total_kills == 2
    assert session.total_items == 3
    assert session.fastest_run == 10.0
    assert session.slowest_run == 20.0

    log.info("PASSED: multiple runs")
    return True


def test_session_summary_properties():
    """Test SessionSummary computed properties."""
    log = get_logger()
    log.info("Testing session summary properties...")

    summary = SessionSummary(
        start_time=time.time() - 3600,  # 1 hour ago
        runs_completed=10,
        runs_failed=2,
        runs_chickened=3,
        total_run_time=150.0,
    )

    assert summary.total_runs == 15
    assert summary.average_run_time == 15.0
    assert summary.success_rate == (10 / 15) * 100
    assert summary.runs_per_hour > 9

    log.info("PASSED: session summary properties")
    return True


def test_session_summary_empty():
    """Test SessionSummary properties when empty."""
    log = get_logger()
    log.info("Testing empty session summary...")

    summary = SessionSummary(start_time=time.time())

    assert summary.total_runs == 0
    assert summary.average_run_time == 0.0
    assert summary.success_rate == 0.0

    log.info("PASSED: empty session summary")
    return True


def test_record_item():
    """Test recording found items."""
    log = get_logger()
    log.info("Testing record item...")

    tracker, _ = create_tracker()

    tracker.record_item("unique", name="Shako", run_type="pindleskin")
    tracker.record_item("set", name="Tal Rasha's Guardianship")
    tracker.record_item("unique", name="Stormshield")

    session = tracker.get_session_stats()
    assert session.items_by_quality.get("unique") == 2
    assert session.items_by_quality.get("set") == 1

    log.info("PASSED: record item")
    return True


def test_record_death():
    """Test recording death events."""
    log = get_logger()
    log.info("Testing record death...")

    tracker, _ = create_tracker()

    tracker.record_death()
    tracker.record_death()

    assert tracker.session.deaths == 2

    log.info("PASSED: record death")
    return True


def test_record_chicken():
    """Test recording chicken events."""
    log = get_logger()
    log.info("Testing record chicken...")

    tracker, _ = create_tracker()

    tracker.record_chicken()

    assert tracker.session.chickens == 1

    log.info("PASSED: record chicken")
    return True


def test_export_json():
    """Test JSON export."""
    log = get_logger()
    log.info("Testing JSON export...")

    tmpdir = tempfile.mkdtemp()
    tracker, _ = create_tracker(tmpdir)

    tracker.record_run("pindleskin", "SUCCESS", 15.0, kills=1, items_picked=2)
    tracker.record_item("unique", name="Shako")

    filepath = os.path.join(tmpdir, "test_export.json")
    result = tracker.export_json(filepath)

    assert os.path.exists(result)

    with open(result) as f:
        data = json.load(f)

    assert "session" in data
    assert "runs" in data
    assert "items" in data
    assert len(data["runs"]) == 1
    assert len(data["items"]) == 1

    log.info("PASSED: JSON export")
    return True


def test_load_session():
    """Test loading a session from JSON."""
    log = get_logger()
    log.info("Testing load session...")

    tmpdir = tempfile.mkdtemp()
    tracker, _ = create_tracker(tmpdir)

    tracker.record_run("pindleskin", "SUCCESS", 15.0, kills=1)
    filepath = os.path.join(tmpdir, "test_load.json")
    tracker.export_json(filepath)

    # Load it
    loaded = tracker.load_session(filepath)
    assert loaded is not None
    assert loaded.runs_completed == 1

    log.info("PASSED: load session")
    return True


def test_load_session_invalid():
    """Test loading a non-existent session."""
    log = get_logger()
    log.info("Testing load invalid session...")

    tracker, _ = create_tracker()

    loaded = tracker.load_session("/nonexistent/path.json")
    assert loaded is None

    log.info("PASSED: load invalid session")
    return True


def test_print_summary():
    """Test formatted summary output."""
    log = get_logger()
    log.info("Testing print summary...")

    tracker, _ = create_tracker()

    tracker.record_run("pindleskin", "SUCCESS", 15.0, kills=1, items_picked=2)
    tracker.record_item("unique", name="Shako")

    summary = tracker.print_summary()

    assert "BOT SESSION STATISTICS" in summary
    assert "Total Runs" in summary
    assert "unique" in summary

    log.info("PASSED: print summary")
    return True


def test_end_session():
    """Test ending a session."""
    log = get_logger()
    log.info("Testing end session...")

    tracker, _ = create_tracker()

    tracker.record_run("pindleskin", "SUCCESS", 10.0)
    tracker.end_session()

    assert tracker.session.end_time > 0

    log.info("PASSED: end session")
    return True


def test_run_record_dataclass():
    """Test RunRecord dataclass."""
    log = get_logger()
    log.info("Testing RunRecord dataclass...")

    record = RunRecord(
        run_type="pindleskin",
        status="SUCCESS",
        duration=15.5,
        kills=1,
        items_picked=3,
    )

    assert record.run_type == "pindleskin"
    assert record.status == "SUCCESS"
    assert record.duration == 15.5
    assert record.timestamp > 0

    log.info("PASSED: RunRecord dataclass")
    return True


def test_item_record_dataclass():
    """Test ItemRecord dataclass."""
    log = get_logger()
    log.info("Testing ItemRecord dataclass...")

    record = ItemRecord(
        quality="unique",
        name="Shako",
        run_type="pindleskin",
    )

    assert record.quality == "unique"
    assert record.name == "Shako"
    assert record.timestamp > 0

    log.info("PASSED: ItemRecord dataclass")
    return True


def run_all_tests():
    """Run all statistics tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("Statistics Tracker Tests")
    log.info("=" * 50)

    tests = [
        ("Initial Session", test_initial_session),
        ("Record Successful Run", test_record_successful_run),
        ("Record Chicken Run", test_record_chicken_run),
        ("Record Death Run", test_record_death_run),
        ("Record Error Run", test_record_error_run),
        ("Multiple Runs", test_multiple_runs),
        ("Session Summary Properties", test_session_summary_properties),
        ("Empty Session Summary", test_session_summary_empty),
        ("Record Item", test_record_item),
        ("Record Death", test_record_death),
        ("Record Chicken", test_record_chicken),
        ("Export JSON", test_export_json),
        ("Load Session", test_load_session),
        ("Load Invalid Session", test_load_session_invalid),
        ("Print Summary", test_print_summary),
        ("End Session", test_end_session),
        ("RunRecord Dataclass", test_run_record_dataclass),
        ("ItemRecord Dataclass", test_item_record_dataclass),
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
