import json
import os
import random as rand
from datetime import date as ddate
from functools import wraps

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config as cfg
from app.database.models import (
    HW_TYPE_NOZZLE,
    HW_TYPE_SHOCK_WEDGE,
    AnyHomework,
    ControlWork,
    HomeworkNozzle,
    HomeworkSettings,
    HomeworkShockWedge,
    Lab,
    Student,
    Teacher,
    async_session,
)

rand.seed(ddate.today().year)


def connection(func):
    @wraps(func)
    async def inner(*args, **kw):
        async with async_session() as session:
            return await func(session, *args, **kw)

    return inner


@connection
async def db_is_empty(session: AsyncSession):
    return await session.scalar(select(Student)) is None


async def fill_database():
    async with async_session() as session:
        _init_teachers(session)
        _init_students(session)
        await session.commit()

        await _init_controls(session)
        await _init_homework_nozzle(session)
        await _init_homework_shock_wedge(session)
        await _init_labs(session)
        await session.commit()


def _require_setting(value, name: str):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise RuntimeError(f"Не задано значение {name} в настройках")
    return value


def _init_teachers(session: AsyncSession):
    owner = {
        "firstname": _require_setting(cfg.settings.owner_firstname, "OWNER_FIRSTNAME"),
        "middlename": _require_setting(
            cfg.settings.owner_middlename, "OWNER_MIDDLENAME"
        ),
        "lastname": _require_setting(cfg.settings.owner_lastname, "OWNER_LASTNAME"),
        "tg_id": _require_setting(cfg.settings.owner_id, "OWNER_ID"),
    }
    session.add(Teacher(**owner))


def _init_students(session: AsyncSession):
    path = cfg.get_file("students")
    with open(path, "r", encoding="utf-8") as f:
        journal = json.load(f)
    for gname, group in journal.items():
        for mark_book in group:
            session.add(Student(group=gname, mark_book=mark_book, **group[mark_book]))


async def _init_controls(session: AsyncSession):
    students = await session.scalars(select(Student))
    for s in students:
        for n in range(1, 5):  # 4 контрольных работы: 1,2 — сем. 1; 3,4 — сем. 2
            session.add(ControlWork(student_id=s.id, control_number=n))


async def _init_homework_nozzle(session: AsyncSession):
    path = cfg.get_file("home_nozzle")
    with open(path, "r") as f:
        variants = _shuffle_variants(json.load(f))
    students = await session.scalars(select(Student))
    for v, s in zip(variants, students):
        session.add(HomeworkNozzle(student_id=s.id, variant=v, **variants[v]))


async def _init_homework_shock_wedge(session: AsyncSession):
    path = cfg.get_file("home_shock_wedge")
    with open(path, "r") as f:
        variants = _shuffle_variants(json.load(f))
    students = await session.scalars(select(Student))
    for v, s in zip(variants, students):
        session.add(HomeworkShockWedge(student_id=s.id, variant=v, **variants[v]))


async def _init_labs(session: AsyncSession):
    students = await session.scalars(select(Student))
    for s in students:
        for n in range(1, 7):
            session.add(Lab(student_id=s.id, lab_number=n))


def _shuffle_variants(variants: dict):
    items = list(variants.items())
    rand.shuffle(items)
    return dict(items)


def _get_hw_class(hw_type: str):
    """Return the ORM class for the given homework type string."""
    if hw_type == HW_TYPE_NOZZLE:
        return HomeworkNozzle
    if hw_type == HW_TYPE_SHOCK_WEDGE:
        return HomeworkShockWedge
    raise RuntimeError(f"unknown homework type: {hw_type!r}")


def _get_semester_hw(sem: int):
    """Legacy helper: map semester number to ORM class (used by teacher flows)."""
    if sem < 1 or sem > 2:
        raise RuntimeError(f"нет задания для {sem} семестра")
    return HomeworkNozzle if sem == 1 else HomeworkShockWedge


