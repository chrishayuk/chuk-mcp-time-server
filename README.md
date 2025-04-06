# MCP Time Server

[![smithery badge](https://smithery.ai/badge/@chrishayuk/chuk-mcp-time-server)](https://smithery.ai/server/@chrishayuk/chuk-mcp-time-server)

## Overview

The MCP Time Server is a sophisticated Python-based microservice designed to provide advanced time-related utilities across different timezones. It offers robust functionality for retrieving current times and converting times between various global timezones.

## Project Details

- **Version**: 0.1.1
- **Python Compatibility**: Python 3.11+

## Features

- **Current Time Retrieval**: Get the current time for any IANA timezone
- **Time Zone Conversion**: Convert times between different time zones
- **Comprehensive Validation**: Robust input validation using Pydantic models
- **Async Server Architecture**: Built with asyncio for efficient performance
- **Flexible Configuration**: Configurable through environment variables and config files

## Dependencies

Core dependencies:
- mcp (>=1.6.0)
- pydantic (>=2.11.2)
- PyYAML (>=6.0.2)
- pyz (>=0.4.3)

Development dependencies:
- pytest (>=8.3.5)

## Installation

### Installing via Smithery

To install MCP Time Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@chrishayuk/chuk-mcp-time-server):

```bash
npx -y @smithery/cli install @chrishayuk/chuk-mcp-time-server --client claude
```

### Prerequisites

- Python 3.11 or higher
- pip
- (Optional) Virtual environment recommended

### Install from PyPI

```bash
pip install chuk-mcp-time-server
```

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd chuk-mcp-time-server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install the package:
```bash
pip install .  # Installs the package in editable mode
```

### Development Installation

To set up for development:
```bash
pip install .[dev]  # Installs package with development dependencies
```

## Running the Server

### Command-Line Interface

```bash
chuk-mcp-time-server
```

### Programmatic Usage

```python
from chuk_mcp_time_server.main import main

if __name__ == "__main__":
    main()
```

## Environment Variables

- `NO_BOOTSTRAP`: Set to disable component bootstrapping
- Other configuration options can be set in the configuration files

## Available Tools

### 1. Get Current Time

**Input**:
- `timezone`: IANA timezone name (e.g., 'America/New_York')

**Example**:
```python
get_current_time('Europe/London')
```

**Returns**:
- Current time in the specified timezone
- Timezone details
- Daylight Saving Time (DST) status

### 2. Convert Time

**Input**:
- `source_timezone`: Source timezone (IANA format)
- `time`: Time in HH:MM (24-hour) format
- `target_timezone`: Target timezone (IANA format)

**Example**:
```python
convert_time('America/New_York', '14:30', 'Europe/Paris')
```

**Returns**:
- Source time details
- Target time details
- Time difference between zones

## Development

### Code Formatting

- Black is used for code formatting
- isort is used for import sorting
- Line length is set to 88 characters

### Running Tests

```bash
pytest
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Ensure code passes formatting and testing
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

## License

[MIT License](LICENSE)
