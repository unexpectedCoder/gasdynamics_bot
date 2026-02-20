from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database.requests as rq
from app.database.models import (
    Base,
    ControlWork,
    HomeworkNozzle,
    HomeworkSettings,
    HomeworkShockWedge,
    Lab,
    Student,
    Teacher,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def _make_student(**kwargs) -> Student:
    defaults = dict(
        firstname="Иван",
        middlename="Иванович",
        lastname="Иванов",
        group="КА-401",
        mark_book="17М235",
        tg_id=None,
    )
    defaults.update(kwargs)
    return Student(**defaults)


def _make_hw_nozzle(**kwargs) -> HomeworkNozzle:
    defaults = dict(
        variant=1,
        p0="5000000.0",
        T0="2500",
        R="287.0",
        k="1.4",
        d_critic="0.15",
        area_ratio="8.5",
        d_chamber="1.2",
        alpha="40",
        beta="10",
        rel_propel_mass="0.75",
    )
    defaults.update(kwargs)
    return HomeworkNozzle(**defaults)


def _make_hw_wedge(**kwargs) -> HomeworkShockWedge:
    defaults = dict(
        variant=1,
        mach="2.5",
        beta1="10.0",
        beta2="20.0",
        beta3="30.0",
    )
    defaults.update(kwargs)
    return HomeworkShockWedge(**defaults)


# ---------------------------------------------------------------------------
# Session-level engine fixture (shared across all DB tests in this module)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def patch_session(session_factory, monkeypatch):
    """Redirect all DB requests to the in-memory test database."""
    monkeypatch.setattr("app.database.requests.async_session", session_factory)
    monkeypatch.setattr("app.database.models.async_session", session_factory)


# ---------------------------------------------------------------------------
# get_student_by_mark_book
# ---------------------------------------------------------------------------


class TestGetStudentByMarkBook:
    async def test_returns_none_when_not_found(self):
        result = await rq.get_student_by_mark_book("NONEXISTENT")
        assert result is None

    async def test_returns_student_when_found(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

        result = await rq.get_student_by_mark_book("17М235")
        assert result is not None
        assert result.mark_book == "17М235"

    async def test_returns_correct_student_among_many(self, session_factory):
        async with session_factory() as session:
            session.add(_make_student(mark_book="AAA111"))
            session.add(_make_student(mark_book="BBB222", tg_id=1))
            await session.commit()

        result = await rq.get_student_by_mark_book("BBB222")
        assert result is not None
        assert result.mark_book == "BBB222"


# ---------------------------------------------------------------------------
# get_student_by_tg
# ---------------------------------------------------------------------------


class TestGetStudentByTg:
    async def test_returns_none_when_not_found(self):
        result = await rq.get_student_by_tg(999999)
        assert result is None

    async def test_returns_student_when_found(self, session_factory):
        async with session_factory() as session:
            s = _make_student(tg_id=42)
            session.add(s)
            await session.commit()

        result = await rq.get_student_by_tg(42)
        assert result is not None
        assert result.tg_id == 42

    async def test_different_tg_id_not_returned(self, session_factory):
        async with session_factory() as session:
            session.add(_make_student(tg_id=100))
            await session.commit()

        result = await rq.get_student_by_tg(200)
        assert result is None


# ---------------------------------------------------------------------------
# get_student_by_id
# ---------------------------------------------------------------------------


class TestGetStudentById:
    async def test_returns_none_for_unknown_id(self):
        result = await rq.get_student_by_id(9999)
        assert result is None

    async def test_returns_student_for_known_id(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()
            sid = s.id

        result = await rq.get_student_by_id(sid)
        assert result is not None
        assert result.id == sid


# ---------------------------------------------------------------------------
# add_student
# ---------------------------------------------------------------------------


class TestAddStudent:
    async def test_add_new_student(self):
        data = dict(
            firstname="Мария",
            middlename="Александровна",
            lastname="Козлова",
            group="КА-402",
            mark_book="18М001",
        )
        student, created = await rq.add_student(data)
        assert created is True
        assert student is not None
        assert student.mark_book == "18М001"

    async def test_add_duplicate_mark_book_returns_existing(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="DUP001")
            session.add(s)
            await session.commit()

        data = dict(
            firstname="Другой",
            middlename="Другойович",
            lastname="Другойов",
            group="КА-401",
            mark_book="DUP001",
        )
        student, created = await rq.add_student(data)
        assert created is False
        assert student.mark_book == "DUP001"

    async def test_created_student_is_retrievable(self):
        data = dict(
            firstname="Алексей",
            middlename="Сергеевич",
            lastname="Попов",
            group="КА-403",
            mark_book="19М099",
        )
        await rq.add_student(data)
        found = await rq.get_student_by_mark_book("19М099")
        assert found is not None
        assert found.firstname == "Алексей"


# ---------------------------------------------------------------------------
# reg_student (tg_id assignment)
# ---------------------------------------------------------------------------


class TestRegStudent:
    async def test_registers_tg_id(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="REG001", tg_id=None)
            session.add(s)
            await session.commit()
            s_id = s.id

        result = await rq.get_student_by_id(s_id)
        result.tg_id = 77777
        await rq.reg_student(result)

        updated = await rq.get_student_by_id(s_id)
        assert updated.tg_id == 77777

    async def test_tg_lookup_works_after_registration(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="REG002", tg_id=None)
            session.add(s)
            await session.commit()
            s_id = s.id

        result = await rq.get_student_by_id(s_id)
        result.tg_id = 88888
        await rq.reg_student(result)

        by_tg = await rq.get_student_by_tg(88888)
        assert by_tg is not None
        assert by_tg.mark_book == "REG002"


# ---------------------------------------------------------------------------
# get_students
# ---------------------------------------------------------------------------


class TestGetStudents:
    async def test_empty_db_returns_empty(self):
        result = await rq.get_students()
        assert list(result) == []

    async def test_returns_all_students(self, session_factory):
        async with session_factory() as session:
            session.add(_make_student(mark_book="S001"))
            session.add(_make_student(mark_book="S002", tg_id=1))
            session.add(_make_student(mark_book="S003", tg_id=2))
            await session.commit()

        result = list(await rq.get_students())
        assert len(result) == 3

    async def test_returned_objects_are_students(self, session_factory):
        async with session_factory() as session:
            session.add(_make_student(mark_book="S_TYPE"))
            await session.commit()

        result = list(await rq.get_students())
        assert all(isinstance(s, Student) for s in result)


# ---------------------------------------------------------------------------
# db_is_empty
# ---------------------------------------------------------------------------


class TestDbIsEmpty:
    async def test_empty_on_fresh_db(self):
        assert await rq.db_is_empty() is True

    async def test_not_empty_after_adding_student(self, session_factory):
        async with session_factory() as session:
            session.add(_make_student())
            await session.commit()

        assert await rq.db_is_empty() is False


# ---------------------------------------------------------------------------
# get_teacher_by_tg
# ---------------------------------------------------------------------------


class TestGetTeacherByTg:
    async def test_returns_none_for_unknown_tg(self):
        result = await rq.get_teacher_by_tg(999)
        assert result is None

    async def test_returns_teacher_for_known_tg(self, session_factory):
        async with session_factory() as session:
            t = Teacher(
                firstname="Пётр",
                middlename="Петрович",
                lastname="Петров",
                tg_id=55555,
            )
            session.add(t)
            await session.commit()

        result = await rq.get_teacher_by_tg(55555)
        assert result is not None
        assert result.tg_id == 55555
        assert result.lastname == "Петров"


# ---------------------------------------------------------------------------
# Homework (nozzle — semester 1)
# ---------------------------------------------------------------------------


class TestGetHomeworkOf:
    async def test_returns_none_when_no_homework(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        result = await rq.get_homework_of(student, sem=1)
        assert result is None

    async def test_returns_homework_when_assigned(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        result = await rq.get_homework_of(student, sem=1)
        assert result is not None
        assert result.variant == 1

    async def test_returns_none_for_wrong_semester(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        # sem=2 uses HomeworkShockWedge, not HomeworkNozzle
        result = await rq.get_homework_of(student, sem=2)
        assert result is None


class TestGetFreeHomework:
    async def test_returns_none_when_no_homework_records(self):
        result = await rq.get_free_homework(sem=1)
        assert result is None

    async def test_returns_unassigned_homework(self, session_factory):
        async with session_factory() as session:
            hw = _make_hw_nozzle(student_id=None)
            session.add(hw)
            await session.commit()

        result = await rq.get_free_homework(sem=1)
        assert result is not None
        assert result.student_id is None

    async def test_does_not_return_assigned_homework(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()

        result = await rq.get_free_homework(sem=1)
        assert result is None


class TestSetHomework:
    async def test_assigns_homework_to_student(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=None)
            session.add(hw)
            await session.commit()
            s_id = s.id
            hw_id = hw.id

        student = await rq.get_student_by_id(s_id)
        from sqlalchemy import select

        from app.database.models import async_session

        async with session_factory() as session:
            hw = await session.get(HomeworkNozzle, hw_id)
            await rq.set_homework(student, hw)

        result = await rq.get_homework_of(student, sem=1)
        assert result is not None
        assert result.student_id == s_id


class TestSetHomeworkDeadline:
    async def test_deadline_is_set_on_active_settings(self, session_factory):
        async with session_factory() as session:
            session.add(HomeworkSettings(hw_type="nozzle", available=True))
            await session.commit()

        target_date = date(2025, 6, 1)
        await rq.set_homework_deadline(target_date)

        result = await rq.get_homework_deadline()
        assert result == target_date

    async def test_get_deadline_returns_none_when_not_set(self, session_factory):
        async with session_factory() as session:
            session.add(HomeworkSettings(hw_type="nozzle", available=True))
            await session.commit()

        result = await rq.get_homework_deadline()
        assert result is None

    async def test_get_deadline_returns_none_when_no_active_settings(self):
        result = await rq.get_homework_deadline()
        assert result is None


# ---------------------------------------------------------------------------
# send_homework / approve_homework
# ---------------------------------------------------------------------------


class TestSendHomework:
    async def test_send_flag_is_set(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            s_id = s.id
            hw_id = hw.id

        async with session_factory() as session:
            hw = await session.get(HomeworkNozzle, hw_id)
            assert hw.send is False
            await rq.send_homework(hw)

        async with session_factory() as session:
            hw_after = await session.get(HomeworkNozzle, hw_id)
            assert hw_after.send is True


class TestApproveHomework:
    async def test_approve_sets_approved_flag(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            s_id = s.id
            hw_id = hw.id

        student = await rq.get_student_by_id(s_id)
        await rq.approve_homework(student, date=date(2025, 5, 1), sem=1)

        async with session_factory() as session:
            hw_after = await session.get(HomeworkNozzle, hw_id)
            assert hw_after.approved is True
            assert hw_after.approve_date == date(2025, 5, 1)


# ---------------------------------------------------------------------------
# Lab operations
# ---------------------------------------------------------------------------


class TestGetFreelab:
    async def test_returns_none_when_no_lab_records(self):
        result = await rq.get_free_lab(lab_n=1)
        assert result is None

    async def test_returns_unassigned_lab(self, session_factory):
        async with session_factory() as session:
            lab = Lab(lab_number=1, student_id=None)
            session.add(lab)
            await session.commit()

        result = await rq.get_free_lab(lab_n=1)
        assert result is not None
        assert result.student_id is None

    async def test_does_not_return_assigned_lab(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            lab = Lab(lab_number=2, student_id=s.id)
            session.add(lab)
            await session.commit()

        result = await rq.get_free_lab(lab_n=2)
        assert result is None

    async def test_returns_correct_lab_number(self, session_factory):
        async with session_factory() as session:
            session.add(Lab(lab_number=3, student_id=None))
            session.add(Lab(lab_number=4, student_id=None))
            await session.commit()

        result = await rq.get_free_lab(lab_n=3)
        assert result.lab_number == 3


class TestGetLabOf:
    async def test_returns_none_when_no_lab(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        result = await rq.get_lab_of(student, lab_n=1)
        assert result is None

    async def test_returns_correct_lab(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            lab = Lab(lab_number=1, student_id=s.id)
            session.add(lab)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        result = await rq.get_lab_of(student, lab_n=1)
        assert result is not None
        assert result.lab_number == 1


class TestSendLab:
    async def test_send_flag_is_set(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            lab = Lab(lab_number=1, student_id=s.id)
            session.add(lab)
            await session.commit()
            lab_id = lab.id

        async with session_factory() as session:
            lab = await session.get(Lab, lab_id)
            assert lab.send is False
            await rq.send_lab(lab)

        async with session_factory() as session:
            lab_after = await session.get(Lab, lab_id)
            assert lab_after.send is True


class TestAssessLab:
    async def test_assess_sets_done_and_points(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            lab = Lab(lab_number=1, student_id=s.id)
            session.add(lab)
            await session.commit()
            lab_id = lab.id

        async with session_factory() as session:
            lab = await session.get(Lab, lab_id)

        data = {"points": 8, "date": date(2025, 3, 10)}
        await rq.assess_lab(data, lab)

        async with session_factory() as session:
            lab_after = await session.get(Lab, lab_id)
            assert lab_after.done is True
            assert lab_after.points == 8
            assert lab_after.done_date == date(2025, 3, 10)


# ---------------------------------------------------------------------------
# assess_homework
# ---------------------------------------------------------------------------


class TestAssessHomework:
    async def test_assess_sets_done_and_points(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            s_id = s.id
            hw_id = hw.id

        student = await rq.get_student_by_id(s_id)
        data = {"student": student, "points": 9, "date": date(2025, 4, 15)}
        await rq.assess_homework(data, sem=1)

        async with session_factory() as session:
            hw_after = await session.get(HomeworkNozzle, hw_id)
            assert hw_after.done is True
            assert hw_after.points == 9
            assert hw_after.done_date == date(2025, 4, 15)


# ---------------------------------------------------------------------------
# get_students_homeworks
# ---------------------------------------------------------------------------


class TestGetStudentsHomeworks:
    async def test_returns_only_assigned_homeworks(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            # assigned
            session.add(_make_hw_nozzle(variant=1, student_id=s.id))
            # free (not assigned)
            session.add(_make_hw_nozzle(variant=2, student_id=None))
            await session.commit()

        result = list(await rq.get_students_homeworks(sem=1))
        assert len(result) == 1
        assert result[0].variant == 1

    async def test_returns_empty_when_none_assigned(self, session_factory):
        async with session_factory() as session:
            session.add(_make_hw_nozzle(variant=5, student_id=None))
            await session.commit()

        result = list(await rq.get_students_homeworks(sem=1))
        assert result == []


# ---------------------------------------------------------------------------
# delete_student
# ---------------------------------------------------------------------------


class TestDeleteStudent:
    async def test_student_is_removed_from_db(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="DEL001")
            session.add(s)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        await rq.delete_student(student)

        result = await rq.get_student_by_id(s_id)
        assert result is None

    async def test_homework_is_freed_on_delete(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="DEL002")
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            session.add(hw)
            await session.commit()
            hw_id = hw.id
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        await rq.delete_student(student)

        async with session_factory() as session:
            hw_after = await session.get(HomeworkNozzle, hw_id)
            assert hw_after.student_id is None
            assert hw_after.done is False
            assert hw_after.points is None

    async def test_lab_is_freed_on_delete(self, session_factory):
        async with session_factory() as session:
            s = _make_student(mark_book="DEL003")
            session.add(s)
            await session.commit()

            lab = Lab(lab_number=1, student_id=s.id, send=True, done=True, points=7)
            session.add(lab)
            await session.commit()
            lab_id = lab.id
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        await rq.delete_student(student)

        async with session_factory() as session:
            lab_after = await session.get(Lab, lab_id)
            assert lab_after.student_id is None
            assert lab_after.send is False
            assert lab_after.done is False
            assert lab_after.points is None


# ---------------------------------------------------------------------------
# get_controls_of / set_control_points_of
# ---------------------------------------------------------------------------


class TestControlWorks:
    async def test_get_controls_of_returns_two_for_sem1(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            for n in (1, 2, 3, 4):
                session.add(ControlWork(student_id=s.id, control_number=n))
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        controls = await rq.get_controls_of(student, sem=1)
        assert len(controls) == 2
        assert controls[0].control_number == 1
        assert controls[1].control_number == 2

    async def test_get_controls_of_returns_two_for_sem2(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            for n in (1, 2, 3, 4):
                session.add(ControlWork(student_id=s.id, control_number=n))
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        controls = await rq.get_controls_of(student, sem=2)
        assert len(controls) == 2
        assert controls[0].control_number == 3
        assert controls[1].control_number == 4

    async def test_set_control_points_persists(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            for n in (1, 2):
                session.add(ControlWork(student_id=s.id, control_number=n))
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        controls = await rq.get_controls_of(student, sem=1)

        controls[0].points = 15
        controls[1].points = 20
        await rq.set_control_points_of(controls)

        # Re-fetch and verify
        updated = await rq.get_controls_of(student, sem=1)
        assert updated[0].points == 15
        assert updated[1].points == 20


# ---------------------------------------------------------------------------
# get_progress_of
# ---------------------------------------------------------------------------


class TestGetProgressOf:
    async def test_returns_none_for_missing_data(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        hw_nozzle, hw_wedge, labs, controls = await rq.get_progress_of(student)

        assert hw_nozzle is None
        assert hw_wedge is None
        assert all(p is None for p in labs)

    async def test_returns_correct_nozzle_hw_points(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_nozzle(student_id=s.id)
            hw.points = 85
            session.add(hw)
            await session.commit()

            for n in (1, 2, 3, 4):
                session.add(ControlWork(student_id=s.id, control_number=n))
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        hw_nozzle, hw_wedge, labs, controls = await rq.get_progress_of(student)

        assert hw_nozzle == 85
        assert hw_wedge is None

    async def test_returns_correct_wedge_hw_points(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            hw = _make_hw_wedge(student_id=s.id)
            hw.points = 72
            session.add(hw)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        hw_nozzle, hw_wedge, labs, controls = await rq.get_progress_of(student)

        assert hw_nozzle is None
        assert hw_wedge == 72

    async def test_returns_six_lab_slots(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        _, _, labs, _ = await rq.get_progress_of(student)

        assert len(labs) == 6

    async def test_returns_all_four_controls(self, session_factory):
        async with session_factory() as session:
            s = _make_student()
            session.add(s)
            await session.commit()

            for n in (1, 2, 3, 4):
                session.add(ControlWork(student_id=s.id, control_number=n))
            await session.commit()
            s_id = s.id

        student = await rq.get_student_by_id(s_id)
        _, _, _, controls = await rq.get_progress_of(student)

        assert len(controls) == 4
        assert [c.control_number for c in controls] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# update_groups
# ---------------------------------------------------------------------------


class TestUpdateGroups:
    async def test_update_groups_changes_group_suffix(self, session_factory):
        async with session_factory() as session:
            # Group name ends with two characters; update_groups replaces [-2] with
            # "4" (sem=1) or "5" (sem=2) and keeps the last char.
            s = _make_student(group="КА-401")
            session.add(s)
            await session.commit()
            s_id = s.id

        await rq.update_groups(sem=1)

        updated = await rq.get_student_by_id(s_id)
        # last two chars: "01" → "4" + "1" = "41"
        assert updated.group.endswith("41")

    async def test_update_groups_sem2_uses_5(self, session_factory):
        async with session_factory() as session:
            s = _make_student(group="КА-401")
            session.add(s)
            await session.commit()
            s_id = s.id

        await rq.update_groups(sem=2)

        updated = await rq.get_student_by_id(s_id)
        assert updated.group.endswith("51")
