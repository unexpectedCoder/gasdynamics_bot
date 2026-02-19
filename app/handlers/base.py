from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

import app.database.requests as rq
import app.keyboards.keyboards as kb
from app.handlers.registration import router as reg_router

router = Router()
router.include_router(reg_router)


@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id

    # Для зареганых преподов
    teacher = await rq.get_teacher_by_tg(user_id)
    if teacher is not None:
        name = f"{teacher.firstname} {teacher.middlename}"
        await message.answer(f"Приветствую вас, {name}", reply_markup=kb.teacher)
        return

    # Для зареганых студентов
    student = await rq.get_student_by_tg(user_id)
    if student is not None:
        name = f"{student.firstname} {student.lastname}"
        await message.answer(f"Приветствую, {name}", reply_markup=kb.student)
        return

    # Если пользователь не зареган
    await message.answer(
        f"Приветствую, {message.from_user.first_name}!\n"
        "Для получения доступа к моим функциям необходимо зарегистрироваться. "
        "Сделать это можно командой /reg или соответствующей кнопкой.",
        reply_markup=kb.default_user,
    )


@router.message(default_state, Command("cancel"))
async def cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})
    await message.answer("Нечего отменять...")


@router.message(Command("about_bot"))
@router.message(F.text.lower().startswith("о боте"))
async def about_bot_handler(message: Message):
    await message.answer(
        "Бот предназначен для автоматизации проверки и учёта контрольных "
        "мероприятий, выполняемых студентами, а также для контроля "
        "успеваемости. Более подробная информация доступна после регистрации "
        "при использовании соответствующих функций"
    )


@router.message(Command("kb"))
async def keyboard(message: Message):
    await message.answer("Держите клаву!", reply_markup=kb.default_user)
