import os
import pandas as pd
import shutil
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message
from datetime import date, datetime
from statistics import median

import app.database.requests as rq
import app.inline_keyboards as ikb
import app.keyboards as kb
import config as cfg
from app.filters import IsTeacher
from app.states import (
    AddStudent,
    AssessHomework,
    AssessLab,
    DeleteStudent,
    HomeworkDeadline,
    ProgressOf
)
from app.utils.seasons import get_current_semester


router = Router()
router.message.filter(IsTeacher())


@router.message(default_state, F.text.casefold().startswith("добавить студента"))
@router.message(default_state, Command("add_student"))
async def add_student_handler(message: Message, state: FSMContext):
    await state.set_state(AddStudent.name)
    await message.answer("ФИО студента:\n/cancel")


@router.message(AddStudent.name, lambda m: len(m.text.split()) == 3)
async def add_student_name(message: Message, state: FSMContext):
    ln, fn, mn = message.text.title().split()
    await state.update_data(firstname=fn, middlename=mn, lastname=ln)
    await state.set_state(AddStudent.group)
    await message.answer("Группа:\n/cancel")


@router.message(AddStudent.group,
                lambda m: len(m.text.split()) == 1,
                F.text != "/cancel")
async def add_student_group(message: Message, state: FSMContext):
    group = message.text.upper()
    await state.update_data(group=group)
    await state.set_state(AddStudent.mark_book)
    await message.answer("Номер зачётки:\n/cancel")


@router.message(AddStudent.mark_book,
                lambda m: len(m.text.split()) == 1,
                F.text != "/cancel")
async def add_student_mark_book(message: Message, state: FSMContext):
    mark_book = message.text.upper()
    await state.update_data(mark_book=mark_book)
    data = await state.get_data()
    await state.clear()

    student, is_new = await rq.add_student(data)
    if is_new:
        await message.answer(f"{student} добавлен в БД")
        return
    await message.answer(f"{student} уже есть в БД")


@router.message(StateFilter(AddStudent), Command("cancel"))
async def add_student_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление студента отменено")


@router.message(default_state, F.text.casefold().startswith("удалить студента"))
@router.message(default_state, Command("delete_student"))
async def delete_student_handler(message: Message, state: FSMContext):
    await state.set_state(DeleteStudent.mark_book)
    await message.answer("Номер зачётки студента:\n/cancel")


@router.message(DeleteStudent.mark_book,
                lambda m: len(m.text.split()) == 1,
                F.text != "/cancel")
async def delete_student_mark_book(message: Message, state: FSMContext):
    await state.clear()

    mark_book = message.text.upper()
    student = await rq.get_student_by_mark_book(mark_book)
    if student:
        await rq.delete_student(student)
        await message.answer(f"{student} удалён из БД")
        return
    await message.answer(f"Зачётка `{mark_book}` не найдена в БД")


@router.message(StateFilter(DeleteStudent), Command("cancel"))
async def delete_student_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Удаление студента отменено")


@router.message(default_state, F.text.casefold().startswith("установить дедлайн"))
@router.message(default_state, Command("set_deadline"))
async def set_deadline(message: Message, state: FSMContext):
    await state.set_state(HomeworkDeadline.set_date)
    await message.answer(
        "Введите дату сдачи ДЗ в формате `дд.мм.гггг`:\n/cancel"
    )


@router.message(HomeworkDeadline.set_date)
async def set_homework_deadline_date(message: Message, state: FSMContext):
    await state.clear()

    deadline = None
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Некорректный формат даты. Требуется `дд.мм.гггг`")
        return

    await rq.set_homework_deadline(get_current_semester(), deadline)
    await message.answer(f"Срок сдачи ДЗ установлен: *{deadline}*")


@router.message(F.text.casefold().startswith("студенты"))
@router.message(Command("students"))
async def students_handler(message: Message):
    await message.answer(
        "Какая информация о студентах вам нужна?",
        reply_markup=ikb.students_info
    )


