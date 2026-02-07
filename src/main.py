"""D2R Bot - Main CLI entry point."""

import signal
import sys
import time
from typing import Optional

import click

from src.data.config import ConfigManager
from src.data.statistics import StatisticsTracker
from src.game.combat import SorceressCombat
from src.game.health import HealthMonitor
from src.game.leveling import LevelManager
from src.game.loot import LootManager
from src.game.menu import MenuNavigator
from src.game.runs.base import RunStatus
from src.game.runs.leveling import LevelingManager
from src.game.runs.mephisto import MephistoRun
from src.game.runs.pindle import PindleRun
from src.game.town import TownManager
from src.input.controller import InputController
from src.utils.error_handler import ErrorHandler
from src.utils.logger import get_logger, setup_logger
from src.vision.game_detector import GameStateDetector
from src.vision.screen_capture import ScreenCapture
from src.vision.template_matcher import TemplateMatcher


class BotRunner:
    """Main bot runner that orchestrates all components."""

    def __init__(self, run_type: str, run_count: int, config_manager: ConfigManager):
        self.run_type = run_type
        self.run_count = run_count
        self.config_manager = config_manager
        self.config = config_manager.load()
        self.log = get_logger()
        self.running = False
        self.runs_completed = 0

        # Core components
        self.capture: Optional[ScreenCapture] = None
        self.matcher: Optional[TemplateMatcher] = None
        self.detector: Optional[GameStateDetector] = None
        self.input_ctrl: Optional[InputController] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.menu_nav: Optional[MenuNavigator] = None
        self.town_manager: Optional[TownManager] = None
        self.combat: Optional[SorceressCombat] = None
        self.loot_manager: Optional[LootManager] = None
        self.level_manager: Optional[LevelManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.stats_tracker: Optional[StatisticsTracker] = None

        # Run executor
        self.run_executor = None

    def initialize(self):
        """Initialize all bot components."""
        self.log.info("Initializing bot components...")

        # Vision system
        self.log.info("  - Screen capture")
        self.capture = ScreenCapture(window_title=self.config.window_title)

        self.log.info("  - Template matcher")
        self.matcher = TemplateMatcher(template_dir="assets/templates")

        self.log.info("  - Game state detector")
        self.detector = GameStateDetector(
            screen_capture=self.capture, template_matcher=self.matcher
        )

        # Input system
        self.log.info("  - Input controller")
        self.input_ctrl = InputController(
            config=self.config,
            human_like=self.config.human_like_input,
        )

        # Game systems
        self.log.info("  - Health monitor")
        self.health_monitor = HealthMonitor(
            config=self.config,
            detector=self.detector,
            input_ctrl=self.input_ctrl,
        )

        self.log.info("  - Menu navigator")
        self.menu_nav = MenuNavigator(
            config=self.config,
            input_ctrl=self.input_ctrl,
            detector=self.detector,
            matcher=self.matcher,
            capture=self.capture,
        )

        self.log.info("  - Town manager")
        self.town_manager = TownManager(
            config=self.config,
            input_ctrl=self.input_ctrl,
            detector=self.detector,
            matcher=self.matcher,
            capture=self.capture,
        )

        self.log.info("  - Combat system")
        self.combat = SorceressCombat(
            config=self.config, input_ctrl=self.input_ctrl, detector=self.detector
        )

        self.log.info("  - Loot manager")
        try:
            pickit_rules = self.config_manager.get_pickit_rules()
        except Exception as e:
            self.log.warning(f"Could not load pickit rules: {e}, using defaults")
            pickit_rules = None

        self.loot_manager = LootManager(
            config=self.config,
            input_ctrl=self.input_ctrl,
            detector=self.detector,
            capture=self.capture,
            matcher=self.matcher,
            pickit_rules=pickit_rules,
        )

        # Level manager (for leveling runs)
        if self.run_type == "level":
            self.log.info("  - Level manager")
            try:
                build = self.config_manager.get_build(self.config.build_name)
            except Exception as e:
                self.log.warning(f"Could not load build: {e}, using defaults")
                build = None

            self.level_manager = LevelManager(
                config=self.config,
                input_ctrl=self.input_ctrl,
                detector=self.detector,
                matcher=self.matcher,
                capture=self.capture,
                build=build,
            )

        # Error handler
        self.log.info("  - Error handler")
        self.error_handler = ErrorHandler(max_retries=3)

        # Statistics
        self.log.info("  - Statistics tracker")
        self.stats_tracker = StatisticsTracker(stats_dir="stats")

        # Initialize run executor
        self.log.info(f"  - Run executor ({self.run_type})")
        self._initialize_run_executor()

        self.log.info("Bot initialization complete!")

    def _initialize_run_executor(self):
        """Initialize the appropriate run executor based on run type."""
        common_args = {
            "config": self.config,
            "input_ctrl": self.input_ctrl,
            "combat": self.combat,
            "health_monitor": self.health_monitor,
            "town_manager": self.town_manager,
            "game_detector": self.detector,
            "screen_capture": self.capture,
            "menu_navigator": self.menu_nav,
            "loot_manager": self.loot_manager,
        }

        if self.run_type == "pindle":
            self.run_executor = PindleRun(**common_args)
        elif self.run_type == "mephisto":
            self.run_executor = MephistoRun(**common_args)
        elif self.run_type == "level":
            # Leveling run uses LevelingManager
            self.run_executor = LevelingManager(
                **common_args, level_manager=self.level_manager
            )
        else:
            raise ValueError(f"Unknown run type: {self.run_type}")

    def start(self):
        """Start the bot main loop."""
        self.running = True
        self.runs_completed = 0

        # Start health monitoring
        self.health_monitor.start_monitoring()

        self.log.info("Bot started! Press Ctrl+C to stop.")
        self.log.info("")

        try:
            while self.running:
                # Check if we've hit run count limit
                if self.run_count > 0 and self.runs_completed >= self.run_count:
                    self.log.info(
                        f"Completed {self.runs_completed} runs. Target reached!"
                    )
                    break

                # Execute one run
                run_number = self.runs_completed + 1
                self.log.info("=" * 60)
                self.log.info(
                    f"Starting run #{run_number}"
                    + (f" of {self.run_count}" if self.run_count > 0 else "")
                )
                self.log.info("=" * 60)

                try:
                    result = self.run_executor.execute()

                    # Log result
                    status_str = result.status.name
                    self.log.info(f"Run completed: {status_str} ({result.run_time:.1f}s)")

                    # Track statistics
                    self.stats_tracker.record_run(result)

                    # Handle different results
                    if result.status == RunStatus.SUCCESS:
                        self.runs_completed += 1
                    elif result.status == RunStatus.CHICKEN:
                        self.log.warning("Chicken triggered! Starting new run...")
                        self.runs_completed += 1
                        time.sleep(2)  # Brief pause before restarting
                    elif result.status == RunStatus.DEATH:
                        self.log.error("Character died! Starting new run...")
                        self.runs_completed += 1
                        time.sleep(3)  # Longer pause after death
                    elif result.status == RunStatus.ERROR:
                        self.log.error(f"Run failed: {result.error_message}")
                        # Still count as a run attempt
                        self.runs_completed += 1
                        time.sleep(5)  # Pause to avoid rapid errors
                    elif result.status == RunStatus.TIMEOUT:
                        self.log.warning("Run timed out! Starting new run...")
                        self.runs_completed += 1
                        time.sleep(3)

                    # Print session stats every 10 runs
                    if self.runs_completed % 10 == 0:
                        self._print_session_summary()

                except KeyboardInterrupt:
                    raise  # Re-raise to be caught by outer handler
                except Exception as e:
                    self.log.error(f"Unhandled error during run: {e}", exc_info=True)
                    time.sleep(5)
                    self.runs_completed += 1

        except KeyboardInterrupt:
            self.log.info("\nBot stopped by user")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown of bot components."""
        self.log.info("Shutting down bot...")
        self.running = False

        # Stop health monitor
        if self.health_monitor:
            self.health_monitor.stop_monitoring()

        # Print final stats
        self._print_session_summary()

        self.log.info("Bot shutdown complete")

    def _print_session_summary(self):
        """Print session statistics summary."""
        stats = self.stats_tracker.get_session_stats()
        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("SESSION SUMMARY")
        self.log.info("=" * 60)
        self.log.info(f"Total runs: {stats.total_runs}")
        self.log.info(f"Successful: {stats.successful_runs}")
        self.log.info(f"Failed: {stats.failed_runs}")
        self.log.info(f"Items picked: {stats.items_picked}")
        self.log.info(
            f"Average run time: {stats.average_run_time:.1f}s"
            if stats.average_run_time > 0
            else "N/A"
        )
        self.log.info("=" * 60)
        self.log.info("")


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Set logging level",
)
@click.option(
    "--log-dir",
    type=click.Path(),
    default="logs",
    help="Directory for log files",
)
@click.pass_context
def cli(ctx, log_level: str, log_dir: str):
    """D2R Bot - Diablo II: Resurrected automation bot.

    A computer vision based bot for automating farming runs
    and leveling in Diablo II: Resurrected.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Setup logger
    setup_logger(level=log_level, log_dir=log_dir)

    # Store in context for subcommands
    ctx.obj["logger"] = get_logger()
    ctx.obj["log_level"] = log_level


@cli.command()
@click.option(
    "--run",
    type=click.Choice(["pindle", "mephisto", "level"]),
    default="pindle",
    help="Run type to execute",
)
@click.option(
    "--count",
    type=int,
    default=0,
    help="Number of runs (0 = infinite)",
)
@click.pass_context
def start(ctx, run: str, count: int):
    """Start the bot with specified run type."""
    log = ctx.obj["logger"]

    log.info("=" * 50)
    log.info("D2R Bot Starting")
    log.info("=" * 50)
    log.info(f"Run type: {run}")
    log.info(f"Run count: {'infinite' if count == 0 else count}")
    log.info(f"Log level: {ctx.obj['log_level']}")
    log.info("")

    try:
        # Load configuration
        config_manager = ConfigManager()

        # Create and initialize bot runner
        bot = BotRunner(run_type=run, run_count=count, config_manager=config_manager)

        # Setup signal handlers for clean shutdown
        def signal_handler(signum, frame):
            log.info("\nReceived shutdown signal")
            bot.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize components
        bot.initialize()

        # Start bot
        bot.start()

    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def status():
    """Show bot status and statistics."""
    log = get_logger()
    log.info("Status command not yet implemented")
    log.info("Use 'stats' command to view run statistics")


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="text")
def stats(fmt: str):
    """Show run statistics."""
    log = get_logger()

    try:
        tracker = StatisticsTracker(stats_dir="stats")
        stats_data = tracker.get_session_stats()

        if fmt == "json":
            import json

            stats_dict = {
                "total_runs": stats_data.total_runs,
                "successful_runs": stats_data.successful_runs,
                "failed_runs": stats_data.failed_runs,
                "items_picked": stats_data.items_picked,
                "average_run_time": stats_data.average_run_time,
            }
            click.echo(json.dumps(stats_dict, indent=2))
        else:
            click.echo("=" * 60)
            click.echo("STATISTICS")
            click.echo("=" * 60)
            click.echo(f"Total runs: {stats_data.total_runs}")
            click.echo(f"Successful: {stats_data.successful_runs}")
            click.echo(f"Failed: {stats_data.failed_runs}")
            click.echo(f"Items picked: {stats_data.items_picked}")
            click.echo(
                f"Average run time: {stats_data.average_run_time:.1f}s"
                if stats_data.average_run_time > 0
                else "N/A"
            )
            click.echo("=" * 60)
    except Exception as e:
        log.error(f"Error loading statistics: {e}")


@cli.command()
def version():
    """Show version information."""
    from src import __version__

    click.echo(f"D2R Bot v{__version__}")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
