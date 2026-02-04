"""Logging configuration using loguru."""

import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Global logger instance
_logger = logger


def setup_logger(
    level: str = "INFO",
    log_dir: str = "logs",
    console: bool = True,
    file: bool = True,
) -> None:
    """
    Configure the logger with console and file outputs.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        console: Enable console output
        file: Enable file output
    """
    global _logger

    # Remove any existing handlers
    _logger.remove()

    # Console format (colorized, concise)
    console_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )

    # File format (detailed)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    if console:
        _logger.add(
            sys.stderr,
            format=console_format,
            level=level,
            colorize=True,
        )

    if file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Main log file (rotates daily, keeps 7 days)
        _logger.add(
            log_path / "bot_{time:YYYY-MM-DD}.log",
            format=file_format,
            level=level,
            rotation="00:00",
            retention="7 days",
            compression="zip",
        )

        # Error log (separate file for errors only)
        _logger.add(
            log_path / "errors_{time:YYYY-MM-DD}.log",
            format=file_format,
            level="ERROR",
            rotation="00:00",
            retention="30 days",
            compression="zip",
        )


def get_logger():
    """Get the configured logger instance."""
    return _logger
