from aiogram.types import InlineKeyboardButton as IKB
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def homework_builder(bot_approved: bool):
    bot_or_teacher = (
        IKB(text="Отправить преподавателю", callback_data="homework:send_report")
        if bot_approved
        else IKB(text="Проверка ботом", callback_data="homework:bot_check")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                IKB(text="Условие", callback_data="homework:description"),
                IKB(text="Дедлайн", callback_data="homework:deadline"),
            ],
            [IKB(text="Получить задание", callback_data="homework:get")],
            [IKB(text="Шаблон результатов", callback_data="homework:results_template")],
            [IKB(text="Алгоритм выполнения", callback_data="homework:algo")],
            [bot_or_teacher],
            [IKB(text="Оценка", callback_data="homework:mark")],
        ]
    )


def labwork(lab_numbers: list[int]):
    builder = InlineKeyboardBuilder()
    for i in lab_numbers:
        builder.add(IKB(text=f"№ {i}", callback_data=f"lab:{i}"))
    return builder.adjust(3).as_markup()


def labs_action(lab_i: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [IKB(text="Описание", callback_data=f"lab:description_{lab_i}")],
            [IKB(text="Отправить отчёт", callback_data=f"lab:send_{lab_i}")],
        ]
    )


examining = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="ДЗ", callback_data="exam:homework"),
            IKB(text="РК", callback_data="exam:rk"),
        ]
    ]
)


# Suffix '_t' means 'teacher'
homework_t = InlineKeyboardMarkup(
    inline_keyboard=[
        [IKB(text="Проверить", callback_data="homework:check")],
        [IKB(text="Установить дедлайн", callback_data="homework:set_deadline")],
    ]
)


set_deadline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="ДЗ", callback_data="set_deadline_homework"),
            IKB(text="Лабы", callback_data="set_deadline_labs"),
        ]
    ]
)


homework_choice = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="№ 1", callback_data="homework:check_1"),
            IKB(text="№ 2", callback_data="homework:check_2"),
        ]
    ]
)


homework_approve_or_remark = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="Замечания", callback_data="homework:remark"),
            IKB(text="Принять", callback_data="homework:approve"),
        ]
    ]
)


labs_action_t = InlineKeyboardMarkup(
    inline_keyboard=[
        [IKB(text="Добавить", callback_data="labs:add")],
        [IKB(text="Проверить", callback_data="labs:check")],
    ]
)


labs_choice_t = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="№ 1", callback_data="labs:check_1"),
            IKB(text="№ 2", callback_data="labs:check_2"),
            IKB(text="№ 3", callback_data="labs:check_3"),
        ],
        [
            IKB(text="№ 4", callback_data="labs:check_4"),
            IKB(text="№ 5", callback_data="labs:check_5"),
            IKB(text="№ 6", callback_data="labs:check_6"),
        ],
    ]
)


labs_approve_or_remark = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="Принять", callback_data="labs:approve"),
            IKB(text="Замечания", callback_data="labs:remark"),
        ]
    ]
)


add_lab = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="№ 1", callback_data="labs:add_1"),
            IKB(text="№ 2", callback_data="labs:add_2"),
            IKB(text="№ 3", callback_data="labs:add_3"),
        ],
        [
            IKB(text="№ 4", callback_data="labs:add_4"),
            IKB(text="№ 5", callback_data="labs:add_5"),
            IKB(text="№ 6", callback_data="labs:add_6"),
        ],
    ]
)


replace_lab = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="Да", callback_data="labs:replace"),
            IKB(text="Нет", callback_data="labs:not_replace"),
        ]
    ]
)


students_actions = InlineKeyboardMarkup(
    inline_keyboard=[
        [IKB(text="Успеваемость", callback_data="students:progress")],
        [IKB(text="Список", callback_data="students:list")],
        [IKB(text="Обновить номера групп", callback_data="students:update")],
        [IKB(text="Статус ДЗ", callback_data="students:homework_status")],
        [
            IKB(text="Добавить", callback_data="students:add"),
            IKB(text="Удалить", callback_data="students:remove"),
        ],
    ]
)


update_groups = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="Весна", callback_data="students:sem_1"),
            IKB(text="Осень", callback_data="students:sem_2"),
        ]
    ]
)


stats = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(text="ДЗ № 1", callback_data="stats_hw_1"),
            IKB(text="ДЗ № 2", callback_data="stats_hw_2"),
        ]
    ]
)


hw_results_code = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            IKB(
                text="Код для формирования такого файла",
                callback_data="homework:template_file_code",
            )
        ]
    ]
)
