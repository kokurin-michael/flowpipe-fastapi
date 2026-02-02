from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from starlette.responses import StreamingResponse

from src.config import Settings, get_settings
from src.downloader.downloader import download, extract_info

router = APIRouter(tags=[''])


@router.get('/extract_info', name='')
def extract_info_handler(url: str, settings: Settings = Depends(get_settings)):
    return extract_info(url, str(settings.cookie_file_path))


@router.get('/download', name='')
def download_handler(
        url: str,
        audio_format_id: Optional[str] = None,
        video_format_id: Optional[str] = None,
        settings: Settings = Depends(get_settings),
):
    # Хотя бы один формат должен быть указан
    if not audio_format_id and not video_format_id:
        raise HTTPException(
            400,
            "Provide at least one of audio_format_id or video_format_id",
        )

    info = extract_info(url, str(settings.cookie_file_path))
    format_ids = {f.format_id for f in info.formats}

    if audio_format_id and audio_format_id not in format_ids:
        raise HTTPException(404, f"audio_format_id '{audio_format_id}' not found in formats")
    if video_format_id and video_format_id not in format_ids:
        raise HTTPException(404, f"video_format_id '{video_format_id}' not found in formats")

    # Селектор: оба / только видео / только аудио
    if video_format_id and audio_format_id:
        format_selector = f"{video_format_id}+{audio_format_id}"
        fmt_id = video_format_id
    elif video_format_id:
        format_selector = video_format_id
        fmt_id = video_format_id
    else:
        format_selector = audio_format_id
        fmt_id = audio_format_id

    fmt = next((f for f in info.formats if f.format_id == fmt_id), None)
    if not fmt:
        raise HTTPException(404, f"format_id {fmt_id} not found")

    ext = fmt.ext or "bin"
    format_note = fmt.format_note or fmt_id
    filename = f"{info.id}_{format_note}.{ext}"

    return StreamingResponse(
        download(url, str(settings.cookie_file_path), format_selector),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
