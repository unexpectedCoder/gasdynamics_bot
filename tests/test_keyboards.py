import pytest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.inline import (
    add_lab,
    examining,
    homework_approve_or_remark,
    homework_builder,
    homework_choice,
    homework_t,
    hw_results_code,
    labs_action,
    labs_action_t,
    labs_approve_or_remark,
    labs_choice_t,
    labwork,
    replace_lab,
    set_deadline,
    stats,
    students_actions,
)
from app.keyboards.keyboards import default_user, student, teacher

# ---------------------------------------------------------------------------
# Reply keyboards
# ---------------------------------------------------------------------------


class TestReplyKeyboards:
    def test_default_user_is_reply_keyboard(self):
        assert isinstance(default_user, ReplyKeyboardMarkup)

    def test_default_user_has_two_buttons(self):
        buttons = [btn for row in default_user.keyboard for btn in row]
        assert len(buttons) == 2

    def test_default_user_contains_registration_button(self):
        texts = [btn.text for row in default_user.keyboard for btn in row]
        assert any("регистрация" in t.lower() for t in texts)

    def test_default_user_contains_about_button(self):
        texts = [btn.text for row in default_user.keyboard for btn in row]
        assert any("бот" in t.lower() for t in texts)

    def test_default_user_resize_keyboard(self):
        assert default_user.resize_keyboard is True

    def test_student_is_reply_keyboard(self):
        assert isinstance(student, ReplyKeyboardMarkup)

    def test_student_has_three_rows(self):
        assert len(student.keyboard) == 3

    def test_student_contains_homework_button(self):
        texts = [btn.text for row in student.keyboard for btn in row]
        assert any("домашнее задание" in t.lower() for t in texts)

    def test_student_contains_labs_button(self):
        texts = [btn.text for row in student.keyboard for btn in row]
        assert any("лаборатор" in t.lower() for t in texts)

    def test_student_contains_progress_button(self):
        texts = [btn.text for row in student.keyboard for btn in row]
        assert any("успеваемость" in t.lower() for t in texts)

    def test_student_resize_keyboard(self):
        assert student.resize_keyboard is True

    def test_teacher_is_reply_keyboard(self):
        assert isinstance(teacher, ReplyKeyboardMarkup)

    def test_teacher_has_three_rows(self):
        assert len(teacher.keyboard) == 3

    def test_teacher_contains_control_button(self):
        texts = [btn.text for row in teacher.keyboard for btn in row]
        assert any("контрольн" in t.lower() for t in texts)

    def test_teacher_contains_labs_button(self):
        texts = [btn.text for row in teacher.keyboard for btn in row]
        assert any("лаборатор" in t.lower() for t in texts)

    def test_teacher_contains_students_button(self):
        texts = [btn.text for row in teacher.keyboard for btn in row]
        assert any("студент" in t.lower() for t in texts)

    def test_teacher_resize_keyboard(self):
        assert teacher.resize_keyboard is True


# ---------------------------------------------------------------------------
# homework_builder
# ---------------------------------------------------------------------------


class TestHomeworkBuilder:
    def test_returns_inline_keyboard_markup(self):
        kb = homework_builder(bot_approved=False)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_not_approved_has_bot_check_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:bot_check" in all_callbacks

    def test_approved_has_send_report_button(self):
        kb = homework_builder(bot_approved=True)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:send_report" in all_callbacks

    def test_approved_no_bot_check_button(self):
        kb = homework_builder(bot_approved=True)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:bot_check" not in all_callbacks

    def test_not_approved_no_send_report_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:send_report" not in all_callbacks

    def test_contains_description_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:description" in all_callbacks

    def test_contains_deadline_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:deadline" in all_callbacks

    def test_contains_get_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:get" in all_callbacks

    def test_contains_template_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:results_template" in all_callbacks

    def test_contains_mark_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:mark" in all_callbacks

    def test_contains_algo_button(self):
        kb = homework_builder(bot_approved=False)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "homework:algo" in all_callbacks

    def test_six_rows(self):
        kb = homework_builder(bot_approved=False)
        assert len(kb.inline_keyboard) == 6


# ---------------------------------------------------------------------------
# labwork
# ---------------------------------------------------------------------------


