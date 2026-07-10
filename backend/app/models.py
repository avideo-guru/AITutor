from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"))
    sender: Mapped[str] = mapped_column(String(10))  # "user" | "tutor"
    text: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    step_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # diagnostic dataset seed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
