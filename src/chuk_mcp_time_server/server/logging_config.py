# server/logging_config.py
"""
Logging configuration module for the MCP server.
This module sets up a shared logger with a default logging level
and a basic console handler.
"""
import logging
from logging import Logger
import os

def get_logger(name: str = "generic_mcp_server", 
               level: int = logging.INFO, 
               config: dict = None) -> Logger:
    """
    Get a configured logger with the specified name and level.
    
    Args:
        name: The name of the logger.
        level: The default logging level.
        config: Optional configuration dictionary to override log level.
        
    Returns:
        A logger instance with a console handler attached if none exist.
    """
    # Determine log level from config or environment, with fallback to default
    if config:
        log_level_name = config.get("host", {}).get("log_level", "INFO")
    else:
        log_level_name = os.getenv("LOG_LEVEL", "INFO")
    
    # Convert log level name to actual logging level
    log_level = getattr(logging, log_level_name.upper(), level)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Create a basic console handler if none exist
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# Create and configure the common logger for the module.
logger = get_logger()