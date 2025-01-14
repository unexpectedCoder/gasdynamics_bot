from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class AssessHomework(StatesGroup):
    choice = State()
    assessment = State()
    approving = State()
    remarking = State()


class CheckHomeYAML(StatesGroup):
    send_yaml = State()


class Registration(StatesGroup):
    mark_book = State()


class SendHomeworkReport(StatesGroup):
    send_pdf = State()
