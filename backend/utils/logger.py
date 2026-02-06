"""
Centralized logging configuration for Market Intelligence Dashboard.

Usage:
    from utils.logger import logger
    
    logger.info("Your message")
    logger.error("Error message")
"""
import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Will be configured on first import based on settings
_configured = False


def setup_logging(log_dir: Path = None, log_level: str = "INFO", app_name: str = "app"):
    """
    Configure logging with console and file outputs.
    
    Args:
        log_dir: Directory to store log files. If None, file logging is disabled.
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        app_name: Name prefix for log files (e.g., "scheduler", "api")
    """
    global _configured
    
    if _configured:
        return
    
    # Console logging with colors
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    
    # File logging (if log_dir provided)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file - rotates daily
        logger.add(
            log_dir / f"{app_name}_{{time:YYYY-MM-DD}}.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
            rotation="00:00",      # New file at midnight
            retention="30 days",   # Keep logs for 30 days
            compression="gz",      # Compress old logs
            encoding="utf-8"
        )
        
        logger.info(f"Logging configured. Log directory: {log_dir}")
    
    _configured = True


def init_logging(app_name: str = "app"):
    """
    Initialize logging using settings from config.
    Call this once at application startup.
    
    Args:
        app_name: Name prefix for log files (e.g., "scheduler", "api")
    """
    try:
        from config import settings, ensure_directories
        ensure_directories()
        setup_logging(log_dir=settings.LOG_DIR, log_level=settings.LOG_LEVEL, app_name=app_name)
    except ImportError:
        # Fallback if config not available
        setup_logging(log_level="INFO", app_name=app_name)


# Export logger for easy import
__all__ = ["logger", "setup_logging", "init_logging"]
