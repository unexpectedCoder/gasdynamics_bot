import json
import os
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionMiddleware

import app.database.requests as rq
import app.keyboards.inline as ikb
import app.keyboards.keyboards as kb
import config as cfg
from app.checker import all_right, check_solution_json, whats_wrong
from app.constants import MARK_RIGHT, MARK_WRONG
from app.filters import IsStudent
from app.states import BotCheckHomework, SendHomeworkReport, SendLabReport
from app.utils.cancel_or import cancel_or
from app.utils.seasons import get_current_semester, rus_date

router = Router()
router.message.filter(IsStudent())
router.message.outer_middleware(ChatActionMiddleware())


@router.message(F.text.casefold().startswith("домашнее задание"))
@router.message(Command("homework"))
async def homework(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    hw = await rq.get_homework_of(student, get_current_semester())
    await message.answer(
        "Выберите действие 👇", reply_markup=ikb.homework_builder(hw.approved)
    )


@router.callback_query(F.data == "homework:get")
async def get_homework(cb: CallbackQuery):
    user_id = cb.from_user.id
    student = await rq.get_student_by_tg(user_id)
    sem = get_current_semester()
    work = await rq.get_homework_of(student, sem)

    if work:
        await cb.message.edit_text(f"Вам уже выдан вариант ДЗ № {work.variant}")
        await cb.answer()
        return

    free = await rq.get_free_homework(sem)
    if not free:
        await cb.message.edit_text(
            "Свободных вариантов ДЗ не осталось, обратитесь к преподавателю..."
        )
        await cb.answer()
        return

    await rq.set_homework(student, free)
    await cb.bot.send_message(
        cb.message.chat.id,
        f"Ваше ДЗ:\n\n{str(free)}",
        reply_markup=ikb.homework_builder(False),
    )

    await cb.message.delete()
    await cb.answer()


@router.callback_query(F.data == "homework:description")
async def get_homework_description(cb: CallbackQuery):
    await cb.message.delete()

    sem = get_current_semester()
    hw_theme = "homework_nozzle" if sem == 1 else "homework_shock_wedge"
    answer = cfg.get_answer(hw_theme)

    student = await rq.get_student_by_tg(cb.from_user.id)
    work = await rq.get_homework_of(student, sem)

    if work is not None:
        answer = f"{answer}\n\n{work}"

    await cb.bot.send_message(cb.message.chat.id, answer)
    await cb.answer()


@router.callback_query(F.data == "homework:deadline")
async def get_homework_deadline(cb: CallbackQuery):
    deadline = await rq.get_homework_deadline(get_current_semester())
    if not deadline:
        text = "Срок сдачи ДЗ не установлен"
    else:
        text = f"Срок сдачи ДЗ - {rus_date(deadline)}"
    await cb.message.edit_text(text)
    await cb.answer()


@router.callback_query(F.data == "homework:results_template")
async def get_homework_results_template(cb: CallbackQuery):
    sem = get_current_semester()
    hw_file_key = "hw_nozzle_template" if sem == 1 else "hw_wedge_template"
    template_path = cfg.get_file(hw_file_key)

    if not os.path.exists(template_path):
        await cb.message.edit_text(
            "Не найден шаблон JSON-файла решения. Обратитесь к преподавателю"
        )
        await cb.answer()
        return

    # Trying to find a cached file
    cache_key = f"hw_template_{sem}"
    file_id = cfg.get_link(cache_key)
    msg = await cb.bot.send_document(
        cb.message.chat.id,
        file_id if file_id else FSInputFile(template_path),
        caption=cfg.get_answer("help_json"),
        reply_markup=ikb.hw_results_code,
    )
    if not file_id:
        cfg.set_link(cache_key, msg.document.file_id)

    await cb.answer()
    await cb.message.delete()


@router.callback_query(F.data == "homework:template_file_code")
async def get_homework_template_code(cb: CallbackQuery):
    await cb.answer()
    await cb.bot.send_message(cb.message.chat.id, cfg.get_answer("help_json_code"))


@router.callback_query(F.data == "homework:mark")
async def get_homework_mark(cb: CallbackQuery):
    sem = get_current_semester()
    s = await rq.get_student_by_tg(cb.from_user.id)
    w = await rq.get_homework_of(s, sem)
    done_date = rus_date(w.done_date)
    points = w.points

    if points is None:
        await cb.message.edit_text("Оценка вашему ДЗ не выставлена")
    else:
        await cb.message.edit_text(
            f"Оценка за ДЗ - {w.points} баллов (дата: {done_date})"
        )
    await cb.answer()


@router.callback_query(F.data == "homework:algo")
async def homework_algo(cb: CallbackQuery):
    await cb.bot.send_message(cb.message.chat.id, cfg.get_answer("homework_algo"))
    await cb.answer()
    await cb.message.delete()


@router.callback_query(F.data == "homework:bot_check", default_state)
async def homework_bot_check(cb: CallbackQuery, state: FSMContext):
    sem = get_current_semester()
    student = await rq.get_student_by_tg(cb.from_user.id)
    work = await rq.get_homework_of(student, sem)

    if work is None:
        await cb.message.edit_text(
            "Вы ещё не получили ДЗ. "
            "Получите его через кнопку (команду) 'Домашнее задание'"
        )
        await cb.answer()
        return
    if work.approved:
        await cb.message.edit_text("Ваше решение уже прошло проверку ботом")
        await cb.answer()
        return

    await state.set_state(BotCheckHomework.send_num_solution)
    await state.update_data(sem=sem, student=student, work=work)

    await cb.bot.send_message(
        cb.message.chat.id, cancel_or("Прикрепите файл JSON с ответами >>>")
    )

    await cb.answer()
    await cb.message.delete()


@router.message(BotCheckHomework.send_num_solution)
async def send_homework2bot(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()

    if not data["send_file"]:
        await message.answer("Вы не прикрепили документ")
        return

    sem = data["sem"]
    fname = data["send_file"].file_name.rsplit(".", maxsplit=1)[-1]

    if fname != "json":
        await message.answer(
            "Не тот формат файла: "
            f"`.{message.document.file_name.rsplit('.', 1)[-1]}`. "
            "Допустим только формат: json"
        )
        return

    await _check_json(message, data)


async def _check_json(message: Message, data: dict):
    doc = data["send_file"]
    sem = data["sem"]
    doc_dir = cfg.get_dir(f"sem_{sem}_json_to_check")
    doc_path = os.path.join(doc_dir, f"{message.from_user.id}.json")

    bot = message.bot
    file_id = doc.file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    downloaded_file = await bot.download_file(file_path, doc_path)

    work = data["work"]
    correct_variant = work.variant
    with open(doc_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    json_variant = json_data["Информация"]["Вариант"]
    if correct_variant != json_variant:
        await message.answer(
            f"В файле указан вариант № {json_variant}, "
            f"не совпадающий с выданным вариантом № {correct_variant}. "
            f"Посмотрите на условие вашего задания"
        )
        return

    try:
        checked = check(doc_path, sem)
    except ValueError:
        await message.answer("Файл с ответами не соответствует шаблону")
        return
    except Exception as ex:
        await message.answer(f"Упс... {ex}", parse_mode=None)
        return

    if not all_right(checked):
        wrongs = "".join([f" - {w}\n" for w in whats_wrong(checked)])
        await message.answer(f"{MARK_WRONG} Есть ошибки:\n\n{wrongs}")
        return

    await rq.approve_homework(data["student"], date.today(), sem)

    await message.answer(
        f"{MARK_RIGHT} Проверка прошла успешно.\n"
        "Теперь вы можете отправить преподавателю на проверку "
        "текстовый отчёт в формате PDF"
    )

    os.remove(doc_path)


def check(doc_path: str, sem: int):
    with open(doc_path, "r", encoding="utf-8") as f:
        return check_solution_json(f, sem)


@router.message(StateFilter(BotCheckHomework), Command("cancel"))
async def check_homework_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка файла ответов отменена")


@router.callback_query(F.data == "homework:send_report", default_state)
async def send_homework_report(cb: CallbackQuery, state: FSMContext):
    sem = get_current_semester()
    s = await rq.get_student_by_tg(cb.from_user.id)
    w = await rq.get_homework_of(s, sem)

    if w is None:
        await cb.message.edit_text("Вы ещё не получили (не взяли) ДЗ")
        await cb.answer()
        return
    if w.done:
        await cb.message.edit_text("Вы уже сдали ДЗ")
        await cb.answer()
        return

    await state.set_state(SendHomeworkReport.send_pdf)
    await state.update_data(student=s, work=w, sem=sem)
    await cb.bot.send_message(
        cb.message.chat.id,
        cancel_or("Прикрепите файл отчёта в формате PDF >>>"),
    )

    await cb.answer()
    await cb.message.delete()


@router.message(SendHomeworkReport.send_pdf, F.document)
async def send_homework_report_pdf(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()
    doc = data["send_file"]

    if not doc.file_name.endswith(".pdf"):
        await message.answer("Не тот формат отчёта: требуется `.pdf`")
        return

    await _process_homework_report(message, data)


async def _process_homework_report(message: Message, data: dict):
    doc = data["send_file"]
    sem = data["sem"]
    doc_path = os.path.join(
        cfg.get_dir(f"sem_{sem}_homeworks_to_check"), f"{message.from_user.id}.pdf"
    )
    await message.bot.download(doc, doc_path)

    s, w = data["student"], data["work"]
    await rq.send_homework(w)

    await message.answer(
        "Ваш отчёт передан преподавателю для проверки. "
        "Остаётся дождаться оценки или замечаний"
    )

    await message.bot.send_message(
        os.getenv("OWNER_ID"),
        f"{s.get_name()} прислал(а) на проверку отчёт по ДЗ вар. № {w.variant}",
    )


@router.message(StateFilter(SendHomeworkReport), Command("cancel"))
async def check_home_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка отчёта отменена", reply_markup=kb.student)


@router.message(F.text.casefold().startswith("лабораторные работы"))
@router.message(Command("labwork"))
async def labs(message: Message):
    labs_dir = cfg.get_dir("labs")
    try:
        entries = os.listdir(labs_dir)
    except OSError:
        entries = []

    lab_numbers = sorted(
        [
            int(f[4:-4])
            for f in entries
            if f.startswith("lab_") and f.endswith(".pdf") and f[4:-4].isdigit()
        ]
    )

    if not lab_numbers:
        await message.answer(
            "Пока нет ни одной лабораторной работы. "
            "Она появится, как только преподаватель её загрузит."
        )
        return

    await message.answer("Выберите ЛР 👇", reply_markup=ikb.labwork(lab_numbers))


@router.callback_query(F.data.regexp(r"^lab:\d$"))
async def labs_actions(cb: CallbackQuery):
    lab_i = int(cb.data[-1])
    await cb.message.edit_text(
        f"Выберите действие с ЛР № {lab_i} 👇", reply_markup=ikb.labs_action(lab_i)
    )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^lab:description_\d$"))
async def lab_description(cb: CallbackQuery):
    lab_i = int(cb.data[-1])
    path = os.path.join(cfg.get_dir("labs"), f"lab_{lab_i}.pdf")

    doc_id = cfg.get_link(f"lab_{lab_i}")
    doc = FSInputFile(path, f"ЛР {lab_i}.pdf") if not doc_id else None

    try:
        msg = await cb.bot.send_document(
            cb.message.chat.id, doc if doc else doc_id, caption=f"Описание ЛР № {lab_i}"
        )
    except:
        await cb.message.edit_text(
            "Не найден файл с описанием ЛР. "
            "Обратитесь к преподавателю или посмотрите задание в гугл-классе"
        )
        await cb.answer()
        return

    if not doc_id:
        cfg.set_link(f"lab_{lab_i}", msg.document.file_id)

    s = await rq.get_student_by_tg(cb.from_user.id)
    if not await rq.get_lab_of(s, lab_i):
        await _give_lab(s, lab_i)

    await cb.answer()
    await cb.message.delete()


async def _give_lab(student: rq.Student, lab_i: int):
    lab = await rq.get_free_lab(lab_i)
    await rq.set_lab(student, lab)


@router.callback_query(F.data.regexp(r"^lab:send_\d$"), default_state)
async def send_lab(cb: CallbackQuery, state: FSMContext):
    lab_i = int(cb.data[-1])
    await state.set_state(SendLabReport.send_pdf)
    await state.update_data(student_tg=cb.from_user.id, lab_i=lab_i)
    await cb.bot.send_message(cb.message.chat.id, cancel_or("Прикрепите PDF-файл >>>"))
    await cb.answer()
    await cb.message.delete()


@router.message(SendLabReport.send_pdf, F.document)
async def send_lab_pdf(message: Message, state: FSMContext):
    data = await state.get_data()
    doc = message.document
    await state.clear()

    if not doc.file_name.casefold().endswith(".pdf"):
        await message.answer(
            "Некорректный формат файла "
            f"`.{doc.file_name.rsplit('.', maxsplit=1)[-1]}`. "
            "Требуется PDF-файл"
        )
        return

    s = await rq.get_student_by_tg(message.from_user.id)
    lab_i = data["lab_i"]
    lab = await rq.get_lab_of(s, lab_i)

    if not lab:
        await _give_lab(s, lab_i)
        lab = await rq.get_lab_of(s, lab_i)
    if lab.done:
        await message.answer(f"Вы уже сдали ЛР {lab_i} с оценкой {lab.points})")
        return

    await rq.send_lab(lab)
    dirname = os.path.join(cfg.get_dir("labs_to_check"), str(lab_i))
    try:
        os.mkdir(dirname)
    except OSError:
        pass

    doc_path = os.path.join(dirname, f"{s.tg_id}.pdf")
    await message.bot.download(doc, doc_path)

    await message.answer("Работа отправлена на проверку преподавателю")
    await message.bot.send_message(
        os.getenv("OWNER_ID"), f"{s.get_name()} прислал(а) отчёт по ЛР № {lab_i}"
    )


@router.message(StateFilter(SendLabReport), Command("cancel"))
async def send_lab_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка отчёта отменена")


@router.message(F.text.casefold().startswith("успеваемость"))
@router.message(Command("progress"))
async def progress(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    semesters = [i for i in range(1, get_current_semester() + 1)]
    homeworks = [await rq.get_homework_of(student, sem) for sem in semesters]
    labs_n = (1, 2, 3), (4, 5, 6)
    labs = [
        await rq.get_lab_of(student, n) for sem in semesters for n in labs_n[sem - 1]
    ]

    answer = "Успеваемость:\n\n"
    homeworks_text = ""
    for i, work in enumerate(homeworks, start=1):
        if not work or not work.done:
            homeworks_text = homeworks_text + f"- ДЗ {i}-го семестра *не сдано*\n"
            continue
        homeworks_text = (
            homeworks_text + f"- ДЗ {i}-го семестра - {work.points} баллов\n"
        )

    labs_text = ""
    for i, work in enumerate(labs, start=1):
        if not work or not work.done:
            labs_text = labs_text + f"- ЛР № {i} *не выполнена*\n"
            continue
        labs_text = labs_text + f"- ЛР № {i} - {work.points} баллов\n"

    await message.answer(answer + homeworks_text + labs_text)


@router.message(Command("kb"))
async def keyboard(message: Message):
    await message.answer("Держите клаву!", reply_markup=kb.student)


@router.message(F.text.casefold().startswith("о боте"))
@router.message(Command("about_bot"))
async def about_bot(message: Message):
    await message.answer(cfg.get_answer("about_bot_student"), reply_markup=kb.student)
