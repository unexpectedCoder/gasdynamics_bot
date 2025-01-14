from aiogram import Router
from aiogram.types import ChatJoinRequest

import app.database.requests as rq
import app.keyboards as kb


router = Router()


@router.chat_join_request()
async def join_request_handler(update: ChatJoinRequest):
    user_id = update.from_user.id
    bot = update.bot

    if await rq.get_student_tg(user_id):
        await update.approve()
        await update.bot.send_message(
            user_id,
            f"Добро пожаловать в *{update.chat.full_name}*",
            reply_markup=kb.student
        )
        return
    
    await update.decline()
    await bot.send_message(
        user_id,
        "Для вступления в группу необходимо зарегистрироваться, "
        "что можно сделать командой /reg или соответствующей кнопкой "
        "(кнопки появятся после /start).\n"
        "После регистрации отправьте заявку на вступление ещё раз.",
        reply_markup=kb.user
    )
