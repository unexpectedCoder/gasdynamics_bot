import os
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionMiddleware
from datetime import date

import app.database.requests as rq
import app.inline_keyboards as ikb
import app.keyboards as kb
import config as cfg
from app.checker import all_right, check_solution, whats_wrong
from app.filters import IsStudent
from app.states import CheckHomeYAML, SendLabReport, SendHomeworkReport
from app.utils.seasons import get_current_semester


MARK_WRONG = "❌"
MARK_RIGHT = "✅"


router = Router()
router.message.filter(IsStudent())
router.message.outer_middleware(ChatActionMiddleware())


@router.message(F.text.casefold().startswith("получить дз"))
@router.message(Command("get_homework"))
async def get_homework_handler(message: Message):
    user_id = message.from_user.id
    student = await rq.get_student_by_tg(user_id)
    sem = get_current_semester()

    # Проверить, выдано ли ДЗ
    work = await rq.get_homework_of(student, sem)
    if work:
        await message.answer(f"Вам уже выдан вариант ДЗ *№{work.variant}*")
        return

    work = await rq.get_free_homework(sem)
    if not work:
        await message.answer(
            "Домашних заданий не осталось. Пожалуйста, обратитесь к "
            f"[преподавателю](tg://user?id={os.getenv('OWNER_ID')})."
        )
        return

    await rq.set_homework(student, work)
    await message.answer(
        f"*Выдано ДЗ*\n\n{str(work)}", reply_markup=ikb.student_get_hw
    )


@router.callback_query(F.data == "hw_task")
async def get_homework_task(cb: CallbackQuery):
    sem = get_current_semester()
    ans = "homework_nozzle" if sem == 1 else "homework_shock_wedge"
    task = cfg.get_answer(ans)
    await cb.bot.send_message(cb.message.chat.id, task)
    await cb.answer()


@router.callback_query(F.data == "hw_deadline")
async def get_homework_deadline(cb: CallbackQuery):
    deadline = await rq.get_homework_deadline(get_current_semester())
    chat_id = cb.message.chat.id
    bot = cb.bot

    if not deadline:
        await bot.send_message(
            chat_id, "Срок сдачи ДЗ пока не установлен"
        )
    else:
        await bot.send_message(
            chat_id, f"Срок сдачи ДЗ - *{deadline}*")
    await cb.answer()


