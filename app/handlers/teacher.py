import os
import pandas as pd
import shutil
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionMiddleware
from datetime import date, datetime
from random import choice as rand_choice

import app.database.requests as rq
import app.keyboards.inline as ikb
import app.keyboards.keyboards as kb
import config as cfg
from app.filters import IsTeacher
from app.states import (
    AddLab,
    AddStudent,
    AssessHomework,
    AssessLab,
    ControlsChecking,
    HomeworkDeadline,
    RemoveStudent
)
from app.utils.seasons import get_current_semester


router = Router()
router.message.filter(IsTeacher())
router.message.outer_middleware(ChatActionMiddleware())


@router.message(F.text.casefold().startswith("контрольные мероприятия"))
@router.message(Command("homework"))
async def exams(message: Message):
    await message.answer(
        "Выберите контрольное мероприятие 👇", reply_markup=ikb.examining
    )


@router.callback_query(F.data == "exam:homework")
async def homework(cb: CallbackQuery):
    await cb.message.edit_text(
        "Выберите действие с ДЗ 👇", reply_markup=ikb.homework_t
    )
    await cb.answer()


@router.callback_query(F.data == "homework:check")
async def choose_homework(cb: CallbackQuery):
    await cb.message.edit_text(
        "Выберите ДЗ 👇", reply_markup=ikb.homework_choice
    )
    await cb.answer()


@router.callback_query(F.data.contains("homework:check_"), default_state)
async def check_homework(cb: CallbackQuery, state: FSMContext):
    sem = int(cb.data[-1])
    dirname = cfg.get_dir(f"sem_{sem}_homeworks_to_check")
    files = os.listdir(dirname)
    if not files:
        await state.clear()
        await cb.message.edit_text(f"Нет непроверенных ДЗ за {sem}-й семестр")
        await cb.answer()
        return
    
    f = files[0]
    student_tg = int(f.split(".")[0])
    s = await rq.get_student_by_tg(student_tg)
    hw = await rq.get_homework_of(s, sem)
    doc_path = os.path.join(dirname, f)
    doc = FSInputFile(doc_path)
    
    await state.set_state(AssessHomework.approve_or_remark)
    await state.update_data(
        student=s, homework=hw, report_path=doc_path, sem=sem
    )

    await cb.message.delete()

    name = s.get_name()
    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption=f"Проверьте ДЗ вар. № {hw.variant} "
            f"(выполнил(а) {name}, {s.group}) и выберите действие 👇"
            "\n/cancel",
        reply_markup=ikb.homework_approve_or_remark
    )

    await cb.answer()


@router.callback_query(F.data == "homework:remark",
                       AssessHomework.approve_or_remark)
async def remark_homework(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AssessHomework.remarking)
    await cb.bot.send_message(
        cb.message.chat.id,
        "Напишите замечания или прикрепите файл с ними >>>\n\n"
        "_это сообщение будет переслано студенту_\n"
        "/cancel"
    )
    await cb.answer()
    await cb.message.delete()


@router.message(AssessHomework.remarking, F.text != "/cancel")
async def send_homework_remarks(message: Message, state: FSMContext):
    await state.update_data(remarks=message.text, doc=message.document)
    data = await state.get_data()
    
    tg_id = data["student"].tg_id
    if data["doc"]:
        await message.bot.send_document(
            tg_id,
            data["doc"],
            caption="Ваша работа проверена преподавателем. "
                    "Замечания в прикреплённом файле"
        )
    else:
        await message.bot.send_message(
            tg_id,
            "Ваша работа проверена преподавателем.\n"
            f"Замечания 👇\n\n{data['remarks']}"
        )

    sem = data["sem"]
    file_path = os.path.join(
        cfg.get_dir(f"sem_{sem}_homeworks_to_check"), f"{tg_id}.pdf"
    )
    os.remove(file_path)

    await message.answer("Замечания высланы студенту")
    await state.clear()


@router.callback_query(F.data == "homework:approve",
                       AssessHomework.approve_or_remark)
