from aiogram.types import (
    InlineKeyboardButton as IKB, InlineKeyboardMarkup
)


help = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="Подробнее о YAML", callback_data="help_yaml")
    ]
])

help_yaml = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="Как это сделать в Python?", callback_data="help_pyyaml")
    ]
])

student_hw_deadline = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="Дедлайн сдачи 💀", callback_data="hw_deadline")
    ]
])
