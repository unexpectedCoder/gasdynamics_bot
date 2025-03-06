from aiogram.types import (
    KeyboardButton as KB, ReplyKeyboardMarkup
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder


placeholder = "Тыкайте кнопки"
about_bot = "О боте ℹ️"


user = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Регистрация 🗝"),
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)

student = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Получить ДЗ 📖"),
        KB(text="Моё ДЗ 👁‍🗨")
    ],
    [
        KB(text="Проверить ДЗ 🤖"),
        KB(text="Сдать отчёт ДЗ 📗")
    ],
    [
        KB(text="Получить ЛР"),
        KB(text="Сдать отчёт ЛР")
    ],
    [
        KB(text="Дедлайн 💀"),
        KB(text="Моя успеваемость 📈")
    ],
    [
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)

teacher = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Дедлайн 💀"),
        KB(text="Установить дедлайн ☠️")
    ],
    [
        KB(text="Студенты 📙"),
        KB(text="Проверить работу 🖍")
    ],
    [
        KB(text="Добавить ЛР"),
        KB(text="Добавить студента ➕")
    ],
    [
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)

assess_work_choice = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Принять"),
        KB(text="Замечания")
    ]
], resize_keyboard=True, input_field_placeholder="Выберите действие")


async def send_lab(sem: int):
    if sem == 1:
        n = [i for i in range(1, 4)]
    elif sem == 2:
        n = [i for i in range(4, 7)]
    else:
        raise ValueError("неизвестный семестр")
    builder = ReplyKeyboardBuilder()
    for i in n:
        builder.add(KB(text=f"{i}"))
    return builder.adjust(3).as_markup(resize_keyboard=True)
