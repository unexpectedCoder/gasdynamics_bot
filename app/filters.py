from aiogram.filters import BaseFilter
from aiogram.types import Message

import app.database.requests as rq
import config as cfg


class IsDefaultUser(BaseFilter):
    async def __call__(self, message: Message):
        is_teacher = message.from_user.id in cfg.settings.teachers
        is_student = await rq.get_student_by_tg(message.from_user.id) is not None
        return not (is_teacher or is_student)


class IsTeacher(BaseFilter):
    async def __call__(self, message: Message):
        return message.from_user.id in cfg.settings.teachers


class IsStudent(BaseFilter):
    async def __call__(self, message: Message):
        return await rq.get_student_by_tg(message.from_user.id) is not None
