from datetime import date


def get_current_semester():
    """Returns current semester."""
    return 1 if 1 < date.today().month < 9 else 2


def rus_date(d: date):
    """Transform date `d` into `dd.mm.yyyy` format."""
    return f"{d.day}.{d.month:02}.{d.year}"
