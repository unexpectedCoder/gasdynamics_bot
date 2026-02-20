from app.utils.cancel_or import cancel_or


def test_cancel_or_appends_cancel():
    result = cancel_or("Введите номер зачётной книжки")
    assert result.endswith("/cancel")


def test_cancel_or_contains_original_text():
    text = "Пожалуйста, введите данные"
    result = cancel_or(text)
    assert text in result


def test_cancel_or_newline_separator():
    result = cancel_or("Некоторый текст")
    assert "\n/cancel" in result


def test_cancel_or_empty_string():
    result = cancel_or("")
    assert result == "\n/cancel"


def test_cancel_or_multiline_text():
    text = "Строка 1\nСтрока 2"
    result = cancel_or(text)
    assert result == "Строка 1\nСтрока 2\n/cancel"


def test_cancel_or_returns_string():
    result = cancel_or("любой текст")
    assert isinstance(result, str)


def test_cancel_or_exact_format():
    text = "Введите данные"
    result = cancel_or(text)
    assert result == f"{text}\n/cancel"


def test_cancel_or_special_characters():
    text = "Введите номер: 17М235 (кириллицей)"
    result = cancel_or(text)
    assert result == f"{text}\n/cancel"


def test_cancel_or_with_existing_slash_commands():
    text = "Используйте /help для помощи"
    result = cancel_or(text)
    assert result == f"{text}\n/cancel"
    assert result.count("/cancel") == 1
