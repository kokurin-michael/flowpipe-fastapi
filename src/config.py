from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_COOKIE_FILE = "cookies.txt"
DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_DATABASE_FILE = "flowpipe-database.db"


class Settings(BaseSettings):
    cookie_file: str = Field(
        default=DEFAULT_COOKIE_FILE,
        description="Путь к файлу cookies (относительный — от корня проекта).",
    )
    download_dir: str = Field(
        default=DEFAULT_DOWNLOAD_DIR,
        description="Папка загрузок (относительный путь — от корня проекта).",
    )
    database_file: str = Field(
        default=DEFAULT_DATABASE_FILE,
        description="Файл SQLite БД (относительный путь — от корня проекта).",
    )

    model_config = {
        "env_file": PROJECT_ROOT / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cookie_file_path(self) -> Path:
        """Путь к файлу cookies: относительный разрешается от корня проекта."""
        p = Path(self.cookie_file)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def download_dir_path(self) -> Path:
        """Папка загрузок: относительный путь разрешается от корня проекта."""
        p = Path(self.download_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def database_path(self) -> Path:
        """Путь к файлу БД: относительный разрешается от корня проекта (вне src)."""
        p = Path(self.database_file)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def database_url(self) -> str:
        """URL подключения к SQLite (строится из database_path)."""
        return f"sqlite:///{self.database_path}"


def get_settings() -> Settings:
    return Settings()
