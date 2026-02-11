"""Telegram client and member scraping functionality."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import (
    Channel,
    ChannelParticipantsSearch,
    User,
    UserStatusEmpty,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

from .config import AppConfig, config
from .models import GroupInfo, ScrapeResult, TelegramMember, UserStatus


def parse_user_status(user: User) -> tuple[UserStatus, datetime | None]:
    """Parse Telegram user status to our model."""
    status = user.status
    
    if status is None or isinstance(status, UserStatusEmpty):
        return UserStatus.UNKNOWN, None
    elif isinstance(status, UserStatusOnline):
        return UserStatus.ONLINE, datetime.now(UTC)
    elif isinstance(status, UserStatusRecently):
        return UserStatus.RECENTLY, None
    elif isinstance(status, UserStatusLastWeek):
        return UserStatus.WITHIN_WEEK, None
    elif isinstance(status, UserStatusLastMonth):
        return UserStatus.WITHIN_MONTH, None
    elif isinstance(status, UserStatusOffline):
        return UserStatus.LONG_AGO, status.was_online
    else:
        return UserStatus.LONG_AGO, None


def user_to_member(user: User) -> TelegramMember:
    """Convert Telethon User to our TelegramMember model."""
    status, last_seen = parse_user_status(user)
    
    return TelegramMember(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name or "",
        last_name=user.last_name,
        phone=user.phone,
        last_seen=last_seen,
        status=status,
        is_bot=user.bot or False,
        is_premium=user.premium or False,
        is_verified=user.verified or False,
    )


class TelegramScraper:
    """Telegram group/channel member scraper."""
    
    def __init__(self, app_config: AppConfig | None = None) -> None:
        """Initialize the scraper with config."""
        self.config: AppConfig = app_config or config
        self._client: TelegramClient | None = None
    
    async def connect(self) -> TelegramClient:
        """Connect to Telegram and return the client."""
        if self._client is not None and self._client.is_connected():
            return self._client
        
        if self.config.telegram is None:
            raise ValueError(
                "Telegram credentials not configured. "
                "Run 'slot auth' or set TELEGRAM_API_ID and TELEGRAM_API_HASH."
            )
        
        session_path = self.config.ensure_data_dir() / self.config.telegram.session_name
        
        self._client = TelegramClient(
            str(session_path),
            self.config.telegram.api_id,
            self.config.telegram.api_hash,
        )
        
        await self._client.start()
        return self._client
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None
    
    async def get_group_info(self, group_identifier: str | int) -> GroupInfo:
        """Get information about a group or channel."""
        client = await self.connect()
        entity = await client.get_entity(group_identifier)
        
        if not isinstance(entity, Channel):
            raise ValueError(f"'{group_identifier}' is not a group or channel")
        
        return GroupInfo(
            group_id=entity.id,
            title=entity.title,
            username=entity.username,
            member_count=entity.participants_count or 0,
            is_channel=entity.broadcast,
            is_public=entity.username is not None,
        )
    
    async def scrape_members(
        self,
        group_identifier: str | int,
        limit: int | None = None,
    ) -> AsyncGenerator[TelegramMember, None]:
        """
        Scrape members with robust error handling and rate limit management.
        """
        from telethon.errors import FloodWaitError, RPCError
        
        client = await self.connect()
        try:
            entity = await client.get_entity(group_identifier)
        except Exception as e:
            raise ValueError(f"Could not find group '{group_identifier}': {e}") from e
            
        if not isinstance(entity, Channel):
            raise ValueError(f"'{group_identifier}' is not a group or channel")
        
        offset = 0
        batch_size = self.config.scraper.batch_size
        total_scraped = 0
        retries = 0
        
        while True:
            try:
                # Respect configured delay
                await asyncio.sleep(self.config.scraper.delay_between_requests)
                
                participants = await client(GetParticipantsRequest(
                    channel=entity,
                    filter=ChannelParticipantsSearch(""),
                    offset=offset,
                    limit=batch_size,
                    hash=0,
                ))
                
                if not participants.users:
                    break
                
                for user in participants.users:
                    if isinstance(user, User):
                        yield user_to_member(user)
                        total_scraped += 1
                        
                        if limit and total_scraped >= limit:
                            return
                
                offset += len(participants.users)
                retries = 0 # Reset retries on success
                
                if len(participants.users) < batch_size:
                    break
                    
            except FloodWaitError as e:
                # Handle Telegram rate limits automatically
                wait_time = e.seconds
                if wait_time > 300: # 5 minutes max wait
                    raise RuntimeError(f"Flood wait too long: {wait_time}s. Stopping.") from e
                
                await asyncio.sleep(wait_time)
                continue # Retry same offset
                
            except (RPCError, Exception) as e:
                retries += 1
                if retries > self.config.scraper.max_retries:
                    raise RuntimeError(f"Max retries ({self.config.scraper.max_retries}) exceeded: {e}") from e
                
                # Wait briefly before retry
                await asyncio.sleep(2 * retries)
                continue
    
    async def scrape_to_result(
        self,
        group_identifier: str | int,
        limit: int | None = None,
    ) -> ScrapeResult:
        """
        Scrape members and return a complete ScrapeResult.
        
        Use this for smaller groups. For large groups, use scrape_members()
        with streaming export.
        """
        group = await self.get_group_info(group_identifier)
        members: list[TelegramMember] = []
        errors: list[str] = []
        
        try:
            async for member in self.scrape_members(group_identifier, limit):
                members.append(member)
        except Exception as e:
            errors.append(str(e))
        
        return ScrapeResult(
            group=group,
            members=members,
            total_scraped=len(members),
            errors=errors,
        )
    
    async def __aenter__(self) -> "TelegramScraper":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def add_members(
        self,
        source_group: str | int,
        target_group: str | int,
        limit: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Add members from source group to target group safely.
        
        Yields status updates:
        {"status": "adding", "user": "username", "count": 5}
        {"status": "waiting", "seconds": 300}
        {"status": "error", "message": "..."}
        """
        from telethon.errors import (
            FloodWaitError, UserPrivacyRestrictedError, UserNotMutualContactError,
            UserChannelsTooMuchError, BotGroupsBlockedError
        )
        from telethon.tl.functions.channels import InviteToChannelRequest
        from telethon.tl.functions.messages import AddChatUserRequest
        from telethon.tl.types import Chat, InputPeerChat
        
        client = await self.connect()
        
        # Get entities
        try:
            target = await client.get_entity(target_group)
        except Exception as e:
            raise ValueError(f"Could not find target group '{target_group}': {e}")

        # We stream members from source
        count = 0
        added_in_batch = 0
        total_added = 0
        
        async for member in self.scrape_members(source_group, limit):
            if self.config.adder.max_additions and total_added >= self.config.adder.max_additions:
                break
                
            # Check batch limit
            if added_in_batch >= self.config.adder.batch_size:
                delay = self.config.adder.batch_delay
                yield {"status": "waiting", "seconds": delay, "message": f"Batch limit reached. Waiting {delay}s..."}
                await asyncio.sleep(delay)
                added_in_batch = 0
            
            try:
                # Add user
                user_input = await client.get_input_entity(member.user_id)
                
                if isinstance(target, Chat):
                    # Basic group
                    await client(AddChatUserRequest(
                        chat_id=target.id,
                        user_id=user_input,
                        fwd_limit=0  # Required arg for basic groups, usually 0 or 100
                    ))
                else:
                    # Supergroup / Channel
                    await client(InviteToChannelRequest(
                        channel=target,
                        users=[user_input]
                    ))
                
                added_in_batch += 1
                total_added += 1
                yield {"status": "added", "user": member.username or member.first_name, "count": total_added}
                
                # Small random delay between individual adds to be safe
                await asyncio.sleep(self.config.scraper.delay_between_requests * 2)
                
            except UserPrivacyRestrictedError:
                yield {"status": "skipped", "message": f"Privacy settings: {member.username}"}
            except UserNotMutualContactError:
                 yield {"status": "skipped", "message": f"Not mutual contact: {member.username}"}
            except (UserChannelsTooMuchError, BotGroupsBlockedError):
                 yield {"status": "skipped", "message": f"User cannot be added: {member.username}"}
            except FloodWaitError as e:
                yield {"status": "waiting", "seconds": e.seconds, "message": f"Flood wait: {e.seconds}s"}
                await asyncio.sleep(e.seconds)
            except RPCError as e:
                if "CHAT_MEMBER_ADD_FAILED" in str(e) or "USER_PRIVACY_RESTRICTED" in str(e):
                    yield {"status": "skipped", "message": f"Privacy restricted: {member.username}"}
                elif "USER_ALREADY_PARTICIPANT" in str(e):
                    yield {"status": "skipped", "message": f"Already in group: {member.username}"}
                else:
                    yield {"status": "error", "message": f"Telegram Error: {e}"}
            except Exception as e:
                yield {"status": "error", "message": str(e)}
