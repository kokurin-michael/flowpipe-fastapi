import json
import mimetypes
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import StreamingResponse, FileResponse, Response

from src.config import Settings, get_settings
from src.database import get_session, SessionLocal
from src.downloader.downloader import download, extract_info
from src.downloader.models import YtDlpInfoResponse, DownloadStatusEnum, DownloadStatusResponse, DownloadProgressUpdate
from src.entities import YtDlpFile

router = APIRouter(
    tags=["Загрузка"],
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
                    "examples": {
                        "default": {
                            "value": {
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
                    }
                }
            },
        },
        400: {
            "description": "Некорректный URL. Ссылка не поддерживается (не YouTube или неверный формат).",
            "content": {
                "application/json": {
                    "examples": {"default": {
                        "value": {"detail": "Ссылки такого формата не поддерживаются. Примеры: https://youtu.be/..."}}}
                }
            },
        },
        404: {
            "description": "Файл с куками не найден или недоступен.",
            "content": {
                "application/json": {"examples": {"default": {"value": {"detail": "Файл с куки не существует: ..."}}}}},
        },
        422: {
            "description": "Ошибка валидации: не передан параметр url или передан в неверном формате.",
        },
        500: {
            "description": "Ошибка при обращении к YouTube/yt-dlp: видео недоступно, приватное, удалено или сетевая ошибка.",
            "content": {"application/json": {
                "examples": {"default": {"value": {"detail": "Не удалось получить информацию о видео."}}}}},
        },
    },
)
def extract_info_handler(
        url: str = Query(
            ...,
            description="Ссылка на видео YouTube. Допустимые форматы: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID.",
            examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
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
    summary="Запустить загрузку видео/аудио на сервер",
    description="""
Запускает фоновую загрузку выбранного формата (или комбинации видео+аудио) в папку на сервере (см. настройку download_dir). Возвращает идентификатор задачи для опроса прогресса через GET `/download/status/{download_id}`.

**Параметры форматов:**
- **audio_format_id** — идентификатор аудио-формата из `extract_info.formats` (например `140` — m4a 128kbps). Опционально, если передан только **video_format_id** (тогда скачается только видео без звука).
- **video_format_id** — идентификатор видео-формата (например `137` — 1080p, `22` — 720p с аудио). Опционально, если передан только **audio_format_id** (тогда скачается только аудио).
- **Оба опциональны, но хотя бы один обязателен.** Если переданы оба — скачивается видео + аудио и склеивается в один файл (требуется ffmpeg).

**Типичные format_id (YouTube):** 22 (720p mp4), 137 (1080p video), 140 (m4a 128kbps), 251 (opus 160k). Точный список возвращает `/extract_info`.

**Ответ:** JSON с полем `download_id`. Опрашивайте GET `/download/status/{download_id}` для получения прогресса в процентах и статуса (pending / downloading / ready).
    """,
    responses={
        200: {
            "description": "Успешно. Возвращается объект с полем download_id (строка). Используйте его для опроса GET /download/status/{download_id}.",
            "content": {"application/json": {"examples": {"default": {"value": {"download_id": "a1b2c3d4e5f6..."}}}}},
        },
        400: {
            "description": "Не указан ни один формат: нужно передать хотя бы audio_format_id или video_format_id.",
            "content": {
                "application/json": {
                    "examples": {"default": {"value": {
                        "detail": "Укажите хотя бы один из параметров: audio_format_id или video_format_id."}}}
                }
            },
        },
        404: {
            "description": "Указанный format_id не найден в списке форматов видео, либо некорректный URL, либо файл с куками не найден. В detail приходит текст ошибки.",
            "content": {
                "application/json": {
                    "examples": {"default": {
                        "value": {"detail": "audio_format_id '999' не найден в списке форматов этого видео."}}}
                }
            },
        },
        422: {
            "description": "Ошибка валидации параметров (отсутствует url и т.п.).",
        },
        500: {
            "description": "Ошибка при скачивании: yt-dlp/ffmpeg недоступны, видео недоступно или сетевая ошибка.",
            "content": {
                "application/json": {"examples": {"default": {"value": {"detail": "Ошибка при скачивании видео."}}}}},
        },
    },
)
def download_handler(
        url: str = Query(
            ...,
            description="Ссылка на видео YouTube (те же форматы, что и в /extract_info).",
            examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        ),
        audio_format_id: Optional[str] = Query(
            None,
            description="Идентификатор аудио-формата из списка formats (например 140, 251). Опционально, если передан video_format_id.",
            examples=["140"],
        ),
        video_format_id: Optional[str] = Query(
            None,
            description="Идентификатор видео-формата из списка formats (например 22, 137, 160). Опционально, если передан audio_format_id.",
            examples=["137"],
        ),
        settings: Settings = Depends(get_settings),
        session: Session = Depends(get_session),
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

    download_id = uuid.uuid4().hex
    download_dir = settings.download_dir_path
    ext = fmt.ext

    yt_dlp_file = YtDlpFile(
        id=download_id,
        progress=0.0,
        status=DownloadStatusEnum.PENDING,
        file_path=None,
        description=info.description,
        extension=ext,
        thumbnails=[t.model_dump() for t in (info.thumbnails or [])],
    )
    session.add(yt_dlp_file)
    session.commit()

    def progress_callback(update: DownloadProgressUpdate):
        progress_callback_session = SessionLocal()
        try:
            row = progress_callback_session.get(YtDlpFile, download_id)
            if row is not None:
                row.status = update.status
                row.progress = update.progress
                if update.file_path is not None:
                    row.file_path = update.file_path
                progress_callback_session.commit()
        finally:
            progress_callback_session.close()

    try:
        threading.Thread(
            target=download,
            kwargs={
                "url": url,
                "cookies_file_path": str(settings.cookie_file_path),
                "format_selector": format_selector,
                "download_dir": str(download_dir),
                "progress_callback": progress_callback
            },
            daemon=True,
        ).start()
        return {"download_id": download_id}
    except Exception as e:
        yt_dlp_file.status = DownloadStatusEnum.FAILURE
        session.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при запуске загрузки: {e!s}",
        )


@router.get(
    "/download/status/{download_id}",
    response_model=DownloadStatusResponse,
    summary="Получить прогресс и статус загрузки",
    description="""
Возвращает текущий прогресс загрузки в процентах и статус по идентификатору задачи, полученному из ответа GET `/download`.

**Поля ответа:**
- **progress** — прогресс в процентах (0–100). 0 до начала и в начале загрузки, 100 по завершении.
- **status** — статус: `pending` (задача создана), `downloading` (идёт скачивание), `ready` (загрузка завершена), `failure` (ошибка).

**Использование:** после вызова GET `/download` получите `download_id` и опрашивайте этот эндпоинт, пока `status` не станет `ready` или `failure`. Для лайф-обновлений используйте GET `/download/status/{download_id}/stream` (SSE).
    """,
    responses={
        200: {
            "description": "Успешно. Возвращается объект с полями progress (0–100) и status (pending | downloading | ready | failure).",
            "content": {
                "application/json": {
                    "examples": {"default": {"value": {"progress": 45.5, "status": "downloading"}}}
                }
            },
        },
        404: {
            "description": "Загрузка с указанным download_id не найдена (неверный id или запись уже удалена).",
            "content": {"application/json": {"examples": {"default": {"value": {"detail": "Загрузка не найдена."}}}}},
        },
    },
)
def download_status_handler(
        download_id: str,
        session: Session = Depends(get_session),
) -> DownloadStatusResponse:
    task = session.get(YtDlpFile, download_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Загрузка не найдена.")
    return DownloadStatusResponse(
        progress=float(task.progress),
        status=DownloadStatusEnum(task.status),
    )


@router.get(
    "/download/file/{download_id}",
    summary="Скачать файл по идентификатору загрузки (с поддержкой паузы и возобновления)",
    description="""
Возвращает файл по идентификатору задачи загрузки (`download_id`). Файл доступен только после завершения загрузки (статус `ready`).

**Поддержка паузы и возобновления:** эндпоинт поддерживает HTTP Range-запросы (RFC 7233). Клиент может передавать заголовок `Range: bytes=start-end` и получать ответ `206 Partial Content` с запрошенным диапазоном байт. Это позволяет:
- приостанавливать и возобновлять загрузку;
- перематывать воспроизведение в плеере без докачки с начала.

Без заголовка `Range` возвращается весь файл (статус 200). В ответе всегда присутствует заголовок `Accept-Ranges: bytes`.

**Использование:** убедитесь, что загрузка завершена (GET `/download/status/{download_id}` → `status: ready`), затем запрашивайте GET `/download/file/{download_id}`. Для возобновления передайте, например, `Range: bytes=1024-`.
    """,
    responses={
        200: {
            "description": "Успешно. Возвращается весь файл (тело — бинарный поток).",
        },
        206: {
            "description": "Частичное содержимое. Запрос с заголовком Range выполнен успешно, в теле — запрошенный диапазон байт.",
        },
        404: {
            "description": "Файл не найден: загрузка с указанным download_id отсутствует, ещё не завершена (не ready), либо файл на диске удалён.",
            "content": {
                "application/json": {
                    "examples": {
                        "default": {"value": {"detail": "Файл не найден или ещё не готов."}},
                        "not_on_disk": {"value": {"detail": "Файл на диске не найден."}},
                    }
                }
            },
        },
        416: {
            "description": "Диапазон не выполним. Заголовок Range задан некорректно (например, start больше размера файла).",
            "content": {
                "application/json": {
                    "examples": {"default": {"value": {"detail": "Запрошенный диапазон байт не выполним."}}}
                }
            },
        },
        500: {
            "description": "Внутренняя ошибка при чтении файла или разборе Range.",
            "content": {
                "application/json": {
                    "examples": {"default": {"value": {"detail": "Ошибка при отдаче файла."}}}
                }
            },
        },
    },
)
def get_download_by_id(
    download_id: str,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """
    Отдаёт файл по download_id с поддержкой Range (пауза/возобновление).
    """
    # Проверка существования записи и готовности файла
    yt_dlp_file = session.get(YtDlpFile, download_id)
    file_path = yt_dlp_file.file_path if yt_dlp_file else None
    if yt_dlp_file is None or yt_dlp_file.status != "ready" or not file_path:
        raise HTTPException(status_code=404, detail="Файл не найден или ещё не готов.")

    try:
        path = Path(file_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при отдаче файла.")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл на диске не найден.")

    # Безопасность: файл должен находиться внутри директории загрузок
    try:
        path.resolve().relative_to(settings.download_dir_path.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Файл не найден или ещё не готов.")

    try:
        size = path.stat().st_size
    except OSError:
        raise HTTPException(status_code=500, detail="Ошибка при отдаче файла.")

    # Определяем MIME-тип по расширению
    media_type, _ = mimetypes.guess_type(path.name)
    if not media_type:
        media_type = "application/octet-stream"

    range_header = request.headers.get("range")

    # Запрос без Range — отдаём весь файл (200)
    if not range_header or not range_header.startswith("bytes="):
        return FileResponse(path, media_type=media_type, filename=path.name)

    # Парсинг Range: "bytes=start-end" или "bytes=start-"
    try:
        parts = range_header.replace("bytes=", "").strip().split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else size - 1
    except (ValueError, IndexError):
        return Response(
            status_code=416,
            content=json.dumps({"detail": "Запрошенный диапазон байт не выполним."}),
            media_type="application/json",
            headers={"Content-Range": f"bytes */{size}"},
        )
    end = min(end, size - 1)
    if start > end or start < 0:
        return Response(
            status_code=416,
            content=json.dumps({"detail": "Запрошенный диапазон байт не выполним."}),
            media_type="application/json",
            headers={"Content-Range": f"bytes */{size}"},
        )

    # Генератор: читаем и отдаём только запрошенный диапазон байт
    def iterfile():
        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                chunk_size = 64 * 1024
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        except OSError:
            # При ошибке чтения во время стрима цикл прерывается — клиент может получить неполные данные
            return

    return StreamingResponse(
        iterfile(),
        status_code=206,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(end - start + 1),
        },
    )

#
# @router.get(
#     "/download/status/{download_id}/stream",
#     summary="Стрим статуса загрузки (SSE)",
#     description="""
# Подписка на обновления прогресса и статуса загрузки в реальном времени через Server-Sent Events (SSE).
# Клиент получает поток событий `data: {"progress": ..., "status": ...}` с интервалом ~1 с до перехода статуса в `ready` или `failure`.
#
# **Формат:** текст `text/event-stream`, каждое событие — строка `data: {json}\n\n`. Поля: **progress** (0–100), **status** (pending | downloading | ready | failure). file_path не отдаётся.
#
# **Использование:** откройте GET `/download/status/{download_id}/stream` и читайте события (EventSource в браузере или поток в клиенте).
#     """,
#     responses={
#         200: {
#             "description": "Поток SSE-событий с полями progress и status до завершения загрузки.",
#         },
#         404: {
#             "description": "Загрузка с указанным download_id не найдена.",
#         },
#     },
# )
# def download_status_stream_handler(download_id: str):
#     def _sse_status_stream(download_id: str, poll_interval: float = 1.0):
#         """Генератор SSE-событий: прогресс и статус загрузки (без file_path). Останавливается при ready/failure или отсутствии задачи."""
#         while True:
#             session = SessionLocal()
#             try:
#                 task = session.get(DownloadTask, download_id)
#                 if task is None:
#                     yield f"data: {json.dumps({'error': 'Загрузка не найдена.'})}\n\n"
#                     return
#                 payload = {"progress": task.progress, "status": task.status}
#                 yield f"data: {json.dumps(payload)}\n\n"
#                 if task.status in (DownloadStatusEnum.READY.value, DownloadStatusEnum.FAILURE.value):
#                     return
#             finally:
#                 session.close()
#             time.sleep(poll_interval)
#
#     session = SessionLocal()
#     try:
#         task = session.get(DownloadTask, download_id)
#         if task is None:
#             raise HTTPException(status_code=404, detail="Загрузка не найдена.")
#     finally:
#         session.close()
#     return StreamingResponse(
#         _sse_status_stream(download_id),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no",
#         },
#     )
