"""Statistics tracking and reporting for D2R Bot."""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.logger import get_logger


@dataclass
class RunRecord:
    """Record of a single run."""
    run_type: str
    status: str
    duration: float
    kills: int = 0
    items_picked: int = 0
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ItemRecord:
    """Record of a found item."""
    quality: str
    name: str = ""
    position: str = ""
    run_type: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionSummary:
    """Summary statistics for a session."""
    start_time: float
    end_time: float = 0.0
    runs_completed: int = 0
    runs_failed: int = 0
    runs_chickened: int = 0
    total_kills: int = 0
    total_items: int = 0
    items_by_quality: Dict[str, int] = field(default_factory=dict)
    deaths: int = 0
    chickens: int = 0
    total_run_time: float = 0.0
    fastest_run: float = 0.0
    slowest_run: float = 0.0

    @property
    def average_run_time(self) -> float:
        """Average time per successful run."""
        if self.runs_completed == 0:
            return 0.0
        return self.total_run_time / self.runs_completed

    @property
    def total_runs(self) -> int:
        """Total runs attempted."""
        return self.runs_completed + self.runs_failed + self.runs_chickened

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.runs_completed / self.total_runs) * 100

    @property
    def session_duration(self) -> float:
        """Total session duration in seconds."""
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def runs_per_hour(self) -> float:
        """Runs completed per hour."""
        hours = self.session_duration / 3600
        if hours == 0:
            return 0.0
        return self.runs_completed / hours


