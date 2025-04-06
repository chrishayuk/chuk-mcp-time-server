"""
Tests for the MCP server module
"""
import pytest
import logging
import importlib

from chuk_mcp_time_server.server.server import MCPServer
from chuk_mcp_time_server.common.mcp_tool_decorator import TOOLS_REGISTRY

def test_mcp_server_initialization():
    """Test MCPServer initialization"""
    default_config = {
        "host": {
            "name": "test-mcp",
            "log_level": "INFO"
        },
        "core": {
            "common": "common/src",
            "runtime": "runtime/src"
        },
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {
            "components": {
                "tools": False,
                "resources": False,
                "prompts": False
            }
        }
    }
    
    server = MCPServer(default_config)
    
    assert server.config == default_config
    assert server.server_name == "test-mcp"

def test_mcp_server_tools_registry():
    """Test tools registry import"""
    default_config = {
        "host": {
            "name": "test-mcp",
            "log_level": "INFO"
        },
        "core": {
            "common": "common/src",
            "runtime": "runtime/src"
        },
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {
            "components": {
                "tools": False,
                "resources": False,
                "prompts": False
            }
        }
    }
    
    server = MCPServer(default_config)
    
    # Verify tools registry import
    assert hasattr(server, 'tools_registry')
    
    # The actual content of the registry depends on your project
    # This is a generic check that doesn't assume specific tools
    assert isinstance(server.tools_registry, dict)

def test_mcp_server_log_reconfiguration():
    """Test logger reconfiguration"""
    default_config = {
        "host": {
            "name": "test-mcp",
            "log_level": "DEBUG"
        },
        "core": {
            "common": "common/src",
            "runtime": "runtime/src"
        },
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {
            "components": {
                "tools": False,
                "resources": False,
                "prompts": False
            }
        }
    }
    
    server = MCPServer(default_config)
    
    assert server.logger.level == logging.DEBUG

def test_mcp_server_no_tools():
    """Test server behavior with no tools"""
    # Temporarily remove tools registry to simulate no tools
    original_registry = TOOLS_REGISTRY.copy()
    
    try:
        # Clear the tools registry
        TOOLS_REGISTRY.clear()
        
        default_config = {
            "host": {
                "name": "test-mcp",
                "log_level": "INFO"
            },
            "core": {
                "common": "common/src",
                "runtime": "runtime/src"
            },
            "mcp_servers": {},
            "auto_discover": False,
            "discovery": {
                "components": {
                    "tools": False,
                    "resources": False,
                    "prompts": False
                }
            }
        }
        
        server = MCPServer(default_config)
        
        assert len(server.tools_registry) == 0
    finally:
        # Restore the original registry
        TOOLS_REGISTRY.update(original_registry)

def test_mcp_server_tool_import_failure(monkeypatch):
    """Test handling of tools registry import failure"""
    def mock_import_module(*args, **kwargs):
        raise ImportError("Mocked import failure")
    
    # Mock importlib.import_module to simulate import failure
    monkeypatch.setattr(importlib, 'import_module', mock_import_module)
    
    default_config = {
        "host": {
            "name": "test-mcp",
            "log_level": "INFO"
        },
        "core": {
            "common": "common/src",
            "runtime": "runtime/src"
        },
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {
            "components": {
                "tools": False,
                "resources": False,
                "prompts": False
            }
        }
    }
    
    server = MCPServer(default_config)
    
    # Verify empty tools registry on import failure
    assert len(server.tools_registry) == 0