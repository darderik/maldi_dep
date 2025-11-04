"""
Logging configuration module for MALDI Sample Preparation application.

This module provides a centralized logging setup that can be used throughout
the application for real-time terminal output during optimization and simulation.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if sys.platform == 'win32':
            # Windows doesn't support ANSI colors by default
            log_color = ''
            reset = ''
        else:
            log_color = self.COLORS.get(record.levelname, '')
            reset = self.RESET
        
        record.msg = f"{log_color}{record.msg}{reset}"
        return super().format(record)


def setup_logging(name: str = "MALDI", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger instance with both console and file handlers.
    
    Args:
        name: Logger name (typically __name__ or 'MALDI')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        logger.setLevel(level)
        
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            fmt='[%(asctime)s] %(levelname)s - %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler (optional - for persistent logging)
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = logs_dir / f"maldi_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s - %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "MALDI") -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Module-level logger for direct use
logger = setup_logging("MALDI")
