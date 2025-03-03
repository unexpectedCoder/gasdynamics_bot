import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import app.database.requests as rq
import config
from app.admin import router as admin_router
from app.database.models import async_main
from app.handlers import router
from app.student import router as student_router
from app.teacher import router as teacher_router


async def main():
    token = os.getenv("TOKEN")
    bot = Bot(
        token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
            link_preview_is_disabled=True
        )
    )
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()
    dp.include_routers(
        router, student_router, teacher_router, admin_router
    )
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


async def on_startup(dispatcher):
    config.init()
    flag = not os.path.exists("db.sqlite3")
    await async_main()
    if flag:
        await rq.fill_database()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот выключен")
