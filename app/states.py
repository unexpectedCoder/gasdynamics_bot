from aiogram.fsm.state import State, StatesGroup


class AddStudent(StatesGroup):
    name = State()
    group = State()
    mark_book = State()


class AddLab(StatesGroup):
    lab_exists = State()
    send_file = State()


class AssessHomework(StatesGroup):
    approve_or_remark = State()
    approving = State()
    remarking = State()


class AssessLab(StatesGroup):
    approve_or_remark = State()
    approve = State()
    remark = State()


class BotCheckHomework(StatesGroup):
    send_yaml = State()


class Registration(StatesGroup):
    mark_book = State()


class RemoveStudent(StatesGroup):
    mark_book = State()


class SendHomeworkReport(StatesGroup):
    send_pdf = State()


class SendLabReport(StatesGroup):
    send_pdf = State()


class HomeworkDeadline(StatesGroup):
    enter_date = State()


class ControlsChecking(StatesGroup):
    send_excel = State()
