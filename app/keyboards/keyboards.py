from aiogram.types import KeyboardButton as KB, ReplyKeyboardMarkup


placeholder = "Используйте кнопки или вводите команды..."
about_bot = "О боте ℹ️"


default_user = ReplyKeyboardMarkup(keyboard=[
    [
        KB(text="Регистрация 🗝"),
        KB(text=about_bot)
    ]
], resize_keyboard=True, input_field_placeholder=placeholder)


student = ReplyKeyboardMarkup(
    keyboard=[
        [KB(text="Домашнее задание 📕")],
        [KB(text="Лабораторные работы 📗")],
        [KB(text="Успеваемость 📈")],
        [KB(text=about_bot)]
    ],
    resize_keyboard=True,
    input_field_placeholder=placeholder
)


teacher = ReplyKeyboardMarkup(
    keyboard=[
        [
            KB(text="Контрольные мероприятия 📕")
        ],
        [
            KB(text="Лабораторные работы 📗")
        ],
        [
            KB(text="Студенты 📙")
        ],
        [
            KB(text=about_bot)
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder=placeholder
)
