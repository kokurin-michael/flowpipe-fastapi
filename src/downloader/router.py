from pathlib import Path

from fastapi.routing import APIRouter
from src.downloader.downloader import extract
from src.downloader.utils import upgrade_version, get_cookies_from_chrome

router = APIRouter(tags=["Downloader"])


@router.get('/extract', description='Extract all available data from url')
def extract_handler(url: str):
    return extract(url)


@router.get('/upgrade_version', description='Upgrade yt-dlp version')
def upgrade_version_handler():
    return upgrade_version()


@router.get('/get_cookies_from_chrome', description='Get cookies for yt-dlp if server run locally')
def get_cookies_from_chrome_handler(cookies_file_path: Path):
    return get_cookies_from_chrome(cookies_file_path)