async def approve_homework(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    deadline = data["homework"].deadline
    if deadline and date.today() > deadline:
        await cb.bot.send_message(
            cb.message.chat.id,
            "Оцените работу (сдана с опозданием) >>>\n/cancel"
        )
    else:
        await cb.bot.send_message(
            cb.message.chat.id, "Оцените работу >>>\n/cancel"
        )
    
    await state.set_state(AssessHomework.approving)
    await cb.answer()


@router.message(AssessHomework.approving, F.text != "/cancel")
async def assess_homework(message: Message, state: FSMContext):
    points: str = message.text
    if not points.isdigit() or int(points) < 0:
        await message.answer("Некорректная оценка ДЗ")
        await state.clear()
        return
    
    await state.update_data(points=points)
    data = await state.get_data()

    data["date"] = date.today()
    sem = get_current_semester()
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

    student_tg = data["student"].tg_id
    await message.bot.send_message(
        student_tg, f"Ваше ДЗ принято преподавателем: оценка - {data['points']}"
    )
    await message.answer(
        "Работа принята, информация выслана студенту", reply_markup=kb.teacher
    )

    await state.clear()


@router.message(StateFilter(AssessHomework), Command("cancel"))
async def cancel_homework_assess(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Рассмотрение ДЗ отменено", reply_markup=kb.teacher)


@router.callback_query(F.data == "homework:set_deadline", default_state)
async def set_homework_deadline(cb: CallbackQuery, state: FSMContext):
    await state.set_state(HomeworkDeadline.enter_date)
    await cb.message.edit_text(
        "Введите дату сдачи ДЗ в формате `дд.мм.гггг` >>>\n/cancel"
    )


@router.message(HomeworkDeadline.enter_date)
async def enter_homework_deadline(message: Message, state: FSMContext):
    await state.clear()

    deadline = None
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Некорректный формат даты. Требуется `дд.мм.гггг`")
        return

    await rq.set_homework_deadline(get_current_semester(), deadline)
    await message.answer(f"Установлен срок сдачи ДЗ - {deadline}")


@router.message(StateFilter(HomeworkDeadline), Command("cancel"))
async def set_homework_deadline_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Назначение дедлайна ДЗ отменено")


@router.callback_query(F.data == "exam:rk", default_state)
async def exam_controlling(cb: CallbackQuery, state: FSMContext):
    sem = get_current_semester()
    students = list(await rq.get_students())
    controls = [await rq.get_controls_of(s, sem) for s in students]
    groups = [s.group for s in students]

    progress = pd.DataFrame({
        "id": [s.id for s in students],
        "ФИО": [s.get_name() for s in students],
        "Группа": groups,
        "РК 1": list(map(lambda c: c.points_1, controls)),
        "РК 2": list(map(lambda c: c.points_2, controls))
    }).sort_values(by=["Группа", "ФИО"])
    
    excel_path = f"controls.xlsx"
    progress.to_excel(excel_path, index=False)
    doc = FSInputFile(excel_path)

    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption="Проставьте РК в присланном файле и пришлите его обратно >>>\n"
                "/cancel"
    )

    await state.set_state(ControlsChecking.send_excel)

    await cb.message.delete()
    await cb.answer()


@router.message(F.document, ControlsChecking.send_excel)
async def send_controls_excel(message: Message, state: FSMContext):
    await state.clear()

    doc = message.document
    doc_format = doc.file_name.rsplit(".", maxsplit=1)[-1].lower()
    formats = ["xls", "xlsx", "xlsm", "xlsb", "odf", "ods", "odt"]
    if doc_format not in formats:
        await message.answer(
            "Не тот формат файла. "
            f"Допустимы следующие форматы: {', '.join(formats)}"
        )
        return
    
    timestamp = datetime.today().strftime(r'%d-%m-%Y-%H-%M')
    dst = os.path.join(
        cfg.get_dir("controls"), f"controls_{timestamp}.{doc_format}"
    )
    await message.bot.download(doc, dst)
    excel = pd.read_excel(dst)
    sem = get_current_semester()
    for _, row in excel.iterrows():
        student = await rq.get_student_by_id(row["id"])
        controls = await rq.get_controls_of(student, sem)
        controls.points_1 = row["РК 1"]
        controls.points_2 = row["РК 2"]
        await rq.set_control_points_of(student, controls)
    
    os.remove(dst)
    await message.answer("Успеваемость студентов обновлена")


@router.message(Command("cancel"), StateFilter(ControlsChecking))
async def cancel_controls_checking(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Проверка РК отменена")


@router.message(F.text.casefold().startswith("лабораторные работы"))
@router.message(Command("labs"))
async def labs(message: Message):
    await message.answer(
        "Выберите действие с ЛР 👇", reply_markup=ikb.labs_action_t
    )


@router.callback_query(F.data == "labs:check")
async def check_labs(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "Выберите ЛР 👇", reply_markup=ikb.labs_choice_t
    )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^labs:check_\d$"), default_state)
async def check_lab(cb: CallbackQuery, state: FSMContext):
    lab_n = int(cb.data[-1])
    dirname = os.path.join(cfg.get_dir(f"labs_to_check"), str(lab_n))
    
    if not os.path.exists(dirname) or not os.listdir(dirname):
        await state.clear()
        await cb.message.edit_text(f"Нет непроверенных ЛР № {lab_n}")
        await cb.answer()
        return
    
    f = rand_choice(os.listdir(dirname))
    student_tg = int(f.split(".")[0])
    student = await rq.get_student_by_tg(student_tg)
    doc_path = os.path.join(dirname, f)
    doc = FSInputFile(doc_path)
    
    await state.set_state(AssessLab.approve_or_remark)
    await state.update_data(
        student=student, report_path=doc_path, lab_n=lab_n
    )

    await cb.bot.send_document(
        cb.message.chat.id,
        doc,
        caption="Проверьте отчёт и выберите действие >>>\n/cancel",
        reply_markup=ikb.labs_approve_or_remark
    )

    await cb.message.delete()
    await cb.answer()


@router.callback_query(F.data == "labs:remark", AssessLab.approve_or_remark)
async def lab_remarks(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AssessLab.remark)
    await cb.bot.send_message(
        cb.message.chat.id,
        "Напишите замечания или прикрепите файл с ними >>>\n\n"
        "_это сообщение будет переслано студенту_\n"
        "/cancel"
    )
    await cb.answer()


@router.message(AssessLab.remark, F.text != "/cancel")
async def send_lab_remark(message: Message, state: FSMContext):
    await state.update_data(remarks=message.text, doc=message.document)
    data = await state.get_data()
    await state.clear()
    
    tg_id = data["student"].tg_id
    if data["doc"]:
        await message.bot.send_document(
            tg_id,
            data["doc"],
            caption="Ваша работа проверена преподавателем. "
                    "Замечания в прикреплённом файле."
        )
    else:
        await message.bot.send_message(
            tg_id,
            "Ваша работа проверена преподавателем. "
            f"Замечания 👇\n\n{data['remarks']}"
        )

    file_path = os.path.join(
        cfg.get_dir(f"labs_to_check"), str(data["lab_n"]), f"{tg_id}.pdf"
    )
    os.remove(file_path)

    await message.answer(f"Замечания высланы студенту")


@router.callback_query(F.data == "labs:approve", AssessLab.approve_or_remark)
async def approve_lab(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AssessLab.approve)
    await cb.bot.send_message(
        cb.message.chat.id,
        "Оцените выполнение ЛР по пятибалльной шкале >>>\n/cancel"
    )
    await cb.answer()
    await cb.message.delete()


@router.message(AssessLab.approve)
async def assess_lab(message: Message, state: FSMContext):
    points: str = message.text
    if not points.isdigit() or int(points) < 0:
        await message.answer("Некорректная оценка")
        await state.clear()
        return
    
    await state.update_data(points=points, date=date.today())
    data = await state.get_data()
    await state.clear()

    lab_n = data["lab_n"]
    dst = os.path.join(cfg.get_dir(f"checked_labs"), str(lab_n))
    try:
        os.mkdir(dst)
    except OSError:
        pass

    lab = await rq.get_lab_of(data["student"], lab_n)
    await rq.assess_lab(data, lab)

    src = data["report_path"]
    s = data["student"]
    name = f"{s.lastname}_{s.firstname}"
    dst = os.path.join(dst, f"{s.group}_{name}_ЛР_{lab_n}.pdf")
    shutil.move(src, dst)

    student_tg = data["student"].tg_id
    await message.bot.send_message(
        student_tg, f"Ваше ДЗ принято преподавателем с оценкой {data['points']}"
    )
    await message.answer(
        "Отчёт по ЛР принят.\n"
        f"Информация выслана [студенту](tg://user?id={student_tg})"
    )


@router.message(StateFilter(AssessLab), Command("cancel"))
async def assess_lab_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Приём ЛР отменён", reply_markup=kb.teacher)


@router.callback_query(F.data == "labs:add")
async def add_lab(cb: CallbackQuery):
    await cb.message.edit_text(
        "Материал для какой ЛР добавить? 👇", reply_markup=ikb.add_lab
    )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^labs:add_\d$"), default_state)
async def add_lab_n(cb: CallbackQuery, state: FSMContext):
    lab_n = int(cb.data[-1])
    lab_file = f"lab_{lab_n}.pdf"
    labs_dir = cfg.get_dir("labs")

    if lab_file in os.listdir(labs_dir):
        await state.set_state(AddLab.lab_exists)
    else:
        await state.set_state(AddLab.send_file)
        await cb.message.delete()
        await cb.bot.send_message(
            cb.message.chat.id,
            f"Прикрепите PDF-файл ЛР № {lab_n} (до 10 МБ):\n/cancel"
        )

    await state.update_data(lab_n=lab_n)
    await cb.answer()


@router.callback_query(F.data == "labs:replace", AddLab.lab_exists)
async def replace_lab(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await cb.message.edit_text(
            f"Материалы ЛР № {data['lab_n']} уже есть. Хотите заменить?",
            reply_markup=ikb.replace_lab
        )
    await state.set_state(AddLab.send_file)
    await cb.bot.send_message(
        cb.message.chat.id, "Прикрепите файл >>>\n/cancel"
    )
    await cb.answer()


@router.message(F.document, AddLab.send_file)
async def send_lab_pdf(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    lab_n = data["lab_n"]
    doc = message.document
    if not doc.file_name.casefold().endswith(".pdf"):
        await message.answer("Требуется PDF-файл (до 10 МБ)")
        return
    if doc.file_size > 10485760:
        await message.answer("Файл слишком большой (> 10 МБ)")
        return
    
    dst = os.path.join(cfg.get_dir("labs"), f"lab_{lab_n}.pdf")
    doc = await message.bot.download(doc, dst)
    await message.answer(f"Материал ЛР № {lab_n} сохранён")


@router.callback_query(F.data == "labs:not_replace", AddLab.lab_exists)
async def replace_lab(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("На нет и суда нет")
    await cb.answer()


@router.message(StateFilter(AddLab), Command("cancel"))
async def add_lab_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Замена ЛР отменена")


@router.message(F.text.casefold().startswith("студенты"))
@router.message(Command("students"))
async def students(message: Message):
    await message.answer(
        "Выберите действие 👇", reply_markup=ikb.students_actions
    )


@router.callback_query(F.data == "students:progress")
async def students_progress(cb: CallbackQuery):
    students = list(await rq.get_students())
    sem = get_current_semester()
    progresses = [await rq.get_progress_of(s, sem) for s in students]
    homeworks = list(map(lambda p: p[0], progresses))
    labs = [list(map(lambda p: p[1][i], progresses)) for i in range(3)]
    controls = list(map(lambda p: p[2], progresses))
    groups = [s.group for s in students]

    progress = pd.DataFrame({
        "ФИО": [s.get_name() for s in students],
        "Группа": groups,
        "РК 1": list(map(lambda c: 0 if c is None else c.points_1, controls)),
        "РК 2": list(map(lambda c: 0 if c is None else c.points_2, controls)),
        "ДЗ": homeworks,
        "ЛР № 1": labs[0],
        "ЛР № 2": labs[1],
        "ЛР № 3": labs[2]
    }).sort_values(by=["Группа", "ФИО"])
    
    excel_path = "progress.xlsx"
    progress.to_excel(excel_path, index=False)
    doc = FSInputFile(excel_path)
    await cb.bot.send_document(
        cb.message.chat.id, doc, caption="Успеваемость студентов"
    )

    await cb.message.delete()
    await cb.answer()


@router.callback_query(F.data == "students:list")
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
    sem = get_current_semester()

    answer = "Список студентов:\n\n"
    for group in students:
        answer = answer + f"\n{group}:\n"

        for i, s in enumerate(students[group], start=1):
            if not s.tg_id:
                text = f"  {i}. {s.lastname} {s.firstname}"
            else:
                text = f"  {i}. [{s.lastname} {s.firstname}]" \
                       f"(tg://user?id={s.tg_id})"

            work = await rq.get_homework_of(s, sem)
            variant = f" (вар. № {work.variant})" if work else ""
            answer = answer + text + variant + "\n"

    await cb.message.edit_text(answer)
    await cb.answer()


@router.callback_query(F.data == "students:add", default_state)
async def add_student(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddStudent.name)
    await cb.message.edit_text("ФИО студента >>>\n/cancel")
    await cb.answer()


@router.message(AddStudent.name,
                F.text.regexp(
                    r"^[A-Za-zА-Яа-яёЁ'-]+\s[A-Za-zА-Яа-яёЁ'-]+\s"
                    r"[A-Za-zА-Яа-яёЁ'-]+$")
                )
async def give_student_name(message: Message, state: FSMContext):
    ln, fn, mn = message.text.title().split()
    await state.update_data(firstname=fn, middlename=mn, lastname=ln)
    await state.set_state(AddStudent.group)
    await message.answer("Группа >>>\n/cancel")


@router.message(AddStudent.group, F.text.casefold().regexp(r"^см6-\d{2,3}$"))
async def give_student_group(message: Message, state: FSMContext):
    group = message.text.upper()
    await state.update_data(group=group)
    await state.set_state(AddStudent.mark_book)
    await message.answer("Номер зачётки >>>\n/cancel")


@router.message(AddStudent.mark_book, F.text.regexp(r"^\d{2}М\d{3}$"))
async def give_student_mark_book(message: Message, state: FSMContext):
    mark_book = message.text.upper()
    await state.update_data(mark_book=mark_book)
    data = await state.get_data()
    await state.clear()

    student, is_new = await rq.add_student(data)
    if is_new:
        await message.answer(
            f"{student} добавлен(а) в БД", reply_markup=kb.teacher
        )
        return
    await message.answer(f"{student} уже есть в БД", reply_markup=kb.teacher)


@router.message(StateFilter(AddStudent), Command("cancel"))
async def add_student_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление студента отменено")


@router.callback_query(F.data == "students:remove", default_state)
async def remove_student(cb: CallbackQuery, state: FSMContext):
    await state.set_state(RemoveStudent.mark_book)
    await cb.message.edit_text("Номер зачётной книжки >>>\n/cancel")
    await cb.answer()


@router.message(RemoveStudent.mark_book, F.text.regexp(r"^\d{2}М\d{3}$"))
async def remove_student_by_mark_book(message: Message, state: FSMContext):
    await state.clear()
    mb = message.text
    s = await rq.get_student_by_mark_book(mb)
    if s is not None:
        await rq.delete_student(s)
        await message.answer(
            f"Студент {s.get_name()} удалён из списка группы {s.group}"
        )
        return
    await message.answer(f"Не найден студен с зачётной книжкой {mb}")


@router.message(StateFilter(RemoveStudent), Command("cancel"))
async def remove_student_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Удаление студента отменено")


@router.callback_query(F.data == "students:homework_status")
async def students_stats(cb: CallbackQuery):
    await cb.message.delete()

    students = list(await rq.get_students())
    answer = "Статистика:\n\n"

    for i, s in enumerate(students, start=1):
        answer = answer + f"{i}. {s}\n"
        work = await rq.get_homework_of(s, get_current_semester())
        if not work:
            text = f"    ДЗ *не выдано*"
        elif work.done:
            text = f"    ДЗ *сдано* на *{work.points} баллов*"
        elif work.approved:
            text = f"    ДЗ *проверено ботом*, но *не сдано*"
        else:
            text = f"    ДЗ *не проверено ботом* и *не сдано*"
        answer = answer + text + "\n"
        if i % 10 == 0:
            await cb.bot.send_message(cb.message.chat.id, answer)
            answer = ""
    answer = answer + text + "\n"

    if i % 10 != 0:
        await cb.bot.send_message(cb.message.chat.id, answer)
    await cb.answer()


@router.callback_query(F.data == "students:update")
async def update_students_groups(cb: CallbackQuery):
    await cb.message.edit_text(
        "Выберите семестр 👇", reply_markup=ikb.update_groups
    )
    await cb.answer()


@router.callback_query(F.data.startswith("students:sem_"))
async def update_students_groups_sem(cb: CallbackQuery):
    await rq.update_groups(int(cb.data[-1]))
    await cb.message.edit_text("Обозначение учебных групп обновлено")
    await cb.answer()


@router.message(Command("kb"))
async def keyboard(message: Message):
    await message.answer("Держите клаву!", reply_markup=kb.teacher)


@router.message(F.text.casefold().startswith("о боте"))
@router.message(Command("about_bot"))
async def about_bot(message: Message):
    await message.answer(
        "Вы как преподаватель можете:\n"
        "1. Проверять и/или оценивать контрольные мероприятия "
        "(РК, ДЗ)\n",
        "2. Проверять и оценивать отчёты по лабораторным работам\n"
        "3. Просматривать успеваемость студентов\n"
        "4. Добавлять/удалять студентов из базы данных",
        reply_markup=kb.teacher
    )
