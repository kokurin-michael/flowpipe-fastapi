from pathlib import Path
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    cookie_file: str = "cookies.txt"
    download_dir: str = "downloads"

    model_config = {
        "env_file": _PROJECT_ROOT / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cookie_file_path(self) -> Path:
        """Путь к файлу куки: если относительный — от корня проекта."""
        p = Path(self.cookie_file)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p

    @property
    def download_dir_path(self) -> Path:
        """Папка загрузок: если относительный путь — от корня проекта."""
        p = Path(self.download_dir)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p


def get_settings() -> Settings:
    return Settings()
