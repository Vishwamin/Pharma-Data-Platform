import logging
import sys
from config.config import Config

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance with dual handlers:
    1. Console Handler (stdout) for real-time monitoring.
    2. File Handler for persistent log audit trailing.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if logger is already configured
    if logger.hasHandlers():
        return logger

    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    
    # Standard format: Time | Level | Module:Line | Message
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    file_handler = logging.FileHandler(Config.LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
