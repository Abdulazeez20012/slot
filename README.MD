# Slot - Telegram Member Scraper

Software designed to scrape and export member IDs from Telegram groups and channels.

## Features

- ✅ Extract members from private/public groups with or without admin privileges
- ✅ Unlimited exporting of active members
- ✅ Uses the official Telegram API (MTProto) for compliance and safety
- ✅ Activity-based filters (online, recently, last seen, etc.)
- ✅ Multiple export formats: CSV, JSON, XLSX, TXT

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd slot

# Install dependencies (using pip)
pip install -e .

# Or using uv (recommended)
uv pip install -e .
```

## Quick Start

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click "API Development Tools"
4. Create a new application
5. Copy your `api_id` and `api_hash`

### 2. Authenticate

```bash
slot auth --api-id=YOUR_ID --api-hash=YOUR_HASH
```

You'll be prompted to enter your phone number and the verification code.

### 3. Scrape Members

```bash
# Basic scrape
slot scrape @groupname

# Export to Excel with filters
slot scrape @groupname -o members -f xlsx --filter=recently

# Limit to 1000 members
slot scrape @groupname -l 1000

# Get group info only
slot info @groupname
```

## Commands

| Command | Description |
|---------|-------------|
| `slot auth` | Authenticate with Telegram |
| `slot scrape <group>` | Scrape members from a group |
| `slot info <group>` | Get group information |
| `slot --version` | Show version |

## Export Formats

- **CSV** - Universal spreadsheet format
- **JSON** - For programmatic use
- **XLSX** - Excel with styling
- **TXT** - Simple user ID list

## Filter Options

| Filter | Description |
|--------|-------------|
| `--filter=online` | Currently online users |
| `--filter=recently` | Active within 2-3 days |
| `--filter=within_week` | Active within a week |
| `--filter=within_month` | Active within a month |
| `--exclude-bots` | Exclude bot accounts (default) |
| `--include-bots` | Include bot accounts |

## Project Structure

```
slot/
├── src/slot/
│   ├── __init__.py      # Package init
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration management
│   ├── models.py        # Pydantic data models
│   ├── scraper.py       # Telegram API integration
│   ├── filters.py       # Activity-based filters
│   └── exporters.py     # Export (CSV, JSON, XLSX, TXT)
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
├── .env.example         # Example credentials file
└── README.md            # This file
```

## Requirements

- Python 3.11+
- Telegram account
- API credentials from my.telegram.org

## License

MIT