@router.callback_query(F.data == "students_list")
async def students_list(cb: CallbackQuery):
    students = list(await rq.get_students())
    groups = sorted({s.group for s in students})
    students = {
        g: sorted(
            [s for s in students if s.group == g],
            key=lambda x: x.get_name()
        )
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

    await cb.message.edit_text(answer)
    await cb.answer("Список студентов")


@router.callback_query(F.data == "students_progress")
async def progress_handler(cb: CallbackQuery):
    await cb.answer("Успеваемость студентов")
    await cb.message.edit_reply_markup(reply_markup=None)
    
    students = list(await rq.get_students())
    sem = get_current_semester()
    points = [
        await rq.get_progress_of(s, sem) for s in students
    ]
    names = [s.get_name() for s in students]
    homeworks = [hw for hw, _ in points]
    labs = [
        [labs[i-1] for _, labs in points]
        for i in ((1, 2, 3) if sem == 1 else (4, 5, 6))
    ]
    groups = [s.group for s in students]

    progress = pd.DataFrame({
        "ФИО": names,
        "Группа": groups,
        "ДЗ": homeworks,
        "ЛР № 1": labs[0],
        "ЛР № 2": labs[1],
        "ЛР № 3": labs[2]
    }).sort_values(by=["Группа", "ФИО"])
    
    excel_path = "progress.xlsx"
    progress.to_excel(excel_path, index=False)
    doc = FSInputFile(excel_path)
    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption="Успеваемость студентов в Excel-файле"
    )
    await cb.message.delete()


@router.message(F.text.casefold().startswith("статистика"))
@router.message(Command("stats"))
async def stats_handler(message: Message):
    await message.answer(
        "Какая статистика вас интересует?",
        reply_markup=ikb.stats
    )


@router.callback_query(F.data.contains("stats_hw"))
async def stats_homework(cb: CallbackQuery):
    await cb.answer("Статистика по ДЗ")

    sem = int(cb.data.replace("stats_hw_", ""))
    dirname = cfg.get_dir(f"sem_{sem}_homeworks_to_check")
    files = os.listdir(dirname)

    reg_students = []
    for path in files:
        fname = os.path.basename(os.path.abspath(path))
        student_tg = int(fname.split(".")[0])
        reg_students.append(await rq.get_student_by_tg(student_tg))
    
    if reg_students == []:
        await cb.message.edit_text(
            "Статистика отсутствует: "
            "пока не зарегистрирован ни один студент",
            reply_markup=None
        )
        return

    reg_groups = sorted({s.group for s in reg_students})
    reg_journal = {
        rg: sorted([
            s for s in reg_students if s.group == rg
        ], key=lambda x: x.lastname)
        for rg in reg_groups
    }

    answer = f"К проверке допущено *{len(reg_students)}* отчётов по ДЗ:\n"
    for group in reg_journal:
        answer = answer + f" - *{group}*:\n"
        for i, s in enumerate(reg_journal[group], start=1):
            name = f"{s.lastname} {s.firstname}"
            answer = answer + f"    {i}. {name}\n"
    answer = answer + "\n"
    
    students = list(await rq.get_students())
    n_students = len(students)
    works = await rq.get_students_homeworks(sem)
    if not works:
        return
    
    works = list(await rq.get_students_homeworks(sem))
    
    works_text, done_works_text = "", ""
    n_works = len(works)
    n_checked_works = len([w for w in works if w.checked])
    works_text = \
        f"ДЗ в работе - *{n_works} шт.*, " \
        f"из из них *{n_checked_works}* прошли проверку на правильность.\n" \

    done_works = [w for w in works if w.done]
    if done_works:
        n_done_works = len(done_works)
        points = [w.points for w in done_works]
        min_points, max_points = min(points), max(points)
        median_points = int(median(points))
        done_works_text = \
            f"Отчёты приняты по *{n_done_works}* ДЗ. "\
            f"Максимальный балл - *{max_points}*, " \
            f"минимальный - *{min_points}*. " \
            f"Медианный балл - *{median_points}*.\n"
            
    answer = answer + \
        f"Всего {n_students} студентов." + \
        works_text + done_works_text
    
    await cb.bot.send_message(cb.message.chat.id, answer)


@router.message(F.text.casefold().startswith("проверить работу"))
@router.message(Command("assess"))
async def check_work_handler(message: Message):
    await message.answer(
        "Какую работу вы хотите проверить?",
        reply_markup=ikb.check_work
    )


@router.callback_query(F.data == "check_homework")
async def check_homework(cb: CallbackQuery):
    await cb.message.edit_text(
        "Выберите ДЗ:", reply_markup=ikb.check_homework
    )


@router.callback_query(default_state, F.data.contains("check_hw"))
async def assess_homework(cb: CallbackQuery, state: FSMContext):
    await cb.answer("Проверка ДЗ")

    sem = int(cb.data.replace("check_hw_", ""))
    dirname = cfg.get_dir(f"sem_{sem}_homeworks_to_check")
    files = os.listdir(dirname)
    if not files:
        await cb.message.edit_text(
            f"Нет непроверенных ДЗ (семестр {sem})"
        )
        await state.clear()
        return
    
    f = files[0]
    student_tg = int(f.split(".")[0])
    student = await rq.get_student_by_tg(student_tg)
    work = await rq.get_homework_of(student, sem)
    doc_path = os.path.join(dirname, f)
    doc = FSInputFile(doc_path)
    
    await state.set_state(AssessHomework.choice)
    await state.update_data(
        student=student,
        homework=work,
        report_path=doc_path,
        sem=sem
    )

    await cb.message.delete()
    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption=\
            "Пожалуйста, проверьте отчёт и выберите действие:"
            "\n/cancel",
        reply_markup=kb.assess_work_choice
    )


