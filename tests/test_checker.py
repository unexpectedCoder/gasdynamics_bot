import json
import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.checker.homework import _approx_eq, _check_keys, all_right, whats_wrong

# ---------------------------------------------------------------------------
# _approx_eq
# ---------------------------------------------------------------------------


class TestApproxEq:
    def test_equal_floats(self):
        assert _approx_eq(1.0, 1.0) is True

    def test_close_floats_within_tolerance(self):
        # default tolerance is 0.001 (0.1%)
        assert _approx_eq(1.0, 1.0005) is True

    def test_floats_outside_tolerance(self):
        assert _approx_eq(1.0, 1.01) is False

    def test_equal_ints(self):
        assert _approx_eq(5, 5) is True

    def test_unequal_ints(self):
        assert _approx_eq(5, 6) is False

    def test_negative_floats_close(self):
        assert _approx_eq(-2.0, -2.001) is True

    def test_negative_floats_far(self):
        assert _approx_eq(-2.0, -2.1) is False

    def test_lists_equal(self):
        # _approx_eq on lists returns a numpy scalar, so use bool()
        result = _approx_eq([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert bool(result) is True

    def test_lists_close(self):
        result = _approx_eq([1.0, 2.0], [1.0005, 2.0005])
        assert bool(result) is True

    def test_lists_one_element_off(self):
        result = _approx_eq([1.0, 2.0, 3.0], [1.0, 2.0, 4.0])
        assert bool(result) is False

    def test_zero_numerator_float(self):
        # both near zero — delta guard prevents division-by-zero
        result = _approx_eq(0.0, 0.0)
        assert bool(result) is True

    def test_large_equal_values(self):
        assert _approx_eq(1_000_000.0, 1_000_000.0) is True

    def test_large_close_values(self):
        assert _approx_eq(1_000_000.0, 1_000_500.0) is True

    def test_large_far_values(self):
        assert _approx_eq(1_000_000.0, 1_100_000.0) is False

    def test_single_element_list(self):
        result = _approx_eq([42.0], [42.0])
        assert bool(result) is True

    def test_int_zero_equal(self):
        assert _approx_eq(0, 0) is True

    def test_int_zero_unequal(self):
        assert _approx_eq(0, 1) is False

    def test_returns_truthy_for_equal_floats(self):
        result = _approx_eq(1.0, 1.0)
        assert result  # truthy check (works for both bool and numpy bool_)

    def test_returns_falsy_for_unequal_floats(self):
        result = _approx_eq(1.0, 2.0)
        assert not result

    def test_returns_bool_for_ints(self):
        result = _approx_eq(3, 3)
        assert isinstance(result, bool)

    def test_list_returns_numpy_or_bool(self):
        # For lists the return type is numpy.bool_ (from np.all)
        result = _approx_eq([1.0], [1.0])
        assert isinstance(result, (bool, np.bool_))


# ---------------------------------------------------------------------------
# _check_keys
# ---------------------------------------------------------------------------


class TestCheckKeys:
    def _make_dicts(self, structure: dict) -> tuple[dict, dict]:
        """Build two identical-structure dicts from a {section: [keys]} map."""
        sol = {sec: {k: 1 for k in keys} for sec, keys in structure.items()}
        correct = {sec: {k: 1 for k in keys} for sec, keys in structure.items()}
        return sol, correct

    def test_identical_structures(self):
        sol, correct = self._make_dicts(
            {"Раздел 1": ["a", "b"], "Раздел 2": ["c", "d"]}
        )
        assert _check_keys(sol, correct) is True

    def test_missing_top_level_key(self):
        sol = {"Раздел 1": {"a": 1}}
        correct = {"Раздел 1": {"a": 1}, "Раздел 2": {"b": 1}}
        assert _check_keys(sol, correct) is False

    def test_extra_top_level_key(self):
        sol = {"Раздел 1": {"a": 1}, "Раздел 2": {"b": 1}, "Раздел 3": {"c": 1}}
        correct = {"Раздел 1": {"a": 1}, "Раздел 2": {"b": 1}}
        assert _check_keys(sol, correct) is False

    def test_missing_subkey(self):
        sol = {"Раздел 1": {"a": 1}}
        correct = {"Раздел 1": {"a": 1, "b": 1}}
        assert _check_keys(sol, correct) is False

    def test_extra_subkey(self):
        sol = {"Раздел 1": {"a": 1, "b": 1, "c": 1}}
        correct = {"Раздел 1": {"a": 1, "b": 1}}
        assert _check_keys(sol, correct) is False

    def test_subkey_name_differs(self):
        sol = {"Раздел 1": {"x": 1}}
        correct = {"Раздел 1": {"y": 1}}
        assert _check_keys(sol, correct) is False

    def test_empty_dicts(self):
        assert _check_keys({}, {}) is True

    def test_key_order_does_not_matter(self):
        sol = {"B": {"b": 1}, "A": {"a": 1}}
        correct = {"A": {"a": 1}, "B": {"b": 1}}
        assert _check_keys(sol, correct) is True

    def test_subkey_order_does_not_matter(self):
        sol = {"Раздел": {"z": 1, "a": 1}}
        correct = {"Раздел": {"a": 1, "z": 1}}
        assert _check_keys(sol, correct) is True

    def test_single_section_single_key(self):
        sol = {"Данные": {"value": 42}}
        correct = {"Данные": {"value": 0}}
        assert _check_keys(sol, correct) is True


# ---------------------------------------------------------------------------
# all_right
# ---------------------------------------------------------------------------


class TestAllRight:
    def _checked(self, results: dict, include_info: bool = True) -> dict:
        """
        Build a checked dict as check_solution_json would return.
        ``results`` maps section -> {key: bool}.
        """
        d = {}
        if include_info:
            d["Информация"] = {"Вариант": 1}
        d.update(results)
        d["Проверка"] = {"Дата проверки": date.today(), "Результат": False}
        return d

    def test_all_true(self):
        checked = self._checked(
            {"1": {"a, ед": True, "b, ед": True}, "2": {"c, ед": True}}
        )
        assert all_right(checked) is True

    def test_one_false(self):
        checked = self._checked(
            {"1": {"a, ед": True, "b, ед": False}, "2": {"c, ед": True}}
        )
        assert all_right(checked) is False

    def test_all_false(self):
        checked = self._checked({"1": {"a, ед": False, "b, ед": False}})
        assert all_right(checked) is False

    def test_empty_sections(self):
        checked = self._checked({})
        assert all_right(checked) is True

    def test_does_not_include_проверка_section(self):
        # Проверка section is deleted before evaluation — should not raise
        checked = self._checked({"1": {"x, м": True}})
        assert all_right(checked) is True

    def test_single_section_single_key_true(self):
        checked = self._checked({"Секция": {"ключ, ед": True}})
        assert all_right(checked) is True

    def test_single_section_single_key_false(self):
        checked = self._checked({"Секция": {"ключ, ед": False}})
        assert all_right(checked) is False

    def test_multiple_sections_one_false(self):
        checked = self._checked(
            {
                "Секция А": {"a, м/с": True, "b, Па": True},
                "Секция Б": {"c, К": True, "d, кг": False},
            }
        )
        assert all_right(checked) is False

    def test_returns_bool(self):
        checked = self._checked({"1": {"x, ед": True}})
        assert isinstance(all_right(checked), bool)

    def test_does_not_mutate_input(self):
        checked = self._checked({"1": {"x, ед": True}})
        original_keys = set(checked.keys())
        all_right(checked)
        assert set(checked.keys()) == original_keys


# ---------------------------------------------------------------------------
# whats_wrong
# ---------------------------------------------------------------------------


class TestWhatsWrong:
    """
    whats_wrong iterates ALL sections in the checked dict (including
    "Информация" and "Проверка").

    "Информация" values are truthy (variant number, etc.) so they won't
    appear in the output.

    "Проверка" contains {"Дата проверки": <date>, "Результат": <bool>}.
    When "Результат" is False, "Проверка/Результат" IS included in the
    output — this is the actual runtime behaviour of the function.

    The helper _checked_with_result() sets "Результат" correctly to avoid
    it appearing as a spurious "wrong" entry when we want to test only the
    subject-matter fields.
    """

    def _checked_with_result(self, sections: dict, result_flag: bool) -> dict:
        """Build a realistic checked dict, setting Результат explicitly."""
        d = {"Информация": {"Вариант": 1}}
        d.update(sections)
        d["Проверка"] = {"Дата проверки": date.today(), "Результат": result_flag}
        return d

    # --- tests where all answers are correct (Результат=True) ---

    def test_no_errors_returns_empty_list(self):
        checked = self._checked_with_result(
            {"1": {"число Маха, -": True, "давление, Па": True}},
            result_flag=True,
        )
        assert whats_wrong(checked) == []

    def test_all_true_sections_empty_list(self):
        checked = self._checked_with_result(
            {
                "1": {"a, м": True},
                "2": {"b, К": True, "c, Па": True},
            },
            result_flag=True,
        )
        assert whats_wrong(checked) == []

    def test_returns_list(self):
        checked = self._checked_with_result({"1": {"a, м": True}}, result_flag=True)
        assert isinstance(whats_wrong(checked), list)

    # --- tests where some answers are wrong (Результат=False) ---
    # "Проверка/Результат" will appear because Результат is False.

    def test_one_wrong_field_plus_проверка(self):
        checked = self._checked_with_result(
            {"1": {"число Маха, -": False, "давление, Па": True}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        # Expect both the wrong subject field AND "Проверка/Результат"
        assert "1/число Маха" in result
        assert "Проверка/Результат" in result
        assert len(result) == 2

    def test_multiple_wrong_fields(self):
        checked = self._checked_with_result(
            {
                "1": {"a, м": False, "b, с": True},
                "2": {"c, К": False, "d, Па": False},
            },
            result_flag=False,
        )
        result = whats_wrong(checked)
        # 3 wrong subject fields + "Проверка/Результат"
        assert len(result) == 4

    def test_all_wrong(self):
        checked = self._checked_with_result(
            {"Раздел": {"x, ед": False, "y, ед": False}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        # 2 subject fields + "Проверка/Результат"
        assert len(result) == 3

    def test_error_path_format(self):
        """Key format: 'section/key_without_last_comma_unit_part'."""
        checked = self._checked_with_result(
            {"Секция 1": {"скорость, м/с": False}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        assert "Секция 1/скорость" in result

    def test_true_values_not_included(self):
        checked = self._checked_with_result(
            {"1": {"a, ед": True, "b, ед": False, "c, ед": True}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        assert all("a" not in r and "c" not in r for r in result)
        assert any("b" in r for r in result)

    def test_info_section_skipped_when_all_ok(self):
        """'Информация' values are truthy ints/strings — must not appear."""
        checked = self._checked_with_result({"1": {"x, м": True}}, result_flag=True)
        result = whats_wrong(checked)
        assert not any("Информация" in r for r in result)

    def test_key_stripping_on_comma(self):
        """whats_wrong strips the last ', unit' part via rsplit(',', 1)[0]."""
        checked = self._checked_with_result(
            {"2": {"число Маха, -": False}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        assert "2/число Маха" in result

    def test_проверка_результат_appears_when_false(self):
        """
        Documents the actual behaviour: because whats_wrong iterates ALL
        sections, including "Проверка", a False "Результат" value is treated
        as a wrong answer and appears in the output.
        """
        checked = self._checked_with_result(
            {"1": {"x, ед": True}},
            result_flag=False,
        )
        result = whats_wrong(checked)
        # This is the current (arguably surprising) behaviour of the function.
        assert "Проверка/Результат" in result

    def test_empty_subject_sections_no_wrong(self):
        """No subject sections → only Результат could appear if False."""
        checked = self._checked_with_result({}, result_flag=True)
        assert whats_wrong(checked) == []


# ---------------------------------------------------------------------------
# check_solution_json (integration — uses real file I/O)
# ---------------------------------------------------------------------------


class TestCheckSolutionJson:
    """
    Tests for check_solution_json using temporary files.
    The function signature is check_solution_json(file: IO, sem: int).
    It reads cfg.get_dir(f"sem_{sem}_solutions") / f"{variant}.json".
    """

    CORRECT_SOL = {
        "Информация": {"Вариант": 42},
        "1": {
            "число Маха, -": 2.5,
            "давление, Па": 100000.0,
        },
        "2": {
            "температура, К": 300.0,
        },
    }

    STUDENT_SOL_CORRECT = {
        "Информация": {"Вариант": 42},
        "1": {
            "число Маха, -": 2.5,
            "давление, Па": 100000.0,
        },
        "2": {
            "температура, К": 300.0,
        },
    }

    STUDENT_SOL_WRONG = {
        "Информация": {"Вариант": 42},
        "1": {
            "число Маха, -": 999.0,  # wrong
            "давление, Па": 100000.0,
        },
        "2": {
            "температура, К": 300.0,
        },
    }

    STUDENT_SOL_BAD_KEYS = {
        "Информация": {"Вариант": 42},
        "1": {
            "несуществующий ключ, -": 2.5,
        },
    }

    def _write_json(self, path: Path, data: dict):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _patch_get_dir(self, solutions_dir: Path):
        """Return a patcher that makes cfg.get_dir return solutions_dir."""
        return patch(
            "app.checker.homework.cfg.get_dir",
            return_value=solutions_dir,
        )

    def test_correct_solution_returns_all_right(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student.json"
        self._write_json(student_file, self.STUDENT_SOL_CORRECT)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert result["Проверка"]["Результат"] is True

    def test_wrong_value_returns_not_all_right(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student_wrong.json"
        self._write_json(student_file, self.STUDENT_SOL_WRONG)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert result["Проверка"]["Результат"] is False

    def test_bad_keys_raises_value_error(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "bad_keys.json"
        self._write_json(student_file, self.STUDENT_SOL_BAD_KEYS)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                with pytest.raises(ValueError, match="incorrect solution dict keys"):
                    check_solution_json(f, sem=1)

    def test_result_contains_info_section(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student.json"
        self._write_json(student_file, self.STUDENT_SOL_CORRECT)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert "Информация" in result
        assert result["Информация"]["Вариант"] == 42

    def test_result_contains_check_date(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student.json"
        self._write_json(student_file, self.STUDENT_SOL_CORRECT)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert result["Проверка"]["Дата проверки"] == date.today()

    def test_result_keys_match_correct_solution_sections(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student.json"
        self._write_json(student_file, self.STUDENT_SOL_CORRECT)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert "1" in result
        assert "2" in result

    def test_correct_section_values_are_true(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student.json"
        self._write_json(student_file, self.STUDENT_SOL_CORRECT)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        for key in ("число Маха, -", "давление, Па"):
            assert bool(result["1"][key]) is True
        assert bool(result["2"]["температура, К"]) is True

    def test_wrong_field_value_is_false(self, tmp_path):
        solutions_dir = tmp_path / "solutions"
        solutions_dir.mkdir()
        self._write_json(solutions_dir / "42.json", self.CORRECT_SOL)

        student_file = tmp_path / "student_wrong.json"
        self._write_json(student_file, self.STUDENT_SOL_WRONG)

        with self._patch_get_dir(solutions_dir):
            from app.checker.homework import check_solution_json

            with open(student_file, "r", encoding="utf-8") as f:
                result = check_solution_json(f, sem=1)

        assert bool(result["1"]["число Маха, -"]) is False
        # Correct field must still be True
        assert bool(result["1"]["давление, Па"]) is True
