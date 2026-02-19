from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

import app.database.requests as rq
import app.keyboards.keyboards as kb
from app.filters import IsDefaultUser
from app.states import Registration
from app.utils.cancel_or import cancel_or

router = Router()
router.message.filter(IsDefaultUser())


@router.message(default_state, Command("reg"))
@router.message(default_state, F.text.lower().contains("регистрация"))
async def reg_handler(message: Message, state: FSMContext):
    await state.set_state(Registration.mark_book)
    await message.answer(
        cancel_or(
            "Пожалуйста, введите номер своей зачётной книжки "
            "(кириллицей и с учётом регистра). Например, 17М235 >>>"
        )
    )


@router.message(Registration.mark_book)
async def reg_mark_book(message: Message, state: FSMContext):
    await state.update_data(mark_book=message.text)
    data = await state.get_data()
    await state.clear()

    student = await rq.get_student_by_mark_book(data["mark_book"])
    if not student:
        await message.answer(
            "Не удалось найти вас в базе данных. "
            "Проверьте правильность номера зачётной книжки "
            "и попробуйте ещё раз зарегистрироваться (/reg) "
            "или обратитесь к преподавателю",
            reply_markup=kb.default_user,
        )
        return

    student.tg_id = message.from_user.id
    await rq.reg_student(student)
    await message.answer(
        f"Вы успешно зарегистрированы как студент группы {student.group} "
        f"{student.firstname} {student.lastname}",
        reply_markup=kb.student,
    )


@router.message(StateFilter(Registration), Command("cancel"))
async def reg_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация отменена")
