import os
import pandas as pd
import shutil
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import FSInputFile, Message
from datetime import date
from datetime import datetime
from datetime import timedelta

import app.database.requests as rq
import app.keyboards as kb
import config as cfg
from app.filters import IsTeacher
from app.states import AssessHomework
from app.utils.seasons import get_current_semester


router = Router()
router.message.filter(IsTeacher())


@router.message(Command("homework_deadline"))
@router.message(F.text.casefold().contains("дедлайн дз"))
async def homework_deadline(message: Message):
    deadline = await rq.get_homework_deadline(get_current_semester())
    if deadline:
        await message.answer(f"Дедлайн ДЗ: *{deadline}*")
        return
    await message.answer("Дедлайн ДЗ не установлен")


@router.message(Command("set_homework_deadline"))
async def homework_deadline(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "Необходимо указать дату сдачи ДЗ либо в формате "
            "DD.MM.YYYY, либо как '14 нед' или '50 дн'"
        )
        return
    
    deadline = None
    try:
        deadline = datetime.strptime(command.args, "%d.%m.%Y").date()
    except ValueError:
        pass

    if deadline:
        await rq.set_homeworks_deadline(
            get_current_semester(), deadline
        )
        await message.answer(
            "Срок сдачи ДЗ установлен: "
            f"*{deadline}*"
        )
        return
    
    dt = command.args.split(maxsplit=1)
    if len(dt) != 2 or not dt[0].isdigit():
        await message.answer("Некорректный формат")
        return
    
    n = int(dt[0])
    weeks = dt[1] == "нед"
    days = dt[1] == "дн"
    if weeks:
        delay = timedelta(weeks=n)
    elif days:
        delay = timedelta(days=n)
    else:
        await message.answer("Некорректный формат")
        return
    
    deadline = date.today() + delay
    await rq.set_homeworks_deadline(
        get_current_semester(), deadline
    )
    await message.answer(
        f"Срок сдачи ДЗ установлен: *{deadline}*"
    )


@router.message(Command("students"))
@router.message(F.text.casefold().contains("студенты"))
async def students_handler(message: Message):
    students = list(await rq.get_students())
    groups = sorted({s.group for s in students})
    students = {
        g: sorted([
            s for s in students if s.group == g
        ])
        for g in groups
    }

    answer = "*Список студентов*\n"
    for group in students:
        answer = answer + f"\n*{group}*:\n"

        for i, s in enumerate(students[group], start=1):
            if not s.tg_id:
                text = f"  {i}. {s.lastname} {s.firstname}\n"
            else:
                text = \
                    f"  {i}. [{s.lastname} {s.firstname}]" \
                    f"(tg://user?id={s.tg_id})\n"
            
            answer = answer + text

    await message.answer(answer)


@router.message(Command("homeworks_to_check"))
@router.message(F.text.casefold().contains("непроверенные дз"))
async def homeworks_to_check_handle(message: Message):
    files = os.listdir(cfg.get_dir("homeworks_to_check"))
    if not files:
        await message.answer("Нет непроверенных ДЗ.")
        return
    
    students = []
    for path in files:
        fname = os.path.basename(os.path.abspath(path))
        student_tg = int(fname.split(".")[0])
        students.append(await rq.get_student_tg(student_tg))

    groups = sorted({s.group for s in students})
    journal = {
        g: sorted([
            s for s in students if s.group == g
        ], key=lambda x: x.lastname)
        for g in groups
    }

    answer = f"Непроверенных ДЗ: *{len(students)}* шт.\n\n"
    for group in journal:
        answer = answer + f"*{group}*:\n"
        for i, s in enumerate(journal[group], start=1):
            name = f"{s.lastname} {s.firstname}"
            answer = answer + f"  {i}. {name}"
        answer = answer + "\n"
    
    await message.answer(answer)


@router.message(StateFilter(AssessHomework), Command("cancel"))
async def assess_homework_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=kb.teacher)


@router.message(default_state, Command("assess_homework"))
@router.message(default_state, F.text.casefold().contains("проверить дз"))
async def assess_homework(message: Message, state: FSMContext):
    dir_name = cfg.get_dir("homeworks_to_check")
    files = os.listdir(dir_name)
    if not files:
        await message.answer("Нет непроверенных ДЗ.")
        return
    
    f = files[0]
    student_tg = int(f.split(".")[0])
    student = await rq.get_student_tg(student_tg)
    work = await rq.get_homework_of(
        student, get_current_semester()
    )
    doc_path = os.path.join(dir_name, f)
    doc = FSInputFile(doc_path)
    
    await state.set_state(AssessHomework.choice)
    await state.update_data(
        student=student, homework=work, report_path=doc_path
    )

    await message.answer_document(
        doc,
        caption=\
            "Пожалуйста, проверьте отчёт и выберите действие (/cancel):",
        reply_markup=kb.assess_homework_choice
    )


