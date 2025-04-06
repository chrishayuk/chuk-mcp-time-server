# server/server.py
"""
MCP Server Module

This module provides the core MCP server functionality for 
running tools and managing server operations.
"""
import asyncio
import json
import importlib

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# imports
from chuk_mcp_time_server.server.logging_config import get_logger, logger

class MCPServer:
    """
    Manages the MCP (Messaging Control Protocol) server operations.
    
    Handles tool discovery, registration, and execution.
    """
    def __init__(self, config: dict):
        """
        Initialize the MCP server.
        
        Args:
            config: Configuration dictionary for the server.
        """
        self.config = config
        # Reconfigure logger with the loaded config
        self.logger = get_logger(config=config)
        
        # Server name from configuration
        self.server_name = config.get("host", {}).get("name", "generic-mcp")
        
        # Tools registry
        self.tools_registry = self._import_tools_registry()
    
    def _import_tools_registry(self) -> dict:
        """
        Dynamically import the tools registry.
        
        Returns:
            Dictionary of available tools.
        """
        try:
            tools_decorator_module = importlib.import_module("chuk_mcp_time_server.common.mcp_tool_decorator")
            tools_registry = getattr(tools_decorator_module, "TOOLS_REGISTRY", {})
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to import TOOLS_REGISTRY: {e}")
            tools_registry = {}
        
        if not tools_registry:
            self.logger.warning("No tools available")
        else:
            self.logger.info(f"Loaded {len(tools_registry)} tools")
            self.logger.info(f"Available tools: {', '.join(tools_registry.keys())}")
        
        return tools_registry
    
    async def serve(self) -> None:
        """
        Run the MCP server with stdio communication.
        
        Sets up server, tool listing, and tool execution handlers.
        """
        # Create MCP server instance
        server = Server(self.server_name)

        @server.list_tools()
        async def list_tools() -> list[Tool]:
            """
            List available tools.
            
            Returns:
                List of tool descriptions.
            """
            if not self.tools_registry:
                self.logger.warning("No tools available")
                return []
            return [func._mcp_tool for func in self.tools_registry.values()]

        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
            """
            Execute a specific tool with given arguments.
            
            Args:
                name: Name of the tool to execute.
                arguments: Arguments for the tool.
            
            Returns:
                List of content resulting from tool execution.
            
            Raises:
                ValueError: If tool is not found or fails to execute.
            """
            if name not in self.tools_registry:
                raise ValueError(f"Tool not found: {name}")
            
            func = self.tools_registry[name]
            try:
                result = func(**arguments)
            except Exception as e:
                self.logger.error(f"Error processing tool '{name}': {e}", exc_info=True)
                raise ValueError(f"Error processing tool '{name}': {str(e)}")
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Create initialization options
        options = server.create_initialization_options()
        
        # Run server with stdio communication
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)