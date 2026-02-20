import os

os.environ.setdefault("TOKEN", "test_token_for_testing_only")
os.environ.setdefault("OWNER_ID", "123456789")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.filters import IsDefaultUser, IsStudent, IsTeacher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_message(user_id: int) -> MagicMock:
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    return msg


# ---------------------------------------------------------------------------
# IsTeacher
# ---------------------------------------------------------------------------


class TestIsTeacher:
    async def test_owner_id_is_teacher(self):
        import config as cfg

        owner_id = cfg.settings.owner_id
        msg = make_message(owner_id)
        result = await IsTeacher()(msg)
        assert result is True

    async def test_non_owner_is_not_teacher(self):
        msg = make_message(999999999)
        result = await IsTeacher()(msg)
        assert result is False

    async def test_zero_id_is_not_teacher(self):
        msg = make_message(0)
        result = await IsTeacher()(msg)
        assert result is False

    async def test_negative_id_is_not_teacher(self):
        msg = make_message(-1)
        result = await IsTeacher()(msg)
        assert result is False

    async def test_returns_bool(self):
        msg = make_message(999999999)
        result = await IsTeacher()(msg)
        assert isinstance(result, bool)

    async def test_teacher_list_contains_owner(self):
        import config as cfg

        assert cfg.settings.owner_id in cfg.settings.teachers


# ---------------------------------------------------------------------------
# IsStudent
# ---------------------------------------------------------------------------


class TestIsStudent:
    async def test_user_with_no_db_record_is_not_student(self):
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            msg = make_message(111)
            result = await IsStudent()(msg)
        assert result is False

    async def test_user_with_db_record_is_student(self):
        mock_student = MagicMock()
        with patch(
            "app.filters.rq.get_student_by_tg",
            new=AsyncMock(return_value=mock_student),
        ):
            msg = make_message(222)
            result = await IsStudent()(msg)
        assert result is True

    async def test_calls_get_student_by_tg_with_correct_id(self):
        mock_fn = AsyncMock(return_value=None)
        with patch("app.filters.rq.get_student_by_tg", new=mock_fn):
            msg = make_message(333)
            await IsStudent()(msg)
        mock_fn.assert_called_once_with(333)

    async def test_returns_bool_false(self):
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            msg = make_message(444)
            result = await IsStudent()(msg)
        assert isinstance(result, bool)
        assert result is False

    async def test_returns_bool_true(self):
        with patch(
            "app.filters.rq.get_student_by_tg",
            new=AsyncMock(return_value=MagicMock()),
        ):
            msg = make_message(555)
            result = await IsStudent()(msg)
        assert isinstance(result, bool)
        assert result is True


# ---------------------------------------------------------------------------
# IsDefaultUser
# ---------------------------------------------------------------------------


class TestIsDefaultUser:
    async def test_unregistered_non_teacher_is_default_user(self):
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            msg = make_message(777)
            result = await IsDefaultUser()(msg)
        assert result is True

    async def test_teacher_is_not_default_user(self):
        import config as cfg

        owner_id = cfg.settings.owner_id
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            msg = make_message(owner_id)
            result = await IsDefaultUser()(msg)
        assert result is False

    async def test_registered_student_is_not_default_user(self):
        mock_student = MagicMock()
        with patch(
            "app.filters.rq.get_student_by_tg",
            new=AsyncMock(return_value=mock_student),
        ):
            msg = make_message(888)
            result = await IsDefaultUser()(msg)
        assert result is False

    async def test_returns_bool_true_for_stranger(self):
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            msg = make_message(123456)
            result = await IsDefaultUser()(msg)
        assert isinstance(result, bool)
        assert result is True

    async def test_returns_bool_false_for_student(self):
        with patch(
            "app.filters.rq.get_student_by_tg",
            new=AsyncMock(return_value=MagicMock()),
        ):
            msg = make_message(654321)
            result = await IsDefaultUser()(msg)
        assert isinstance(result, bool)
        assert result is False

    async def test_student_who_is_also_teacher_is_not_default_user(self):
        """Edge case: if a teacher's ID is somehow also in student DB."""
        import config as cfg

        owner_id = cfg.settings.owner_id
        mock_student = MagicMock()
        with patch(
            "app.filters.rq.get_student_by_tg",
            new=AsyncMock(return_value=mock_student),
        ):
            msg = make_message(owner_id)
            result = await IsDefaultUser()(msg)
        # Is a teacher → definitely not default user
        assert result is False

    async def test_calls_db_with_correct_user_id(self):
        mock_fn = AsyncMock(return_value=None)
        with patch("app.filters.rq.get_student_by_tg", new=mock_fn):
            msg = make_message(424242)
            await IsDefaultUser()(msg)
        mock_fn.assert_called_once_with(424242)

    async def test_different_unknown_ids_are_default_users(self):
        with patch(
            "app.filters.rq.get_student_by_tg", new=AsyncMock(return_value=None)
        ):
            for uid in [10001, 10002, 10003]:
                msg = make_message(uid)
                result = await IsDefaultUser()(msg)
                assert result is True, f"user_id={uid} should be default user"
