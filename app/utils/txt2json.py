import json
from itertools import product


def txt2json(txt_path: str, json_path: str, primary_key: str):
    txt_data = []
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = [line for line in f.readlines()]
        for line in lines:
            s = line.split()[1:6]
            txt_data.append(
                {
                    "lastname": s[0],
                    "firstname": s[1],
                    "middlename": s[2],
                    "mark_book": s[3],
                    "group": s[4][-1],
                }
            )

    groups = sorted({d["group"] for d in txt_data})
    json_data = {g: {} for g in groups}
    for d, g in product(txt_data, groups):
        group = d.get("group", "")
        if not group or group != g:
            continue
        json_data[g][d[primary_key]] = d
        del d["group"]
    for g in json_data.values():
        for s in g.values():
            del s[primary_key]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    txt2json("students.txt", "students.json", "mark_book")
