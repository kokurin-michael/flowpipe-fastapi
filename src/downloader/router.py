import asyncio
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from starlette.responses import StreamingResponse

from src.config import Settings, get_settings
from src.downloader.downloader import download, extract_info
from src.downloader.models import YtDlpInfoResponse

router = APIRouter(
    tags=["Загрузка (YouTube)"],
    prefix="",
)


@router.get(
    "/extract_info",
    response_model=YtDlpInfoResponse,
    summary="Получить метаданные и список форматов видео",
    description="""
Возвращает информацию о видео по ссылке YouTube: название, идентификатор, список доступных форматов (видео/аудио) и превью.

**Для чего нужно:** перед скачиванием вызовите этот метод, чтобы получить список `formats` и подставить нужные `format_id` в эндпоинт `/download`.

**Поддерживаемые ссылки:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
    """,
    responses={
        200: {
            "description": "Успешно. Возвращается объект с полями: id, title, formats, thumbnails, description, duration.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "dQw4w9WgXcQ",
                        "title": "Название видео",
                        "formats": [
                            {"format_id": "22", "format_note": "720p", "ext": "mp4"},
                            {"format_id": "140", "format_note": "128kbps", "ext": "m4a"},
                        ],
                        "thumbnails": [{"url": "https://...", "width": 120, "height": 90}],
                        "description": "Описание",
                        "duration": 212.5,
                    }
                }
            },
        },
        400: {
            "description": "Некорректный URL. Ссылка не поддерживается (не YouTube или неверный формат).",
            "content": {
                "application/json": {
                    "example": {"detail": "Ссылки такого формата не поддерживаются. Примеры: https://youtu.be/..."}
                }
            },
        },
        404: {
            "description": "Файл с куками не найден или недоступен.",
            "content": {"application/json": {"example": {"detail": "Файл с куки не существует: ..."}}},
        },
        422: {
            "description": "Ошибка валидации: не передан параметр url или передан в неверном формате.",
        },
        500: {
            "description": "Ошибка при обращении к YouTube/yt-dlp: видео недоступно, приватное, удалено или сетевая ошибка.",
            "content": {"application/json": {"example": {"detail": "Не удалось получить информацию о видео."}}},
        },
    },
)
def extract_info_handler(
        url: str = Query(
            ...,
            description="Ссылка на видео YouTube. Допустимые форматы: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID.",
            example="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ),
        settings: Settings = Depends(get_settings),
) -> YtDlpInfoResponse:
    try:
        return extract_info(url, str(settings.cookie_file_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, IOError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить информацию о видео. Проверьте ссылку и доступность видео.",
        )


@router.get(
    "/download",
    summary="Скачать видео/аудио потоком (стрим)",
    description="""
Скачивает выбранный формат (или комбинацию видео+аудио) и отдаёт файл потоком без сохранения на диск.

**Параметры форматов:**
- **audio_format_id** — идентификатор аудио-формата из `extract_info.formats` (например `140` — m4a 128kbps). Опционально, если передан только **video_format_id** (тогда скачается только видео без звука).
- **video_format_id** — идентификатор видео-формата (например `137` — 1080p, `22` — 720p с аудио). Опционально, если передан только **audio_format_id** (тогда скачается только аудио).
- **Оба опциональны, но хотя бы один обязателен.** Если переданы оба — скачивается видео + аудио и склеивается в один файл (требуется ffmpeg).

**Типичные format_id (YouTube):** 22 (720p mp4), 137 (1080p video), 140 (m4a 128kbps), 251 (opus 160k). Точный список возвращает `/extract_info`.

**Ответ:** бинарный поток (application/octet-stream). Имя файла в заголовке `Content-Disposition`.
    """,
    responses={
        200: {
            "description": "Успешно. Тело ответа — бинарный поток медиа-файла. Заголовок Content-Disposition содержит имя файла (id_формат.ext).",
        },
        400: {
            "description": "Не указан ни один формат: нужно передать хотя бы audio_format_id или video_format_id.",
            "content": {
                "application/json": {
                    "example": {"detail": "Укажите хотя бы один из параметров: audio_format_id или video_format_id."}
                }
            },
        },
        404: {
            "description": "Указанный format_id не найден в списке форматов видео, либо некорректный URL, либо файл с куками не найден. В detail приходит текст ошибки.",
            "content": {
                "application/json": {
                    "example": {"detail": "audio_format_id '999' не найден в списке форматов этого видео."}
                }
            },
        },
        422: {
            "description": "Ошибка валидации параметров (отсутствует url и т.п.).",
        },
        500: {
            "description": "Ошибка при скачивании: yt-dlp/ffmpeg недоступны, видео недоступно или сетевая ошибка.",
            "content": {"application/json": {"example": {"detail": "Ошибка при скачивании видео."}}},
        },
    },
)
def download_handler(
        url: str = Query(
            ...,
            description="Ссылка на видео YouTube (те же форматы, что и в /extract_info).",
            example="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ),
        audio_format_id: Optional[str] = Query(
            None,
            description="Идентификатор аудио-формата из списка formats (например 140, 251). Опционально, если передан video_format_id.",
            example="140",
        ),
        video_format_id: Optional[str] = Query(
            None,
            description="Идентификатор видео-формата из списка formats (например 22, 137, 160). Опционально, если передан audio_format_id.",
            example="137",
        ),
        settings: Settings = Depends(get_settings),
):
    if not audio_format_id and not video_format_id:
        raise HTTPException(
            status_code=400,
            detail="Укажите хотя бы один из параметров: audio_format_id или video_format_id.",
        )

    try:
        info = extract_info(url, str(settings.cookie_file_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, IOError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить информацию о видео. Проверьте ссылку и доступность.",
        )

    format_ids = {f.format_id for f in info.formats}
    if audio_format_id and audio_format_id not in format_ids:
        raise HTTPException(
            status_code=404,
            detail=f"audio_format_id '{audio_format_id}' не найден в списке форматов этого видео.",
        )
    if video_format_id and video_format_id not in format_ids:
        raise HTTPException(
            status_code=404,
            detail=f"video_format_id '{video_format_id}' не найден в списке форматов этого видео.",
        )

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
        raise HTTPException(status_code=404, detail=f"Формат '{fmt_id}' не найден.")

    try:
        download_id = uuid.uuid4().hex
        asyncio.create_task(
            download(url, str(settings.cookie_file_path), format_selector, str(settings.download_dir_path)))
        return download_id
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при скачивании видео.")
