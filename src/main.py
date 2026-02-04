"""D2R Bot - Main CLI entry point."""

import click
from src.utils.logger import setup_logger, get_logger


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

    # TODO: Initialize and start bot
    log.info("Bot initialization not yet implemented")
    log.info("This is Step 1 - Project Setup complete!")


@cli.command()
def status():
    """Show bot status and statistics."""
    log = get_logger()
    log.info("Status command not yet implemented")


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="text")
def stats(fmt: str):
    """Show run statistics."""
    log = get_logger()
    log.info(f"Stats command not yet implemented (format: {fmt})")


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
