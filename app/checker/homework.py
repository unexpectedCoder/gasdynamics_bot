import json
import numpy as np
import os
import yaml
import os
from datetime import date
from typing import IO

import config as cfg


def check_solution_yaml(file: IO, sem: int):
    sol = yaml.safe_load(file)

    variant = sol["Информация"]["Вариант"]
    sol_fname = os.path.join(
        cfg.get_dir(f"sem_{sem}_solutions"), f"{variant}.yml"
    )
    with open(sol_fname, "r", encoding="utf-8") as sf:
        correct_sol = yaml.safe_load(sf)

    if not _check_keys(sol, correct_sol):
        raise ValueError("incorrect solution dict keys")
        
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


def check_solution_json(file: IO, sem: int):
    sol = yaml.safe_load(file)

    variant = sol["Информация"]["Вариант"]
    sol_fname = os.path.join(
        cfg.get_dir(f"sem_{sem}_solutions"), f"{variant}.json"
    )
    with open(sol_fname, "r", encoding="utf-8") as sf:
        correct_sol = json.load(sf)

    if not _check_keys(sol, correct_sol):
        raise ValueError("incorrect solution dict keys")
    
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


def  _check_keys(sol: dict[dict], correct_sol: dict[dict]):
    sol_keys = sorted(sol.keys())
    correct_keys = sorted(correct_sol.keys())
    if sol_keys == correct_keys:
        for ck in correct_keys:
            correct_subkeys = sorted(correct_sol[ck].keys())
            subkeys = sorted(sol[ck].keys())
            if subkeys != correct_subkeys:
                return False
        return True
    return False


def _approx_eq(x, y):
    eps = cfg.get("rel_float_eq_accuracy")
    delta = 1e-8
    if isinstance(x, list):
        x, y = np.array(x), np.array(y)
        return np.all(np.abs((x - y) / (x + delta)) < eps)
    if isinstance(x, int) and isinstance(y, int):
        return x == y
    return abs((x - y) / (x + delta)) < eps


def all_right(checked: dict):
    d = checked.copy()
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
