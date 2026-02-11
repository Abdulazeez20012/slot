"""Activity-based filters for Telegram members."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from .config import FilterConfig
from .models import TelegramMember


class MemberFilter:
    """Filter for Telegram members based on activity and attributes."""
    
    def __init__(self, config: FilterConfig | None = None):
        """Initialize filter with configuration."""
        self.config = config or FilterConfig()
        self._custom_filters: list[Callable[[TelegramMember], bool]] = []
    
    def add_custom_filter(self, fn: Callable[[TelegramMember], bool]) -> "MemberFilter":
        """Add a custom filter function."""
        self._custom_filters.append(fn)
        return self
    
    def matches(self, member: TelegramMember) -> bool:
        """Check if a member matches all filter criteria."""
        # Exclude bots
        if self.config.exclude_bots and member.is_bot:
            return False
        
        # Premium only
        if self.config.premium_only and not member.is_premium:
            return False
        
        # Status filter
        if self.config.status_include:
            if member.status.value not in self.config.status_include:
                return False
        
        # Last seen filter
        if self.config.last_seen_days is not None and member.last_seen:
            cutoff = datetime.now(UTC) - timedelta(days=self.config.last_seen_days)
            if member.last_seen < cutoff:
                return False
        
        # Custom filters
        for custom_fn in self._custom_filters:
            if not custom_fn(member):
                return False
        
        return True
    
    def filter_members(
        self,
        members: list[TelegramMember],
    ) -> list[TelegramMember]:
        """Filter a list of members."""
        return [m for m in members if self.matches(m)]
    
    @classmethod
    def online_only(cls) -> "MemberFilter":
        """Create a filter for online users only."""
        return cls(FilterConfig(status_include=["online"]))
    
    @classmethod
    def recently_active(cls) -> "MemberFilter":
        """Create a filter for recently active users (online + recently)."""
        return cls(FilterConfig(status_include=["online", "recently"]))
    
    @classmethod
    def active_this_week(cls) -> "MemberFilter":
        """Create a filter for users active within a week."""
        return cls(FilterConfig(
            status_include=["online", "recently", "within_week"]
        ))
    
    @classmethod
    def no_bots(cls) -> "MemberFilter":
        """Create a filter that only excludes bots."""
        return cls(FilterConfig(
            exclude_bots=True,
            status_include=[],  # Accept all statuses
        ))
