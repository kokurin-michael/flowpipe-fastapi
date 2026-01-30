from typing import Any, Dict, List
from src.extractor.models import ExtractData, ExtractFormatEnum, ExtractDataItem

def _to_yt_video_quality_label(fmt: Dict[str, Any]) -> str:
    w = fmt.get("width")
    h = fmt.get("height")
    fps = fmt.get("fps")
    if w and h:
        base = f"{w}x{h}"
    else:
        base = fmt.get("resolution") or "unknown"
    return f"{base}@{int(fps)}" if fps else base


def _to_yt_audio_quality_label(fmt: Dict[str, Any]) -> str:
    abr = fmt.get("abr") or fmt.get("tbr")
    ext = fmt.get("ext") or "audio"
    if abr:
        return f"{ext} {int(round(abr))}kbps"
    return ext


def to_yt_video_extra(info: Dict[str, Any]) -> ExtractData:
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
                    format=ExtractFormatEnum.VIDEO,
                    quality=_to_yt_video_quality_label(fmt),
                    url=url,
                    headers=dict(fmt.get("http_headers") or {}),
                )
            )
        elif is_audio:
            data.append(
                ExtractDataItem(
                    format=ExtractFormatEnum.AUDIO,
                    quality=_to_yt_audio_quality_label(fmt),
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
                format=ExtractFormatEnum.THUMBNAIL,
                quality=str(quality),
                url=th_url,
                headers=None,
            )
        )

    description = info.get("description") or None
    return ExtractData(data=data, description=description)