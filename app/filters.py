from aiogram.filters import BaseFilter
from aiogram.types import Message

import app.database.requests as rq
import config as cfg


class IsTeacher(BaseFilter):
    async def __call__(self, message: Message):
        return message.from_user.id in cfg.get("teachers")


class IsStudent(BaseFilter):
    async def __call__(self, message: Message):
        return await rq.get_student_tg(message.from_user.id) is not None
