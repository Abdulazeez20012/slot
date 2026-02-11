"""Persistent storage for Slot using SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from .config import config
from .models import TelegramMember, UserStatus


class Storage:
    """Async SQLite storage for Telegram members and scrape jobs."""
    
    def __init__(self, db_path: Path | None = None):
        """Initialize storage with a database path."""
        self.db_path = db_path or config.ensure_data_dir() / "slot.db"
    
    async def initialize(self):
        """Initialize the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Table for members
            await db.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    last_seen TEXT,
                    status TEXT,
                    is_bot BOOLEAN,
                    is_premium BOOLEAN,
                    is_verified BOOLEAN,
                    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table for groups/scrape jobs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scrape_jobs (
                    job_id TEXT PRIMARY KEY,
                    group_identifier TEXT,
                    group_title TEXT,
                    status TEXT,
                    message TEXT,
                    progress INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for status filtering
            await db.execute("CREATE INDEX IF NOT EXISTS idx_members_status ON members(status)")
            
            await db.commit()
    
    async def save_member(self, member: TelegramMember):
        """Save a single member to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO members (
                    user_id, username, first_name, last_name, phone, 
                    last_seen, status, is_bot, is_premium, is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member.user_id,
                member.username,
                member.first_name,
                member.last_name,
                member.phone,
                member.last_seen.isoformat() if member.last_seen else None,
                member.status.value,
                member.is_bot,
                member.is_premium,
                member.is_verified
            ))
            await db.commit()
    
    async def save_members(self, members: list[TelegramMember]):
        """Save a batch of members efficiently."""
        async with aiosqlite.connect(self.db_path) as db:
            data = []
            for m in members:
                data.append((
                    m.user_id,
                    m.username,
                    m.first_name,
                    m.last_name,
                    m.phone,
                    m.last_seen.isoformat() if m.last_seen else None,
                    m.status.value,
                    m.is_bot,
                    m.is_premium,
                    m.is_verified
                ))
            
            await db.executemany("""
                INSERT OR REPLACE INTO members (
                    user_id, username, first_name, last_name, phone, 
                    last_seen, status, is_bot, is_premium, is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            await db.commit()
    
    async def create_job(self, job_id: str, group_identifier: str):
        """Create a new scrape job entry."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO scrape_jobs (job_id, group_identifier, status, message)
                VALUES (?, ?, 'pending', 'Starting...')
            """, (job_id, group_identifier))
            await db.commit()
    
    async def update_job(self, job_id: str, **kwargs):
        """Update job status or progress."""
        if not kwargs:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            sets = []
            values = []
            for k, v in kwargs.items():
                sets.append(f"{k} = ?")
                values.append(v)
            
            sets.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            
            values.append(job_id)
            query = f"UPDATE scrape_jobs SET {', '.join(sets)} WHERE job_id = ?"
            
            await db.execute(query, values)
            await db.commit()
    
    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a job by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute("SELECT * FROM scrape_jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_jobs(self) -> list[dict[str, Any]]:
        """Retrieve all jobs ordered by creation date."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute("SELECT * FROM scrape_jobs ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_members(self, limit: int = 100, offset: int = 0) -> list[TelegramMember]:
        """Retrieve members with pagination."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            async with db.execute(
                "SELECT * FROM members ORDER BY scraped_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
                members = []
                for row in rows:
                    last_seen = None
                    if row['last_seen']:
                        try:
                            last_seen = datetime.fromisoformat(row['last_seen'])
                        except ValueError:
                            pass
                            
                    members.append(TelegramMember(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        phone=row['phone'],
                        last_seen=last_seen,
                        status=UserStatus(row['status']),
                        is_bot=bool(row['is_bot']),
                        is_premium=bool(row['is_premium']),
                        is_verified=bool(row['is_verified'])
                    ))
                return members

# Global storage instance
storage = Storage()