@router.message(F.text.casefold().startswith("моё дз"))
@router.message(F.text.casefold().startswith("мое дз"))
@router.message(Command("my_homework"))
async def my_homework_handler(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    sem = get_current_semester()
    work = await rq.get_homework_of(student, sem)
    if not work:
        await message.answer(
            "Вы еще не получили задание. "
            "ДЗ можно получить командой /get\_homework "
            "или соответствующей клавишей."
        )
        return
    await message.answer(str(work), reply_markup=ikb.student_get_hw)


@router.message(Command("my_progress"))
@router.message(F.text.casefold().startswith("моя успеваемость"))
async def my_progress_handler(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    semesters = [i for i in range(1, get_current_semester() + 1)]
    homeworks = [
        await rq.get_homework_of(student, sem) for sem in semesters
    ]
    labs_n = (1, 2, 3), (4, 5, 6)
    labs = [
        await rq.get_lab_of(student, n)
        for sem in semesters
        for n in labs_n[sem - 1]
    ]

    answer = "*Успеваемость*\n\n"
    homeworks_text = ""
    for i, work in enumerate(homeworks, start=1):
        if not work or not work.done:
            homeworks_text = homeworks_text + \
                f"- ДЗ № {i} *не сдано*\n"
            continue
        homeworks_text = homeworks_text + \
            f"- ДЗ № {i} *{work.points} баллов*\n"
    
    labs_text = ""
    for i, work in enumerate(labs, start=1):
        if not work or not work.done:
            labs_text = labs_text + \
                f"- ЛР № {i} *не выполнена*\n"
            continue
        labs_text = labs_text + \
            f"- ЛР № {i} *{work.points} баллов*\n"

    await message.answer(answer + homeworks_text + labs_text)


@router.message(default_state, F.text.casefold().startswith("проверить дз"))
@router.message(default_state, Command("check_homework"))
async def check_homework_handler(message: Message, state: FSMContext):
    if await _has_not_homework(message, get_current_semester()):
        await message.answer(
            "Вы ещё не получили ДЗ. "
            "Попробуйте получить его командой /get\_homework "
            "или соответствующей кнопкой"
        )
        return
    if await _has_checked_homework(message):
        await message.answer("Ваше численное решение уже проверено")
        return

    await state.set_state(CheckHomeYAML.send_yaml)
    await message.answer(
        "Пожалуйста, пришлите *YAML-файл численного решения*:\n/cancel"
    )


@router.message(StateFilter(CheckHomeYAML), Command("cancel"))
async def check_homework_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка файла отменена")


async def _has_not_homework(message: Message, sem: int):
    student = await rq.get_student_by_tg(message.from_user.id)
    work = await rq.get_homework_of(student, sem)
    return work is None


async def _has_checked_homework(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    work = await rq.get_homework_of(
        student, get_current_semester()
    )
    return work.checked


@router.message(CheckHomeYAML.send_yaml, F.text != "/cancel")
async def check_send_yaml_handler(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()

    if not data["send_file"]:
        await message.answer(
            "Вы не прикрепили документ. Попробуйте /check_homework ещё раз"
        )
        return
    
    # Проверка формата файла
    if not _is_yaml(data):
        await message.answer(
            "Не тот формат файла: "
            f"`.{message.document.file_name.rsplit('.', 1)[-1]}`. "
            "Требуется формат `.yaml` или `.yml`."
        )
        return
    
    # Проверка численного решения
    await _check_yaml(message, data)


def _is_yaml(data: dict):
    fname = data["send_file"].file_name
    return fname.endswith(".yml") or fname.endswith(".yaml")


async def _check_yaml(message: Message, data: dict):
    doc = data["send_file"]

    # Скачать и сохранить файл от пользователя
    sem = get_current_semester()
    doc_dir = cfg.get_dir(f"sem_{sem}_yaml_to_check")
    doc_path = os.path.join(doc_dir, f"{message.from_user.id}.yml")
    await message.bot.download(doc, doc_path)

    # Сама проверка
    try:
        checked = check(doc_path, sem)
    except:
        await message.answer(
            "Не получилось проверить результаты. "
            "Пожалуйста, обратитесь к "
            f"[преподавателю](tg://user?id={os.getenv('OWNER_ID')})"
        )
        return
    
    if not all_right(checked):
        wrongs = "".join([
            f" - {w}\n" for w in whats_wrong(checked)
        ])

        await message.answer(
            f"{MARK_WRONG} *Есть ошибки:*\n\n{wrongs}"
        )
        return
    
    # Обновляем БД
    student = await rq.get_student_by_tg(message.from_user.id)
    await rq.set_yaml_checked(
        student, date.today(), get_current_semester()
    )

    # Информируем
    await message.answer(
        f"{MARK_RIGHT} Проверка прошла успешно!\n"
        "Теперь вы можете отправить преподавателю на проверку "
        "*текстовый отчёт в формате PDF* командой /send\_homework "
        "или соответствующей кнопкой."
    )

    # Очистка директории
    os.remove(doc_path)


def check(doc_path: str, sem: int):
    with open(doc_path, "r", encoding="utf-8") as f:
        return check_solution(f, sem)


@router.message(StateFilter(SendHomeworkReport), Command("cancel"))
async def check_home_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=kb.student)


@router.message(default_state, F.text.casefold().startswith("сдать отчёт дз"))
@router.message(default_state, F.text.casefold().startswith("сдать отчет дз"))
@router.message(default_state, Command("send_homework"))
async def send_homework_handler(message: Message, state: FSMContext):
    if await _has_not_homework(message, get_current_semester()):
        await message.answer(
            "Возможно, вы ещё не получили ДЗ. "
            "Попробуйте получить его командой /get\_homework "
            "или соответствующей кнопкой"
        )
        return
    if await _has_done_homework(message):
        await message.answer("Вы уже сдали ДЗ")
        return
    if not await _has_checked_homework(message):
        await message.answer(
            "Численное решение вашего ДЗ ещё не принято, "
            "поэтому пока вы не можете отправить отчёт преподавателю"
        )
        return

    await state.set_state(SendHomeworkReport.send_pdf)
    await message.answer(
        "Пожалуйста, прикрепите *файл отчёта в формате PDF*:\n/cancel"
    )


async def _has_done_homework(message: Message):
    student = await rq.get_student_by_tg(message.from_user.id)
    work = await rq.get_homework_of(
        student, get_current_semester()
    )
    return work.done


@router.message(SendHomeworkReport.send_pdf)
async def send_file_handler(message: Message, state: FSMContext):
    await state.update_data(send_file=message.document)
    data = await state.get_data()
    await state.clear()
    doc = data["send_file"]

    # Проверки документа на корректность
    if not doc:
        await message.answer(
            "Вы не прикрепили PDF-файл. "
            "Попробуйте /send\_homework ещё раз"
        )
        return
    
    if not doc.file_name.endswith(".pdf"):
        await message.answer(
            "Не тот формат отчёта: требуется `.pdf`. "
            "Попробуйте /send\_homework ещё раз"
        )
        return
    
    await _process_homework_report(message, data)


async def _process_homework_report(message: Message, data: dict):
    doc = data["send_file"]

    # Скачиваем и сохраняем отчёт
    sem = get_current_semester()
    doc_path = os.path.join(
        cfg.get_dir(f"sem_{sem}_homeworks_to_check"),
        f"{message.from_user.id}.pdf"
    )
    await message.bot.download(doc, doc_path)

    # Делаем пометку в БД
    student = await rq.get_student_by_tg(message.from_user.id)
    await rq.send_homework(await rq.get_homework_of(student, sem))

    # Ответить студенту
    await message.answer(
        "Ваш отчёт передан "
        f"[преподавателю](tg://user?id={os.getenv('OWNER_ID')}) на проверку. "
        "Остаётся дождаться оценки или замечаний"
    )

    # Маякнуть преподавателю о новом поступлении
    name = f"{student.group} {student.lastname} {student.firstname}"
    await message.bot.send_message(
        os.getenv("OWNER_ID"),
        f"Студент группы {name} прислал(а) на проверку *отчёт по ДЗ*."
    )


@router.message(F.text.casefold().startswith("получить лр"))
@router.message(Command("get_lab"))
async def get_lab_handler(message: Message):
    sem = get_current_semester()
    await message.answer(
        "Какая ЛР интересует?", reply_markup=await ikb.get_lab(sem)
    )


@router.callback_query(F.data.contains("get_lab"),
                       flags={"chat_action": "upload_document"})
async def get_lab(cb: CallbackQuery):
    lab_n = int(cb.data[-1])
    path = os.path.join(cfg.get_dir(f"labs"), f"lab_{lab_n}.pdf")
    doc = FSInputFile(path, f"ЛР {lab_n}.pdf")
    try:
        await cb.bot.send_document(
            cb.message.chat.id, doc, reply_markup=kb.student
        )
    except:
        await cb.answer(
            "Не найден файл с описанием ЛР. "
            "Пожалуйста, обратитесь к преподавателю "
            "или посмотрите задание в гугл-классе",
            show_alert=True
        )
        return
    
    student = await rq.get_student_by_tg(cb.from_user.id)
    if not await rq.get_lab_of(student, lab_n):
        lab = await rq.get_free_lab(lab_n)
        await rq.set_lab(student, lab)
    
    await cb.message.delete()
    await cb.answer(f"ЛР № {lab_n}")


@router.message(default_state, F.text.casefold().startswith("сдать отчёт лр"))
@router.message(default_state, F.text.casefold().startswith("сдать отчет лр"))
@router.message(default_state, Command("send_lab"))
async def send_lab_handler(message: Message, state: FSMContext):
    await state.set_state(SendLabReport.lab_choice)
    await state.update_data(student_tg=message.from_user.id)
    await message.answer(
        "Какую ЛР хотите отправить на проверку?\n/cancel",
        reply_markup=await kb.send_lab(get_current_semester())
    )


@router.message(SendLabReport.lab_choice, F.text.isdigit())
async def choose_lab(message: Message, state: FSMContext):
    lab_n = int(message.text)
    if await _has_not_lab(message, lab_n):
        await message.answer(
            f"Возможно, вы ещё не получили ЛР № {lab_n}. "
            "Попробуйте получить его командой /get\_lab "
            "или соответствующей кнопкой",
            reply_markup=kb.student
        )
        await state.clear()
        return
    if await _has_done_lab(message, lab_n):
        await message.answer(
            f"Вы уже сдали ЛР № {lab_n}", reply_markup=kb.student
        )
        await state.clear()
        return
    
    await state.set_state(SendLabReport.send_pdf)
    await state.update_data(lab_n=lab_n)
    await message.answer(
        f"Прикрепите *отчёт по ЛР № {lab_n} в формате PDF*:\n/cancel",
        reply_markup=kb.student
    )


@router.message(SendLabReport.send_pdf, F.document)
async def send_lab(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    doc = message.document
    if not doc.file_name.casefold().endswith(".pdf"):
        await message.answer(
            "Некорректный формат файла "
            f"`.{doc.file_name.rsplit('.', maxsplit=1)[-1]}`. "
            "Требуется PDF-файл",
            reply_markup=kb.student
        )
        return
    
    teacher_tg = os.getenv('OWNER_ID')
    student = await rq.get_student_by_tg(message.from_user.id)
    
    lab_n = data["lab_n"]
    lab = await rq.get_lab_of(student, lab_n)
    await rq.send_lab(lab)

    dirname = os.path.join(cfg.get_dir("labs_to_check"), str(lab_n))
    try:
        os.mkdir(dirname)
    except OSError:
        pass

    doc_path = os.path.join(dirname, f"{student.tg_id}.pdf")
    await message.bot.download(doc, doc_path)

    await message.bot.send_message(
        teacher_tg, f"{student} прислал(а) *отчёт по ЛР № {lab_n}*"
    )
    await message.answer(
        "Работа отправлена на проверку "
        f"[преподавателю](tg://user?id={teacher_tg})",
        reply_markup=kb.student
    )


async def _has_not_lab(message: Message, lab_n: int):
    student = await rq.get_student_by_tg(message.from_user.id)
    work = await rq.get_lab_of(student, lab_n)
    return work is None


async def _has_done_lab(message: Message, lab_n: int):
    student = await rq.get_student_by_tg(message.from_user.id)
    lab = await rq.get_lab_of(student, lab_n)
    return lab.done


@router.message(StateFilter(SendLabReport), Command("cancel"))
async def send_lab_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отсылка отчёта по ЛР отменена", reply_markup=kb.student
    )
