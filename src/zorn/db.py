from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass
####


class EntityRow(Base):
    __tablename__ = "entities"

    entity_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
####


class TaskRow(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(128), nullable=False)
    assignee_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
####


class ObjectRow(Base):
    __tablename__ = "objects"

    object_path: Mapped[str] = mapped_column(String(1024), primary_key=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
####


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
####


class Database:
    def __init__(self, database_url: str) -> None:
        connect_args: dict[str, Any] = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            self._ensure_sqlite_parent(database_url)
        ####
        self.engine: Engine = create_engine(database_url, connect_args=connect_args, future=True)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
    ####

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
    ####

    def session(self) -> Session:
        return self.session_factory()
    ####

    @staticmethod
    def _ensure_sqlite_parent(database_url: str) -> None:
        if database_url == "sqlite:///:memory:":
            return
        ####
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            return
        ####
        path = Path(database_url.removeprefix(prefix))
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        ####
    ####
####
