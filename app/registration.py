from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

import app.database.requests as rq
import app.keyboards as kb
import config as cfg
from app.states import Registration


router = Router()


@router.message(StateFilter(Registration), Command("cancel"))
async def reg_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация отменена")


@router.message(default_state, Command("reg"))
@router.message(default_state, F.text.lower().contains("регистрация"))
async def reg_handler(message: Message, state: FSMContext):
    if await _check_is_reg_teacher(message):
        return
    if await _check_is_reg_student(message):
        return
    
    await state.set_state(Registration.mark_book)
    await message.answer(
        "Пожалуйста, введите *номер своей зачётной книжки* "
        "(например, 17М235) (/cancel):"
    )


async def _check_is_reg_teacher(message: Message):
    user_id = message.from_user.id
    if user_id in cfg.get("teachers"):
        teacher = await rq.get_teacher_tg(user_id)
        name = f"{teacher.firstname} {teacher.middlename}"
        await message.answer(f"{name}, вы уже зарегистрированы")
        return True
    return False


async def _check_is_reg_student(message: Message):
    student = await rq.get_student_tg(message.from_user.id)
    if student is not None:
        await message.answer(
            f"{student.firstname} {student.lastname}, "
            "вы уже зарегистрированы "
            f"как *студент группы {student.group}*"
        )
        return True
    return False


@router.message(Registration.mark_book)
async def reg_mark_book(message: Message, state: FSMContext):
    await state.update_data(mark_book=message.text)
    data = await state.get_data()
    await state.clear()

    student = await rq.get_student_mark_book(data["mark_book"])
    if not student:
        await message.answer(
            "Не удалось найти вас в базе данных. "
            "Проверьте правильность номера зачётной книжки "
            "и попробуйте ещё раз зарегистрироваться (/reg) "
            "или обратитесь к преподавателю.",
            reply_markup=kb.user
        )
        return
    
    student.tg_id = message.from_user.id
    await rq.reg_student(student)
    await message.answer(
        f"Вы успешно зарегистрированы как *студент группы {student.group} "
        f"{student.firstname} {student.lastname}*!",
        reply_markup=kb.student
    )
