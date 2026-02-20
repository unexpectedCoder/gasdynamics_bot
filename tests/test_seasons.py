from datetime import date

import pytest

from app.utils.seasons import rus_date

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
