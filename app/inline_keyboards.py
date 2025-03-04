from aiogram.types import (
    InlineKeyboardButton as IKB, InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


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

student_get_hw = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="Условие задания", callback_data="hw_task"),
        IKB(text="Дедлайн сдачи", callback_data="hw_deadline")
    ]
])


async def get_lab(sem: int):
    if sem == 1:
        n = [i for i in range(1, 4)]
    elif sem == 2:
        n = [i for i in range(4, 7)]
    else:
        raise ValueError("неизвестный семестр")
    builder = InlineKeyboardBuilder()
    for i in n:
        builder.add(IKB(text=f"{i}", callback_data=f"get_lab_{i}"))
    return builder.adjust(3).as_markup()


set_deadline = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="ДЗ", callback_data="set_deadline_homework"),
        IKB(text="Лабы", callback_data="set_deadline_labs")
    ]
])

students_info = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="Список", callback_data="students_list"),
        IKB(text="Успеваемость", callback_data="students_progress")
    ]
])

check_work = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="ДЗ", callback_data="check_homework"),
        IKB(text="Лабы", callback_data="check_lab")
    ]
])

check_homework = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="№ 1", callback_data="check_hw_1"),
        IKB(text="№ 2", callback_data="check_hw_2")
    ]
])

check_lab = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="№ 1", callback_data="check_lab_1"),
        IKB(text="№ 2", callback_data="check_lab_2"),
        IKB(text="№ 3", callback_data="check_lab_3")
    ],
    [
        IKB(text="№ 4", callback_data="check_lab_4"),
        IKB(text="№ 5", callback_data="check_lab_5"),
        IKB(text="№ 6", callback_data="check_lab_6")
    ]
])

stats = InlineKeyboardMarkup(inline_keyboard=[
    [
        IKB(text="ДЗ № 1", callback_data="stats_hw_1"),
        IKB(text="ДЗ № 2", callback_data="stats_hw_2")
    ]
])
