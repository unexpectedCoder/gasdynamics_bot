import os
import yaml
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionMiddleware
from datetime import date

import app.database.requests as rq
import app.keyboards.inline as ikb
import app.keyboards.keyboards as kb
import config as cfg
from app.checker import all_right, check_solution, whats_wrong
from app.filters import IsStudent
from app.states import BotCheckHomework, SendLabReport, SendHomeworkReport
from app.utils.seasons import get_current_semester, rus_date


MARK_WRONG = "❌"
MARK_RIGHT = "✅"


router = Router()
router.message.filter(IsStudent())
router.message.outer_middleware(ChatActionMiddleware())


@router.message(F.text.casefold().startswith("дз"))
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
    s = await rq.get_student_by_tg(user_id)
    sem = get_current_semester()
    w = await rq.get_homework_of(s, sem)

    if w:
        await cb.answer(
            f"Вам уже выдан вариант ДЗ № {w.variant}", cache_time=3
        )
        await cb.message.delete()
        return
    if not w:
        await cb.answer(
            "Домашних заданий не осталось, обратитесь к преподавателю",
            show_alert=True
        )
        await cb.message.delete()
        return

    await rq.set_homework(s, w)
    await cb.bot.send_message(
        cb.message.chat.id,
        f"Ваше ДЗ:\n\n{str(w)}", reply_markup=ikb.homework_builder(False)
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
        await cb.answer("Срок сдачи ДЗ не установлен", cache_time=3)
    else:
        await cb.answer(f"Срок сдачи ДЗ - {rus_date(deadline)}", cache_time=5)
    await cb.message.delete()


@router.callback_query(F.data == "homework:results_template")
async def get_homework_results_template(cb: CallbackQuery):
    sem = get_current_semester()
    template_name = \
        "hw_nozzle_template" if sem == 1 else "hw_shock_wedge_template"
    yaml_template_path = cfg.get_file(template_name)

    if not os.path.exists(yaml_template_path):
        await cb.answer(
            "Не найден шаблон YAML-файла решения. Обратитесь к преподавателю",
            show_alert=True
        )
        await cb.message.delete()
        return
    
    # Trying to find a cached file
    yaml_file_id = cfg.get_yaml_template_link(template_name)
    yaml_file = FSInputFile(yaml_template_path) if not yaml_file_id else None

    s = await rq.get_student_by_tg(cb.from_user.id)
    w = await rq.get_homework_of(s, sem)
    msg = await cb.bot.send_document(
        cb.message.chat.id,
        yaml_file if yaml_file else yaml_file_id,
        caption=cfg.get_answer("help_yaml"),
        reply_markup=ikb.homework_builder(w.approved)
    )
    if not yaml_file_id:
        cfg.set_yaml_template_link("homework_nozzle", msg.document.file_id)
    
    await cb.message.delete()
    await cb.answer()


@router.callback_query(F.data == "homework:mark")
async def get_homework_mark(cb: CallbackQuery):
    sem = get_current_semester()
    s = await rq.get_student_by_tg(cb.from_user.id)
    w = await rq.get_homework_of(s, sem)
    done_date = rus_date(w.done_date)
    points = w.points

    if points is None:
        await cb.answer(
            "Оценка вашему ДЗ не выставлена", show_alert=True
        )
        return
    else:
        await cb.answer(
            f"Оценка за ДЗ - {w.points} баллов (дата: {done_date})",
            cache_time=5
        )
    await cb.message.delete()


@router.callback_query(F.data == "homework:algo")
async def homework_algo(cb: CallbackQuery):
    text = \
        "1. Получить у бота свой вариант ДЗ (кнопка ДЗ -> Получить)\n" \
        "2. Решить задачу, сформировав файл с ответами по шаблону "\
        "(шаблон найдёте команде ДЗ -> Шаблон результатов)\n" \
        "3. Как только бот подтвердил правильность решения - отсылаете отчёт" \
        "преподавателю опять же через меню ДЗ (оно немного изменится " \
        "после прохождения проверки ботом - " \
        "появится кнопка 'Отправить отчёт')\n" \
        "4. Преподаватель выдаёт замечания или принимает работу, " \
        "выставляя оценку. Замечания исправляете, высылаете работу вновь\n" \
        "5. Profit"
    await cb.bot.send_message(cb.message.chat.id, text)
    await cb.message.delete()
    await cb.answer()


@router.callback_query(F.data == "homework:bot_check", default_state)
async def homework_bot_check(cb: CallbackQuery, state: FSMContext):
    sem = get_current_semester()
    student = await rq.get_student_by_tg(cb.from_user.id)
    work = await rq.get_homework_of(student, sem)

    if work is None:
        await cb.answer(
            "Вы ещё не получили ДЗ. "
            "Получите его через кнопку (команду) 'ДЗ'",
            show_alert=True
        )
        await cb.message.delete()
        return
    if work.approved:
        await cb.answer("Ваше решение уже прошло проверку ботом", cache_time=2)
        await cb.message.delete()
        return

    await state.set_state(BotCheckHomework.send_yaml)
    await state.update_data(sem=sem, student=student, work=work)
    await cb.bot.send_message(
        cb.message.chat.id, "Прикрепите YAML-файл с ответами >>>\n/cancel"
    )

    await cb.message.delete()
    await cb.answer()


@router.message(BotCheckHomework.send_yaml)
async def send_homework2bot(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()

    if not data["send_file"]:
        await message.answer("Вы не прикрепили документ")
        return
    
    if not _is_yaml(data):
        await message.answer(
            "Не тот формат файла: "
            f"`.{message.document.file_name.rsplit('.', 1)[-1]}`. "
            "Требуется формат `.yaml` или `.yml`."
        )
        return
    
    await _check_yaml(message, data)


def _is_yaml(data: dict):
    fname = data["send_file"].file_name
    return fname.endswith(".yml") or fname.endswith(".yaml")


async def _check_yaml(message: Message, data: dict):
    doc = data["send_file"]

    sem = data["sem"]
    doc_dir = cfg.get_dir(f"sem_{sem}_yaml_to_check")
    doc_path = os.path.join(doc_dir, f"{message.from_user.id}.yml")
    await message.bot.download(doc, doc_path)

    work = data["work"]
    correct_variant = work.variant
    with open(doc_path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)
    yaml_variant = yaml_data["Информация"]["Вариант"]
    
    if correct_variant != yaml_variant:
        await message.answer(
            f"В файле указан вариант № {yaml_variant}, "
            f"не совпадающий с выданным вариантом № {correct_variant}. "
            f"Посмотрите на условие вашего задания (ДЗ -> Получить -> Условие)"
        )
        return

    try:
        checked = check(doc_path, sem)
    except ValueError:
        await message.answer(
            "Файл с ответами не соответствует шаблону"
        )
        return
    except:
        await message.answer(
            "Упс... "
            "Не получилось проверить результаты. Обратитесь к преподавателю"
        )
        return
    
    if not all_right(checked):
        wrongs = "".join([f" - {w}\n" for w in whats_wrong(checked)])
        await message.answer(f"{MARK_WRONG} Есть ошибки:\n\n{wrongs}")
        return
    
    await rq.approve_homework(data["student"], date.today(), sem)

    await message.answer(
        f"{MARK_RIGHT} Проверка прошла успешно.\n"
        "Теперь вы можете отправить преподавателю на проверку "
        "текстовый отчёт в формате PDF (ДЗ -> Отправить отчёт)"
    )

    os.remove(doc_path)


def check(doc_path: str, sem: int):
    with open(doc_path, "r", encoding="utf-8") as f:
        return check_solution(f, sem)


@router.message(StateFilter(BotCheckHomework), Command("cancel"))
async def check_homework_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка файла ответов отменена")


@router.callback_query(F.data == "homework:send_report", default_state)
async def send_homework_report(cb: CallbackQuery, state: FSMContext):
    sem = get_current_semester()
    s = await rq.get_student_by_tg(cb.from_user.id)
    w = await rq.get_homework_of(s, sem)

    if w is None:
        await cb.answer(
            "Вы ещё не получили (не взяли) ДЗ", show_alert=True
        )
        await cb.message.delete()
        return
    if w.done:
        await cb.answer("Вы уже сдали ДЗ", cache_time=2)
        await cb.message.delete()
        return

    await state.set_state(SendHomeworkReport.send_pdf)
    await state.update_data(student=s, work=w, sem=sem)
    await cb.bot.send_message(
        cb.message.chat.id, "Прикрепите файл отчёта в формате PDF >>>\n/cancel",
    )
    await cb.message.delete()
    await cb.answer()


@router.message(SendHomeworkReport.send_pdf)
async def send_homework_report_pdf(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()
    doc = data["send_file"]

    if not doc:
        await message.answer("Вы не прикрепили PDF-файл")
        return
    if not doc.file_name.endswith(".pdf"):
        await message.answer("Не тот формат отчёта: требуется `.pdf`")
        return
    
    await _process_homework_report(message, data)


async def _process_homework_report(message: Message, data: dict):
    doc = data["send_file"]
    sem = data["sem"]
    doc_path = os.path.join(
        cfg.get_dir(f"sem_{sem}_homeworks_to_check"),
        f"{message.from_user.id}.pdf"
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
        f"{s} прислал(а) на проверку отчёт по ДЗ вар. № {w.variant}"
    )


@router.message(StateFilter(SendHomeworkReport), Command("cancel"))
async def check_home_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка отчёта отменена", reply_markup=kb.student)


@router.message(F.text.casefold().startswith("лр"))
@router.message(Command("labwork"))
async def labs(message: Message):
    sem = get_current_semester()
    await message.answer("Выберите ЛР 👇", reply_markup=ikb.labwork(sem))


@router.callback_query(F.data.regexp(r"^lab:\d$"))
async def labs_actions(cb: CallbackQuery):
    lab_i = int(cb.data[-1])
    await cb.message.edit_text(
        f"Выберите действие с ЛР № {lab_i} 👇",
        reply_markup=ikb.labs_action(lab_i)
    )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^lab:description_\d$"))
async def lab_description(cb: CallbackQuery):
    lab_i = int(cb.data[-1])
    path = os.path.join(cfg.get_dir(f"labs"), f"lab_{lab_i}.pdf")
    doc_id = cfg.get_lab_file_link(lab_i)
    doc = FSInputFile(path, f"ЛР {lab_i}.pdf") if not doc_id else None

    try:
        msg = await cb.bot.send_document(
            cb.message.chat.id,
            doc if doc else doc_id,
            caption=f"Описание ЛР № {lab_i}"
        )
    except:
        await cb.answer(
            "Не найден файл с описанием ЛР. "
            "Обратитесь к преподавателю или посмотрите задание в гугл-классе",
            show_alert=True
        )
        return
    
    if not doc_id:
        cfg.set_lab_file_link(lab_i, msg.document.file_id)
    
    s = await rq.get_student_by_tg(cb.from_user.id)
    if not await rq.get_lab_of(s, lab_i):
        await _give_lab(s, lab_i)
    
    await cb.message.delete()
    await cb.answer()


async def _give_lab(student: rq.Student, lab_i: int):
    lab = await rq.get_free_lab(lab_i)
    await rq.set_lab(student, lab)


@router.callback_query(F.data.regexp(r"^lab:send_\d$"), default_state)
async def send_lab(cb: CallbackQuery, state: FSMContext):
    lab_i = int(cb.data[-1])
    await state.set_state(SendLabReport.send_pdf)
    await state.update_data(student_tg=cb.from_user.id, lab_i=lab_i)
    await cb.bot.send_message(
        cb.message.chat.id, "Прикрепите PDF-файл >>>\n/cancel"
    )
    await cb.message.delete()
    await cb.answer()


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
    
    teacher_tg = os.getenv('OWNER_ID')
    s = await rq.get_student_by_tg(message.from_user.id)
    lab_i = data["lab_i"]
    lab = await rq.get_lab_of(s, lab_i)
    
    if not lab:
        await _give_lab(s, lab_i)
    if lab.done:
        await message.answer(f"Вы уже сдали ЛР {lab_i} (оценка {lab.points})")
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
        teacher_tg, f"{s} прислал(а) отчёт по ЛР № {lab_i}"
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
        await rq.get_lab_of(student, n)
        for sem in semesters for n in labs_n[sem - 1]
    ]

    answer = "Успеваемость:\n\n"
    homeworks_text = ""
    for i, work in enumerate(homeworks, start=1):
        if not work or not work.done:
            homeworks_text = homeworks_text + \
                f"- ДЗ {i}-го семестра *не сдано*\n"
            continue
        homeworks_text = homeworks_text + \
            f"- ДЗ {i}-го семестра - {work.points} баллов\n"
    
    labs_text = ""
    for i, work in enumerate(labs, start=1):
        if not work or not work.done:
            labs_text = labs_text + \
                f"- ЛР № {i} *не выполнена*\n"
            continue
        labs_text = labs_text + \
            f"- ЛР № {i} - {work.points} баллов\n"

    await message.answer(answer + homeworks_text + labs_text)


@router.message(F.text.casefold().startswith("дополнительные материалы"))
@router.message(Command("materials"))
async def materials_handler(message: Message):
    # TODO
    await message.answer("Пу-пу-пу... Эта функция в разработке")
    ...


@router.message(Command("kb"))
async def keyboard(message: Message):
    await message.answer("Держите клаву!", reply_markup=kb.student)
