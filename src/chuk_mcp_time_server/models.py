# chuk_mcp_time_server/models.py
from pydantic import BaseModel, Field
from enum import Enum

# Enum for tool names (optional)
class TimeTools(str, Enum):
    GET_CURRENT_TIME = "get_current_time"
    CONVERT_TIME = "convert_time"

# Input model for get_current_time
class GetCurrentTimeInput(BaseModel):
    timezone: str = Field(
        ...,
        description="IANA timezone name (e.g., 'America/New_York', 'Europe/London')"
    )

# Output model for time results
class TimeResult(BaseModel):
    timezone: str = Field(
        ...,
        description="The timezone used for the time calculation"
    )
    datetime: str = Field(
        ...,
        description="Current time in ISO format (e.g., '2025-03-20T15:30:00')"
    )
    is_dst: bool = Field(
        ...,
        description="Indicates if daylight saving time is in effect"
    )

# Input model for convert_time
class ConvertTimeInput(BaseModel):
    source_timezone: str = Field(
        ...,
        description="IANA timezone name for the source time (e.g., 'America/New_York')"
    )
    time: str = Field(
        ...,
        description="Time to convert in HH:MM (24-hour) format"
    )
    target_timezone: str = Field(
        ...,
        description="IANA timezone name for the target time (e.g., 'Europe/London')"
    )

# Output model for time conversion result
class TimeConversionResult(BaseModel):
    source: TimeResult = Field(
        ...,
        description="The source time details"
    )
    target: TimeResult = Field(
        ...,
        description="The target time details"
    )
    time_difference: str = Field(
        ...,
        description="Difference between source and target times (formatted, e.g., '+2.0h')"
    )