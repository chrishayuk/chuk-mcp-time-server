"""
Tests for the server registry module
"""
import os
import sys

from chuk_mcp_time_server.server.server_registry import ServerRegistry

def test_server_registry_initialization():
    """Test ServerRegistry initialization"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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
    
    registry = ServerRegistry(project_root, default_config)
    
    assert registry.project_root == project_root
    assert registry.config == default_config
    assert isinstance(registry.server_paths, dict)
    assert isinstance(registry.components, dict)

def test_server_registry_core_paths():
    """Test core path setup"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    default_config = {
        "host": {"name": "test-mcp", "log_level": "INFO"},
        "core": {"common": "common/src", "runtime": "runtime/src"},
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {"components": {"tools": False, "resources": False, "prompts": False}}
    }
    
    registry = ServerRegistry(project_root, default_config)
    
    # Check common and runtime paths
    assert "common" in registry.server_paths
    assert "runtime" in registry.server_paths
    
    # Verify paths are correct
    assert registry.server_paths["common"] == os.path.join(project_root, "common", "src")
    assert registry.server_paths["runtime"] == os.path.join(project_root, "runtime", "src")

def test_server_registry_no_auto_discovery():
    """Test server registry with auto-discovery disabled"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    default_config = {
        "host": {"name": "test-mcp", "log_level": "INFO"},
        "core": {"common": "common/src", "runtime": "runtime/src"},
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {"components": {"tools": False, "resources": False, "prompts": False}}
    }
    
    registry = ServerRegistry(project_root, default_config)
    
    # Only core paths should be present
    assert len(registry.server_paths) == 2  # common and runtime

def test_server_registry_python_paths():
    """Test Python path setup"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    default_config = {
        "host": {"name": "test-mcp", "log_level": "INFO"},
        "core": {"common": "common/src", "runtime": "runtime/src"},
        "mcp_servers": {},
        "auto_discover": False,
        "discovery": {"components": {"tools": False, "resources": False, "prompts": False}}
    }
    
    registry = ServerRegistry(project_root, default_config)
    
    # Check that server paths are added to sys.path
    for path in registry.server_paths.values():
        assert path in sys.path, f"Path {path} not in sys.path"

def test_server_registry_load_components():
    """Test loading server components"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    default_config = {
        "host": {"name": "test-mcp", "log_level": "INFO"},
        "core": {"common": "common/src", "runtime": "runtime/src"},
        "mcp_servers": {
            "test_server": {
                "location": "runtime/src",
                "enabled": True,
                "tools": {
                    "module": "chuk_mcp_time_server.common.mcp_tool_decorator",
                    "enabled": True
                }
            }
        },
        "auto_discover": False,
        "discovery": {"components": {"tools": False, "resources": False, "prompts": False}}
    }
    
    registry = ServerRegistry(project_root, default_config)
    registry.load_server_components()
    
    # Verify components are loaded
    assert "chuk_mcp_time_server.common.mcp_tool_decorator" in registry.loaded_modules

def test_server_registry_auto_discovery():
    """Test auto-discovery of servers"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    default_config = {
        "host": {"name": "test-mcp", "log_level": "INFO"},
        "core": {"common": "common/src", "runtime": "runtime/src"},
        "mcp_servers": {},
        "auto_discover": True,
        "discovery": {
            "components": {
                "tools": True,
                "resources": False,
                "prompts": False
            }
        }
    }
    
    registry = ServerRegistry(project_root, default_config)
    
    # Verify some basic auto-discovery behavior
    assert len(registry.server_paths) > 2  # More than just core paths