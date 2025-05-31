# servers/chuk_mcp_artifact_server/tests/test_time_server.py

import re
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

# Import your time tools.
# Adjust the import based on your package structure.
# For example, if your tools are in:
# servers/time_server/src/chuk_mcp_artifact_server/tools/time_tools.py
# then the package might be named "time_server.tools"
from chuk_mcp_artifact_server.tools import get_current_time, convert_time

def test_get_current_time_valid():
    # Use a known valid timezone, e.g., "UTC"
    result = get_current_time("UTC")
    assert isinstance(result, dict)
    
    # Check that the result contains the expected keys.
    for key in ("timezone", "datetime", "is_dst"):
        assert key in result, f"Missing key '{key}' in result"
    
    # Verify the timezone is returned correctly.
    assert result["timezone"] == "UTC"
    
    # Check that the datetime string is valid ISO format.
    try:
        dt = datetime.fromisoformat(result["datetime"])
    except Exception:
        pytest.fail("The 'datetime' field is not in valid ISO format.")
    
    # Check that is_dst is a boolean.
    assert isinstance(result["is_dst"], bool)

def test_get_current_time_invalid_timezone():
    # An invalid timezone should raise an exception (wrapped by McpError or ValueError)
    with pytest.raises(Exception):
        get_current_time("Invalid/Timezone")

def test_convert_time_valid():
    # Convert a known time from UTC to Europe/London.
    # Note: The actual difference might depend on daylight saving.
    result = convert_time("UTC", "12:00", "Europe/London")
    assert isinstance(result, dict)
    
    # The result should contain keys 'source', 'target', and 'time_difference'.
    for key in ("source", "target", "time_difference"):
        assert key in result, f"Missing key '{key}' in result"
    
    # Check that both source and target include the expected structure.
    for loc in ("source", "target"):
        loc_data = result[loc]
        for key in ("timezone", "datetime", "is_dst"):
            assert key in loc_data, f"Missing key '{key}' in {loc} data"
    
    # Check that time_difference is a string and matches a pattern (e.g., "+1.0h" or "-0.0h")
    td = result["time_difference"]
    assert isinstance(td, str)
    pattern = re.compile(r"^[+-]\d+(\.\d+)?h$")
    assert pattern.match(td), f"time_difference '{td}' does not match expected pattern"

def test_convert_time_invalid_time_format():
    # Passing a time that does not match "HH:MM" should raise a ValueError.
    with pytest.raises(ValueError):
        convert_time("UTC", "25:00", "Europe/London")
