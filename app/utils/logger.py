"""
Logging configuration with detailed console and file-based logging.
"""
import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings

# Global variable to track if logging is already configured
_logging_configured = False


def setup_logging() -> None:
    """
    Configure application logging with both console and file handlers.
    
    Creates timestamped log files in logs/ directory with rotation.
    Console logs use simpler format, file logs include detailed context.
    """
    global _logging_configured
    
    if _logging_configured:
        return  # Avoid re-configuring
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{timestamp}.log"
    
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Detailed format for file logs (includes filename, line number, function name)
    file_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
    )
    
    # Simpler format for console logs
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatters
    file_formatter = logging.Formatter(
        file_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        console_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handler with rotation (10MB max, keep 5 backup files)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()  # Clear any existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    
    # Log the logging setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Console: {log_level}, File: {log_file}")
    logger.info(f"File log format: Detailed (filename:line:function)")
    logger.info(f"Console log format: Simple")
    
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__ from the calling module)
    
    Returns:
        Configured logger instance
    """
    # Ensure logging is set up
    if not _logging_configured:
        setup_logging()
    
    return logging.getLogger(name)
