from datetime import date
from unittest.mock import patch

import pytest

from app.utils.seasons import get_current_semester, rus_date

# ---------------------------------------------------------------------------
# get_current_semester
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("month", [2, 3, 4, 5, 6, 7, 8])
def test_get_current_semester_returns_1_for_spring_months(month):
    mock_date = date(2024, month, 15)
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = mock_date
        result = get_current_semester()
    assert result == 1


@pytest.mark.parametrize("month", [9, 10, 11, 12, 1])
def test_get_current_semester_returns_2_for_autumn_months(month):
    year = 2024 if month != 1 else 2025
    mock_date = date(year, month, 15)
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = mock_date
        result = get_current_semester()
    assert result == 2


def test_get_current_semester_february_is_sem_1():
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = date(2024, 2, 1)
        assert get_current_semester() == 1


def test_get_current_semester_august_is_sem_1():
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = date(2024, 8, 31)
        assert get_current_semester() == 1


def test_get_current_semester_september_is_sem_2():
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = date(2024, 9, 1)
        assert get_current_semester() == 2


def test_get_current_semester_january_is_sem_2():
    with patch("app.utils.seasons.date") as mock_dt:
        mock_dt.today.return_value = date(2025, 1, 15)
        assert get_current_semester() == 2


def test_get_current_semester_returns_int():
    result = get_current_semester()
    assert isinstance(result, int)


def test_get_current_semester_is_1_or_2():
    result = get_current_semester()
    assert result in (1, 2)


# ---------------------------------------------------------------------------
# rus_date
# ---------------------------------------------------------------------------


def test_rus_date_basic_format():
    d = date(2024, 5, 9)
    assert rus_date(d) == "09.05.2024"


def test_rus_date_zero_padded_day():
    d = date(2024, 1, 3)
    result = rus_date(d)
    assert result.startswith("03.")


def test_rus_date_zero_padded_month():
    d = date(2024, 3, 15)
    result = rus_date(d)
    assert result[3:5] == "03"


def test_rus_date_year_at_the_end():
    d = date(2025, 11, 20)
    result = rus_date(d)
    assert result.endswith("2025")


def test_rus_date_exact_format():
    d = date(2023, 12, 31)
    assert rus_date(d) == "31.12.2023"


def test_rus_date_separator_is_dot():
    d = date(2024, 6, 1)
    result = rus_date(d)
    parts = result.split(".")
    assert len(parts) == 3


def test_rus_date_day_part():
    d = date(2024, 7, 25)
    result = rus_date(d)
    assert result[:2] == "25"


def test_rus_date_month_part():
    d = date(2024, 7, 25)
    result = rus_date(d)
    assert result[3:5] == "07"


def test_rus_date_year_part():
    d = date(2024, 7, 25)
    result = rus_date(d)
    assert result[6:] == "2024"


def test_rus_date_returns_string():
    assert isinstance(rus_date(date(2024, 1, 1)), str)


def test_rus_date_new_year():
    d = date(2024, 1, 1)
    assert rus_date(d) == "01.01.2024"


def test_rus_date_leap_year():
    d = date(2024, 2, 29)
    assert rus_date(d) == "29.02.2024"
