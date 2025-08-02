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
        await message.answer(
            f"Приветствую вас, {name}", reply_markup=kb.teacher
        )
        return
    
    # Для зареганых студентов
    student = await rq.get_student_by_tg(user_id)
    if student is not None:
        name = f"{student.firstname} {student.lastname}"
        await message.answer(f"Приветствую, {name}", reply_markup=kb.student)
        return
    
    # Если пользователь не зареган
    await message.answer(
        "Приветствую, юзернейм!\n"
        "Для получения доступа к моим функциям необходимо зарегистрироваться. "
        "Сделать это можно командой /reg или соответствующей кнопкой",
        reply_markup=kb.default_user
    )


@router.message(default_state, Command("cancel"))
async def cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})
    await message.answer("Нечего отменять")


@router.message(Command("about_bot"))
@router.message(F.text.lower().startswith("о боте"))
async def about_bot_handler(message: Message):
    await message.answer(
        "Бот предназначен для автоматизации проверки и учёта контрольных "
        "мероприятий, выполняемых студентами, а также для контроля " "успеваемости. Более подробная информация доступна после регистрации "
        "при использовании соответствующих функций"
    )


@router.message(Command("kb"))
async def keyboard(message: Message):
    await message.answer("Держите клаву!", reply_markup=kb.default_user)


# TODO
# @router.message(Command("help_yaml"))
# async def help_yaml_command(message: Message):
#     await help_yaml_handler(message)


# async def help_yaml_handler(message: Message):
#     yaml_template_path = cfg.get_file("hw_nozzle_template")
#     if not os.path.exists(yaml_template_path):
#         await message.bot.send_message(
#             message.chat.id,
#             "К сожалению я не нашёл пример YAML-файла решения. "
#             "Пожалуйста, обратитесь к преподавателю."
#         )
#         print(yaml_template_path)
#         return
    
#     yaml_file_id = cfg.get_yaml_template_link("homework_nozzle")
#     yaml_file = FSInputFile(yaml_template_path) if not yaml_file_id else None

#     msg = await message.bot.send_document(
#         message.chat.id,
#         yaml_file if yaml_file else yaml_file_id,
#         caption=cfg.get_answer("help_yaml"),
#         reply_markup=ikb.help_yaml
#     )

#     if not yaml_file_id:
#         cfg.set_yaml_template_link("homework_nozzle", msg.document.file_id)


# @router.callback_query(F.data == "help_yaml")
# async def help_yaml_callback(cb: CallbackQuery):
#     await help_yaml_handler(cb.message)
#     await cb.answer()


# @router.message(Command("help_pyyaml"))
# async def help_pyyaml_command(message: Message):
#     await help_pyyaml_handler(message)


# @router.callback_query(F.data == "help_pyyaml")
# async def help_pyyaml_callback(cb: CallbackQuery):
#     await help_pyyaml_handler(cb.message)
#     await cb.answer()


# async def help_pyyaml_handler(message: Message):
#     await message.answer(cfg.get_answer("help_pyyaml"))
