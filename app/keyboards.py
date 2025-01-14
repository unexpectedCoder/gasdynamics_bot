from aiogram.types import (
    KeyboardButton as KB, ReplyKeyboardMarkup
)


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
        KB(text="Моя успеваемость 📈"),
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)

teacher = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Дедлайн ДЗ 💀")
    ],
    [
        KB(text="Студенты 📙"),
        KB(text="Успеваемость 📈")
    ],
    [
        KB(text="Непроверенные ДЗ 📝"),
        KB(text="Проверить ДЗ 🖍")
    ],
    [
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)

assess_homework_choice = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Принять"),
        KB(text="Замечания")
    ]
], resize_keyboard=True, input_field_placeholder="Выберите действие")
