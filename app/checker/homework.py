import os
import yaml
import os
from datetime import date
from typing import IO

import config as cfg


def check_solution(file: IO, sem: int):
    sol = yaml.safe_load(file)

    variant = sol["Информация"]["Вариант"]
    sol_fname = os.path.join(
        cfg.get_dir(f"sem_{sem}_solutions"), f"{variant}.yml"
    )
    with open(sol_fname, "r", encoding="utf-8") as sf:
        correct_sol = yaml.safe_load(sf)
        
    res = {}
    res["Информация"] = sol["Информация"]
    del sol["Информация"]
    del correct_sol["Информация"]
        
    zipped = zip(correct_sol.items(), sol.items())
    res.update({
        key: {
            k: _approx_eq(c[k], s[k]) for k in c
        }
        for ((key, c), (_, s)) in zipped
    })

    res["Проверка"] = {}
    res["Проверка"]["Дата проверки"] = date.today()
    res["Проверка"]["Результат"] = all_right(res)
    
    return res


def _approx_eq(x, y):
    return abs((x - y) / x) < cfg.get("rel_float_eq_accuracy")


def all_right(checked: dict):
    d = checked.copy()
    del d["Информация"]
    del d["Проверка"]
    return all([
        v
        for sub_dict in d.values()
        for v in sub_dict.values()
    ])


def whats_wrong(checked: dict[str, dict[str, str]]):
    return [
        f"{sec}/{k.rsplit(',', 1)[0]}"
        for sec in checked
        for k, v in checked[sec].items()
        if not v
    ]
