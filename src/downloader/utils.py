import subprocess
import sys
from pathlib import Path
from src.downloader.exceptions import CookiesFileError


def is_valid_cookies_file(cookies_file_path: Path):
    # Проверка на существование файла
    if not cookies_file_path or not cookies_file_path.exists() or not cookies_file_path.is_file():
        raise CookiesFileError(f"Файл с куки не существует: {cookies_file_path}")

    # Проверка на пустой файл
    if cookies_file_path.stat().st_size == 0:
        raise CookiesFileError(f"Файл с куки пустой: {cookies_file_path}")

    # Проверка на наличие валидных куки (попробуем прочитать первые строки файла)
    try:
        with open(cookies_file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # Простейшая проверка на содержание куки, это может быть более сложная валидация
            if not first_line or not first_line.startswith("# Netscape HTTP Cookie File"):
                raise CookiesFileError(f"Неверный формат файла с куки: {cookies_file_path}")
    except Exception as e:
        raise CookiesFileError(f"Ошибка при чтении файла с куки: {cookies_file_path} - {str(e)}")


def get_cookies_from_chrome(cookies_file_path: Path):
    # если зависает нужно закрыть браузер Chrome
    result = subprocess.run(
        [
            "yt-dlp",
            "--cookies-from-browser",
            "chrome",
            "--cookies",
            cookies_file_path,
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        if "You must provide at least one URL" not in result.stderr:
            result.check_returncode()


def upgrade_version():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
