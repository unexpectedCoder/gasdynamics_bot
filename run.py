import asyncio
import logging
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import app.database.requests as rq
import config
from app.database.models import async_main
from app.handlers.base import router as base_router
from app.handlers.student import router as student_router
from app.handlers.teacher import router as teacher_router

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Библиотеки, которые слишком многословны на INFO
_NOISY_LOGGERS = [
    "aiogram.event",
    "aiosqlite",
    "sqlalchemy.engine",
]


def setup_logging(in_docker: bool):
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT)

    handlers: list[logging.Handler] = []

    # stdout — основной канал для Docker (docker logs, log-драйверы, Loki и т.д.)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    handlers.append(stdout_handler)

    # Файловый хендлер с ротацией — дополнительно, если примонтирован /logging
    log_dir = Path("/logging") if in_docker else Path("logs")
    if in_docker:
        file_logging_available = log_dir.is_dir()
    else:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_logging_available = True

    if file_logging_available:
        log_file = log_dir / "bot.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,  # 5 МБ на файл
            backupCount=3,  # хранить 3 архива → до 20 МБ суммарно
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )

    # Глушим шумные сторонние логгеры
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    """Перехватывает необработанные исключения и пишет их в лог."""
    if issubclass(exc_type, KeyboardInterrupt):
        # KeyboardInterrupt не нужно логировать как ошибку
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(
        "Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback)
    )


async def main() -> None:
    bot = Bot(
        config.settings.token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN, link_preview_is_disabled=True
        ),
    )
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()
    dp.include_routers(student_router, teacher_router, base_router)

    # Startup
    await async_main()
    if await rq.db_is_empty():
        await rq.fill_database()

    logger.info("Бот запущен")
    await dp.start_polling(bot)


def _handle_sigterm(signum, frame) -> None:
    """Docker посылает SIGTERM при `docker stop`. Логируем и завершаем процесс."""
    logger.info("Получен сигнал SIGTERM — завершение работы")
    sys.exit(0)


if __name__ == "__main__":
    setup_logging(in_docker=config.settings.in_docker)
    sys.excepthook = handle_exception
    signal.signal(signal.SIGTERM, _handle_sigterm)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот выключен (KeyboardInterrupt)")