@router.message(AssessHomework.choice, F.text.casefold().startswith("замечания"))
async def assess_homework_choice_comments(message: Message, state: FSMContext):
    await state.set_state(AssessHomework.remarking)
    await message.answer(
        "Напишите замечания или прикрепите файл с ними. "
        "(_это сообщение будет переслано студенту_):"
        "\n/cancel"
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

    sem = data["sem"]
    file_path = os.path.join(
        cfg.get_dir(f"sem_{sem}_homeworks_to_check"), f"{tg_id}.pdf"
    )
    os.remove(file_path)

    await message.answer(
        f"Замечания высланы [студенту](tg://user?id={tg_id})",
        reply_markup=kb.teacher
    )


@router.message(AssessHomework.choice, F.text.casefold().startswith("принять"))
async def assess_homework_points(message: Message, state: FSMContext):
    await state.set_state(AssessHomework.approving)
    data = await state.get_data()
    deadline = data["homework"].deadline
    if deadline and date.today() > deadline:
        await message.answer(
            "Оцените работу (_сдана с опозданием_):\n/cancel"
        )
        return
    await message.answer("Оцените работу:\n/cancel")


@router.message(AssessHomework.approving)
async def assess_homework_approving(message: Message, state: FSMContext):
    # Проверка формата оценки
    points: str = message.text
    if not points.isdigit() or int(points) < 0:
        await message.answer("Не похоже на баллы")
        await state.clear()
        return
    
    await state.update_data(points=points)
    data = await state.get_data()
    await state.clear()

    await _approve_operations(data, get_current_semester())

    # Информируем студента
    student_tg = data["student"].tg_id
    await message.bot.send_message(
        student_tg,
        "Ваше ДЗ принято "
        f"[преподавателем](tg://user?id={os.getenv('OWNER_ID')}).\n"
        f"Оценка - *{data['points']}*"
    )

    await message.answer(
        "Работа принята. "
        f"**Информация выслана [студенту](tg://user?id={student_tg})**",
        reply_markup=kb.teacher
    )


async def _approve_operations(data: dict, sem: int):
    data["date"] = date.today()
    await rq.assess_homework(data, sem)

    dst = os.path.join(
        cfg.get_dir(f"sem_{sem}_checked_homeworks"), f"{data['date'].year}"
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


@router.message(StateFilter(AssessHomework), Command("cancel"))
async def assess_homework_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=kb.teacher)


@router.message(Command("progress_of"), default_state)
async def progress_of_handler(message: Message, state: FSMContext):
    await message.answer("Фамилия студента:")
    await state.set_state(ProgressOf.lastname)
    

@router.message(ProgressOf.lastname)
async def progress_of_lastname(message: Message, state: FSMContext):
    await state.clear()

    lastname = message.text
    students = list(await rq.get_students_lastname(lastname))
    if not students:
        await message.answer(f"Не нашёл студентов с фамилией {lastname}")
        return
    
    sem = get_current_semester()
    if len(students) == 1:
        await _progress_of_student(message, students.pop(), sem)
        return
    await _progress_of_students(message, students, sem)


async def _progress_of_student(message: Message, s: rq.Student, sem: int):
    answer = "*Успеваемость*\n\n"
    answer = answer + f"*{s}*\n"
    work = await rq.get_homework_of(s, sem)
    if not work:
        text = f"  ДЗ *не выдано*"
    elif work.done:
        text = f"  ДЗ *сдано* на *{work.points} балл(ов)*\n"
    elif work.checked:
        text = f"  ДЗ *проверено*, но *не сдано*\n"
    else:
        text = f"  ДЗ *не проверено* и *не сдано*\n"
    await message.answer(answer + text + "\n")


async def _progress_of_students(message: Message,
                                students: list[rq.Student],
                                sem: int):
    answer = "**Успеваемость**\n\n"

    for i, s in enumerate(students, start=1):
        answer = answer + f"*{i}. {s}*\n"
        work = await rq.get_homework_of(s, sem)
        if not work:
            text = f"    ДЗ **не выдано**"
        elif work.done:
            text = f"    ДЗ **сдано** на **{work.points} балл(ов)**\n"
        elif work.checked:
            text = f"    ДЗ **проверено**, но **не сдано**\n"
        else:
            text = f"    ДЗ **не проверено** и **не сдано**\n"
        answer = answer + text + "\n"
    
    answer = answer + text + "\n"
    await message.answer(answer)


@router.callback_query(F.data == "check_lab")
async def check_lab(cb: CallbackQuery):
    await cb.message.edit_text("Выберите ЛР:", reply_markup=ikb.check_lab)


@router.callback_query(default_state, F.data.contains("check_lab"))
async def assess_lab(cb: CallbackQuery, state: FSMContext):
    await cb.answer("Проверка ЛР")

    lab_n = int(cb.data.replace("check_lab_", ""))
    dirname = os.path.join(
        cfg.get_dir(f"labs_to_check"), str(lab_n)
    )
    files = os.listdir(dirname)
    if not files:
        await cb.message.edit_text(f"Нет непроверенных ЛР № {lab_n}")
        await state.clear()
        return
    
    f = files[0]
    student_tg = int(f.split(".")[0])
    student = await rq.get_student_by_tg(student_tg)
    doc_path = os.path.join(dirname, f)
    doc = FSInputFile(doc_path)
    
    await state.set_state(AssessLab.choice)
    await state.update_data(
        student=student, report_path=doc_path, lab_n=lab_n
    )

    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption="Пожалуйста, проверьте отчёт и выберите действие:"
                "\n/cancel",
        reply_markup=kb.assess_work_choice
    )
    await cb.message.delete()


