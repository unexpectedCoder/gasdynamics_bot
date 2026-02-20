from datetime import date

import pytest

from app.database.models import (
    HomeworkNozzle,
    HomeworkShockWedge,
    Student,
)

# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------


class TestStudentGetName:
    def _make_student(self, firstname="Иван", middlename="Иванович", lastname="Иванов"):
        return Student(
            firstname=firstname,
            middlename=middlename,
            lastname=lastname,
            group="КА-401",
            mark_book="17М235",
            tg_id=None,
        )

    def test_get_name_returns_full_name(self):
        s = self._make_student()
        assert s.get_name() == "Иванов Иван Иванович"

    def test_get_name_order_lastname_first(self):
        s = self._make_student(
            firstname="Пётр", middlename="Петрович", lastname="Петров"
        )
        result = s.get_name()
        assert result.startswith("Петров")

    def test_get_name_contains_all_parts(self):
        s = self._make_student(
            firstname="Анна", middlename="Сергеевна", lastname="Смирнова"
        )
        result = s.get_name()
        assert "Анна" in result
        assert "Сергеевна" in result
        assert "Смирнова" in result

    def test_get_name_returns_string(self):
        s = self._make_student()
        assert isinstance(s.get_name(), str)

    def test_get_name_space_separated(self):
        s = self._make_student(
            firstname="Олег", middlename="Олегович", lastname="Олегов"
        )
        parts = s.get_name().split(" ")
        assert len(parts) == 3


class TestStudentStr:
    def _make_student(self, tg_id=None, mark_book="17М235"):
        return Student(
            firstname="Иван",
            middlename="Иванович",
            lastname="Иванов",
            group="КА-401",
            mark_book=mark_book,
            tg_id=tg_id,
        )

    def test_str_without_tg_id_contains_group(self):
        s = self._make_student(tg_id=None)
        assert "КА-401" in str(s)

    def test_str_without_tg_id_contains_mark_book(self):
        s = self._make_student(tg_id=None)
        assert "17М235" in str(s)

    def test_str_without_tg_id_contains_name(self):
        s = self._make_student(tg_id=None)
        result = str(s)
        assert "Иванов" in result
        assert "Иван" in result
        assert "Иванович" in result

    def test_str_without_tg_id_no_tg_link(self):
        s = self._make_student(tg_id=None)
        assert "tg://user" not in str(s)

    def test_str_with_tg_id_contains_tg_link(self):
        s = self._make_student(tg_id=987654321)
        result = str(s)
        assert "tg://user?id=987654321" in result

    def test_str_with_tg_id_contains_group(self):
        s = self._make_student(tg_id=111222333)
        assert "КА-401" in str(s)

    def test_str_with_tg_id_contains_mark_book(self):
        s = self._make_student(tg_id=111222333)
        assert "17М235" in str(s)

    def test_str_returns_string(self):
        s = self._make_student()
        assert isinstance(str(s), str)

    def test_str_with_zero_tg_id_treated_as_falsy(self):
        # tg_id=0 is falsy in Python, so no link should be present
        s = self._make_student(tg_id=0)
        assert "tg://user" not in str(s)

    def test_str_different_mark_books_differ(self):
        s1 = self._make_student(mark_book="17М001")
        s2 = self._make_student(mark_book="17М999")
        assert str(s1) != str(s2)


# ---------------------------------------------------------------------------
# HomeworkNozzle
# ---------------------------------------------------------------------------


class TestHomeworkNozzleStr:
    def _make_hw(self, variant=3):
        return HomeworkNozzle(
            variant=variant,
            p0="5000000.0",  # 5 МПа → round(5_000_000 * 1e-6, 2) = 5.0
            T0="2500",
            R="287.0",
            k="1.4",
            d_critic="0.15",
            area_ratio="8.5",
            d_chamber="1.2",
            alpha="40",
            beta="10",
            rel_propel_mass="0.75",
        )

    def test_str_contains_variant(self):
        hw = self._make_hw(variant=7)
        assert "7" in str(hw)

    def test_str_contains_temperature(self):
        hw = self._make_hw()
        assert "2500" in str(hw)

    def test_str_contains_gas_constant(self):
        hw = self._make_hw()
        assert "287" in str(hw)

    def test_str_contains_k(self):
        hw = self._make_hw()
        assert "1.4" in str(hw)

    def test_str_contains_d_critic(self):
        hw = self._make_hw()
        assert "0.15" in str(hw)

    def test_str_contains_area_ratio(self):
        hw = self._make_hw()
        assert "8.5" in str(hw)

    def test_str_contains_alpha(self):
        hw = self._make_hw()
        assert "40" in str(hw)

    def test_str_contains_beta(self):
        hw = self._make_hw()
        assert "10" in str(hw)

    def test_str_contains_propel_mass(self):
        hw = self._make_hw()
        assert "0.75" in str(hw)

    def test_str_pressure_converted_to_mpa(self):
        hw = self._make_hw()
        # p0=5_000_000 → round(5_000_000 * 1e-6, 2) = 5.0
        assert "5.0" in str(hw)

    def test_str_returns_string(self):
        hw = self._make_hw()
        assert isinstance(str(hw), str)

    def test_str_not_empty(self):
        hw = self._make_hw()
        assert len(str(hw)) > 0

    def test_str_mentions_variant_label(self):
        hw = self._make_hw(variant=1)
        assert "Вариант" in str(hw)

    def test_str_different_variants_differ(self):
        hw1 = self._make_hw(variant=1)
        hw2 = self._make_hw(variant=2)
        assert str(hw1) != str(hw2)


# ---------------------------------------------------------------------------
# HomeworkShockWedge
# ---------------------------------------------------------------------------


class TestHomeworkShockWedgeStr:
    def _make_hw(self, variant=5):
        return HomeworkShockWedge(
            variant=variant,
            mach="2.5",
            beta1="10.0",
            beta2="20.0",
            beta3="30.0",
        )

    def test_str_contains_variant(self):
        hw = self._make_hw(variant=5)
        assert "5" in str(hw)

    def test_str_contains_mach(self):
        hw = self._make_hw()
        assert "2.5" in str(hw)

    def test_str_contains_beta1(self):
        hw = self._make_hw()
        assert "10.0" in str(hw)

    def test_str_contains_beta2(self):
        hw = self._make_hw()
        assert "20.0" in str(hw)

    def test_str_contains_beta3(self):
        hw = self._make_hw()
        assert "30.0" in str(hw)

    def test_str_mentions_mach_label(self):
        hw = self._make_hw()
        result = str(hw)
        assert "M" in result or "Маха" in result or "скорость" in result.lower()

    def test_str_mentions_variant_label(self):
        hw = self._make_hw()
        assert "Вариант" in str(hw)

    def test_str_returns_string(self):
        hw = self._make_hw()
        assert isinstance(str(hw), str)

    def test_str_not_empty(self):
        hw = self._make_hw()
        assert len(str(hw)) > 0

    def test_str_contains_all_betas(self):
        hw = self._make_hw()
        result = str(hw)
        assert "10.0" in result
        assert "20.0" in result
        assert "30.0" in result

    def test_str_different_variants_differ(self):
        hw1 = self._make_hw(variant=1)
        hw2 = self._make_hw(variant=2)
        assert str(hw1) != str(hw2)

    def test_str_k_value_mentioned(self):
        hw = self._make_hw()
        result = str(hw)
        # The __str__ method hardcodes k=1.4 for air
        assert "1.4" in result
