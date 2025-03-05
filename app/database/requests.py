import json
import os
import random as rand
from datetime import date as ddate
from functools import wraps
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

import config as cfg
from app.database.models import async_session
from app.database.models import (
    AnyHomework,
    AnyLab,
    HomeworkNozzle,
    HomeworkShockWedge,
    Lab_1,
    Lab_2,
    Lab_3,
    Lab_4,
    Lab_5,
    Lab_6,
    LABS_TYPES,
    Student,
    Teacher
)


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
        await _init_teachers(session)
        n_students = await _init_students(session)
        await _init_homework_nozzle(session)
        await _init_homework_shock_wedge(session)
        await _init_labs(session, 2*n_students)
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
    for gname, group in journal.items():
        for mark_book in group:
            session.add(Student(
                group=gname, mark_book=mark_book, **group[mark_book]
            ))
    return sum(len(group.keys()) for group in journal.values())


async def _init_homework_nozzle(session: AsyncSession):
    path = cfg.get_file("home_nozzle")
    with open(path, "r") as f:
        variants = _shuffle_variants(json.load(f))
    for v in variants:
        session.add(HomeworkNozzle(variant=v, **variants[v]))


async def _init_labs(session: AsyncSession, n: int):
    for i in range(n):
        for lab in (Lab_1, Lab_2, Lab_3, Lab_4, Lab_5, Lab_6):
            session.add(lab())


def _shuffle_variants(variants: dict):
    variants = list(variants.items())
    rand.shuffle(variants)
    return dict(variants)


async def _init_homework_shock_wedge(session: AsyncSession):
    path = cfg.get_file("home_shock_wedge")
    with open(path, "r") as f:
        variants = _shuffle_variants(json.load(f))
    for v in variants:
        session.add(HomeworkShockWedge(variant=v, **variants[v]))


@connection
async def reg_student(session: AsyncSession, student: Student):
    await session.execute(
        update(Student).where(Student.id == student.id).values(
            tg_id=student.tg_id
        )
    )
    await session.commit()


@connection
async def get_free_homework(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(
        select(HW).where(HW.student_id.is_(None))
    )


@connection
async def get_free_lab(session: AsyncSession, lab_n: int):
    lab = LABS_TYPES[lab_n]
    return await session.scalar(select(lab).where(lab.student_id.is_(None)))


@connection
async def get_homework_of(session: AsyncSession, s: Student, sem: int):
    HW = _get_semester_hw(sem)
    return await session.scalar(
        select(HW).where(HW.student_id == s.id)
    )


def _get_semester_hw(sem: int):
    if sem < 1 or sem > 2:
        raise RuntimeError(f"нет задания для {sem} семестра")
    return HomeworkNozzle if sem == 1 else HomeworkShockWedge


@connection
async def get_lab_of(session: AsyncSession, s: Student, lab_n: int):
    lab = LABS_TYPES[lab_n]
    return await session.scalar(
        select(lab).where(lab.student_id == s.id)
    )


@connection
async def set_homework(session: AsyncSession, s: Student, hw: AnyHomework):
    HW = type(hw)
    await session.execute(
        update(HW).where(HW.id == hw.id).values(student_id=s.id)
    )
    await session.commit()


@connection
async def set_lab(session: AsyncSession, s: Student, lab: AnyLab):
    table = type(lab)
    await session.execute(
        update(table).where(table.id == lab.id).values(student_id=s.id)
    )
    await session.commit()


@connection
async def set_homework_deadline(session: AsyncSession, sem: int, date: ddate):
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
async def get_students_homeworks(session: AsyncSession, sem: int):
    HW = _get_semester_hw(sem)
    await session.scalars(select(HW).where(HW.student_id))


@connection
async def send_homework(session: AsyncSession, hw: AnyHomework):
    HW = type(hw)
    await session.execute(
        update(HW).where(HW.id == hw.id).values(send=True)
    )
    await session.commit()


@connection
async def send_lab(session: AsyncSession, lab: AnyLab):
    table = type(lab)
    await session.execute(
        update(table).where(table.id == lab.id).values(send=True)
    )
    await session.commit()


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
async def assess_lab(session: AsyncSession, data: dict, lab: AnyLab):
    student = data["student"]
    points = data["points"]
    date = data["date"]

    table = type(lab)
    await session.execute(
        update(table).where(table.student_id == student.id).values(
            done=True, done_date=date, points=points
        )
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
async def get_students_by_lastname(session: AsyncSession, lname: str):
    return await session.scalars(
        select(Student).where(Student.lastname == lname)
    )


@connection
async def get_student_by_tg(session: AsyncSession, tg_id: int):
    return await session.scalar(
        select(Student).where(Student.tg_id == tg_id)
    )


@connection
async def get_student_by_mark_book(session: AsyncSession, mark_book: str):
    return await session.scalar(
        select(Student).where(Student.mark_book == mark_book)
    )


@connection
async def add_student(session: AsyncSession, data: dict):
    s = await get_student_by_mark_book(data["mark_book"])
    if s:
        return s, False
    
    session.add(Student(**data))
    await session.commit()
    return await get_student_by_mark_book(data["mark_book"]), True


@connection
async def delete_student(session: AsyncSession, s: Student):
    for sem in (1, 2):
        hw = await get_homework_of(s, sem)
        if hw:
            table = type(hw)
            await session.execute(
                update(table).where(table.student_id == s.id).values(
                    student_id=None,
                    done=False,
                    done_date=None,
                    checked=False,
                    checked_date=None,
                    send=False,
                    points=None
                )
            )
        
    for lab_n in range(1, 7):
        lab = await get_lab_of(s, lab_n)
        if lab:
            table = type(lab)
            await session.execute(
                update(table).where(table.student_id == s.id).values(
                    student_id=None,
                    send=False,
                    done=False,
                    done_date=None,
                    points=None
                )
            )
    
    await session.execute(delete(Student).where(Student.id == s.id))
    await session.commit()


@connection
async def get_progress_of(session: AsyncSession, s: Student, sem: int):
    hw = await get_homework_of(s, sem)
    hw = hw.points if hw else None
    labs_n = (1, 2, 3) if sem == 1 else (4, 5, 6)
    labs = [
        await get_lab_of(s, lab_n) for lab_n in labs_n
    ]
    for i, lab in enumerate(labs):
        labs[i] = lab.points if lab else None
    
    return hw, labs
