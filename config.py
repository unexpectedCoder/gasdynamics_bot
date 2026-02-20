import json
from pathlib import Path

from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

import app.cache as cache


class Dirs(BaseModel):
    sem_1_solutions: Path = Path("solutions/1")
    sem_2_solutions: Path = Path("solutions/2")
    sem_1_json_to_check: Path = Path("/vault/sem_1_json_to_check")
    sem_2_json_to_check: Path = Path("/vault/sem_2_json_to_check")
    sem_1_homeworks_to_check: Path = Path("/vault/sem_1_homeworks_to_check")
    sem_1_checked_homeworks: Path = Path("/vault/sem_1_checked_homeworks")
    sem_2_homeworks_to_check: Path = Path("/vault/sem_2_homeworks_to_check")
    sem_2_checked_homeworks: Path = Path("/vault/sem_2_checked_homeworks")
    labs: Path = Path("/labs")
    labs_to_check: Path = Path("/vault/labs_to_check")
    checked_labs: Path = Path("/vault/checked_labs")
    controls: Path = Path("/vault/controls")


class Files(BaseModel):
    bot_speech: str = "app/files/scratches/bot_speech.json"
    hw_nozzle_template: str = "app/files/scratches/hw_nozzle_template.json"
    hw_wedge_template: str = "app/files/scratches/hw_wedge_template.json"
    home_nozzle: str = "app/files/home_nozzle.json"
    home_shock_wedge: str = "app/files/home_shock_wedge.json"
    files_links: str = "files_links.json"
    students: str = "secrets/students.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path("secrets/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Из .env
    token: str
    owner_id: int
    owner_firstname: str
    owner_middlename: str
    owner_lastname: str
    in_docker: bool = False

    # Числовые настройки
    rel_float_eq_accuracy: float = 0.001

    # Пути (могут быть переопределены через env-переменные вида DIRS__LABS=...)
    dirs: Dirs = Dirs()
    files: Files = Files()

    @computed_field
    @property
    def teachers(self) -> list[int]:
        return [self.owner_id]


settings = Settings()


def get_dir(key: str) -> Path:
    raw: Path = getattr(settings.dirs, key)
    if raw.is_absolute() and not settings.in_docker:
        # Вне контейнера: /vault/... → vault/...
        return Path(*raw.parts[1:])
    return raw


def get_file(key: str) -> Path:
    raw: str = getattr(settings.files, key)
    return Path(raw)


def get_answer(handler_name: str) -> str | None:
    return cache.answers.get(handler_name)


def get_link(key: str) -> str | None:
    return cache.files_links.get(key)


def set_link(key: str, link: str):
    cache.files_links[key] = link


# Startup
for _key in settings.dirs.model_fields:
    _dir = get_dir(_key)
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        print(ex)

with open(get_file("bot_speech"), "r", encoding="utf-8") as f:
    cache.bot_speech = json.load(f)
cache.answers = cache.bot_speech["answers"]
