import re
import subprocess
import sys
from yt_dlp import YoutubeDL
from src.extractor.models import UrlOwnerEnum
from src.extractor.url import get_url_owner
from src.extractor.mappers import to_yt_video_extra
from src.extractor.exceptions import UrlError


def _upgrade_version_if_needed():
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


def extract(url: str):
    owner = get_url_owner(url)

    opt = {
       # 'cookiefile': ''
    }

    _upgrade_version_if_needed()

    with YoutubeDL(opt) as yt:
        info = yt.extract_info(url=url, download=False)

        if owner == UrlOwnerEnum.YOUTUBE:
            return to_yt_video_extra(info)
        else:
            raise UrlError('Не найден маппер для ссылки')
