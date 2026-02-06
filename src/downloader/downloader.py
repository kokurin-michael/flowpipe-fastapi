import re
import subprocess
import sys
from typing import Callable, Optional

from yt_dlp import YoutubeDL
from pathlib import Path

from src.downloader.models import YtDlpInfoResponse, DownloadStatusEnum, DownloadStatusResponse, ProgressCallback, \
    DownloadProgressUpdate

_YT_VIDEO_RE = re.compile(
    r'^https?://(?:www\.)?'
    r'(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)'
    r'[\w-]{11}'  # 11-символьный ID
    r'(?:[?&#].*)?$',
    re.IGNORECASE
)


def validate_supported_url(url: str):
    if not bool(url and _YT_VIDEO_RE.match(url.strip())):
        raise ValueError(
            'Ссылки такого формата не поддерживаются. '
            'Примеры поддерживаемых форматов: '
            'https://youtu.be/7QA-q4i2ifY?si=oZo0IWUi7JAqGwnj, '
            'https://www.youtube.com/watch?v=7QA-q4i2ifY, '
            'https://www.youtube.com/shorts/qTlH6ZuqYKo, '
            'https://youtube.com/shorts/qTlH6ZuqYKo?si=skSxdlNJ9liVQDDc'
        )


def extract_info(url: str, cookies_file_path: str):
    validate_supported_url(url)
    validate_cookies_file(Path(cookies_file_path))

    opt = {
        'cookiefile': cookies_file_path
    }

    with YoutubeDL(opt) as yt:
        return YtDlpInfoResponse.model_validate(yt.extract_info(url=url, download=False))


def download(
        url: str,
        cookies_file_path: str,
        format_selector: str,
        download_dir: str,
        progress_callback: ProgressCallback
):
    """
    Скачивает видео в download_dir.
    Либо обновляет progress_state (dict), либо запись в БД по download_id (если передан db_engine и download_id).
    При успехе в БД пишется expected_file_path; при ошибке — status FAILURE.
    """
    validate_supported_url(url)
    validate_cookies_file(Path(cookies_file_path))

    def progress_hook(info: dict):
        """Обновляет progress_state по данным из yt-dlp progress_hook."""
        status = info.get("status")
        filename = info.get("filename") if info.get("filename") is not None else info.get("tmpfilename")

        if status == "downloading":
            total = info.get("total_bytes") or info.get("total_bytes_estimate")
            downloaded = info.get("downloaded_bytes")
            if total and downloaded is not None and total > 0:
                progress_callback(DownloadProgressUpdate(status=DownloadStatusEnum.DOWNLOADING,
                                                         progress=min(100.0, round(100.0 * downloaded / total, 1)),
                                                         file_path=filename))
            elif "_percent_str" in info and info["_percent_str"]:
                try:
                    progress_callback(DownloadProgressUpdate(status=DownloadStatusEnum.DOWNLOADING,
                                                             progress=float(info["_percent_str"].rstrip("%")),
                                                             file_path=filename))
                except (ValueError, TypeError):
                    pass
        elif status == "finished":
            filename = re.sub(r"(\.[\w-]+)+(?=\.\w+$)", "", filename)
            progress_callback(
                DownloadProgressUpdate(status=DownloadStatusEnum.READY, progress=100.0, file_path=filename))

    opt = {
        "format": format_selector,
        "cookiefile": cookies_file_path,
        "outtmpl": {
            "default": f"{download_dir}/%(id)s/{format_selector}.%(ext)s"
        },
        "progress_hooks": [progress_hook],
        "remote_components": ["ejs:github"],
    }

    try:
        progress_callback(DownloadProgressUpdate(status=DownloadStatusEnum.PENDING, progress=0.0))

        with YoutubeDL(opt) as yt:
            yt.download(url)
    except Exception:
        progress_callback(DownloadProgressUpdate(status=DownloadStatusEnum.FAILURE, progress=0.0))


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


