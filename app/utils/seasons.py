from datetime import date


def get_current_semester():
    return 1 if 1 < date.today().month < 9 else 2
