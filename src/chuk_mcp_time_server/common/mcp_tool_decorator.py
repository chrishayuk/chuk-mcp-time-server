# common/mcp_tool_decorator.py
import inspect
from functools import wraps
from pydantic import create_model
from mcp.types import Tool  # Assumes your MCP types define a Tool model

# Global registry for MCP tool functions.
TOOLS_REGISTRY = {}

def mcp_tool(name: str, description: str):
    """
    Decorator to register an MCP tool function and auto-generate its input JSON schema.
    
    It:
      - Inspects the function's signature and builds a Pydantic model for input.
      - Creates a Tool instance with the provided name, description, and the generated schema.
      - Registers the function in a global registry for later dispatch.
    """
    def decorator(func):
        # Build a Pydantic model for the input parameters using type hints.
        sig = inspect.signature(func)
        fields = {}
        for param in sig.parameters.values():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            fields[param.name] = (annotation, ...)
        
        # Create a temporary Pydantic model for schema generation.
        InputModel = create_model(f"{func.__name__.capitalize()}Input", **fields)
        
        # Use model_json_schema() instead of schema() to generate the input schema.
        tool = Tool(
            name=name,
            description=description,
            inputSchema=InputModel.model_json_schema()
        )
        
        # Register the function in the global registry.
        TOOLS_REGISTRY[name] = func
        
        # Attach the tool metadata to the function for introspection.
        func._mcp_tool = tool

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
