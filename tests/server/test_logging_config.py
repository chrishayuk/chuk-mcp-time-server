"""
Tests for the logging_config module
"""
import logging
import os

from chuk_mcp_time_server.server.logging_config import get_logger

def test_get_logger_default():
    """Test getting a logger with default settings"""
    logger = get_logger()
    
    assert logger.name == "generic_mcp_server"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)

def test_get_logger_with_config():
    """Test getting a logger with custom configuration"""
    config = {
        "host": {
            "log_level": "DEBUG"
        }
    }
    
    logger = get_logger(config=config)
    
    assert logger.level == logging.DEBUG

def test_get_logger_with_env_level(monkeypatch):
    """Test getting a logger with log level from environment variable"""
    # Set log level via environment variable
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    
    logger = get_logger()
    
    assert logger.level == logging.WARNING

def test_logger_handlers():
    """Test that logger only has one handler"""
    logger = get_logger()
    
    assert len(logger.handlers) == 1
    
    # Calling get_logger multiple times should not add additional handlers
    logger2 = get_logger()
    assert len(logger2.handlers) == 1

def test_logger_formatter():
    """Test the log formatter"""
    logger = get_logger()
    formatter = logger.handlers[0].formatter
    
    # Check formatter pattern
    assert formatter._fmt == '%(asctime)s - %(name)s - %(levelname)s - %(message)s'