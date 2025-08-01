import json
import os
import yaml
from enum import Enum
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
        },
        "word_templates": {
            "homework": "",
            "labwork": "",
            "coursework": ""
        },
        "video": {
            "figures": "",
            "tables": "",
            "equations": "",
            "bibliography": "",
            "code": ""
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


class Lab(Enum):
    LAB_1 = "labs:1"
    LAB_2 = "labs:2"
    LAB_3 = "labs:3"
    LAB_4 = "labs:4"
    LAB_5 = "labs:5"
    LAB_6 = "labs:6"


class YAMLTemplate(Enum):
    HW_1 = "yaml_templates:homework_nozzle",
    HW_2 = "yaml_templates:homework_shock_wedge"


class WordTemplate(Enum):
    HOMEWORK = "word_templates:homework"
    LABWORK = "word_templates:labwork"
    COURSEWORK = "word_templates:coursework"


class Video(Enum):
    FIGURES = "video:figures"
    TABLES = "video:tables"
    EQUATIONS_WORD = "video:equations_word"
    EQUATIONS_MATHTYPE = "video:equations_mathtype"
    BIBLIOGRAPHY = "video:bibliography"
    CODE = "video:code"


AnyConfEnum = Lab | WordTemplate | YAMLTemplate | Video


def get_link(tmpl: AnyConfEnum):
    section, filename = tmpl.value.rsplit(":", maxsplit=1)
    return files_links[section][filename]


def set_link(tmpl: AnyConfEnum, link: str):
    global files_links
    section, filename = tmpl.value.rsplit(":", maxsplit=1)
    files_links[section][filename] = link


if __name__ == "__main__":
    init()
