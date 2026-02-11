"""Tests for filters module."""


import pytest

from slot.config import FilterConfig
from slot.filters import MemberFilter
from slot.models import TelegramMember, UserStatus


class TestMemberFilter:
    """Test MemberFilter functionality."""
    
    @pytest.fixture
    def online_user(self) -> TelegramMember:
        """Create an online user."""
        return TelegramMember(
            user_id=1,
            first_name="Online",
            status=UserStatus.ONLINE,
            is_bot=False,
        )
    
    @pytest.fixture
    def bot_user(self) -> TelegramMember:
        """Create a bot user."""
        return TelegramMember(
            user_id=2,
            first_name="Bot",
            status=UserStatus.ONLINE,
            is_bot=True,
        )
    
    @pytest.fixture
    def inactive_user(self) -> TelegramMember:
        """Create an inactive user."""
        return TelegramMember(
            user_id=3,
            first_name="Inactive",
            status=UserStatus.LONG_AGO,
            is_bot=False,
        )
    
    def test_exclude_bots(self, online_user, bot_user):
        """Test bot exclusion filter."""
        filter_config = FilterConfig(exclude_bots=True, status_include=[])
        member_filter = MemberFilter(filter_config)
        
        assert member_filter.matches(online_user) is True
        assert member_filter.matches(bot_user) is False
    
    def test_status_filter(self, online_user, inactive_user):
        """Test status filter."""
        filter_config = FilterConfig(
            exclude_bots=False,
            status_include=["online", "recently"],
        )
        member_filter = MemberFilter(filter_config)
        
        assert member_filter.matches(online_user) is True
        assert member_filter.matches(inactive_user) is False
    
    def test_filter_members_list(self, online_user, bot_user, inactive_user):
        """Test filtering a list of members."""
        member_filter = MemberFilter.recently_active()
        members = [online_user, bot_user, inactive_user]
        
        filtered = member_filter.filter_members(members)
        
        # Should include online_user only (bot excluded, inactive excluded)
        assert len(filtered) == 1
        assert filtered[0].user_id == 1
    
    def test_preset_online_only(self, online_user, inactive_user):
        """Test online_only preset filter."""
        member_filter = MemberFilter.online_only()
        
        assert member_filter.matches(online_user) is True
        assert member_filter.matches(inactive_user) is False
    
    def test_preset_no_bots(self, online_user, bot_user):
        """Test no_bots preset filter."""
        member_filter = MemberFilter.no_bots()
        
        assert member_filter.matches(online_user) is True
        assert member_filter.matches(bot_user) is False
