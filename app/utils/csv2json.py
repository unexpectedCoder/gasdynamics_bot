import csv
import json


def csv2json(csv_path: str, json_path: str, primary_key: str):
    csv_data = []
    with open(csv_path, "r") as f:
        data = csv.DictReader(f)
        for d in data:
            for k in d:
                d[k] = float(d[k])
            d["variant"] = int(d["variant"])
            csv_data.append(d)
            
    json_data = {}
    for d in csv_data:
        json_data[d[primary_key]] = d
    for d in json_data.values():
        del d[primary_key]

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)


if __name__ == "__main__":
    import os


    csv2json(
        os.path.join(*"app/files/home_shock_wedge.csv".split("/")),
        os.path.join(*"app/files/home_shock_wedge.json".split("/")),
        "variant"
    )