def _sem_to_hw_type(sem: int) -> str:
    return HW_TYPE_NOZZLE if sem == 1 else HW_TYPE_SHOCK_WEDGE


# ---------------------------------------------------------------------------
# Приватные версии (принимают сессию, без декоратора)
# ---------------------------------------------------------------------------


async def _get_student_by_mark_book(session: AsyncSession, mark_book: str):
    return await session.scalar(select(Student).where(Student.mark_book == mark_book))


async def _get_homework_of(session: AsyncSession, s: Student, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(select(HW).where(HW.student_id == s.id))


async def _get_homework_of_type(session: AsyncSession, s: Student, hw_type: str):
    HW = _get_hw_class(hw_type)
    return await session.scalar(select(HW).where(HW.student_id == s.id))


async def _get_lab_of(session: AsyncSession, s: Student, lab_n: int):
    return await session.scalar(
        select(Lab).where(Lab.student_id == s.id, Lab.lab_number == lab_n)
    )


async def _get_all_controls_of(session: AsyncSession, s: Student):
    """Return all four control works for the student, sorted by control_number."""
    result = await session.scalars(
        select(ControlWork)
        .where(ControlWork.student_id == s.id)
        .order_by(ControlWork.control_number)
    )
    return list(result.all())


async def _get_controls_of(session: AsyncSession, s: Student, sem: int):
    """Return two control works for the given semester, sorted by control_number."""
    numbers = (1, 2) if sem == 1 else (3, 4)
    result = await session.scalars(
        select(ControlWork)
        .where(ControlWork.student_id == s.id, ControlWork.control_number.in_(numbers))
        .order_by(ControlWork.control_number)
    )
    return list(result.all())


async def _get_active_hw_settings(session: AsyncSession) -> HomeworkSettings | None:
    return await session.scalar(
        select(HomeworkSettings).where(HomeworkSettings.available.is_(True))
    )


async def _get_hw_settings(
    session: AsyncSession, hw_type: str
) -> HomeworkSettings | None:
    return await session.scalar(
        select(HomeworkSettings).where(HomeworkSettings.hw_type == hw_type)
    )


# ---------------------------------------------------------------------------
# Публичный API — HomeworkSettings
# ---------------------------------------------------------------------------


@connection
async def get_active_hw_settings(session: AsyncSession) -> HomeworkSettings | None:
    """Return the HomeworkSettings row that is currently marked available, or None."""
    return await _get_active_hw_settings(session)


@connection
async def get_hw_settings(
    session: AsyncSession, hw_type: str
) -> HomeworkSettings | None:
    """Return HomeworkSettings for a specific hw_type."""
    return await _get_hw_settings(session, hw_type)


@connection
async def set_hw_available(session: AsyncSession, hw_type: str, available: bool):
    """Enable or disable student access to a homework type.

    When enabling a type, all other types are automatically disabled so that
    only one homework is active at a time.
    """
    if available:
        # Close all others first
        await session.execute(
            update(HomeworkSettings)
            .where(HomeworkSettings.hw_type != hw_type)
            .values(available=False)
        )
    await session.execute(
        update(HomeworkSettings)
        .where(HomeworkSettings.hw_type == hw_type)
        .values(available=available)
    )
    await session.commit()


@connection
async def set_homework_deadline(session: AsyncSession, deadline: ddate | None):
    """Set deadline on the currently active HomeworkSettings row."""
    settings = await _get_active_hw_settings(session)
    if settings is None:
        return
    await session.execute(
        update(HomeworkSettings)
        .where(HomeworkSettings.hw_type == settings.hw_type)
        .values(deadline=deadline)
    )
    await session.commit()


@connection
async def get_homework_deadline(session: AsyncSession) -> ddate | None:
    """Return the deadline from the currently active HomeworkSettings, or None."""
    settings = await _get_active_hw_settings(session)
    if settings is None:
        return None
    return settings.deadline


# ---------------------------------------------------------------------------
# Публичный API — Students / Teachers
# ---------------------------------------------------------------------------


@connection
async def reg_student(session: AsyncSession, student: Student):
    await session.execute(
        update(Student).where(Student.id == student.id).values(tg_id=student.tg_id)
    )
    await session.commit()


@connection
async def get_students(session: AsyncSession):
    return await session.scalars(select(Student))


@connection
async def get_student_by_id(session: AsyncSession, id: int):
    return await session.scalar(select(Student).where(Student.id == id))


@connection
async def get_student_by_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(select(Student).where(Student.tg_id == tg_id))


@connection
async def get_student_by_mark_book(session: AsyncSession, mark_book: str):
    return await _get_student_by_mark_book(session, mark_book)


@connection
async def add_student(session: AsyncSession, data: dict):
    s = await _get_student_by_mark_book(session, data["mark_book"])
    if s:
        return s, False

    session.add(Student(**data))
    await session.commit()
    return await _get_student_by_mark_book(session, data["mark_book"]), True


@connection
async def delete_student(session: AsyncSession, s: Student):
    for hw_type in (HW_TYPE_NOZZLE, HW_TYPE_SHOCK_WEDGE):
        hw = await _get_homework_of_type(session, s, hw_type)
        if hw:
            table = type(hw)
            await session.execute(
                update(table)
                .where(table.student_id == s.id)
                .values(
                    student_id=None,
                    done=False,
                    done_date=None,
                    approved=False,
                    approve_date=None,
                    send=False,
                    points=None,
                )
            )

    await session.execute(
        update(Lab)
        .where(Lab.student_id == s.id)
        .values(student_id=None, send=False, done=False, done_date=None, points=None)
    )

    await session.execute(
        update(ControlWork)
        .where(ControlWork.student_id == s.id)
        .values(student_id=None, approved=False, points=0)
    )

    await session.execute(delete(Student).where(Student.id == s.id))
    await session.commit()


@connection
async def get_teacher_by_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(select(Teacher).where(Teacher.tg_id == tg_id))


# ---------------------------------------------------------------------------
# Публичный API — Homework (student-facing, uses active settings)
# ---------------------------------------------------------------------------


@connection
async def get_active_homework_of(
    session: AsyncSession, s: Student
) -> AnyHomework | None:
    """Return the student's homework for the currently active type, or None."""
    settings = await _get_active_hw_settings(session)
    if settings is None:
        return None
    return await _get_homework_of_type(session, s, settings.hw_type)


@connection
async def get_free_active_homework(session: AsyncSession) -> AnyHomework | None:
    """Return an unassigned homework record for the currently active type."""
    settings = await _get_active_hw_settings(session)
    if settings is None:
        return None
    HW = _get_hw_class(settings.hw_type)
    return await session.scalar(select(HW).where(HW.student_id.is_(None)))


# ---------------------------------------------------------------------------
# Публичный API — Homework (teacher-facing / legacy, uses explicit sem)
# ---------------------------------------------------------------------------


@connection
async def get_homework_of(session: AsyncSession, s: Student, sem: int):
    """Get homework by semester number (used in teacher flows and tests)."""
    return await _get_homework_of(session, s, sem)


@connection
async def get_homework_of_type(session: AsyncSession, s: Student, hw_type: str):
    """Get homework by explicit hw_type string."""
    return await _get_homework_of_type(session, s, hw_type)


@connection
async def get_free_homework(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(select(HW).where(HW.student_id.is_(None)))


@connection
async def set_homework(session: AsyncSession, s: Student, hw: AnyHomework):
    HW = type(hw)
    await session.execute(update(HW).where(HW.id == hw.id).values(student_id=s.id))
    await session.commit()


@connection
async def approve_homework(
    session: AsyncSession, student: Student, date: ddate, sem: int
):
    HW = _get_semester_hw(sem)
    await session.execute(
        update(HW)
        .where(HW.student_id == student.id)
        .values(approve_date=date, approved=True)
    )
    await session.commit()


@connection
async def get_students_homeworks(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalars(select(HW).where(HW.student_id.isnot(None)))


@connection
async def send_homework(session: AsyncSession, hw: AnyHomework):
    HW = type(hw)
    await session.execute(update(HW).where(HW.id == hw.id).values(send=True))
    await session.commit()


@connection
async def assess_homework(session: AsyncSession, data: dict, sem: int):
    HW = _get_semester_hw(sem)
    student = data["student"]
    points = data["points"]
    date = data["date"]

    await session.execute(
        update(HW)
        .where(HW.student_id == student.id)
        .values(done=True, done_date=date, points=points)
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Публичный API — Labs
# ---------------------------------------------------------------------------


@connection
async def get_lab_of(session: AsyncSession, s: Student, lab_n: int):
    return await _get_lab_of(session, s, lab_n)


@connection
async def get_free_lab(session: AsyncSession, lab_n: int):
    return await session.scalar(
        select(Lab).where(Lab.lab_number == lab_n, Lab.student_id.is_(None))
    )


@connection
async def set_lab(session: AsyncSession, s: Student, lab: Lab):
    await session.execute(update(Lab).where(Lab.id == lab.id).values(student_id=s.id))
    await session.commit()


@connection
async def send_lab(session: AsyncSession, lab: Lab):
    await session.execute(update(Lab).where(Lab.id == lab.id).values(send=True))
    await session.commit()


@connection
async def assess_lab(session: AsyncSession, data: dict, lab: Lab):
    points = data["points"]
    date = data["date"]

    await session.execute(
        update(Lab)
        .where(Lab.id == lab.id)
        .values(done=True, done_date=date, points=points)
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Публичный API — Controls
# ---------------------------------------------------------------------------


@connection
async def get_controls_of(session: AsyncSession, s: Student, sem: int):
    """Return two control works for the given semester (teacher flow)."""
    return await _get_controls_of(session, s, sem)


@connection
async def get_all_controls_of(session: AsyncSession, s: Student):
    """Return all four control works for the student, sorted by control_number."""
    return await _get_all_controls_of(session, s)


@connection
async def set_control_points_of(session: AsyncSession, controls: list[ControlWork]):
    """Save points for each control work in the list."""
    for cw in controls:
        await session.execute(
            update(ControlWork).where(ControlWork.id == cw.id).values(points=cw.points)
        )
    await session.commit()


# ---------------------------------------------------------------------------
# Публичный API — Progress
# ---------------------------------------------------------------------------


@connection
async def get_progress_of(session: AsyncSession, s: Student):
    """Return (hw_nozzle_points, hw_wedge_points, labs[6], controls[4]) for a student.

    Each entry is the points value (int) or None if not done/not assigned.
    """
    hw_nozzle = await _get_homework_of_type(session, s, HW_TYPE_NOZZLE)
    hw_wedge = await _get_homework_of_type(session, s, HW_TYPE_SHOCK_WEDGE)

    hw_nozzle_points = hw_nozzle.points if hw_nozzle else None
    hw_wedge_points = hw_wedge.points if hw_wedge else None

    labs = [await _get_lab_of(session, s, n) for n in range(1, 7)]
    lab_points = [lab.points if lab else None for lab in labs]

    controls = await _get_all_controls_of(session, s)

    return hw_nozzle_points, hw_wedge_points, lab_points, controls


# ---------------------------------------------------------------------------
# Публичный API — Misc
# ---------------------------------------------------------------------------


@connection
async def update_groups(session: AsyncSession, sem: int):
    students = await session.scalars(select(Student))
    for s in students:
        s.group = s.group[:-2] + ("4" if sem == 1 else "5") + s.group[-1]
    await session.commit()
