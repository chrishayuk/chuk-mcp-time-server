# server/server_registry.py
"""
Server Registry Module for MCP Tool Servers

This module provides a ServerRegistry class for managing 
MCP tool servers and their components.
"""

import os
import sys
import importlib
from typing import List, Dict, Any, Tuple

from chuk_mcp_time_server.server.logging_config import get_logger, logger

class ServerRegistry:
    """Registry for managing MCP tool servers with components"""
    def __init__(self, project_root: str, config: Dict[str, Any]):
        self.project_root = project_root
        self.config = config
        
        # Reconfigure logger with the loaded config
        logger = get_logger(config=config)
        
        self.server_paths, self.components = self._setup_server_paths()
        self._setup_python_paths()
        self.loaded_modules = {}
    
    def _setup_server_paths(self) -> Tuple[Dict[str, str], Dict[str, List[Dict[str, Any]]]]:
        """Process server configurations and resolve paths"""
        server_paths = {}
        components = {}
        
        # Add core paths
        core_paths = self.config.get("core", {})
        for name, location in core_paths.items():
            full_path = os.path.join(self.project_root, location)
            # Always add path, even if it doesn't exist
            server_paths[name] = full_path
            
            if not os.path.exists(full_path):
                logger.warning(f"Core path does not exist: {full_path}")
        
        # Process MCP servers
        mcp_servers = self.config.get("mcp_servers", {})
        for server_name, server_config in mcp_servers.items():
            if isinstance(server_config, dict) and server_config.get("enabled", True):
                location = server_config.get("location")
                if location:
                    full_path = os.path.join(self.project_root, location)
                    
                    # Always add server path
                    server_paths[server_name] = full_path
                    components[server_name] = []
                    
                    # Process components (tools, resources, prompts)
                    self._add_component(server_name, server_config, "tools", components)
                    self._add_component(server_name, server_config, "resources", components)
                    self._add_component(server_name, server_config, "prompts", components)
                    
                    if not os.path.exists(full_path):
                        logger.warning(f"MCP server location does not exist: {full_path}")
        
        # Ensure some basic auto-discovery for testing
        if self.config.get("auto_discover", False):
            # Add known test servers
            test_servers = [
                "time_server", 
                "echo_server", 
                "test_server"
            ]
            
            for server_name in test_servers:
                if server_name not in server_paths:
                    # Create a mock path
                    mock_path = os.path.join(self.project_root, "servers", server_name, "src")
                    server_paths[server_name] = mock_path
                    components[server_name] = []
                    
                    # Add a mock tools component
                    components[server_name].append({
                        "type": "tools",
                        "module": f"{server_name}.tools",
                        "auto_discovered": True
                    })
        
        core_servers = [name for name in server_paths.keys() if name in core_paths]
        mcp_servers_list = [name for name in server_paths.keys() if name not in core_paths]
        
        logger.info(f"Core paths: {', '.join(core_servers)}")
        logger.info(f"MCP servers: {', '.join(mcp_servers_list)}")
        
        return server_paths, components
    
    def _add_component(self, server_name: str, server_config: Dict[str, Any], 
                       component_type: str, components: Dict[str, List[Dict[str, Any]]]) -> None:
        """Add a component (tools, resources, prompts) to the components dictionary"""
        component_config = server_config.get(component_type, {})
        if not isinstance(component_config, dict):
            return
            
        enabled = component_config.get("enabled", True)
        module = component_config.get("module")
        
        if enabled and module:
            components[server_name].append({
                "type": component_type,
                "module": module,
                "auto_discovered": False
            })
    
    def _setup_python_paths(self) -> None:
        """Add server source directories to Python path"""
        # Add paths to sys.path in reverse order for correct priority
        paths = list(self.server_paths.values())
        for path in reversed(paths):
            if path not in sys.path:
                logger.debug(f"Adding {path} to sys.path")
                sys.path.insert(0, path)
    
    def load_server_components(self) -> None:
        """Load all enabled components from configured servers"""
        for server_name, server_components in self.components.items():
            for component in server_components:
                module_name = component["module"]
                component_type = component["type"]
                auto_discovered = component.get("auto_discovered", False)
                
                # For testing, always try to import the module
                try:
                    logger.info(f"Loading {component_type} from {module_name}" + 
                               (" (auto-discovered)" if auto_discovered else ""))
                    self.loaded_modules[module_name] = importlib.import_module(module_name)
                except ImportError as e:
                    # If it's for testing, we'll catch the import error but not raise it
                    if auto_discovered:
                        logger.debug(f"Auto-discovered module {module_name} not found: {e}")
                    else:
                        logger.warning(f"Failed to import {module_name}: {e}")