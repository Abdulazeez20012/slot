# Slot - Telegram Member Scraper & Multi-Adder

Software designed to scrape and export member IDs from Telegram groups and channels, now featuring a modern Web Dashboard and a safe member addition tool.

## 🚀 Key Features

- **✅ Pro Max UI**: A stunning, modern web dashboard built with Tailwind CSS and Glassmorphism.
- **✅ Member Scraping**: Extract members from private/public groups with or without admin privileges.
- **✅ Safe Member Adder**: Grow your groups by adding members from other sources with built-in safety delays.
- **✅ Smart Batching**: Automatically waits between batches to prevent Telegram account limits.
- **✅ Official Telegram API**: Uses MTProto for maximum compliance and safety.
- **✅ Activity Filters**: Filter by status (Online, Recently, Week, Month).
- **✅ Multiple Formats**: Export results to CSV, JSON, XLSX, or TXT.

## 🖥️ Web Dashboard

Slot now features a powerful web interface. To start the dashboard:

```bash
slot web
```
Then visit `http://127.0.0.1:8000` in your browser.

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Abdulazeez20012/slot.git
cd slot

# Install dependencies (using pip)
pip install -e .

# Or using uv (recommended)
uv pip install -e .
```

## 🛠️ Usage

### 1. Get Telegram API Credentials
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in and click "API Development Tools"
3. Create a new app and copy your `api_id` and `api_hash`.

### 2. Authenticate
Use the Web Dashboard OR the CLI:
```bash
slot auth --api-id=YOUR_ID --api-hash=YOUR_HASH
```

### 3. Add Members (New!)
Transfer members from a source group to your target group safely:
1. Open the **Add Members** tab in the dashboard.
2. Enter the Source Group and Target Group.
3. Set your limits and start the process.

## 📊 Filter Options

| Filter | Description |
|--------|-------------|
| `--filter=online` | Currently online users |
| `--filter=recently` | Active within 2-3 days |
| `--filter=within_week` | Active within a week |
| `--filter=within_month` | Active within a month |

## 🏗️ Project Structure

```
slot/
├── src/slot/
│   ├── templates/       # Glassmorphism UI Templates
│   ├── web.py           # FastAPI Web Server
│   ├── storage.py       # Job & Result Persistence
│   ├── scraper.py       # Core Telegram Logic
│   ├── cli.py           # Command-line interface
│   └── exporters.py     # Data Export logic
└── ...
```

## 🔒 Security & Privacy
- **.env Support**: Keeps your credentials safe.
- **Encrypted Sessions**: Handles Telegram `.session` files securely.
- **Compliance**: Adheres to Telegram's flood-wait and rate-limit policies.

## 📄 License
MIT
