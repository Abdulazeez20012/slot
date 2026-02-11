"""Tests for Slot models."""


from slot.models import GroupInfo, ScrapeResult, TelegramMember


class TestTelegramMember:
    """Test TelegramMember model."""
    
    def test_create_basic_member(self):
        """Test creating a basic member."""
        member = TelegramMember(
            user_id=123456,
            first_name="John",
        )
        assert member.user_id == 123456
        assert member.first_name == "John"
        assert member.username is None
        assert member.is_bot is False
    
    def test_display_name_with_last_name(self):
        """Test display name includes last name."""
        member = TelegramMember(
            user_id=123,
            first_name="John",
            last_name="Doe",
        )
        assert member.display_name == "John Doe"
    
    def test_display_name_without_last_name(self):
        """Test display name without last name."""
        member = TelegramMember(
            user_id=123,
            first_name="John",
        )
        assert member.display_name == "John"
    
    def test_mention_with_username(self):
        """Test mention returns @username."""
        member = TelegramMember(
            user_id=123,
            first_name="John",
            username="johndoe",
        )
        assert member.mention == "@johndoe"
    
    def test_mention_without_username(self):
        """Test mention returns display name."""
        member = TelegramMember(
            user_id=123,
            first_name="John",
        )
        assert member.mention == "John"


class TestGroupInfo:
    """Test GroupInfo model."""
    
    def test_create_group(self):
        """Test creating a group."""
        group = GroupInfo(
            group_id=123456,
            title="Test Group",
        )
        assert group.group_id == 123456
        assert group.title == "Test Group"
        assert group.is_channel is False
    
    def test_public_group(self):
        """Test public group with username."""
        group = GroupInfo(
            group_id=123,
            title="Public Group",
            username="public_group",
            is_public=True,  # Explicitly set since it's not computed
        )
        assert group.is_public is True
        assert group.username == "public_group"


class TestScrapeResult:
    """Test ScrapeResult model."""
    
    def test_empty_result(self):
        """Test empty scrape result."""
        group = GroupInfo(group_id=123, title="Test")
        result = ScrapeResult(group=group)
        
        assert result.total_scraped == 0
        assert len(result.members) == 0
        assert len(result.errors) == 0
