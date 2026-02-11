"""Pydantic models for Telegram member data."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UserStatus(StrEnum):
    """User online status types from Telegram."""
    
    ONLINE = "online"
    RECENTLY = "recently"  # within 2-3 days
    WITHIN_WEEK = "within_week"
    WITHIN_MONTH = "within_month"
    LONG_AGO = "long_ago"
    UNKNOWN = "unknown"


class TelegramMember(BaseModel):
    """Represents a Telegram group/channel member."""
    
    user_id: int = Field(..., description="Unique Telegram user ID")
    username: str | None = Field(None, description="@username if set")
    first_name: str = Field(..., description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    phone: str | None = Field(None, description="Phone number (admin only)")
    last_seen: datetime | None = Field(None, description="Last seen timestamp")
    status: UserStatus = Field(UserStatus.UNKNOWN, description="Online status")
    is_bot: bool = Field(False, description="Whether user is a bot")
    is_premium: bool = Field(False, description="Whether user has Telegram Premium")
    is_verified: bool = Field(False, description="Whether account is verified")
    
    @property
    def display_name(self) -> str:
        """Get the full display name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    @property
    def mention(self) -> str:
        """Get @username or display name."""
        if self.username:
            return f"@{self.username}"
        return self.display_name


class GroupInfo(BaseModel):
    """Represents a Telegram group or channel."""
    
    group_id: int = Field(..., description="Unique group/channel ID")
    title: str = Field(..., description="Group title")
    username: str | None = Field(None, description="@username if public")
    member_count: int = Field(0, description="Total member count")
    is_channel: bool = Field(False, description="True if channel, False if group")
    is_public: bool = Field(False, description="Whether group is public")
    scraped_at: datetime = Field(default_factory=datetime.now)


class ScrapeResult(BaseModel):
    """Result of a scraping operation."""
    
    group: GroupInfo
    members: list[TelegramMember] = Field(default_factory=list)
    total_scraped: int = 0
    filtered_count: int = 0
    errors: list[str] = Field(default_factory=list)
