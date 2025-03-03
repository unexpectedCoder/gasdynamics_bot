import os
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, FSInputFile, Message

import app.database.requests as rq
import app.inline_keyboards as ikb
import app.keyboards as kb
import config as cfg
from app.registration import router as reg_router
from app.utils.seasons import get_current_semester


router = Router()
router.include_router(reg_router)


@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id

    # Для зареганых преподов
    teacher = await rq.get_teacher_by_tg(user_id)
    if teacher is not None:
        name = f"{teacher.firstname} {teacher.middlename}"
        await message.answer(
            f"Приветствую вас, {name}!", reply_markup=kb.teacher
        )
        return
    
    # Для зареганых студентов
    student = await rq.get_student_by_tg(user_id)
    if student is not None:
        name = f"{student.firstname} {student.lastname}"
        await message.answer(f"Приветствую, {name}!", reply_markup=kb.student)
        return
    
    # Если пользователь не зареган
    await message.answer(
        f"Приветствую, @{message.from_user.username}!\n"
        "Для получения доступа к моим функциям необходимо зарегистрироваться. "
        "Сделать это можно командой /reg или соответствующей кнопкой.",
        reply_markup=kb.user
    )


@router.message(default_state, Command("cancel"))
async def check_home_yaml_cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})
    await message.answer("Нечего отменять")


@router.message(Command("deadline"))
@router.message(F.text.casefold().startswith("дедлайн"))
async def deadline_handler(message: Message):
    deadline = await rq.get_homework_deadline(get_current_semester())
    if deadline:
        await message.answer(f"Дедлайн ДЗ - *{deadline}*")
        return
    await message.answer("Дедлайн ДЗ не установлен")


@router.message(Command("homework"))
async def homework_handler(message: Message, command: CommandObject):
    theme = command.args

    if not theme:
        await send_current_homework(message)
        return
    
    text = "*Домашнее задание*"
    match theme:
        case "nozzle":
            await message.answer(text + cfg.get_answer("homework_nozzle"))
        case "wedge":
            await message.answer(text + cfg.get_answer("homework_shock_wedge"))
        case _:
            await message.answer("Не знаю такого задания")


async def send_current_homework(message: Message):
    sem = get_current_semester()
    if sem == 1:
        text = "*Домашнее задание весеннего семестра*\n\n"
        await message.answer(text + cfg.get_answer("homework_nozzle"))
        return
    text = "*Домашнее задание осеннего семестра*\n\n"
    await message.answer(text + cfg.get_answer("homework_shock_wedge"))


@router.message(F.text.casefold().contains("о боте"))
@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(cfg.get_answer("help"))


@router.message(Command("help_teacher"))
async def help_teacher_handler(message: Message):
    await message.answer(cfg.get_answer("help_teacher"))


@router.message(Command("help_student"))
async def help_student_handler(message: Message):
    await message.answer(
        cfg.get_answer("help_student"), reply_markup=ikb.help
    )


@router.message(Command("help_yaml"))
async def help_yaml_command(message: Message):
    await help_yaml_handler(message)


@router.callback_query(F.data == "help_yaml")
async def help_yaml_callback(cb: CallbackQuery):
    await help_yaml_handler(cb.message)
    await cb.answer()


async def help_yaml_handler(message: Message):
    yaml_template_path = cfg.get_file("home_nozzle")
    if not os.path.exists(yaml_template_path):
        await message.bot.send_message(
            message.chat.id,
            "К сожалению я не нашёл пример YAML-файла решения. "
            "Пожалуйста, обратитесь к преподавателю."
        )
        print(yaml_template_path)
        return
    
    yaml_template = FSInputFile(yaml_template_path)
    await message.bot.send_document(
        message.chat.id,
        yaml_template,
        caption=cfg.get_answer("help_yaml"),
        reply_markup=ikb.help_yaml
    )


@router.message(Command("help_pyyaml"))
async def hel_pyyaml_command(message: Message):
    await help_pyyaml_handler(message)


@router.callback_query(F.data == "help_pyyaml")
async def help_pyyaml_callback(cb: CallbackQuery):
    await help_pyyaml_handler(cb.message)
    await cb.answer()


async def help_pyyaml_handler(message: Message):
    await message.answer(cfg.get_answer("help_pyyaml"))
