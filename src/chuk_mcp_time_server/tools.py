# chuk_mcp_time_server/tools.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pydantic import ValidationError
from mcp.shared.exceptions import McpError

# imports
from chuk_mcp_time_server.common.mcp_tool_decorator import mcp_tool

# Import our models - use relative import for better modularity
from chuk_mcp_time_server.models import (
    GetCurrentTimeInput,
    TimeResult,
    ConvertTimeInput,
    TimeConversionResult
)

@mcp_tool(name="get_current_time", description="Get current time in a specified timezone")
def get_current_time(timezone: str) -> dict:
    """
    Validate input using GetCurrentTimeInput, compute current time in the provided timezone,
    and return the result as defined by TimeResult.
    """
    try:
        validated_input = GetCurrentTimeInput(timezone=timezone)
    except ValidationError as e:
        raise ValueError(f"Invalid input for get_current_time: {e}")

    try:
        # Get the timezone
        tz = ZoneInfo(validated_input.timezone)
    except Exception as e:
        raise McpError(f"Invalid timezone '{validated_input.timezone}': {e}")
    
    # Get the time
    now = datetime.now(tz)

    # Build the result
    result = TimeResult(
        timezone=validated_input.timezone,
        datetime=now.isoformat(timespec="seconds"),
        is_dst=bool(now.dst())
    )

    # Return the result
    return result.model_dump()

@mcp_tool(name="convert_time", description="Convert time between timezones")
def convert_time(source_timezone: str, time: str, target_timezone: str) -> dict:
    """
    Validate input using ConvertTimeInput, convert the time from source timezone to target timezone,
    and return the result as defined by TimeConversionResult.
    """
    try:
        validated_input = ConvertTimeInput(
            source_timezone=source_timezone,
            time=time,
            target_timezone=target_timezone
        )
    except ValidationError as e:
        raise ValueError(f"Invalid input for convert_time: {e}")

    try:
        source_tz = ZoneInfo(validated_input.source_timezone)
        target_tz = ZoneInfo(validated_input.target_timezone)
    except Exception as e:
        raise McpError(f"Invalid timezone: {e}")

    try:
        # Expecting time in "HH:MM" format
        parsed_time = datetime.strptime(validated_input.time, "%H:%M").time()
    except ValueError:
        raise ValueError("Invalid time format. Expected HH:MM (24-hour format)")

    now = datetime.now(source_tz)
    source_time = datetime(
        now.year,
        now.month,
        now.day,
        parsed_time.hour,
        parsed_time.minute,
        tzinfo=source_tz
    )
    target_time = source_time.astimezone(target_tz)

    source_offset = source_time.utcoffset() or timedelta()
    target_offset = target_time.utcoffset() or timedelta()
    hours_difference = (target_offset - source_offset).total_seconds() / 3600

    if hours_difference.is_integer():
        time_diff_str = f"{hours_difference:+.1f}h"
    else:
        time_diff_str = f"{hours_difference:+.2f}".rstrip("0").rstrip(".") + "h"

    result = TimeConversionResult(
        source=TimeResult(
            timezone=validated_input.source_timezone,
            datetime=source_time.isoformat(timespec="seconds"),
            is_dst=bool(source_time.dst())
        ),
        target=TimeResult(
            timezone=validated_input.target_timezone,
            datetime=target_time.isoformat(timespec="seconds"),
            is_dst=bool(target_time.dst())
        ),
        time_difference=time_diff_str
    )
    return result.model_dump()