def validate_cookies_file(cookies_file_path: Path):
    # Проверка на существование файла
    if not cookies_file_path or not cookies_file_path.exists() or not cookies_file_path.is_file():
        raise FileNotFoundError(f"Файл с куки не существует: {cookies_file_path}")

    # Проверка на пустой файл
    if cookies_file_path.stat().st_size == 0:
        raise ValueError(f"Файл с куки пустой: {cookies_file_path}")

    # Проверка на наличие валидных куки (попробуем прочитать первые строки файла)
    try:
        with open(cookies_file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # Простейшая проверка на содержание куки, это может быть более сложная валидация
            if not first_line or not first_line.startswith("# Netscape HTTP Cookie File"):
                raise ValueError(f"Неверный формат файла с куки: {cookies_file_path}")
    except Exception as e:
        raise IOError(f"Ошибка при чтении файла с куки: {cookies_file_path} - {str(e)}")


def upgrade_version():
    # текущая версия yt-dlp
    try:
        current = subprocess.check_output(
            ["yt-dlp", "--version"],
            text=True
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        # yt-dlp не установлен / недоступен или команда вернула ошибку
        current = None

    # последняя версия из PyPI
    try:
        pip_out = subprocess.check_output(
            [sys.executable, "-m", "pip", "index", "versions", "yt-dlp"],
            text=True
        )
        # пример строки (pip): "Available versions: 2025.12.8, 2025.11.12, ..."
        m = re.search(r"available versions:\s*([0-9][0-9A-Za-z.\-]*)", pip_out, flags=re.IGNORECASE)
        latest = m.group(1).strip() if m else None
    except (subprocess.CalledProcessError, IndexError):
        # pip не смог получить список версий или формат вывода изменился
        latest = None

    if not current or not latest:
        # если не смогли определить версии — просто пробуем обновиться
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        return

    if current != latest:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])

# def _progress_hook(progress_state: dict, info: dict) -> None:
#     """Обновляет progress_state по данным из yt-dlp progress_hook."""
#     status = info.get("status")
#     if status == "downloading":
#         progress_state["status"] = DownloadStatusEnum.DOWNLOADING
#         total = info.get("total_bytes") or info.get("total_bytes_estimate")
#         downloaded = info.get("downloaded_bytes")
#         if total and downloaded is not None and total > 0:
#             progress_state["progress"] = min(100.0, round(100.0 * downloaded / total, 1))
#         elif "_percent_str" in info and info["_percent_str"]:
#             try:
#                 progress_state["progress"] = float(info["_percent_str"].rstrip("%"))
#             except (ValueError, TypeError):
#                 pass
#     elif status == "finished":
#         progress_state["status"] = DownloadStatusEnum.READY
#         progress_state["progress"] = 100.0


# def _update_db(
#         db_engine: Any,
#         download_id: str,
#         progress: float,
#         status: str,
#         file_path: str | None = None,
# ) -> None:
#     """Обновляет запись DownloadTask в БД (вызывается из потока загрузки)."""
#     session = Session(bind=db_engine)
#     try:
#         task = session.get(DownloadTask, download_id)
#         if task:
#             task.progress = progress
#             task.status = status
#             if file_path is not None:
#                 task.file_path = file_path
#             session.commit()
#     finally:
#         session.close()
#
#
# def _progress_hook_db(
#         info: dict,
#         update_fn: Any,
#         expected_file_path: str | None,
# ) -> None:
#     """Progress hook: извлекает прогресс из info и вызывает update_fn(progress, status, file_path)."""
#     status = info.get("status")
#     if status == "downloading":
#         progress = 0.0
#         total = info.get("total_bytes") or info.get("total_bytes_estimate")
#         downloaded = info.get("downloaded_bytes")
#         if total and downloaded is not None and total > 0:
#             progress = min(100.0, round(100.0 * downloaded / total, 1))
#         elif "_percent_str" in info and info["_percent_str"]:
#             try:
#                 progress = float(info["_percent_str"].rstrip("%"))
#             except (ValueError, TypeError):
#                 pass
#         update_fn(progress, DownloadStatusEnum.DOWNLOADING, None)
#     elif status == "finished":
#         update_fn(100.0, DownloadStatusEnum.READY, expected_file_path)


# def download(
#         url: str,
#         cookies_file_path: str,
#         format_selector: str,
#         chunk_size: int = 512 * 1024
# ):
#     validate_supported_url(url)
#     validate_cookies_file(Path(cookies_file_path))
#
#     cmd = [
#         "yt-dlp", "-f", format_selector,
#         "--cookies", cookies_file_path,
#         "-o", "-", "--no-part", "--quiet",
#         url,
#     ]
#     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=chunk_size)
#
#     try:
#         while True:
#             chunk = proc.stdout.read(chunk_size)
#             if not chunk:
#                 break
#             yield chunk
#     finally:
#         proc.wait()

# def extract_video_id(url: str) -> str:
#     """Достаёт 11-символьный id видео из валидного YouTube URL."""
#     url = url.strip()
#     match = _YT_VIDEO_RE.match(url)
#     if not match:
#         raise ValueError("Недопустимый URL")
#     # Id — 11 символов: в youtu.be/ID, в watch?v=ID или в shorts/ID
#     for pattern in (r"(?:youtu\.be/)([\w-]{11})", r"(?:[?&]v=)([\w-]{11})", r"(?:/shorts/)([\w-]{11})"):
#         m = re.search(pattern, url, re.IGNORECASE)
#         if m:
#             return m.group(1)
#     raise ValueError("В URL не найден video id")
