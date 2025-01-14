import json
import os
from datetime import date as ddate
from functools import wraps
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config as cfg
from app.database.models import async_session
from app.database.models import (
    HomeworkNozzle, HomeworkShockWedge, Student, Teacher
)


def connection(func):
    @wraps(func)
    async def inner(*args, **kw):
        async with async_session() as session:
            return await func(session, *args, **kw)
    return inner


async def fill_database():
    async with async_session() as session:
        await _init_teachers(session)
        await _init_students(session)
        await _init_homework_nozzle(session)
        await _init_homework_shock_wedge(session)
        await session.commit()


async def _init_teachers(session: AsyncSession):
    owner = {
        "firstname": os.getenv("OWNER_FIRSTNAME"),
        "middlename": os.getenv("OWNER_MIDDLENAME"),
        "lastname": os.getenv("OWNER_LASTNAME"),
        "tg_id": os.getenv("OWNER_ID")
    }
    session.add(Teacher(**owner))


async def _init_students(session: AsyncSession):
    path = cfg.get_file("students")
    with open(path, "r", encoding="utf-8") as f:
        journal = json.load(f)
    for group in journal:
        for i in journal[group]:
            session.add(Student(
                group=group, **journal[group][i]))


async def _init_homework_nozzle(session: AsyncSession):
    path = cfg.get_file("home_nozzle")
    with open(path, "r") as f:
        variants = json.load(f)
    for v in variants:
        session.add(HomeworkNozzle(variant=v, **variants[v]))


async def _init_homework_shock_wedge(session: AsyncSession):
    path = cfg.get_file("home_shock_wedge")
    with open(path, "r") as f:
        variants = json.load(f)
    for v in variants:
        session.add(HomeworkShockWedge(variant=v, **variants[v]))


@connection
async def get_free_homeworks(session: AsyncSession, sem: int):
    if sem < 1 or sem > 2:
        raise RuntimeError(f"нет задания для {sem} семестра")
    HW = _get_semester_hw(sem)
    return await session.scalars(
        select(HW).where(HW.student_id.is_(None))
    )


@connection
async def get_homework_of(session: AsyncSession, student: Student, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(
        select(HW).where(HW.student_id == student.id)
    )


def _get_semester_hw(sem: int):
    if sem < 1 or sem > 2:
        raise RuntimeError(f"нет задания для {sem} семестра")
    return HomeworkNozzle if sem == 1 else HomeworkShockWedge


@connection
async def set_homework(session: AsyncSession,
                       student: Student,
                       work: HomeworkNozzle | HomeworkShockWedge):
    HW = type(work)
    await session.execute(
        update(HW).where(HW.id == work.id).values(student_id=student.id)
    )
    await session.commit()


@connection
async def set_homeworks_deadline(session: AsyncSession, sem: int, date: ddate):
    HW = _get_semester_hw(sem)
    await session.execute(update(HW).values(deadline=date))
    await session.commit()


@connection
async def set_yaml_checked(session: AsyncSession,
                           student: Student,
                           date: ddate,
                           sem: int):
    HW = _get_semester_hw(sem)
    await session.execute(
        update(HW).where(HW.student_id == student.id).values(
            check_date=date, checked=True
        )
    )
    await session.commit()


@connection
async def get_student_mark_book(session: AsyncSession, mark_book: str):
    return await session.scalar(
        select(Student).where(Student.mark_book == mark_book)
    )


@connection
async def reg_student(session: AsyncSession, student: Student):
    await session.execute(
        update(Student).where(Student.id == student.id).values(
            tg_id=student.tg_id
        )
    )
    await session.commit()


@connection
async def get_teacher_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(
        select(Teacher).where(Teacher.tg_id == tg_id)
    )


@connection
async def get_student_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(
        select(Student).where(Student.tg_id == tg_id)
    )


@connection
async def get_students(session: AsyncSession):
    return await session.scalars(select(Student))


@connection
async def send_homework(session: AsyncSession,
                        hw: HomeworkNozzle | HomeworkShockWedge):
    HW = type(hw)
    await session.execute(
        update(HW).where(HW.id == hw.id).values(send=True)
    )


@connection
async def assess_homework(session: AsyncSession, data: dict, sem: int):
    HW = _get_semester_hw(sem)
    student = data["student"]
    points = data["points"]
    date = data["date"]

    await session.execute(
        update(HW).where(HW.student_id == student.id).values(
            done=True, done_date=date, points=points
        )
    )
    await session.commit()


@connection
async def get_students_lastname(session: AsyncSession, lname: str):
    return await session.scalars(
        select(Student).where(Student.lastname == lname)
    )


@connection
async def get_homework_deadline(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    work = await session.scalar(select(HW))
    return work.deadline
