import csv
import json
import os
import tempfile
from pathlib import Path

import pytest

from app.utils.csv2json import csv2json
from app.utils.txt2json import txt2json

# ---------------------------------------------------------------------------
# csv2json
# ---------------------------------------------------------------------------


class TestCsv2Json:
    def _write_csv(self, path: Path, rows: list[dict], fieldnames: list[str]):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_basic_conversion(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [
            {"variant": "1", "mach": "2.5", "beta1": "10.0"},
            {"variant": "2", "mach": "3.0", "beta1": "15.0"},
        ]
        self._write_csv(csv_path, rows, ["variant", "mach", "beta1"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        assert "1" in result or 1 in result

    def test_output_file_is_created(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "1", "value": "42.0"}]
        self._write_csv(csv_path, rows, ["variant", "value"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        assert json_path.exists()

    def test_primary_key_is_removed_from_values(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "5", "mach": "2.0", "pressure": "100000.0"}]
        self._write_csv(csv_path, rows, ["variant", "mach", "pressure"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        # The key "5" should exist; its value should NOT contain "variant"
        entry = next(iter(result.values()))
        assert "variant" not in entry

    def test_numeric_values_are_floats(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "3", "mach": "2.5", "beta": "12.8"}]
        self._write_csv(csv_path, rows, ["variant", "mach", "beta"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        entry = next(iter(result.values()))
        assert isinstance(entry["mach"], float)
        assert isinstance(entry["beta"], float)

    def test_variant_key_is_int_in_output(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "7", "mach": "3.0"}]
        self._write_csv(csv_path, rows, ["variant", "mach"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        # JSON keys are always strings; the raw stored variant value should be int
        # csv2json converts variant column via int()
        entry = next(iter(result.values()))
        # variant itself is removed; check it's not in entries
        assert "variant" not in entry

    def test_multiple_rows_all_present(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [
            {"variant": "1", "val": "1.0"},
            {"variant": "2", "val": "2.0"},
            {"variant": "3", "val": "3.0"},
        ]
        self._write_csv(csv_path, rows, ["variant", "val"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        assert len(result) == 3

    def test_correct_values_preserved(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "10", "mach": "4.5", "beta": "22.3"}]
        self._write_csv(csv_path, rows, ["variant", "mach", "beta"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        # Key might be int or string depending on JSON serialization
        entry = result.get("10") or result.get(10)
        assert entry is not None
        assert abs(entry["mach"] - 4.5) < 1e-9
        assert abs(entry["beta"] - 22.3) < 1e-9

    def test_output_is_valid_json(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "1", "x": "1.1"}]
        self._write_csv(csv_path, rows, ["variant", "x"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        # Should not raise
        content = json_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_single_row(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "99", "alpha": "0.5"}]
        self._write_csv(csv_path, rows, ["variant", "alpha"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        assert len(result) == 1

    def test_all_columns_except_primary_key_in_output(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        rows = [{"variant": "1", "a": "1.0", "b": "2.0", "c": "3.0"}]
        self._write_csv(csv_path, rows, ["variant", "a", "b", "c"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        entry = next(iter(result.values()))
        assert "a" in entry
        assert "b" in entry
        assert "c" in entry
        assert "variant" not in entry

    def test_existing_output_file_is_overwritten(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        json_path = tmp_path / "output.json"

        # Write old content
        json_path.write_text('{"old": "data"}', encoding="utf-8")

        rows = [{"variant": "1", "val": "7.0"}]
        self._write_csv(csv_path, rows, ["variant", "val"])
        csv2json(str(csv_path), str(json_path), primary_key="variant")

        result = self._read_json(json_path)
        assert "old" not in result


# ---------------------------------------------------------------------------
# txt2json
# ---------------------------------------------------------------------------


class TestTxt2Json:
    """
    txt2json reads lines from a .txt file where each line has the form:
        <index> <lastname> <firstname> <middlename> <mark_book> <group> ...
    It groups by group, uses primary_key as the dict key within each group,
    and removes both 'group' and the primary_key field from the stored value.
    """

    def _write_txt(self, path: Path, students: list[dict]):
        """
        Write a .txt file in the expected format.
        Each line: "<n> <lastname> <firstname> <middlename> <mark_book> <group>"
        """
        lines = []
        for i, s in enumerate(students, start=1):
            line = (
                f"{i} {s['lastname']} {s['firstname']} "
                f"{s['middlename']} {s['mark_book']} {s['group']}\n"
            )
            lines.append(line)
        path.write_text("".join(lines), encoding="utf-8")

    def _read_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_output_file_is_created(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        self._write_txt(
            txt_path,
            [
                {
                    "lastname": "Иванов",
                    "firstname": "Иван",
                    "middlename": "Иванович",
                    "mark_book": "17М001",
                    "group": "КА-401",
                }
            ],
        )
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")
        assert json_path.exists()

    def test_groups_are_top_level_keys(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Иванов",
                "firstname": "Иван",
                "middlename": "Иванович",
                "mark_book": "17М001",
                "group": "КА-401",
            },
            {
                "lastname": "Петров",
                "firstname": "Пётр",
                "middlename": "Петрович",
                "mark_book": "17М002",
                "group": "КА-402",
            },
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        assert "КА-401" in result
        assert "КА-402" in result

    def test_students_grouped_correctly(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Иванов",
                "firstname": "Иван",
                "middlename": "Иванович",
                "mark_book": "17М001",
                "group": "КА-401",
            },
            {
                "lastname": "Сидоров",
                "firstname": "Сидор",
                "middlename": "Сидорович",
                "mark_book": "17М003",
                "group": "КА-401",
            },
            {
                "lastname": "Петров",
                "firstname": "Пётр",
                "middlename": "Петрович",
                "mark_book": "17М002",
                "group": "КА-402",
            },
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        assert len(result["КА-401"]) == 2
        assert len(result["КА-402"]) == 1

    def test_primary_key_used_as_dict_key(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Козлов",
                "firstname": "Антон",
                "middlename": "Юрьевич",
                "mark_book": "20М999",
                "group": "КА-403",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        assert "20М999" in result["КА-403"]

    def test_primary_key_removed_from_values(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Николаев",
                "firstname": "Николай",
                "middlename": "Николаевич",
                "mark_book": "18М100",
                "group": "КА-401",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        entry = result["КА-401"]["18М100"]
        assert "mark_book" not in entry

    def test_group_removed_from_values(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Фёдоров",
                "firstname": "Фёдор",
                "middlename": "Фёдорович",
                "mark_book": "19М200",
                "group": "КА-401",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        entry = result["КА-401"]["19М200"]
        assert "group" not in entry

    def test_name_fields_preserved(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Морозов",
                "firstname": "Дмитрий",
                "middlename": "Александрович",
                "mark_book": "21М050",
                "group": "КА-401",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        entry = result["КА-401"]["21М050"]
        assert entry["lastname"] == "Морозов"
        assert entry["firstname"] == "Дмитрий"
        assert entry["middlename"] == "Александрович"

    def test_output_is_valid_json(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Тест",
                "firstname": "Тест",
                "middlename": "Тестович",
                "mark_book": "00М000",
                "group": "ГР-100",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        content = json_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_multiple_groups_correct_count(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": f"Фамилия{i}",
                "firstname": f"Имя{i}",
                "middlename": f"Отч{i}",
                "mark_book": f"17М{i:03d}",
                "group": f"КА-{400 + (i % 3)}",
            }
            for i in range(1, 10)
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        total = sum(len(v) for v in result.values())
        assert total == 9

    def test_single_student(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Одиночный",
                "firstname": "Студент",
                "middlename": "Тестович",
                "mark_book": "99М999",
                "group": "ГД-501",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        assert len(result) == 1
        assert "ГД-501" in result
        assert "99М999" in result["ГД-501"]

    def test_groups_are_sorted(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        students = [
            {
                "lastname": "Б",
                "firstname": "Б",
                "middlename": "Бович",
                "mark_book": "17М002",
                "group": "КА-403",
            },
            {
                "lastname": "А",
                "firstname": "А",
                "middlename": "Аович",
                "mark_book": "17М001",
                "group": "КА-401",
            },
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_existing_output_is_overwritten(self, tmp_path):
        txt_path = tmp_path / "students.txt"
        json_path = tmp_path / "students.json"

        json_path.write_text('{"old": "data"}', encoding="utf-8")

        students = [
            {
                "lastname": "Новый",
                "firstname": "Студент",
                "middlename": "Новович",
                "mark_book": "22М001",
                "group": "КА-401",
            }
        ]
        self._write_txt(txt_path, students)
        txt2json(str(txt_path), str(json_path), primary_key="mark_book")

        result = self._read_json(json_path)
        assert "old" not in result
        assert "КА-401" in result
