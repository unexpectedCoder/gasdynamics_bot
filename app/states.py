from aiogram.fsm.state import State, StatesGroup


class AddStudent(StatesGroup):
    name = State()
    group = State()
    mark_book = State()


class AddLab(StatesGroup):
    lab_exists = State()
    send_file = State()


class DeleteStudent(StatesGroup):
    mark_book = State()


class AssessHomework(StatesGroup):
    choice = State()
    assessment = State()
    approving = State()
    remarking = State()


class AssessLab(StatesGroup):
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


class SendLabReport(StatesGroup):
    lab_choice = State()
    send_pdf = State()


class HomeworkDeadline(StatesGroup):
    set_date = State()


class ProgressOf(StatesGroup):
    lastname = State()
