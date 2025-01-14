import os
import random as rand
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from datetime import date

import app.database.requests as rq
import app.inline_keyboards as ikb
import app.keyboards as kb
import config as cfg
from app.checker import all_right, check_solution, whats_wrong
from app.filters import IsStudent
from app.states import CheckHomeYAML, SendHomeworkReport
from app.utils.seasons import get_current_semester


# Настройки
MARK_WRONG = "❌"
MARK_RIGHT = "✅"
# -------------------------


router = Router()
router.message.filter(IsStudent())


@router.message(Command("get_homework"))
@router.message(F.text.casefold().contains("получить дз"))
async def get_homework_handler(message: Message):
    user_id = message.from_user.id
    student = await rq.get_student_tg(user_id)
    sem = get_current_semester()

    # Проверить, выдано ли ДЗ
    work = await rq.get_homework_of(student, sem)
    if work:
        await message.answer(f"Вам уже выдан вариант ДЗ *№{work.variant}*")
        return

    works = list(await rq.get_free_homeworks(sem))
    if not works:
        await message.answer(
            "Домашних заданий не осталось. Пожалуйста, обратитесь к "
            f"[преподавателю](tg://user?id={os.getenv('OWNER_ID')})."
        )
        return

    work = rand.choice(works)
    await rq.set_homework(student, work)
    await message.answer(
        f"*Выдано ДЗ*\n\n{str(work)}",
        reply_markup=ikb.student_hw_deadline
    )


@router.callback_query(F.data == "hw_deadline")
async def get_homework_deadline_callback(cb: CallbackQuery):
    deadline = await rq.get_homework_deadline(get_current_semester())
    dt = 2
    if not deadline:
        await cb.answer("Срок сдачи ДЗ пока не установлен", cache_time=dt)
        return
    await cb.answer(f"Срок сдачи ДЗ - {deadline}", cache_time=dt)


@router.message(Command("my_homework"))
@router.message(F.text.casefold().contains("моё дз"))
@router.message(F.text.casefold().contains("мое дз"))
async def my_homework_handler(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
    sem = get_current_semester()
    work = await rq.get_homework_of(student, sem)
    if not work:
        await message.answer(
            "Вы еще не получили задание. "
            "ДЗ можно получить командой /get\_homework "
            "или соответствующей клавишей."
        )
        return
    await message.answer(str(work))


@router.message(Command("my_progress"))
@router.message(F.text.casefold().contains("успеваемость"))
async def my_progress_handler(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
    semesters = [i for i in range(1, get_current_semester() + 1)]
    works = [
        await rq.get_homework_of(student, sem) for sem in semesters
    ]

    answer = "*Успеваемость*\n\n"
    works_text = ""
    for i, hw in enumerate(works, start=1):
        if not hw or not hw.done:
            works_text = works_text + \
                f"- ДЗ № {i} *не сдано*\n"
            continue
        works_text = works_text + \
            f"- ДЗ № {i} *{hw.points} баллов*\n"

    await message.answer(answer + works_text)


@router.message(default_state, Command("check_homework"))
@router.message(default_state, F.text.casefold().contains("проверить дз"))
async def check_homework_handler(message: Message, state: FSMContext):
    if await _has_not_homework(message):
        await message.answer(
            "Возможно, вы ещё не получили ДЗ. "
            "Попробуйте получить его командой /get\_homework "
            "или соответствующей кнопкой"
        )
        return
    if await _has_checked_homework(message):
        await message.answer("Ваше численное решение уже проверено")
        return

    await state.set_state(CheckHomeYAML.send_yaml)
    await message.answer(
        "Пожалуйста, пришлите *YAML-файл численного решения* (/cancel):"
    )


async def _has_not_homework(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
    work = await rq.get_homework_of(
        student, get_current_semester()
    )
    return work is None


async def _has_checked_homework(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
    work = await rq.get_homework_of(
        student, get_current_semester()
    )
    return work.checked


@router.message(CheckHomeYAML.send_yaml)
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
    doc_dir = cfg.get_dir("yaml_to_check")
    doc_path = os.path.join(doc_dir, f"{message.from_user.id}.yml")
    await message.bot.download(doc, doc_path)

    # Сама проверка
    checked = check(doc_path)
    if not all_right(checked):
        wrongs = "".join([
            f" - {w}\n" for w in whats_wrong(checked)
        ])

        await message.answer(
            f"{MARK_WRONG} *Есть ошибки:*\n\n{wrongs}"
        )
        return
    
    # Обновляем БД
    student = await rq.get_student_tg(message.from_user.id)
    await rq.set_yaml_checked(
        student, date.today(), get_current_semester()
    )

    # Информируем
    await message.answer(
        f"{MARK_RIGHT} Проверка прошла успешно!\n"
        "Теперь вы можете отправить преподавателю на проверку "
        "*текстовый отчёт в формате PDF* командой /send\_report "
        "или соответствующей кнопкой."
    )

    # Очистка директории
    os.remove(doc_path)


def check(doc_path: str):
    with open(doc_path, "r", encoding="utf-8") as f:
        return check_solution(f)


@router.message(StateFilter(SendHomeworkReport), Command("cancel"))
async def check_home_yaml_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=kb.student)


@router.message(default_state, Command("send_report"))
@router.message(default_state, F.text.casefold().contains("сдать отчёт дз"))
@router.message(default_state, F.text.casefold().contains("сдать отчет дз"))
async def send_report_handler(message: Message, state: FSMContext):
    if await _has_not_homework(message):
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
        "Пожалуйста, пришлите *файл отчёта в формате PDF* (/cancel):"
    )


async def _has_done_homework(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
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
            "Вы ничего не прикрепили. "
            "Попробуйте /send\_report ещё раз"
        )
        return
    
    if not doc.file_name.endswith(".pdf"):
        await message.answer(
            "Не тот формат отчёта: требуется `.pdf`. "
            "Попробуйте ещё раз"
        )
        return
    
    await _process_homework_report(message, data)


async def _process_homework_report(message: Message, data: dict):
    doc = data["send_file"]

    # Скачиваем и сохраняем отчёт
    doc_path = os.path.join(
        cfg.get_dir("homeworks_to_check"),
        f"{message.from_user.id}.pdf"
    )
    await message.bot.download(doc, doc_path)

    # Делаем пометку в БД
    student = await rq.get_student_tg(message.from_user.id)
    await rq.send_homework(await rq.get_homework_of(
        student, get_current_semester()
    ))

    # Ответить студенту
    await message.answer(
        "Ваш отчёт передан преподавателю на проверку! "
        "Остаётся дождаться оценки или замечаний."
    )

    # Маякнуть преподавателю о новом поступлении
    name = f"{student.group} {student.lastname} {student.firstname}"
    await message.bot.send_message(
        os.getenv("OWNER_ID"),
        f"Студент группы {name} прислал(а) на проверку *отчёт по ДЗ*."
    )