class TestLabwork:
    def test_returns_inline_keyboard_markup(self):
        kb = labwork([1, 2, 3])
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_buttons_count_matches_input(self):
        kb = labwork([1, 2, 3, 4])
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(all_buttons) == 4

    def test_callbacks_contain_lab_prefix(self):
        kb = labwork([1, 2, 3])
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert all(cb.startswith("lab:") for cb in all_callbacks)

    def test_callbacks_contain_correct_numbers(self):
        numbers = [2, 4, 6]
        kb = labwork(numbers)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        for n in numbers:
            assert f"lab:{n}" in all_callbacks

    def test_empty_list_returns_empty_keyboard(self):
        kb = labwork([])
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert all_buttons == []

    def test_single_lab(self):
        kb = labwork([5])
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(all_buttons) == 1
        assert all_buttons[0].callback_data == "lab:5"


# ---------------------------------------------------------------------------
# labs_action
# ---------------------------------------------------------------------------


class TestLabsAction:
    def test_returns_inline_keyboard_markup(self):
        kb = labs_action(3)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_contains_description_callback(self):
        kb = labs_action(3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "lab:description_3" in all_callbacks

    def test_contains_send_callback(self):
        kb = labs_action(3)
        all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "lab:send_3" in all_callbacks

    def test_lab_index_is_included_in_callbacks(self):
        for i in [1, 4, 6]:
            kb = labs_action(i)
            all_callbacks = [
                btn.callback_data for row in kb.inline_keyboard for btn in row
            ]
            assert f"lab:description_{i}" in all_callbacks
            assert f"lab:send_{i}" in all_callbacks

    def test_two_buttons(self):
        kb = labs_action(1)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(all_buttons) == 2


# ---------------------------------------------------------------------------
# Static inline keyboards
# ---------------------------------------------------------------------------


class TestStaticInlineKeyboards:
    def _all_callbacks(self, kb: InlineKeyboardMarkup) -> list[str]:
        return [btn.callback_data for row in kb.inline_keyboard for btn in row]

    def test_examining_is_inline_markup(self):
        assert isinstance(examining, InlineKeyboardMarkup)

    def test_examining_has_homework_and_rk(self):
        cbs = self._all_callbacks(examining)
        assert "exam:homework" in cbs
        assert "exam:rk" in cbs

    def test_homework_t_is_inline_markup(self):
        assert isinstance(homework_t, InlineKeyboardMarkup)

    def test_homework_t_has_check_button(self):
        cbs = self._all_callbacks(homework_t)
        assert "homework:check" in cbs

    def test_homework_t_has_set_deadline_button(self):
        cbs = self._all_callbacks(homework_t)
        assert "homework:set_deadline" in cbs

    def test_homework_choice_has_two_options(self):
        cbs = self._all_callbacks(homework_choice)
        assert "homework:check_1" in cbs
        assert "homework:check_2" in cbs

    def test_homework_approve_or_remark_has_both_actions(self):
        cbs = self._all_callbacks(homework_approve_or_remark)
        assert "homework:remark" in cbs
        assert "homework:approve" in cbs

    def test_labs_action_t_has_add_and_check(self):
        cbs = self._all_callbacks(labs_action_t)
        assert "labs:add" in cbs
        assert "labs:check" in cbs

    def test_labs_choice_t_has_six_labs(self):
        cbs = self._all_callbacks(labs_choice_t)
        for i in range(1, 7):
            assert f"labs:check_{i}" in cbs

    def test_labs_approve_or_remark_has_both_actions(self):
        cbs = self._all_callbacks(labs_approve_or_remark)
        assert "labs:approve" in cbs
        assert "labs:remark" in cbs

    def test_add_lab_has_six_labs(self):
        cbs = self._all_callbacks(add_lab)
        for i in range(1, 7):
            assert f"labs:add_{i}" in cbs

    def test_replace_lab_has_yes_and_no(self):
        cbs = self._all_callbacks(replace_lab)
        assert "labs:replace" in cbs
        assert "labs:not_replace" in cbs

    def test_students_actions_has_all_actions(self):
        cbs = self._all_callbacks(students_actions)
        assert "students:progress" in cbs
        assert "students:list" in cbs
        assert "students:add" in cbs
        assert "students:remove" in cbs

    def test_stats_has_two_homework_options(self):
        cbs = self._all_callbacks(stats)
        assert "stats_hw_nozzle" in cbs
        assert "stats_hw_shock_wedge" in cbs

    def test_hw_results_code_has_template_file_code(self):
        cbs = self._all_callbacks(hw_results_code)
        assert "homework:template_file_code" in cbs

    def test_set_deadline_has_homework_and_labs(self):
        cbs = self._all_callbacks(set_deadline)
        assert "set_deadline_homework" in cbs
        assert "set_deadline_labs" in cbs