@router.message(AssessLab.choice, F.text.casefold().startswith("замечания"))
async def assess_lab_choice_remarks(message: Message, state: FSMContext):
    await state.set_state(AssessLab.remarking)
    await message.answer(
        "Напишите замечания или прикрепите файл с ними. "
        "(_это сообщение будет переслано студенту_):"
        "\n/cancel"
    )


@router.message(AssessLab.remarking, F.text != "/cancel")
async def assess_homework_comments(message: Message, state: FSMContext):
    await state.update_data(comments=message.text, doc=message.document)
    data = await state.get_data()
    await state.clear()
    await _assess_lab_operations(message, data)


async def _assess_lab_operations(message: Message, data: dict):
    tg_id = data["student"].tg_id
    if data["doc"]:
        await message.bot.send_document(
            tg_id,
            data["doc"],
            caption="Ваша работа проверена "
                    f"[преподавателем](tg://user?id={os.getenv('OWNER_ID')}). "
                    "Замечания в прикреплённом файле."
        )
    else:
        await message.bot.send_message(
            tg_id,
            "Ваша работа проверена "
            f"[преподавателем](tg://user?id={os.getenv('OWNER_ID')}).\n\n"
            f"**Замечания**\n\n{data['comments']}"
        )

    file_path = os.path.join(cfg.get_dir(f"labs_to_check"), f"{tg_id}.pdf")
    os.remove(file_path)

    await message.answer(
        f"Замечания высланы [студенту](tg://user?id={tg_id})",
        reply_markup=kb.teacher
    )


@router.message(AssessLab.choice, F.text.casefold().startswith("принять"))
async def assess_lab_ok(message: Message, state: FSMContext):
    await state.set_state(AssessLab.approving)
    await message.answer("Оцените отчёт по ЛР:\n/cancel")


@router.message(AssessLab.approving, F.text != "/cancel")
async def assess_lab_approving(message: Message, state: FSMContext):
    # Проверка формата оценки
    points: str = message.text
    if not points.isdigit() or int(points) < 0:
        await message.answer("Не похоже на баллы")
        await state.clear()
        return
    
    await state.update_data(points=points)
    data = await state.get_data()
    await state.clear()

    _approve_operations_lab(data)

    # Информируем студента
    student_tg = data["student"].tg_id
    await message.bot.send_message(
        student_tg,
        "Ваше ДЗ принято "
        f"[преподавателем](tg://user?id={os.getenv('OWNER_ID')}). "
        f"Оценка: *{data['points']}*"
    )

    await message.answer(
        "Отчёт по ЛР принят.\nИнформация выслана "
        f"[студенту](tg://user?id={student_tg})",
        reply_markup=kb.teacher
    )


def _approve_operations_lab(data: dict):
    lab_n = data["lab_n"]
    dst = os.path.join(
        cfg.get_dir(f"checked_labs"), str(lab_n)
    )
    try:
        os.mkdir(dst)
    except OSError:
        pass

    src = data["report_path"]
    s = data["student"]
    name = f"{s.lastname}_{s.firstname}"
    dst = os.path.join(dst, f"{s.group}_{name}_ЛР_{lab_n}.pdf")
    shutil.move(src, dst)


@router.message(StateFilter(AssessLab), Command("cancel"))
async def assess_lab_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Приём ЛР отменён", reply_markup=kb.teacher)
