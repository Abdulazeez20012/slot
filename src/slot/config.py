"""Configuration management for Slot."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file if present
load_dotenv()


class TelegramConfig(BaseModel):
    """Telegram API configuration."""
    
    api_id: int = Field(..., description="Telegram API ID from my.telegram.org")
    api_hash: str = Field(..., description="Telegram API Hash from my.telegram.org")
    session_name: str = Field("slot_session", description="Session file name")
    
    @classmethod
    def from_env(cls) -> Optional["TelegramConfig"]:
        """Load configuration from environment variables."""
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            return None
        
        return cls(
            api_id=int(api_id),
            api_hash=api_hash,
            session_name=os.getenv("TELEGRAM_SESSION_NAME", "slot_session"),
        )


class ScraperConfig(BaseModel):
    """Scraper behavior configuration."""
    
    batch_size: int = Field(200, description="Members per API request")
    delay_between_requests: float = Field(0.5, description="Seconds between requests")
    max_retries: int = Field(3, description="Max retries on failure")
    timeout: int = Field(30, description="Request timeout in seconds")


class FilterConfig(BaseModel):
    """Member filter configuration."""
    
    exclude_bots: bool = Field(True, description="Exclude bot accounts")
    status_include: list[str] = Field(
        default_factory=lambda: ["online", "recently"],
        description="Include only these statuses"
    )
    last_seen_days: int | None = Field(None, description="Last seen within N days")
    premium_only: bool = Field(False, description="Only premium users")


class AddMemberConfig(BaseModel):
    """Configuration for adding members to groups."""
    
    batch_size: int = Field(10, description="Members to add per batch")
    batch_delay: int = Field(1800, description="Seconds to wait between batches (30 mins)")
    max_additions: int = Field(0, description="Maximum members to add (0 for unlimited)")


class AppConfig(BaseModel):
    """Main application configuration."""
    
    mock_mode: bool = Field(False, description="Enable mock mode")
    telegram: TelegramConfig | None = None
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    adder: AddMemberConfig = Field(default_factory=AddMemberConfig)
    data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".slot",
        description="Data storage directory"
    )
    
    def ensure_data_dir(self) -> Path:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


# Global config instance
config = AppConfig(telegram=TelegramConfig.from_env(), mock_mode=False)
