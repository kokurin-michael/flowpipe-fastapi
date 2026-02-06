from typing import Any, Optional, Callable
from pydantic import BaseModel, Field, model_validator
from enum import StrEnum
from typing import Union


class DownloadStatusEnum(StrEnum):
    """Статус загрузки: ожидание, в процессе, готово, ошибка."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    READY = "ready"
    FAILURE = "failure"


class DownloadStatusResponse(BaseModel):
    """Прогресс и статус загрузки (без file_path) для GET и SSE эндпоинтов."""

    progress: float = Field(
        ...,
        ge=0,
        le=100,
        description="Прогресс загрузки в процентах (0–100). До начала загрузки 0, по завершении 100.",
    )
    status: DownloadStatusEnum = Field(
        ...,
        description="Статус: pending — задача создана; downloading — идёт скачивание; ready — загрузка завершена; failure — ошибка.",
    )


class DownloadProgressUpdate(BaseModel):
    """Одно обновление прогресса загрузки для progress_callback."""

    status: DownloadStatusEnum = Field(
        ...,
        description="Текущий статус: pending, downloading, ready, failure.",
    )
    progress: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Прогресс в процентах (0–100).",
    )
    file_path: str | None = Field(
        default=None,
        description="Путь к файлу после успешной загрузки (заполняется при status=ready).",
    )


ProgressCallback = Callable[[DownloadProgressUpdate], None]


class ProtocolEnum(StrEnum):
    HTTPS = "https"
    HTTP = "http"
    M3U8_NATIVE = "m3u8_native"
    M3U8 = "m3u8"
    MHTML = "mhtml"
    RTMP = "rtmp"
    RTMPE = "rtmpe"
    RTMPS = "rtmps"
    RTMPT = "rtmpt"
    RTMPTE = "rtmpte"
    WS = "ws"
    WSS = "wss"
    F4M = "f4m"


class FormatItem(BaseModel):
    """Один формат: только поля, используемые в downloader."""

    format_id: str = Field(
        ...,
        description="Внутренний идентификатор формата у экстрактора (напр. 22, 251, sb2). По нему и format_note отфильтровывают сториборды (sb*).",
    )
    format_note: Optional[str] = Field(None, description="Пометка формата: 720p, 128kbps, storyboard и т.д.")
    ext: Optional[str] = Field(None, description="Расширение/контейнер: mp4, webm, m4a и т.д.")
    protocol: Optional[Union[ProtocolEnum, str]] = Field(None, description="Протокол выдачи.")
    url: Optional[str] = Field(None, description="Прямая ссылка на медиа для скачивания.")
    filesize_approx: Optional[int] = Field(None, description="Примерный размер файла в байтах.")
    http_headers: Optional[dict[str, str]] = Field(
        None,
        description="Заголовки для запроса по url (User-Agent, Cookie и т.д.).",
    )


class ThumbnailItem(BaseModel):
    """Один вариант превью."""

    url: str = Field(..., description="URL картинки превью.")
    width: Optional[int] = Field(None, description="Ширина превью в пикселях.")
    height: Optional[int] = Field(None, description="Высота превью в пикселях.")


class YtDlpInfoResponse(BaseModel):
    """Ответ yt-dlp extract_info(): только поля из списка в downloader."""

    id: str = Field(..., description="Идентификатор видео на платформе.")
    title: str = Field(..., description="Название видео.")
    formats: list[FormatItem] = Field(default_factory=list, description="Доступные форматы.")
    thumbnails: Optional[list[ThumbnailItem]] = Field(None, description="Превью разного размера.")
    description: Optional[str] = Field(None, description="Текст описания под видео.")
    duration: Optional[float] = Field(
        None,
        description="Длительность видео в секундах. Берётся из корня или из formats[].fragments[].duration.",
    )

    @model_validator(mode="before")
    @classmethod
    def set_duration_from_fragments(cls, data: Any) -> Any:
        """Если в сырых данных нет duration — считаем из первого формата с fragments."""
        if not isinstance(data, dict):
            return data
        if data.get("duration") is not None:
            return data
        for fmt in data.get("formats") or []:
            frags = fmt.get("fragments") or []
            if not frags:
                continue
            total = sum((f.get("duration") or 0) for f in frags)
            if total > 0:
                data = {**data, "duration": total}
                break
        return data
