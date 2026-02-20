from datetime import date


def rus_date(d: date):
    """Transform date `d` into `dd.mm.yyyy` format."""
    return d.strftime(r"%d.%m.%Y")