class StatisticsTracker:
    """
    Tracks and persists bot statistics.

    Records runs, items found, deaths, and chickens.
    Provides session and all-time statistics.
    Persists data to JSON files.
    """

    def __init__(self, stats_dir: str = "stats"):
        """
        Initialize statistics tracker.

        Args:
            stats_dir: Directory for stats files
        """
        self.log = get_logger()
        self.stats_dir = Path(stats_dir)
        self.stats_dir.mkdir(parents=True, exist_ok=True)

        # Current session
        self.session = SessionSummary(start_time=time.time())
        self._runs: List[RunRecord] = []
        self._items: List[ItemRecord] = []

        # Session file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_file = self.stats_dir / f"session_{timestamp}.json"

    def record_run(self, run_type: str, status: str, duration: float,
                   kills: int = 0, items_picked: int = 0, error: str = "") -> None:
        """
        Record a completed run.

        Args:
            run_type: Type of run (pindleskin, mephisto, etc.)
            status: Run status (SUCCESS, CHICKEN, ERROR, etc.)
            duration: Run duration in seconds
            kills: Number of kills
            items_picked: Number of items picked up
            error: Error message if failed
        """
        record = RunRecord(
            run_type=run_type,
            status=status,
            duration=duration,
            kills=kills,
            items_picked=items_picked,
            error=error,
        )
        self._runs.append(record)

        # Update session summary
        if status == "SUCCESS":
            self.session.runs_completed += 1
            self.session.total_run_time += duration

            if self.session.fastest_run == 0 or duration < self.session.fastest_run:
                self.session.fastest_run = duration
            if duration > self.session.slowest_run:
                self.session.slowest_run = duration
        elif status == "CHICKEN":
            self.session.runs_chickened += 1
            self.session.chickens += 1
        elif status == "DEATH":
            self.session.runs_failed += 1
            self.session.deaths += 1
        else:
            self.session.runs_failed += 1

        self.session.total_kills += kills
        self.session.total_items += items_picked

        self.log.info(
            f"Run recorded: {run_type} - {status} ({duration:.1f}s, "
            f"{kills} kills, {items_picked} items)"
        )

        # Auto-save
        self._save_session()

    def record_item(self, quality: str, name: str = "", run_type: str = "") -> None:
        """
        Record a found item.

        Args:
            quality: Item quality (unique, set, rare, etc.)
            name: Item name if known
            run_type: Run type where item was found
        """
        record = ItemRecord(
            quality=quality,
            name=name,
            run_type=run_type,
        )
        self._items.append(record)

        # Update quality counts
        quality_key = quality.lower()
        self.session.items_by_quality[quality_key] = (
            self.session.items_by_quality.get(quality_key, 0) + 1
        )

        self.log.info(f"Item recorded: {quality} {name}")

    def record_death(self) -> None:
        """Record a death event."""
        self.session.deaths += 1
        self.log.warning(f"Death recorded (total: {self.session.deaths})")

    def record_chicken(self) -> None:
        """Record a chicken event."""
        self.session.chickens += 1
        self.log.warning(f"Chicken recorded (total: {self.session.chickens})")

    def get_session_stats(self) -> SessionSummary:
        """Get current session statistics."""
        return self.session

    def print_summary(self) -> str:
        """
        Generate and return a formatted summary string.

        Returns:
            Formatted statistics summary
        """
        s = self.session
        lines = [
            "=" * 50,
            "  BOT SESSION STATISTICS",
            "=" * 50,
            f"  Session Duration: {s.session_duration / 60:.1f} minutes",
            f"  Total Runs:       {s.total_runs}",
            f"  Successful:       {s.runs_completed}",
            f"  Failed:           {s.runs_failed}",
            f"  Chickened:        {s.runs_chickened}",
            f"  Success Rate:     {s.success_rate:.1f}%",
            f"  Runs/Hour:        {s.runs_per_hour:.1f}",
            "",
            f"  Avg Run Time:     {s.average_run_time:.1f}s",
            f"  Fastest Run:      {s.fastest_run:.1f}s",
            f"  Slowest Run:      {s.slowest_run:.1f}s",
            "",
            f"  Total Kills:      {s.total_kills}",
            f"  Total Items:      {s.total_items}",
            f"  Deaths:           {s.deaths}",
            f"  Chickens:         {s.chickens}",
        ]

        if s.items_by_quality:
            lines.append("")
            lines.append("  Items by Quality:")
            for quality, count in sorted(s.items_by_quality.items()):
                lines.append(f"    {quality:12s}: {count}")

        lines.append("=" * 50)

        summary = "\n".join(lines)
        self.log.info(f"\n{summary}")
        return summary

    def export_json(self, filepath: Optional[str] = None) -> str:
        """
        Export statistics to JSON file.

        Args:
            filepath: Output file path (default: stats dir)

        Returns:
            Path to exported file
        """
        if filepath is None:
            filepath = str(self._session_file)

        data = {
            "session": asdict(self.session),
            "runs": [asdict(r) for r in self._runs],
            "items": [asdict(i) for i in self._items],
            "exported_at": time.time(),
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        self.log.info(f"Statistics exported to {filepath}")
        return filepath

    def _save_session(self) -> None:
        """Auto-save session data."""
        try:
            self.export_json()
        except Exception as e:
            self.log.error(f"Failed to save statistics: {e}")

    def load_session(self, filepath: str) -> Optional[SessionSummary]:
        """
        Load a previous session from JSON.

        Args:
            filepath: Path to session file

        Returns:
            SessionSummary or None if loading failed
        """
        try:
            with open(filepath) as f:
                data = json.load(f)

            session_data = data.get("session", {})
            summary = SessionSummary(
                start_time=session_data.get("start_time", 0),
                end_time=session_data.get("end_time", 0),
                runs_completed=session_data.get("runs_completed", 0),
                runs_failed=session_data.get("runs_failed", 0),
                runs_chickened=session_data.get("runs_chickened", 0),
                total_kills=session_data.get("total_kills", 0),
                total_items=session_data.get("total_items", 0),
                items_by_quality=session_data.get("items_by_quality", {}),
                deaths=session_data.get("deaths", 0),
                chickens=session_data.get("chickens", 0),
                total_run_time=session_data.get("total_run_time", 0),
                fastest_run=session_data.get("fastest_run", 0),
                slowest_run=session_data.get("slowest_run", 0),
            )

            self.log.info(f"Loaded session from {filepath}")
            return summary

        except Exception as e:
            self.log.error(f"Failed to load session: {e}")
            return None

    def get_all_time_stats(self) -> SessionSummary:
        """
        Aggregate statistics from all saved sessions.

        Returns:
            Combined SessionSummary
        """
        combined = SessionSummary(start_time=time.time())

        for stats_file in sorted(self.stats_dir.glob("session_*.json")):
            session = self.load_session(str(stats_file))
            if session is None:
                continue

            combined.runs_completed += session.runs_completed
            combined.runs_failed += session.runs_failed
            combined.runs_chickened += session.runs_chickened
            combined.total_kills += session.total_kills
            combined.total_items += session.total_items
            combined.deaths += session.deaths
            combined.chickens += session.chickens
            combined.total_run_time += session.total_run_time

            if session.fastest_run > 0:
                if combined.fastest_run == 0 or session.fastest_run < combined.fastest_run:
                    combined.fastest_run = session.fastest_run
            if session.slowest_run > combined.slowest_run:
                combined.slowest_run = session.slowest_run

            for quality, count in session.items_by_quality.items():
                combined.items_by_quality[quality] = (
                    combined.items_by_quality.get(quality, 0) + count
                )

        return combined

    def end_session(self) -> None:
        """Mark session as ended and save final stats."""
        self.session.end_time = time.time()
        self._save_session()
        self.print_summary()