@router.message(AssessHomework.choice, F.text.casefold().contains("замечания"))
async def assess_homework_choice_comments(message: Message, state: FSMContext):
    await state.set_state(AssessHomework.remarking)
    await message.answer(
        "Напишите замечания или прикрепите файл с ними. "
        "Это сообщение *будет переслано студенту* (/cancel):"
    )


@router.message(AssessHomework.remarking)
async def assess_homework_comments(message: Message, state: FSMContext):
    await state.update_data(comments=message.text, doc=message.document)
    data = await state.get_data()
    await state.clear()
    await _assess_homework_operations(message, data)


async def _assess_homework_operations(message: Message, data: dict):
    tg_id = data["student"].tg_id
    if data["doc"]:
        await message.bot.send_document(
            tg_id,
            data["doc"],
            caption=\
                "Ваша работа проверена преподавателем. "
                "Замечания в прикреплённом файле."
        )
    else:
        await message.bot.send_message(
            tg_id,
            "Ваша работа проверена преподавателем. *Замечания:*\n\n" + \
                data["comments"]
        )

    file_path = os.path.join(
        cfg.get_dir("homeworks_to_check"), f"{tg_id}.pdf"
    )
    os.remove(file_path)

    await message.answer(
        f"Замечания высланы [студенту](tg://user?id={tg_id})",
        reply_markup=kb.teacher
    )


@router.message(AssessHomework.choice, F.text.casefold().contains("принять"))
async def assess_homework_points(message: Message, state: FSMContext):
    await state.set_state(AssessHomework.approving)
    await message.answer("Оцените работу (/cancel):")


@router.message(AssessHomework.approving)
async def assess_homework_approving(message: Message, state: FSMContext):
    # Проверка формата оценки
    points: str = message.text
    if not points.isdigit() or int(points) < 0:
        await message.answer("Не похоже на баллы")
        await state.set_state(AssessHomework.points)
        return
    
    await state.update_data(points=points)
    data = await state.get_data()
    await state.clear()

    await _approve_operations(data)

    # Информируем студента
    await message.bot.send_message(
        data["student"].tg_id,
        f"Ваше ДЗ принято преподавателем. Оценка: *{data['points']}*"
    )

    await message.answer(
        "Работа принята. *Информация выслана студенту*.",
        reply_markup=kb.teacher
    )


async def _approve_operations(data: dict):
    data["date"] = date.today()
    await rq.assess_homework(data, get_current_semester())

    dst = os.path.join(
        cfg.get_dir("checked_homeworks"), f"{data['date'].year}"
    )
    try:
        os.mkdir(dst)
    except OSError as ex:
        print(ex)

    src = data["report_path"]
    s = data["student"]
    dst = os.path.join(
        dst, f"{s.group}_{s.lastname}_{s.firstname}.pdf"
    )

    shutil.move(src, dst)


@router.message(Command("progress"))
@router.message(F.text.casefold().contains("успеваемость"))
async def progress_handler(message: Message):
    students = list(await rq.get_students())
    groups = {s.group for s in students}
    sem = get_current_semester()

    works = {g: [] for g in groups}
    for g in works:
        for s in students:
            if s.group != g:
                continue
            works[g].append(await rq.get_homework_of(s, sem))
    homeworks_points = {
        g: [w.points if w else None for w in works[g]]
        for g in works
    }
    names = {
        g: sorted([
            f"{s.lastname} {s.firstname}" for s in students if s.group == g
        ])
        for g in groups
    }

    names_list = []
    groups_list = []
    homeworks_list = []
    for g in groups:
        names_list.extend(names[g])
        groups_list.extend([g]*len(names[g]))
        homeworks_list.extend(homeworks_points[g])

    result = pd.DataFrame({
        "ФИО": names_list,
        "Группа": groups_list,
        "ДЗ": homeworks_list
    })
    result = result.sort_values(by=["Группа", "ФИО"])

    excel_path = "progress.xlsx"
    result.to_excel(excel_path, index=False)
    doc = FSInputFile(excel_path)

    await message.answer_document(
        doc, caption="Успеваемость студентов в Excel-файле"
    )


@router.message(Command("progress_of"))
async def progress_of_handler(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "Команде /progress\_of нужно задать фамилию студента."
        )
        return
    
    lastname = command.args
    students = await rq.get_students_lastname(lastname)
    if not students:
        await message.answer(f"Не нашёл студентов с фамилией {lastname}")
        return

    answer = "*Успеваемость*\n\n"
    for s in students:
        answer = answer + f"*{s}*\n"
        work = await rq.get_homework_of(s, get_current_semester())
        if not work:
            homework = f"  ДЗ *не выдано*"
        elif work.done:
            homework = f"  ДЗ сдано на *{work.points} балл(ов)*\n"
        else:
            homework = f"  ДЗ *не сдано*\n"
        answer = answer + homework + "\n"
    
    await message.answer(answer)
