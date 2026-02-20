import os
import sys

# Must be set BEFORE any project imports so pydantic-settings picks them up
os.environ.setdefault("TOKEN", "test_token_for_testing_only")
os.environ.setdefault("OWNER_ID", "123456789")

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# In-memory SQLite engine shared across DB tests
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default asyncio policy."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory SQLite engine with all tables for each test."""
    from app.database.models import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a transactional AsyncSession that is rolled back after each test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def patched_session(db_engine, monkeypatch):
    """
    Replace the async_session used by app.database.requests with an
    in-memory session factory so that all public DB functions work against
    the test database.
    """
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr("app.database.requests.async_session", session_factory)
    monkeypatch.setattr("app.database.models.async_session", session_factory)
    return session_factory


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_student_data():
    return {
        "firstname": "Иван",
        "middlename": "Иванович",
        "lastname": "Иванов",
        "group": "КА-401",
        "mark_book": "17М235",
        "tg_id": None,
    }


@pytest.fixture
def sample_teacher_data():
    return {
        "firstname": "Пётр",
        "middlename": "Петрович",
        "lastname": "Петров",
        "tg_id": 123456789,
    }


# ---------------------------------------------------------------------------
# Temporary file helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir(tmp_path):
    """Return a temporary directory Path."""
    return tmp_path


@pytest.fixture
def solution_json_factory(tmp_path):
    """
    Returns a factory that writes a solution JSON to a temp file and gives
    back its path as an open file-like object.
    """

    def _factory(data: dict, filename: str = "solution.json"):
        fpath = tmp_path / filename
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return fpath

    return _factory


# ---------------------------------------------------------------------------
# Minimal mock for a Telegram Message / CallbackQuery
# ---------------------------------------------------------------------------


def make_mock_message(text: str = "/start", user_id: int = 999):
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.first_name = "Test"
    msg.answer = AsyncMock()
    msg.answer_document = AsyncMock()
    msg.delete = AsyncMock()
    return msg


def make_mock_callback(data: str = "some:data", user_id: int = 999):
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.message = make_mock_message(user_id=user_id)
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    return cb


@pytest.fixture
def mock_message():
    return make_mock_message()


@pytest.fixture
def mock_callback():
    return make_mock_callback()
