import json
from pathlib import Path

from src.downloader.downloader import upgrade_version, extract_info, download


def test_extract_info():
    data = extract_info('https://youtu.be/jQhKoXhNecQ?si=96UGKVcRTwJnP6RO', '../cookies.txt')
    data
    # json.dump(data, open("file.json", "w", encoding="utf-8"))


def test_download():
    url = 'https://youtu.be/jQhKoXhNecQ?si=96UGKVcRTwJnP6RO'
    cookie_file = '../cookies.txt'
    download_dir = 'downloads'
    info = extract_info('https://youtu.be/jQhKoXhNecQ?si=96UGKVcRTwJnP6RO', cookie_file)
    format_id = info.formats[12].format_id
    download(url, cookie_file, format_id, download_dir)


def test_upgrade_version():
    upgrade_version()


if __name__ == '__main__':
    # test_extract_info()
    # test_download()
    test_upgrade_version()
