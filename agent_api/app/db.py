# app/db.py
from datetime import datetime
from typing import List, Tuple
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, ForeignKey
import asyncio
from sqlalchemy import select

import os
from pathlib import Path

# ── ensure ./data exists ────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)             # creates /app/data inside container

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'chat.db'}"

# DATABASE_URL = "sqlite+aiosqlite:///./data/chat.db"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[UUID] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String, ForeignKey("chats.id"))
    role: Mapped[str] = mapped_column(String)          # user / assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ───────────────────────────────── helpers ─────────────────────────────────── #

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# asyncio.run(init_db())     # one-shot migrate on container start


async def get_or_create_chat(chat_id: str | None) -> UUID:
    async with SessionLocal() as session:
        if chat_id is not None:
            # already a UUID? → keep it;  string? → parse it
            cid: UUID = chat_id if isinstance(chat_id, UUID) else UUID(str(chat_id))

            # (optional) create a row if the client sent an unknown id
            if await session.get(Chat, str(cid)) is None:
                session.add(Chat(id=str(cid)))
                await session.commit()

            return cid

        # ── no id provided → create a new one ─────────────────────────
        cid = uuid4()
        session.add(Chat(id=str(cid)))
        await session.commit()
        return cid


async def save_message(chat_id: UUID, role: str, content: str):
    async with SessionLocal() as session:
        session.add(Message(chat_id=str(chat_id), role=role, content=content))
        await session.commit()

async def fetch_history(chat_id: UUID, limit: int | None = 20) -> List[Tuple[str, str]]:
    """
    Returns [(role, content), …] ordered oldest→newest.
    Set `limit=None` if you want the full thread.
    """
    async with SessionLocal() as session:
        q = (await session.execute(
                 select(Message.role, Message.content)
                 .where(Message.chat_id == str(chat_id))
                 .order_by(Message.created_at.asc())
                 .limit(limit)
             )
        ).all()
    return [(r, c) for r, c in q]
