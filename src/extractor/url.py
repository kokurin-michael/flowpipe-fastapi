from src.extractor.exceptions import UrlError
from src.extractor.models import UrlOwnerEnum
from urllib.parse import parse_qs, urlparse


def get_url_owner(url: str) -> UrlOwnerEnum:
    if not isinstance(url, str):
        raise UrlError("URL пустой")

    candidate = url.strip()
    if not candidate:
        raise UrlError("URL пустой")

    parsed = urlparse(candidate)

    # Разрешаем передавать URL без схемы (http/https)
    if not parsed.scheme:
        parsed = urlparse("https://" + candidate)

    if parsed.scheme not in {"http", "https"}:
        raise UrlError("Поддерживаются только http/https URL")

    host = (parsed.netloc or "").lower().strip()

    if host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }:
        path = (parsed.path or "").strip()

        # Жёстко отсекаем не-single video роуты
        lowered_path = path.lower()
        if any(
                seg in lowered_path
                for seg in (
                        "/playlist",
                        "/shorts",
                        "/live",
                        "/channel",
                        "/c/",
                        "/user/",
                        "/@",
                )
        ):
            raise UrlError("Поддерживаются только ссылки на одно видео")

        qs = parse_qs(parsed.query or "")

        # Отсекаем плейлисты/миксы (обычно list=PL... или list=RD...)
        if "list" in qs and qs.get("list"):
            raise UrlError("Плейлисты/миксы не поддерживаются")

        return UrlOwnerEnum.YOUTUBE
    else:
        raise UrlError("Неподдерживаемый сервис")
