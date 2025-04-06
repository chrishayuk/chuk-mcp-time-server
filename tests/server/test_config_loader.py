"""
Tests for the config_loader module
"""
import os
import yaml
import tempfile

from chuk_mcp_time_server.server.config_loader import load_config, get_project_root

def test_load_config_default():
    """Test loading default configuration when no config file exists"""
    # Create a temporary directory that doesn't contain a config file
    with tempfile.TemporaryDirectory() as temp_dir:
        config = load_config(temp_dir)
        
        # Check default configuration structure
        assert isinstance(config, dict)
        assert config.get("host", {}).get("name") == "generic-mcp"
        assert "core" in config
        assert "mcp_servers" in config
        assert "auto_discover" in config

def test_load_config_yaml():
    """Test loading configuration from a YAML file"""
    # Create a temporary config file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_config = {
            "host": {
                "name": "test-server",
                "log_level": "DEBUG"
            },
            "core": {
                "common": "test/common",
                "runtime": "test/runtime"
            },
            "mcp_servers": {
                "test_server": {
                    "location": "test/servers/test_server",
                    "enabled": True
                }
            }
        }
        
        # Write config to a YAML file
        config_path = os.path.join(temp_dir, "config.yaml")
        with open(config_path, 'w') as f:
            yaml.safe_dump(test_config, f)
        
        # Load config
        config = load_config(temp_dir)
        
        # Verify loaded configuration
        assert config["host"]["name"] == "test-server"
        assert config["host"]["log_level"] == "DEBUG"
        assert config["core"]["common"] == "test/common"
        assert "test_server" in config["mcp_servers"]

def test_get_project_root():
    """Test project root retrieval"""
    root_path = get_project_root()
    
    # Verify the project root path
    assert os.path.isdir(root_path)
    assert os.path.basename(root_path) in ["mcp-host", "agent-x", "chuk-mcp-time-server"]