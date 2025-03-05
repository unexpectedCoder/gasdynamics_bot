import json
import os
import yaml
from typing import Any


config: dict[str, Any] = None

files_links: dict[str, dict[str, str]] = None
bot_speech: dict[str, dict[str, str]] = None
answers: dict[str, str] = None


def init():
    global config
    global bot_speech
    global answers
    global files_links

    with open("settings.json", "r") as f:
        config = json.load(f)
    config["teachers"] = [int(os.getenv("OWNER_ID"))]

    for d in config["dirs"].values():
        try:
            if os.getenv("IN_DOCKER") and d.startswith("/"):
                os.makedirs(d)
            else:
                os.makedirs(os.path.join(*d.split("/")))
        except OSError as ex:
            print(ex)
    
    path = os.path.join(*config["files"]["bot_speech"].split("/"))
    with open(path, "r", encoding="utf-8") as f:
        bot_speech = yaml.safe_load(f)
    answers = bot_speech["answers"]

    files_links = {
        "labs": {
            "1": "",
            "2": "",
            "3": "",
            "4": "",
            "5": "",
            "6": ""
        },
        "yaml_templates": {
            "homework_nozzle": "",
            "homework_shock_wedge": ""
        }
    }


def get(key: str):
    return config.get(key, None)


def get_dir(key: str):
    dirs = config["dirs"]
    if os.getenv("IN_DOCKER") and dirs[key].startswith("/"):
        return os.path.join("/", *dirs[key].split("/"))
    return os.path.join(*dirs[key].split("/"))


def get_file(key: str):
    files = config["files"]
    return os.path.join(*files[key].split("/"))


def get_answer(handler_name: str):
    return answers.get(handler_name, None)


def get_lab_file_link(lab_n: int):
    return files_links["labs"][str(lab_n)]


def set_lab_file_link(lab_n: int, link: str):
    global files_links
    files_links["labs"][str(lab_n)] = link


def get_yaml_template_link(template_name: str):
    return files_links["yaml_templates"][template_name]


def set_yaml_template_link(template_name: str, link: str):
    global files_links
    files_links["yaml_templates"][template_name] = link


if __name__ == "__main__":
    init()
