import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import app.database.requests as rq
import config as cfg
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
    cfg.init()
    await async_main()
    if await rq.db_is_empty():
        await rq.fill_database()

    await dp.start_polling(bot)


if __name__ == "__main__":
    from dotenv import load_dotenv


    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    load_dotenv(os.path.join("secrets", ".env"))
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот выключен")
