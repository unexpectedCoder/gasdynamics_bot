import json
import os
import yaml
from dotenv import load_dotenv
from typing import Any


config: dict[str, Any] = None

bot_speech: dict[str, dict[str, str]] = None
answers: dict[str, str] = None


def init():
    global config
    global bot_speech
    global answers

    load_dotenv()

    with open("settings.json", "r") as f:
        config = json.load(f)
    config["teachers"] = [int(os.getenv("OWNER_ID"))]

    for d in config["dirs"].values():
        try:
            os.mkdir(d)
        except OSError as ex:
            print(ex)
    
    path = os.path.join(*config["files"]["bot_speech"].split("/"))
    with open(path, "r", encoding="utf-8") as f:
        bot_speech = yaml.safe_load(f)
    answers = bot_speech["answers"]


def get(key: str):
    return config.get(key, None)


def get_dir(key: str):
    dirs = config["dirs"]
    return os.path.join(*dirs[key].split("/"))


def get_file(key: str):
    files = config["files"]
    return os.path.join(*files[key].split("/"))


def get_answer(handler_name: str):
    return answers.get(handler_name, None)


if __name__ == "__main__":
    init()
