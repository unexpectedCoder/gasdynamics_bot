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

    # Startup
    config.init()
    await async_main()
    if await rq.db_is_empty():
        await rq.fill_database()

    await dp.start_polling(bot)


if __name__ == "__main__":
    from dotenv import load_dotenv


    load_dotenv(os.path.join("secrets", ".env"))
    if os.getenv("IN_DOCKER"):
        log_file = os.path.join("/logging", "log")
        logging.basicConfig(
            level=logging.INFO, filename=log_file, encoding="utf-8"
        )
    else:
        logging.basicConfig(
            level=logging.INFO, stream=sys.stdout, encoding="utf-8"
        )
    

    def handle_exception(exc_type, exc_value, exc_traceback):
        logging.error(
            "Exception", exc_info=(exc_type, exc_value, exc_traceback)
        )


    sys.excepthook = handle_exception
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот выключен")
