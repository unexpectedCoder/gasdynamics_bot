import json
import os
import random as rand
from datetime import date as ddate
from functools import wraps

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config as cfg
from app.database.models import (
    AnyHomework,
    ControlWork,
    HomeworkNozzle,
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


def _init_teachers(session: AsyncSession):
    owner = {
        "firstname": os.getenv("OWNER_FIRSTNAME"),
        "middlename": os.getenv("OWNER_MIDDLENAME"),
        "lastname": os.getenv("OWNER_LASTNAME"),
        "tg_id": os.getenv("OWNER_ID"),
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


def _get_semester_hw(sem: int):
    if sem < 1 or sem > 2:
        raise RuntimeError(f"нет задания для {sem} семестра")
    return HomeworkNozzle if sem == 1 else HomeworkShockWedge


# ---------------------------------------------------------------------------
# Приватные версии (принимают сессию, без декоратора)
# ---------------------------------------------------------------------------


async def _get_student_by_mark_book(session: AsyncSession, mark_book: str):
    return await session.scalar(select(Student).where(Student.mark_book == mark_book))


async def _get_homework_of(session: AsyncSession, s: Student, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(select(HW).where(HW.student_id == s.id))


async def _get_lab_of(session: AsyncSession, s: Student, lab_n: int):
    return await session.scalar(
        select(Lab).where(Lab.student_id == s.id, Lab.lab_number == lab_n)
    )


async def _get_controls_of(session: AsyncSession, s: Student, sem: int):
    """Возвращает список из двух контрольных работ для указанного семестра,
    отсортированных по control_number (т.е. [РК1, РК2]).
    """
    numbers = (1, 2) if sem == 1 else (3, 4)
    result = await session.scalars(
        select(ControlWork)
        .where(ControlWork.student_id == s.id, ControlWork.control_number.in_(numbers))
        .order_by(ControlWork.control_number)
    )
    return list(result.all())


# ---------------------------------------------------------------------------
# Публичный API
# ---------------------------------------------------------------------------


@connection
async def reg_student(session: AsyncSession, student: Student):
    await session.execute(
        update(Student).where(Student.id == student.id).values(tg_id=student.tg_id)
    )
    await session.commit()


@connection
async def get_free_homework(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(select(HW).where(HW.student_id.is_(None)))


@connection
async def get_free_lab(session: AsyncSession, lab_n: int):
    return await session.scalar(
        select(Lab).where(Lab.lab_number == lab_n, Lab.student_id.is_(None))
    )


@connection
async def get_homework_of(session: AsyncSession, s: Student, sem: int):
    return await _get_homework_of(session, s, sem)


@connection
async def get_lab_of(session: AsyncSession, s: Student, lab_n: int):
    return await _get_lab_of(session, s, lab_n)


@connection
async def set_homework(session: AsyncSession, s: Student, hw: AnyHomework):
    HW = type(hw)
    await session.execute(update(HW).where(HW.id == hw.id).values(student_id=s.id))
    await session.commit()


@connection
async def set_lab(session: AsyncSession, s: Student, lab: Lab):
    await session.execute(update(Lab).where(Lab.id == lab.id).values(student_id=s.id))
    await session.commit()


@connection
async def set_homework_deadline(session: AsyncSession, sem: int, date: ddate):
    HW = _get_semester_hw(sem)
    await session.execute(update(HW).values(deadline=date))
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
async def send_lab(session: AsyncSession, lab: Lab):
    await session.execute(update(Lab).where(Lab.id == lab.id).values(send=True))
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


@connection
async def get_homework_deadline(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    work = await session.scalar(select(HW))
    return work.deadline


@connection
async def get_teacher_by_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(select(Teacher).where(Teacher.tg_id == tg_id))


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
    for sem in (1, 2):
        hw = await _get_homework_of(session, s, sem)
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
                    approved_date=None,
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
async def get_progress_of(session: AsyncSession, s: Student, sem: int):
    hw = await _get_homework_of(session, s, sem)
    hw = hw.points if hw else None

    labs_n = (1, 2, 3) if sem == 1 else (4, 5, 6)
    labs = [await _get_lab_of(session, s, n) for n in labs_n]
    for i, lab in enumerate(labs):
        labs[i] = lab.points if lab else None

    controls = await _get_controls_of(session, s, sem)

    return hw, labs, controls


@connection
async def get_controls_of(session: AsyncSession, s: Student, sem: int):
    return await _get_controls_of(session, s, sem)


@connection
async def set_control_points_of(session: AsyncSession, controls: list[ControlWork]):
    """Сохраняет очки для каждой контрольной работы в списке."""
    for cw in controls:
        await session.execute(
            update(ControlWork).where(ControlWork.id == cw.id).values(points=cw.points)
        )
    await session.commit()


@connection
async def update_groups(session: AsyncSession, sem: int):
    students = await session.scalars(select(Student))
    for s in students:
        s.group = s.group[:-2] + ("4" if sem == 1 else "5") + s.group[-1]
    await session.commit()
