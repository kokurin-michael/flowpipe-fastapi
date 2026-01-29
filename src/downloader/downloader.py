from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse
from yt_dlp import YoutubeDL
from src.downloader.models import ExtractMappedData, ExtractFormatKind, ExtractDataItem
from src.downloader.constants import YT_VIDEO_ID_RE
from src.downloader.exceptions import YouTubeUrlError


def _map_video_quality_label(fmt: Dict[str, Any]) -> str:
    w = fmt.get("width")
    h = fmt.get("height")
    fps = fmt.get("fps")
    if w and h:
        base = f"{w}x{h}"
    else:
        base = fmt.get("resolution") or "unknown"
    return f"{base}@{int(fps)}" if fps else base


def _map_audio_quality_label(fmt: Dict[str, Any]) -> str:
    abr = fmt.get("abr") or fmt.get("tbr")
    ext = fmt.get("ext") or "audio"
    if abr:
        return f"{ext} {int(round(abr))}kbps"
    return ext


def _map_extract_info(info: Dict[str, Any]) -> ExtractMappedData:
    data: List[ExtractDataItem] = []

    # formats (video/audio)
    for fmt in info.get("formats", []):
        url = fmt.get("url")
        if not url:
            # "missing a url" — такие пропускаем
            continue

        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")

        is_video = vcodec not in (None, "none")
        is_audio = (not is_video) and acodec not in (None, "none")

        # пропускаем "storyboard" / служебные штуки
        format_id = fmt.get("format_id", "")
        if str(format_id).startswith("sb"):
            continue

        if is_video:
            data.append(
                ExtractDataItem(
                    format=ExtractFormatKind.VIDEO,
                    quality=_map_video_quality_label(fmt),
                    url=url,
                    headers=dict(fmt.get("http_headers") or {}),
                )
            )
        elif is_audio:
            data.append(
                ExtractDataItem(
                    format=ExtractFormatKind.AUDIO,
                    quality=_map_audio_quality_label(fmt),
                    url=url,
                    headers=dict(fmt.get("http_headers") or {}),
                )
            )

    # thumbnails
    # у yt-dlp thumbnails — список {url, width, height, ...}
    for th in info.get("thumbnails", []) or []:
        th_url = th.get("url")
        if not th_url:
            continue
        w = th.get("width")
        h = th.get("height")
        quality = f"{w}x{h}" if w and h else (th.get("id") or "thumbnail")

        data.append(
            ExtractDataItem(
                format=ExtractFormatKind.THUMBNAIL,
                quality=str(quality),
                url=th_url,
                headers=None,
            )
        )

    description = info.get("description") or None
    return ExtractMappedData(data=data, description=description)


def _is_youtube_host(host: str) -> bool:
    host = host.lower().strip()

    return host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "www.youtube-nocookie.com",
        "youtube-nocookie.com",
    }


def _extract_video_id_from_parsed(parsed) -> Optional[str]:
    """Extract 11-char YouTube video id from a parsed URL (no playlist)."""
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    q = parse_qs(parsed.query or "")

    # Hard reject playlist-style URLs and any URL that includes list=...
    # We treat `watch?v=...&list=...` as playlist context -> reject.
    if "list" in q:
        return None
    if path.startswith("/playlist") or path.startswith("/mix"):
        return None

    # youtu.be/<id>
    if host.endswith("youtu.be"):
        vid = path.lstrip("/").split("/")[0]
        return vid or None

    # Standard watch: /watch?v=<id>
    if path == "/watch":
        vid = (q.get("v") or [None])[0]
        return vid

    # Shorts: /shorts/<id>
    if path.startswith("/shorts/"):
        return path.split("/shorts/", 1)[1].split("/", 1)[0] or None

    # Embed: /embed/<id>
    if path.startswith("/embed/"):
        return path.split("/embed/", 1)[1].split("/", 1)[0] or None

    # Legacy: /v/<id>
    if path.startswith("/v/"):
        return path.split("/v/", 1)[1].split("/", 1)[0] or None

    # Live: /live/<id>
    if path.startswith("/live/"):
        return path.split("/live/", 1)[1].split("/", 1)[0] or None

    # Attribution links sometimes wrap the real URL in `u=`.
    # Example: /attribution_link?...&u=%2Fwatch%3Fv%3D<id>%26feature%3Dshare
    if path == "/attribution_link":
        u = (q.get("u") or [None])[0]
        if u:
            inner = urlparse(unquote(u))
            # inner may be relative; normalize it as a youtube.com URL
            inner_parsed = urlparse(f"https://www.youtube.com{inner.path}?{inner.query}")
            return _extract_video_id_from_parsed(inner_parsed)

    return None


def _check_is_available_url(url: str) -> str:
    """Validate that `url` is a YouTube *single video* URL (not a playlist).

    Returns a normalized watch URL (https://www.youtube.com/watch?v=<id>)
    or raises YouTubeUrlError.
    """
    if not isinstance(url, str) or not url.strip():
        raise YouTubeUrlError("URL is empty")

    candidate = url.strip()
    parsed = urlparse(candidate)

    # Allow users to pass URLs without scheme.
    if not parsed.scheme and parsed.netloc == "":
        parsed = urlparse("https://" + candidate)

    if parsed.scheme not in {"http", "https"}:
        raise YouTubeUrlError("Only http/https URLs are supported")

    if not _is_youtube_host(parsed.netloc):
        raise YouTubeUrlError("Not a YouTube URL")

    vid = _extract_video_id_from_parsed(parsed)
    if not vid:
        raise YouTubeUrlError("Not a supported single-video YouTube URL (or playlist detected)")

    if not YT_VIDEO_ID_RE.match(vid):
        raise YouTubeUrlError("Invalid YouTube video id")

    # Normalize to a canonical watch URL.
    return f"https://www.youtube.com/watch?v={vid}"


def extract(url: str) -> ExtractMappedData:
    normalized = _check_is_available_url(url)
    with YoutubeDL() as yt:
        return _map_extract_info(yt.extract_info(url=normalized, download=False))
